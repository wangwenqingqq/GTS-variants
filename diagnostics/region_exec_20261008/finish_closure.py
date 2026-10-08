#!/usr/bin/env python3
"""Append missing qualification/count evidence without replaying formal timing."""
import argparse
import hashlib
import itertools
import json
from pathlib import Path

import run_region as r


def work_records(path):
    with path.open() as stream:
        for line in stream:
            if line.startswith('REGION_WORK '):
                yield line[12:].strip()


def compare_work(paths, expected_queries):
    digest = hashlib.sha256()
    totals = dict.fromkeys(('nodes', 'pivots', 'leaves', 'objects'), 0)
    epochs = set()
    queries = 0
    for records in itertools.zip_longest(*(work_records(p) for p in paths)):
        assert records[0] is not None and records[0] == records[1] == records[2], \
            ('work set mismatch', queries)
        digest.update((records[0] + '\n').encode())
        record = json.loads(records[0])
        for key in totals:
            totals[key] += sum(record[key])
        epochs.add(record['epoch'])
        queries += 1
    assert queries == expected_queries, (queries, expected_queries)
    return {'queries': queries, 'epochs': sorted(epochs),
            'same_node_pivot_leaf_object_sets': True, 'totals': totals,
            'normalized_work_stream_sha256': digest.hexdigest()}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('raw', 'workflow', 'dest', 'u0', 'helpers'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--gpu', required=True)
    a = p.parse_args()
    assert r.read(a.dest / 'COMPLETE.json')['formal_processes'] == 24
    source = r.read(a.dest / 'SOURCE.json')
    for name, digest in source['sources'].items():
        assert r.sha(a.dest / 'native_timed/source' / name) == digest, name
    assert r.sha(Path(r.__file__)) == source['controller_sha256']
    registration = a.dest / 'CLOSURE_REGISTERED.json'
    assert not registration.exists(), 'append a new namespace; never overwrite'
    r.save(registration, {
        'purpose': 'missing PAR sanitizers and exact full-trace work-set control',
        'primary_processes_replayed': 0,
        'source_manifest_sha256': r.sha(a.dest / 'SOURCE.json'),
        'primary_results_sha256': r.sha(a.dest / 'RESULTS.json'),
        'controller_sha256': r.sha(__file__),
        'formal_controller_sha256': r.sha(Path(r.__file__)),
        'sanitizers': ['memcheck', 'racecheck', 'synccheck'],
        'counter_modes': list(r.MODES[1:]), 'counter_queries': 10000,
        'timing_admission': 'diagnostic only; never enter the 24-row estimator'})
    rows = []
    for tool in ('memcheck', 'racecheck', 'synccheck'):
        rows.append(r.run(a, 'closure_' + tool + '_PAR_STRONG',
                          a.dest / 'boundaries/10000', 'PAR_STRONG', tool=tool))
        r.save(a.dest / 'CLOSURE_SANITIZERS.json', rows)
    case = a.dest / 'native' / str(r.SEED)
    counted = []
    for mode in r.MODES[1:]:
        counted.append(r.run(a, 'closure_full_work_' + mode, case, mode,
                             observe=False, counters=True))
        r.save(a.dest / 'CLOSURE_COUNTER_ROWS.json', counted)
    assert all(r.equal_output(counted[0], x) for x in counted[1:])
    paths = [a.dest / 'runs' / ('closure_full_work_' + mode) / 'stdout.log'
             for mode in r.MODES[1:]]
    work = compare_work(paths, 10000)
    work.update(modes=list(r.MODES[1:]),
                raw_stdout_sha256=[r.sha(path) for path in paths],
                registration_sha256=r.sha(registration),
                counter_binary_sha256=source['counter_binary_sha256'],
                separate_from_primary=True)
    r.save(a.dest / 'FULL_WORK.json', work)
    r.save(a.dest / 'CLOSURE_COMPLETE.json', {
        'new_sanitizer_processes': 3, 'new_counter_processes': 3,
        'primary_replays': 0, 'full_work_sha256': r.sha(a.dest / 'FULL_WORK.json')})
    print('CLOSURE COMPLETE', json.dumps(work), flush=True)


if __name__ == '__main__':
    main()
