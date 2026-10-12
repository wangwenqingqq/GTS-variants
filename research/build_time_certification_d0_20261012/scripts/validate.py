#!/usr/bin/env python3
"""Check the D0 record and derivations, not a distance/index implementation."""
import argparse
import hashlib
import json
import re
from fractions import Fraction
from pathlib import Path
from urllib.parse import urlsplit

SHIP = [
    '.gitignore', 'README.md', 'CONTRACT.json', 'B0_GRAPH.md', 'C2_GRAPH.md',
    'B1_GRAPH.md', 'CANDIDATES.md', 'NUMERIC_KILL_TEST.md', 'COST_MODEL.md',
    'PRIOR_ART_MINI_GATE.md', 'DECISION.md', 'NEXT_PROTOTYPE.md',
    'CLAIM_EVIDENCE.md', 'PUBLICATION_GATE.md', 'evidence/GRAPHS.json',
    'evidence/COSTS.json', 'evidence/DECISION.json',
    'evidence/KEEPER_SOURCES.json', 'evidence/PRIMARY_SOURCES.json',
    'evidence/SOURCE_LOCATIONS.json', 'scripts/validate.py',
]
ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent.parent


def read(name):
    return json.loads((ROOT / name).read_text())


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def check(condition, message):
    if not condition:
        raise ValueError(message)


def validate_graphs():
    record = read('evidence/GRAPHS.json')
    graphs = record['graphs']
    check(set(graphs) == {'B0', 'C2', 'B1_Z'}, 'Exactly one retained B1')
    fields = {'producer', 'consumer', 'value', 'value_type', 'lifetime',
              'storage', 'synchronization', 'owner_identity'}
    for name, graph in graphs.items():
        nodes = graph['nodes']
        check(len(nodes) == len(set(nodes)), 'Duplicate graph node')
        adjacency = {node: [] for node in nodes}
        for item in graph['edges']:
            check(set(item) == fields, 'Incomplete dependency edge')
            check(all(isinstance(v, str) and v for v in item.values()),
                  'Empty edge metadata')
            check(item['producer'] in adjacency and item['consumer'] in adjacency,
                  'Unknown graph node')
            adjacency[item['producer']].append(item['consumer'])
        visiting, done = set(), set()

        def visit(node):
            check(node not in visiting, 'Cycle in a single-level graph')
            if node not in done:
                visiting.add(node)
                for child in adjacency[node]:
                    visit(child)
                visiting.remove(node)
                done.add(node)

        for node in nodes:
            visit(node)
        state_names = [s['state'] for s in graph['memory']]
        check(len(state_names) == len(set(state_names)), 'Duplicate memory state')
        for state in graph['memory']:
            check(set(state) == {'state', 'producer', 'consumer', 'cardinality',
                                 'bytes', 'lifetime', 'storage'}, 'Incomplete state')
            check(state['bytes'] is None or
                  (isinstance(state['bytes'], int) and state['bytes'] >= 0),
                  'Unknown bytes must be null, not negative')
        doc = (ROOT / ('B1_GRAPH.md' if name == 'B1_Z' else name + '_GRAPH.md')).read_text()
        for item in graph['edges']:
            row = '| ' + ' | '.join(str(v).replace('|', '/')
                                    for v in item.values()) + ' |'
            check(row in doc, 'Markdown edge drift: ' + name)
        for item in graph['memory']:
            row = '| ' + ' | '.join('unknown' if v is None else str(v)
                                    for v in item.values()) + ' |'
            check(row in doc, 'Markdown state drift: ' + name)
    # Ignore execution labels only; compare all value/storage/owner/readiness metadata.
    for key in ('nodes', 'edges', 'memory'):
        check(graphs['C2'][key] == graphs['B1_Z'][key], 'C2/Z graph differs')
    check(graphs['C2']['execution'] != graphs['B1_Z']['execution'],
          'Retain the proposed execution-label distinction')
    b0_states = {s['state']: s for s in graphs['B0']['memory']}
    c2_states = {s['state']: s for s in graphs['C2']['memory']}
    check(b0_states['per-pair endpoint sidecar']['bytes'] == 0,
          'B0 has no global pair sidecar')
    for name in ('additional N-entry owner map',
                 'additional endpoint permutation payload'):
        check(c2_states[name]['bytes'] == 0, 'Strengthened C2 was weakened')
    check(c2_states['level lower sidecar']['bytes'] == 8_000_000 and
          c2_states['level upper sidecar']['bytes'] == 8_000_000,
          'One-level endpoint capacity drift')
    return len(graphs), sum(len(g['edges']) for g in graphs.values())


