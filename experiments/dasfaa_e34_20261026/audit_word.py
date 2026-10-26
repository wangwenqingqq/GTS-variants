"""Audit complete edit-distance outputs against an exhaustive CPU oracle."""
import json
import sys
from pathlib import Path

import numpy as np


def load(path, n=None):
    path = Path(path)
    h = np.fromfile(path, dtype='<i4', count=2)
    if len(h) != 2:
        raise ValueError('truncated string header')
    rows, stride = map(int, h)
    if rows <= 0 or stride != 109 or path.stat().st_size != 8 + rows * (4 + stride):
        raise ValueError('invalid string dimensions or payload size')
    if n is None:
        n = rows
    if not 0 < n <= rows:
        raise ValueError('requested string prefix is unavailable')
    lengths = np.fromfile(path, dtype='<i4', count=n, offset=8)
    if (lengths < 0).any() or (lengths >= stride).any():
        raise ValueError('string length exceeds the DP-array contract')
    text = np.memmap(path, dtype=np.uint8, offset=8 + 4 * rows,
                     mode='r', shape=(rows, stride))
    return lengths, text[:n]


def value(lengths, text, i):
    return text[i, :int(lengths[i])].tobytes()


def distance(a, b):
    # Full-table DP is deliberately independent of both rolling-row programs.
    table = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
    for i in range(len(a) + 1):
        table[i][0] = i
    for j in range(len(b) + 1):
        table[0][j] = j
    for i, ac in enumerate(a, 1):
        for j, bc in enumerate(b, 1):
            table[i][j] = min(table[i - 1][j] + 1, table[i][j - 1] + 1,
                              table[i - 1][j - 1] + (ac != bc))
    return table[-1][-1]


def audit(root, case, result, k=8, expected_rows=None):
    root = Path(root)
    xl, x = load(root / case['base'], case['N'])
    ql, q = load(root / case['query'])
    nq = len(ql)
    raw = (root / case['oracle']).read_bytes()
    if len(raw) != nq * 10 * 12:
        raise ValueError('incomplete CPU oracle')
    oi = np.frombuffer(raw, dtype='<i4', count=nq * 10).reshape(nq, 10)
    od = np.frombuffer(raw, dtype='<f8', offset=nq * 10 * 4).reshape(nq, 10)
    if ((oi < 0).any() or (oi >= case['N']).any() or not np.isfinite(od).all()
            or (od < 0).any() or (np.diff(od, axis=1) < 0).any()
            or any(len(set(row)) != 10 for row in oi)):
        raise ValueError('malformed CPU oracle')
    queries = [value(ql, q, i) for i in range(nq)]
    for row in range(nq):
        if any(distance(value(xl, x, int(i)), queries[row]) != d
               for i, d in zip(oi[row], od[row])):
            raise ValueError('CPU oracle has inconsistent distances')
    ids = np.fromfile(str(result) + '.ids', dtype='<i4')
    if len(ids) % k:
        raise ValueError('truncated result row')
    ids = ids.reshape(-1, k)
    if expected_rows is not None:
        if len(ids) != expected_rows:
            raise ValueError('incomplete query output')
    elif len(ids) not in (nq, 1024 if nq == 1000 else nq):
        raise ValueError('incomplete query output')
    invalid = duplicates = failures = 0
    for row, got in enumerate(ids):
        qi = row % nq
        duplicates += len(set(got)) != k
        for i in got:
            if i < 0 or i >= case['N']:
                invalid += 1
                failures += 1
            elif distance(value(xl, x, int(i)), queries[qi]) > od[qi, k - 1] * (1 + 1e-5):
                failures += 1
    out = {'results': int(ids.size), 'rows': len(ids), 'invalid_ids': invalid,
           'duplicate_rows': duplicates, 'distance_failures': failures,
           'tie_aware_recall': 1 - failures / ids.size,
           'correct': not (failures or duplicates), 'oracle_k': k,
           'tolerance': 1e-5,
           'oracle': 'independent exhaustive CPU rolling-row edit oracle',
           'candidate_distance_check': 'independent Python full-table edit DP'}
    Path(str(result) + '.audit.json').write_text(json.dumps(out, indent=2) + '\n')
    return out


if __name__ == '__main__':
    root = Path(sys.argv[1])
    cases = json.loads((root / 'WORD_MANIFEST.json').read_text())['cases']
    case = next(c for c in cases if c['N'] == int(sys.argv[2]))
    print(json.dumps(audit(root, case, sys.argv[3])))
