#!/usr/bin/env python3
"""Prepare byte-identical original GTS plus bounded synthetic update-count probes."""
import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
N, D = 1000, 128
# Every query targets original row zero; it is never deleted or moved. Inserts
# occur only before the first rebuild, so original/current row namespaces agree.
CASES = {
    'query_only': (0, [(2, 0)] * 3),
    'all_include': (10000, [(2, 0)]),
    'buffer_insert': (0, [(2, 0), (0, 0), (2, 0)]),
    'base_delete': (10000, [(2, 0), (1, 1), (2, 0)]),
    'buffer_delete': (0, [(0, 0), (2, 0), (1, N), (2, 0)]),
    'rebuild_no_prior_buffer_query': (0, [(0, 0)] * 10 + [(2, 0)]),
    'rebuild_after_buffer_query': (0, [(0, 0), (2, 0)] + [(0, 0)] * 9 + [(2, 0)] * 2),
    'mixed_delete_rebuild': (10000, [(1, 1)] + [(0, 0)] * 10 + [(2, 0)]),
    'rebuild_then_delete': (0, [(0, 0)] * 10 + [(2, 0), (1, N), (2, 0)]),
}

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def oracle(rows, operations, radius):
    live = list(range(len(rows)))
    result = []
    for flag, idx in operations:
        if flag == 0:
            assert 0 <= idx < len(rows)
            live.append(idx)
        elif flag == 1:
            assert 0 < idx < len(live)
            live.pop(idx)
        else:
            assert flag == 2 and idx == 0
            result.append(sum(sum((a-b)**2 for a, b in zip(rows[0], rows[j])) <= radius**2 for j in live))
    return result

def validate(cost, expected):
    match = re.search(r'Result num:\s*([^\n]+)', cost)
    actual = None
    if match and re.fullmatch(r'\s*\d+(?:\s+\d+)*\s*', match[1]):
        actual = list(map(int, match[1].split()))
    return {'pass': actual == expected, 'actual': actual, 'expected': expected,
            'scope': 'Exact counts only; not full result IDs/distances or performance admission'}

def prepare(source, out):
    pins = json.loads((HERE.parent/'original_tree_redundancy/SOURCE_PINS.json').read_text())
    files = {k.removeprefix('GTS/'): v for k, v in pins['sha256'].items() if k.startswith('GTS/')}
    assert len(files) == 8
    for f, h in files.items():
        assert sha(source/f) == h, f'Source drift: {f}'
    assert '__managed__ int MAX_IN_SIZE = 10;' in (source/'include/update.cuh').read_text()
    assert '__managed__ int MAX_H = 3;' in (source/'include/tree.cuh').read_text()
    out.mkdir(parents=True, exist_ok=False)
    for f in files:
        dest = out/'source'/f
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source/f, dest)
    fixtures = out/'fixtures'
    fixtures.mkdir()
    rows = [list(b''.join(hashlib.sha256(f'gts-original-20260924:{i}:{j}'.encode()).digest() for j in range(4))) for i in range(N)]
    assert len({tuple(x) for x in rows}) == N and all(len(x) == D for x in rows)
    (fixtures/'data.txt').write_text(f'{D} {N} 2\n' + ''.join(' '.join(map(str, row))+'\n' for row in rows))
    cases = {}
    for name, (radius, ops) in CASES.items():
        f = fixtures/(name+'.updates')
        f.write_text(str(len(ops))+'\n'+''.join(f'{flag} {idx}\n' for flag, idx in ops))
        cases[name] = {'radius': radius, 'operations': len(ops), 'expected_counts': oracle(rows, ops, radius), 'updates_sha256': sha(f)}
    meta = {'source_commit': pins['commit'], 'source_sha256': files,
            'scope': 'Prepared only. Synthetic integer-L2 correctness probes, not benchmark data or GPU validation.',
            'n': N, 'dimensions': D, 'metric': 'L2', 'storage': 'FP32 integer coordinates [0,255]',
            'native_height': 3, 'native_leaf_limit': 20, 'native_buffer_threshold': 10,
            'peak_live_rows': N+10, 'cases': cases, 'data_sha256': sha(fixtures/'data.txt')}
    (out/'manifest.json').write_text(json.dumps(meta, indent=2)+'\n')
    for sub in ['bin', 'logs', 'runs']:
        (out/sub).mkdir()
    return meta

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='mode', required=True)
    s = sub.add_parser('prepare')
    s.add_argument('source', type=Path, help='Original GTS directory containing include/ and src/')
    s.add_argument('out', type=Path)
    s = sub.add_parser('check')
    s.add_argument('root', type=Path)
    s.add_argument('case', choices=CASES)
    s.add_argument('cost', type=Path)
    a = p.parse_args()
    if a.mode == 'prepare':
        m = prepare(a.source, a.out)
        print(f'Prepared {len(m["source_sha256"])} unchanged source files and {len(m["cases"])} probes; no GPU executed')
    else:
        expected = json.loads((a.root/'manifest.json').read_text())['cases'][a.case]['expected_counts']
        r = validate(a.cost.read_text(), expected)
        print(json.dumps(r, indent=2))
        raise SystemExit(0 if r['pass'] else 1)