def validate_costs(contract):
    shape = contract['coordinate_shape']
    n, d, levels, order = (shape[k] for k in ('n', 'd', 'levels', 'tree_order'))
    check((n, d, levels, order, shape['coordinate_bytes']) ==
          (1_000_000, 960, 5, 10, 4), 'Shape drift')
    size, height = n, 1
    while size > 20:
        size -= 9 * (size // 10)
        height += 1
    nodes = (order**height - 1) // (order - 1)
    check(height - 1 == levels, 'Frozen tree height')
    children = [order**i for i in range(1, levels + 1)]
    sweep = 2 * n * d * 4
    expect = dict(
        n=n, d=d, levels=levels, nodes=nodes, children_per_level=children,
        coordinate_payload=n*d*4, source_operand_bytes_per_sweep_per_level=sweep,
        object_operand_bytes_per_sweep_per_level=n*d*4,
        pivot_operand_bytes_per_sweep_per_level=n*d*4,
        safe_directed_sub_calls_per_level=2*n*d,
        safe_directed_mul_calls_per_level=2*n*d,
        safe_directed_add_calls_per_level=2*n*d,
        safe_directed_total_calls_per_level=6*n*d,
        safe_directed_sqrt_calls_per_level=2*n,
        sidecar_capacity_bytes=2*n*8, sidecar_write_bytes_per_level=2*n*8,
        sidecar_read_bytes_per_level=2*n*8, sidecar_roundtrip_bytes_per_level=4*n*8,
        sidecar_roundtrip_bytes_per_rebuild=4*n*8*levels,
        source_coordinate_operand_bytes_removed_per_rebuild=sweep*levels,
        net_source_operand_bytes_removed_excluding_other_costs_per_rebuild=
        (sweep-4*n*8)*levels,
        final_bound_bytes=2*nodes*8, native_key_bytes=n*8, native_order_bytes=n*4,
        extra_owner_map_bytes=0, extra_endpoint_permutation_bytes=0,
        validation_d2h_payload_bytes=nodes*(20+4)+n*4,
        validation_host_vectors_payload_bytes=nodes*(20+4)+3*n*4,
        native_boundary_tasks=sum(children),
        native_boundary_coordinate_iterations=d*sum(children),
    )
    check(read('evidence/COSTS.json')['counts'] == expect, 'Cost formula mismatch')
    return len(expect)


def validate_witness():
    # Exact algebra only: no floating-point simulator or dataset distance loop.
    lower = Fraction(-1)
    upper = lower + Fraction(1, 2**24)
    midpoint = lower + Fraction(1, 2**25)
    check(midpoint - lower == upper - midpoint, 'FP32 exact midpoint')
    check((2**23) % 2 == 0 and (2**24-1) % 2 == 1,
          'Ties-even significands')
    distance = Fraction(1) - Fraction(1, 2**25)
    square = Fraction((2**25-1)**2, 2**50)
    check(square == distance*distance, 'Exact square identity')
    check(square.numerator.bit_length() == 50 <= 53 and
          square.denominator == 2**50, 'FP64 square representability')
    check(distance.numerator.bit_length() == 25 <= 53 and distance != 1,
          'Distinct exact directed roots')


def validate_provenance(contract, local):
    pair = REPO / 'diagnostics/construction_refit_pair_overlap_20261012/summary/RESULTS.json'
    check(digest(pair.read_bytes()) == contract['pair_result_sha256'],
          'Inherited result hash')
    prior = json.loads(pair.read_text())
    check(len(prior['rebuilds']) == 2, 'R1/R2 only')
    for rebuild in prior['rebuilds']:
        overlap = rebuild['scoring_vs_refit']
        check(overlap['construction_tasks'] == overlap['refit_tasks'] == 5_000_000,
              'Inherited task counts')
        check(overlap['task_overlap_fraction'] == 1 and
              rebuild['multiplicity_equal'] and
              rebuild['owner']['same_owner_matched_tasks'] == 0,
              'Inherited overlap/owner scope')
    previous = ROOT.parent / 'build_time_certification_gate0_20261012/evidence/DECISION.json'
    check(digest(previous.read_bytes()) == contract['gate0_decision_sha256'],
          'Previous Gate 0 hash')
    previous_data = json.loads(previous.read_text())
    check(previous_data['generic_thesis'] == previous_data['gpu_only_thesis'] == 'KILL',
          'Do not reopen generic prior-art rejection')
    keeper = read('evidence/KEEPER_SOURCES.json')['files']
    prior_inputs = json.loads((REPO / 'diagnostics/construction_refit_pair_overlap_20261012/evidence/INPUT_MANIFEST.json').read_text())['files']
    keeper_prior = {x['file']: x for x in prior_inputs if x['group'] == 'source'}
    check(len(keeper) == 6, 'Six exact keeper files')
    for item in keeper:
        check(item['sha256'] == keeper_prior[item['file']]['sha256'] and
              item['bytes'] == keeper_prior[item['file']]['bytes'], 'Keeper pin drift')
        if local:
            raw = (ROOT / 'local/source' / item['file']).read_bytes()
            check(len(raw) == item['bytes'] and digest(raw) == item['sha256'],
                  'Private keeper bytes')
    primary = read('evidence/PRIMARY_SOURCES.json')
    check(primary['cub_tag'] == 'v2.8.0' and
          primary['cub_commit'] == '6d02e11d914428000ec01625d765efa3a2d34ce7',
          'Primary library pin')
    check(len(primary['sources']) == 4, 'Narrow primary scope')
    for item in primary['sources']:
        check(urlsplit(item['url']).scheme == 'https' and
              re.fullmatch('[0-9a-f]{64}', item['sha256']) and item['bytes'] > 0,
              'Primary provenance metadata')
        if local:
            raw = (ROOT / item['local_file']).read_bytes()
            check(digest(raw) == item['sha256'] and len(raw) == item['bytes'],
                  'Private primary bytes')
    locators = read('evidence/SOURCE_LOCATIONS.json')
    for locator in locators:
        check(locator['file'] in keeper_prior and
              1 <= locator['start'] <= locator['end'], 'Source locator')
        if local:
            lines = (ROOT / 'local/source' / locator['file']).read_text().splitlines()
            check(locator['end'] <= len(lines), 'Locator outside source')
    if local:
        check(digest((ROOT / 'local/USER_PLAN.md').read_bytes()) ==
              contract['user_plan_sha256'], 'Private supplied plan hash')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check-local-sources', action='store_true')
    args = parser.parse_args()
    contract, decision = read('CONTRACT.json'), read('evidence/DECISION.json')
    for key in ('gpu_process_budget', 'prototype_budget', 'timing_budget'):
        check(contract[key] == 0, 'Design-only budget')
    check(decision['decision'] == 'D0_KILL' and
          decision['retained_b1'] == 'B1_Z' and
          decision['removed_necessary_c2_dependencies'] == [] and
          decision['normalized_graph_equivalent'] is True, 'Bounded kill decision')
    check((decision['gpu_processes'], decision['prototypes'],
           decision['timing_runs']) == (0, 0, 0), 'No experimental admission')
    check(contract['parent_commit'] == '04c4e0d7d891ce348c2e29bbd5a4e65bf0834b6a',
          'Parent revision')
    ng, ne = validate_graphs()
    nc = validate_costs(contract)
    validate_witness()
    validate_provenance(contract, args.check_local_sources)
    for name in SHIP:
        text = (ROOT / name).read_text()
        check(not re.search(r'/(?:Users|home)/|gh[pousr]_[A-Za-z0-9]{20,}', text),
              'Nonportable/private content')
        if name.endswith('.md'):
            for link in re.findall(r'\]\(([^)]+)\)', text):
                if not urlsplit(link).scheme:
                    check((ROOT / link.split('#', 1)[0]).exists(), 'Broken link: ' + link)
    for name in ('README.md', 'DECISION.md', 'NEXT_PROTOTYPE.md'):
        check('D0_KILL' in (ROOT / name).read_text(), 'Decision prose drift')
    print(f'PASS: {len(SHIP)} public files; {ng} graphs/{ne} complete edges; '
          f'{nc} source-cost checks; inherited hashes; exact rational witness; '
          'strong C2/Z equivalence; zero GPU/prototype/timing. Not runtime validation.')
    if args.check_local_sources:
        print('PASS: six private keeper hashes, four primary byte hashes and supplied plan hash.')


if __name__ == '__main__':
    main()
