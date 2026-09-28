#!/usr/bin/env python3
"""Fail-closed local audit of the five-mode large-L2 ledger."""
import argparse
import csv
import hashlib
import itertools
import json
import math
import sqlite3
import statistics as st
from pathlib import Path

import numpy as np
from suite import DATASETS, SIZES, STAGES, ORDERS, rows, verify_stage
from verify import check, clean, qids, read, sha

HERE = Path(__file__).resolve().parent
PRIOR = HERE.parent/'fusion_large_l2_20260924'
PAIRS = (('A', 'B'), ('B', 'C'), ('B', 'D'), ('C', 'E'), ('D', 'E'), ('A', 'E'))


def canonical(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def percentile(values, proportion):
    values = sorted(values)
    return values[min(len(values)-1, math.ceil(proportion*len(values))-1)]


def paired(before, after):
    assert len(before) == len(after) == 4
    log_ratios = [math.log(x/y) for x, y in zip(before, after)]
    boot = sorted(math.exp(st.mean(x)) for x in itertools.product(log_ratios, repeat=4))
    return {'ratio_of_medians': st.median(before)/st.median(after),
            'paired_geomean': math.exp(st.mean(log_ratios)),
            'bootstrap_95': [percentile(boot, .025), percentile(boot, .975)],
            'wins': sum(x > y for x, y in zip(before, after)),
            'round_ratios': [x/y for x, y in zip(before, after)],
            'method': 'exact 4^4 paired log-ratio bootstrap'}


def process(path):
    result = read(path/'result.json')
    samples = list(csv.DictReader((path/'result.csv').open()))
    us = [float(x['query_us']) for x in samples]
    mean = result['sum_query_s']*1e6/result['queries']
    assert len(us) == result['queries']
    assert math.isclose(st.mean(us), mean, rel_tol=1e-9, abs_tol=.002)
    return {'mean_us': mean, 'queries': result['queries'],
            'query_p10_p50_p90_us': [percentile(us, p) for p in (.1, .5, .9)],
            'setup_us': result['setup_s']*1e6,
            'capture_us': result['capture_instantiate_s']*1e6,
            'first_us': result['first_query_s']*1e6,
            'setup_first_amortized_us': (result['setup_s']+result['first_query_s']+
                                         result['sum_query_s'])*1e6/result['queries'],
            'cpu_one_core_percent': 100*result['loop_cpu_s']/result['loop_wall_s']}


def profile(path):
    with sqlite3.connect(path) as db:
        kernels = db.execute('''SELECT s.value,k.gridX,k.gridY,k.gridZ,k.blockX,k.blockY,k.blockZ,
                              k.registersPerThread,k.staticSharedMemory,k.dynamicSharedMemory,k.end-k.start
                              FROM CUPTI_ACTIVITY_KIND_KERNEL k JOIN StringIds s ON s.id=k.demangledName
                              ORDER BY k.start''').fetchall()
        first = next(i for i, x in enumerate(kernels) if x[0].startswith('initQnode('))
        kernels = kernels[first:]
        assert len(kernels) % 5 == 0
        count = len(kernels)//5
        signature = [list(x[:-1]) for x in kernels[:count]]
        assert all([list(x[:-1]) for x in kernels[i:i+count]] == signature
                   for i in range(0, len(kernels), count))
        assert db.execute('SELECT count(*) FROM CUPTI_ACTIVITY_KIND_RUNTIME WHERE returnValue!=0').fetchone()[0] == 0
        return {'kernels_per_query': count, 'query_instances': 5,
                'signature': signature, 'kernel_sum_us': sum(x[-1] for x in kernels)/5000,
                'selected_kernel_us': {
                    name: sum(x[-1] for x in kernels if name in x[0])/5000
                    for name in ('getQresultCount(', 'fusedResultSelect(')},
                'sqlite_sha256': sha(path)}


def main(root, output):
    registration = read(root/'preregistration.json')
    assert registration == read(HERE/'PREREGISTRATION.json')
    for key, name in (('contract_sha256', 'CONTRACT.md'), ('suite_sha256', 'suite.py'),
                      ('verify_sha256', 'verify.py'), ('source_binary_sha256', 'bin/graph_bench'),
                      ('source_cuda_sha256', 'graph_bench.cu'), ('source_run_py_sha256', 'run.py'),
                      ('source_pins_sha256', 'source_pins.json')):
        assert sha(root/name) == registration[key], name
    assert sha(PRIOR/'EVIDENCE.json') == registration['source_evidence_sha256']
    old = read(PRIOR/'EVIDENCE.json')
    assert old['runs'] == 192 and old['hardware']['gpu_index'] == 1
    for name, digest in read(root/'source_pins.json').items():
        assert sha(root/'source'/name.removeprefix('GTS/')) == digest
    preflight = read(root/'logs/preflight.json')
    assert preflight['all_preregistered_files_match'] and preflight['all_fixture_hashes_match']
    assert preflight['preregistration_sha256'] == sha(root/'preregistration.json')
    assert preflight['binary_sha256'] == registration['source_binary_sha256']
    admission = read(root/'logs/admission.json')
    gpu = admission['state']['gpu'].split(',')[1].strip()
    assert not admission['state']['apps'].strip() and gpu in preflight['hardware']
    assert read(root/'logs/COMPLETE.json')['runs'] == registration['runs'] == 264
    for stage in STAGES:
        expected_rows = rows(stage, root)
        assert len(expected_rows) == registration['stage_counts'][stage]
        assert canonical(expected_rows) == registration['stage_rows_sha256'][stage]
        verify_stage(root, stage)
        expected_receipts = [read(root/'data'/d/str(n)/'runs'/label/'receipt.json')
                             for d, n, label, *_ in expected_rows]
        observed_receipts = [json.loads(line) for line in (root/'logs'/f'{stage}.txt').read_text().splitlines()
                             if line.startswith('{')]
        assert observed_receipts == expected_receipts, stage
    evidence = {'experiment': registration['experiment'], 'state': 'complete, locally audited',
                'scope': 'GIST/Deep/Tloc N65536/1000000, five modes A/B/C/D/E, complete hot host-ready query',
                'hardware': {'gpu_index': admission['gpu_index'], 'gpu_uuid': gpu,
                             'gpu_name': preflight['hardware'].split(', ')[2],
                             'driver': preflight['hardware'].split(', ')[3],
                             'compute_cap': preflight['hardware'].split(', ')[4],
                             'cuda': '13.1.115', 'cpu': 'shared/unpinned',
                             'clocks': 'unchanged/uncontrolled'},
                'source_binary_sha256': registration['source_binary_sha256'],
                'prior_evidence_sha256': registration['source_evidence_sha256'],
                'runs': 264, 'orders': ORDERS, 'data': {}, 'ledger': {}}
    sample_gaps = []
    for d in DATASETS:
        evidence['data'][d] = {}
        for n in SIZES:
            path = root/'data'/d/str(n)
            fixture = read(path/'fixtures/oracle.json')
            registered = registration['fixture'][d][str(n)]
            assert sha(path/'fixtures/oracle.json') == registered['oracle_json_sha256']
            for name, digest in fixture['sha256'].items():
                assert sha(path/'fixtures'/name) == digest, (d, n, name)
            for name, digest in registered['expected_sha256'].items():
                assert sha(path/'fixtures'/f"expected_{fixture['radii'][name]:g}.json") == digest
            planned = {row[2]: row for stage in STAGES for row in rows(stage, root)
                       if row[0] == d and row[1] == n}
            assert {x.name for x in (path/'runs').iterdir()} == set(planned)
            matrix = np.load(path/'fixtures/oracle.npy', mmap_mode='r')
            full_new = read(path/'full_verified_new.json')
            assert set(full_new) == {x for x in planned if x.startswith('full_')}
            for label, row in planned.items():
                _, _, _, mode, radius, reps, warm, tool, dump, qfile = row
                run = path/'runs'/label
                receipt = read(run/'receipt.json')
                clean(receipt)
                assert receipt['input_sha256']['data.f32bin'] == fixture['sha256']['data.f32bin']
                assert receipt['input_sha256'][qfile] == fixture['sha256'][qfile]
                for phase in ('before', 'after'):
                    state = read(run/f'{phase}.json')
                    assert not state['apps'].strip() and gpu in state['gpu']
                checks = read(run/'checks.json')
                assert checks and all(not x['foreign'] for x in checks)
                times = [0]+[x['elapsed_s'] for x in checks]+[receipt['wall_s']]
                sample_gaps.extend(b-a for a, b in zip(times, times[1:]))
                samples = list(csv.DictReader((run/'result.csv').open()))
                assert [int(x['qid']) for x in samples] == qids(path/'fixtures'/qfile)*reps
                gold = read(path/'fixtures'/f'expected_{radius:g}.json')
                assert all([int(x['count']), x['ordered_hash']] == gold[x['qid']] for x in samples)
                process(run)
                if label.startswith('full_'):
                    name = label.split('_')[1]
                    got, band = check(path, label, mode, name, fixture, matrix)
                    assert all(gold[str(q)] == [count, fnv] for q, count, _, fnv in got)
                    assert full_new[label]['output_sha256'] == sha(run/'result.results')
                    if name == 'normal':
                        assert full_new[label]['normal_boundary_count'] == band
                evidence['ledger'][f'{d}/{n}/{label}'] = {
                    'receipt_sha256': sha(run/'receipt.json'),
                    'samples_sha256': sha(run/'result.csv')}
            primary = {mode: [process(path/'runs'/f'timing_{i}_{mode}') for i in range(4)]
                       for mode in 'ABCDE'}
            ratios = {before+'/'+after: paired(
                [x['mean_us'] for x in primary[before]],
                [x['mean_us'] for x in primary[after]]) for before, after in PAIRS}
            sustained = [{mode: process(path/'runs'/f'sustained_{i}_{mode}') for mode in 'ABCDE'}
                         for i in range(2)]
            for item in sustained:
                item['ratios'] = {before+'/'+after: item[before]['mean_us']/item[after]['mean_us']
                                  for before, after in PAIRS}
            traces = {mode: profile(path/'runs'/f'nsys_{mode}/trace.sqlite') for mode in 'BD'}
            prior_traces = old['data'][d][str(n)]['nsys']
            assert traces['B']['signature'] == prior_traces['C']['signature']
            assert traces['D']['signature'] == prior_traces['E']['signature']
            assert traces['B']['kernels_per_query'] == prior_traces['C']['kernels_per_query']
            assert traces['D']['kernels_per_query'] == prior_traces['E']['kernels_per_query']
            evidence['data'][d][str(n)] = {
                'dataset': d, 'n': n, 'dimension': fixture['dimension'],
                'normal_radius': fixture['radii']['normal'],
                'data_sha256': fixture['sha256']['data.f32bin'],
                'oracle_sha256': fixture['sha256']['oracle.npy'],
                'normal_boundary_count': full_new['full_normal_B']['normal_boundary_count'],
                'tree': {key: read(path/'runs/full_normal_B/result.json')[key]
                         for key in ('tree_height', 'nodes', 'slots', 'used_nodes', 'leaves')},
                'primary': primary, 'ratios': ratios,
                'sustained': sustained, 'nsys': traces,
                'full_verification': full_new}
    evidence['safety'] = {'max_sample_gap_s': max(sample_gaps),
                          'median_sample_gap_s': st.median(sample_gaps),
                          'all_runs_had_inprocess_checks': True}
    output.write_text(json.dumps(evidence, indent=2)+'\n')
    for d, shapes in evidence['data'].items():
        for n, item in shapes.items():
            modes = {m: st.median(x['mean_us'] for x in item['primary'][m]) for m in 'ABCDE'}
            print(d, n, {m: round(v, 3) for m, v in modes.items()},
                  {k: round(v['ratio_of_medians'], 4) for k, v in item['ratios'].items()})


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('root', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    main(args.root.resolve(), args.output)
