#!/usr/bin/env python3
"""Verify private frozen evidence and curate only the declared public result set."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def read(path):
    return json.loads(path.read_text())


def integer_oracle(data, operations, radius):
    norms = (data * data).sum(1)
    sq = norms[:, None] + norms[None, :] - 2 * data @ data.T
    assert sq.min() == 0 and sq.max() < 2 ** 24
    base = np.arange(len(data)); alive = np.ones(len(base), dtype=bool); buffer = []
    queries = []; states = []; rebuilds = 0
    for step, (flag, index) in enumerate(operations):
        before = (len(base), len(buffer)); rebuilt = False
        if flag == 0:
            buffer.append(int(base[index]))
            if len(buffer) == 10:
                base = np.r_[base[alive], buffer]
                alive = np.ones(len(base), dtype=bool); buffer = []; rebuilt = True; rebuilds += 1
        elif flag == 1:
            positions = np.flatnonzero(alive)
            if index < len(positions):
                alive[positions[index]] = False
            else:
                buffer.pop(index - len(positions))
        else:
            assert flag == 2
            live = np.r_[base[alive], np.asarray(buffer, dtype=np.int64)]
            distances = sq[base[index], live]
            ids = np.flatnonzero(distances <= radius ** 2)
            fields = np.sqrt(distances[ids].astype(np.float64)).astype('<f4')
            queries.append((step, index, len(base), len(buffer), dict(zip(map(int, ids), map(bytes, fields)))))
        states.append((*before, len(base), len(buffer), rebuilt))
    return queries, states, rebuilds


def validate(root):
    source = read(root / 'SOURCE.json'); registered = read(root / 'REGISTERED.json')
    assert sha(root / 'SOURCE.json') == registered['source_sha256']
    for name, digest in source['sources'].items():
        assert sha(root / 'native_timed/source' / name) == digest, name
    for name in ('data.txt', 'events.txt', 'expected.json'):
        assert sha(root / name) == registered['input_sha256'][name], name
    data = np.loadtxt(root / 'data.txt', skiprows=1, dtype=np.int64)
    operations = np.loadtxt(root / 'events.txt', skiprows=1, dtype=np.int64).tolist()
    assert data.shape == (1000, 128) and len(operations) == 12000
    queries, states, rebuilds = integer_oracle(data, operations, read(root / 'expected.json')['radius'])
    assert len(queries) == 10000 and rebuilds == 50
    formal = read(root / 'FORMAL_ROWS.json'); cost = read(root / 'COST_ROWS.json')
    assert len(formal) == 24 and len(cost) == 48
    output_identity = None
    receipt_hashes = {}
    for row in formal + cost:
        label = row['label']; prefix = root / 'native_timed' / label
        for suffix, digest in row['outputs'].items():
            assert sha(Path(str(prefix) + suffix)) == digest, (label, suffix)
        identity = [row['outputs'][s] for s in ('.ids.i32', '.dist.f32', '.queries.csv')]
        if output_identity is None:
            output_identity = identity
        assert identity == output_identity, label
        receipt = read(root / 'runs' / label / 'receipt.json')
        assert receipt['runtime_valid'] and receipt['exit_code'] == 0 and receipt['stop_reason'] is None
        assert receipt['binary_sha256'] == source['binary_sha256']
        assert not read(root / 'runs' / label / 'before.json')['apps']
        assert not read(root / 'runs' / label / 'after.json')['apps']
        assert all(not x['foreign'] for x in read(root / 'runs' / label / 'checks.json'))
        assert sha(root / 'registrations' / (label + '.json')) == row['registration_sha256']
        receipt_hashes[label] = sha(root / 'runs' / label / 'receipt.json')
        ids = np.fromfile(str(prefix) + '.ids.i32', dtype='<i4')
        fields = np.fromfile(str(prefix) + '.dist.f32', dtype='<f4')
        records = list(csv.DictReader(open(str(prefix) + '.queries.csv')))
        assert len(records) == len(queries); offset = 0
        for got, want in zip(records, queries):
            step, qid, n, buffer, expected = want
            assert [int(got[k]) for k in ('step', 'qid', 'tree_size', 'buffer')] == [step, qid, n, buffer]
            count = int(got['count']); assert int(got['offset']) == offset and count == len(expected)
            result = dict(zip(map(int, ids[offset:offset+count]), map(bytes, fields[offset:offset+count])))
            assert len(result) == count and result == expected, (label, step)
            offset += count
        assert offset == len(ids) == len(fields)
        ops = list(csv.DictReader(open(str(prefix) + '.ops.csv')))
        if row['summary']['observe']:
            assert len(ops) == len(states)
            for step, (op, state) in enumerate(zip(ops, states)):
                assert int(op['step']) == step and int(op['flag']) == operations[step][0]
                assert tuple(int(op[k]) for k in ('base_before', 'buffer_before', 'base_after', 'buffer_after')) == state[:4]
                assert (float(op['rebuild_ms']) > 0) == state[4]
                assert float(op['ack_ms']) >= float(op['rebuild_ms'])
        else:
            assert not ops
        assert row['region']['final_owned_bytes'] == 0
        if row['mode'] != 'NATIVE':
            assert row['region']['refreshes'] == 51
    for round_index, order in enumerate(registered['orders'], 1):
        assert [x['mode'] for x in formal if x['round'] == round_index] == order
    results = read(root / 'RESULTS.json')
    for pair, metrics in results['comparisons'].items():
        a, b = pair.split('/')
        left = [x for x in formal if x['mode'] == a]; right = [x for x in formal if x['mode'] == b]
        for key, estimate in metrics.items():
            ratios = [(x['summary'][key] / y['summary'][key] if key == 'trace_ms'
                       else x['region'][key] / y['region'][key]) for x, y in zip(left, right)]
            assert np.allclose(ratios, estimate['raw_ratios'], rtol=0, atol=1e-12)
            assert math.isclose(math.exp(np.log(ratios).mean()), estimate['geomean'], rel_tol=1e-12)
            rng = np.random.default_rng(202610081022)
            ci = np.quantile(np.exp(np.log(ratios)[rng.integers(0, 6, (20000, 6))].mean(1)), [.025, .975])
            assert np.allclose(ci, estimate['CI95'], rtol=0, atol=1e-12)
    qualification = read(root / 'COST_QUALIFICATION.json')
    assert len(qualification) == 4 and all(x['output_equal'] and x['admitted'] and x['CI95'][1] <= 1.03 for x in qualification)
    return dict(state='independently_audited', formal_processes=24, observer_processes=48,
                oracle='independent integer squared L2 and live-multiset replay; exact FP32 fields',
                queries_checked=720000, events_per_process=12000, rebuilds_per_process=50,
                all_ordered_outputs_identical=True, all_guard_receipts_valid=True,
                statistics_recomputed=True, measured_binary_sha256=source['binary_sha256'],
                raw_source_manifest_sha256=sha(root / 'SOURCE.json'), receipt_sha256=receipt_hashes)


PUBLIC_FILES = ('SOURCE.json', 'REGISTERED.json', 'RESULTS.json', 'FORMAL_ROWS.json',
                'FORMAL_TIMER.json', 'COST_ROWS.json', 'COST_QUALIFICATION.json', 'STRUCTURAL.json',
                'BOUNDARIES.json', 'WORK_0.json', 'WORK_10000.json', 'CLOSURE_REGISTERED.json',
                'CLOSURE_SANITIZERS.json', 'CLOSURE_COUNTER_ROWS.json', 'FULL_WORK.json',
                'CLOSURE_COMPLETE.json', 'CLOSURE_PROFILE_REGISTERED.json', 'CLOSURE_PROFILE_ROWS.json')


def curate(root, destination):
    audit = validate(root)
    destination.mkdir(parents=True, exist_ok=False)
    binary = Path(read(root / 'SOURCE.json')['build'][-1])
    remote_root = binary.parent.parent
    prefixes = ((str(remote_root), '$REGION_RUN'),
                (str(remote_root.parent.parent.parent), '$CAMPAIGN_ROOT'))
    def portable(value):
        if isinstance(value, dict):
            return {key: portable(item) for key, item in value.items()}
        if isinstance(value, list):
            return [portable(item) for item in value]
        if isinstance(value, str):
            for prefix, marker in prefixes:
                value = value.replace(prefix, marker)
        return value
    manifest = {}
    for name in PUBLIC_FILES:
        target = destination / name
        target.write_text(json.dumps(portable(read(root / name)), indent=2) + '\n')
        manifest[name] = dict(raw_sha256=sha(root / name), curated_sha256=sha(target))
    (destination / 'INDEPENDENT_AUDIT.json').write_text(json.dumps(audit, indent=2) + '\n')
    (destination / 'PUBLICATION.json').write_text(json.dumps(dict(
        files=manifest, primary_scope='24 retained processes; no primary replay or kernel change',
        derived_receipts={'INDEPENDENT_AUDIT.json': dict(
            curated_sha256=sha(destination / 'INDEPENDENT_AUDIT.json'),
            provenance='independent verification derived from the registered raw evidence')},
        raw_evidence='External task-owned storage; hashes are not substituted by curated hashes',
        exclusions=['raw inputs', 'full binary outputs', 'profiler databases', 'GPU identifiers',
                    'process identifiers', 'device configuration', 'private source paths']), indent=2) + '\n')
    print(json.dumps({k: v for k, v in audit.items() if k != 'receipt_sha256'}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    curate(args.raw, args.output)
