"""Independent packed-bit Tanimoto audit using Python integer bit_count."""
import json
import math
from pathlib import Path
import sys

import numpy as np

if not hasattr(int, 'bit_count'):
    raise RuntimeError('audit_bits requires Python >=3.10 for the independent int.bit_count reference')

WORDS = 32
BITS = 2048
ORACLE_K = 10


def load(path, n=None):
    path = Path(path)
    header = np.fromfile(path, dtype='<i4', count=2)
    if len(header) != 2:
        raise ValueError('truncated packed-bit header')
    rows, bits = map(int, header)
    if rows <= 0 or bits != BITS or path.stat().st_size != 8 + rows * WORDS * 8:
        raise ValueError('invalid packed-bit dimensions or payload size')
    if n is None:
        n = rows
    if isinstance(n, bool) or not isinstance(n, (int, np.integer)) or not 0 < n <= rows:
        raise ValueError('requested packed-bit prefix is unavailable')
    values = np.memmap(path, dtype='<u8', offset=8, mode='r', shape=(rows, WORDS))
    return values[:int(n)]


def feature_int(row):
    # Independent representation from the CUDA/CPU-oracle uint64 word loops.
    return int.from_bytes(row.tobytes(), byteorder='little', signed=False)


def distance(a, b):
    union = (a | b).bit_count()
    return 1.0 - (a & b).bit_count() / union if union else 0.0


def oracle_values(path, n, indexed, queries):
    nq = len(queries)
    raw = Path(path).read_bytes()
    if len(raw) != nq * ORACLE_K * 12:
        raise ValueError('incomplete CPU bit oracle')
    ids = np.frombuffer(raw, dtype='<i4', count=nq * ORACLE_K).reshape(nq, ORACLE_K)
    dd = np.frombuffer(raw, dtype='<f8', offset=nq * ORACLE_K * 4).reshape(nq, ORACLE_K)
    if ((ids < 0).any() or (ids >= n).any() or not np.isfinite(dd).all()
            or (dd < 0).any() or (dd > 1).any() or (np.diff(dd, axis=1) < 0).any()
            or any(len(set(row)) != ORACLE_K for row in ids)):
        raise ValueError('malformed CPU bit oracle')
    for row in range(nq):
        for i, value in zip(ids[row], dd[row]):
            if not math.isclose(distance(indexed(int(i)), queries[row]), float(value),
                                rel_tol=0.0, abs_tol=1e-12):
                raise ValueError('CPU bit oracle has inconsistent distances')
    return ids, dd


def audit(root, case, result, k=8, expected_rows=None):
    if k != 8:
        raise ValueError('the E3 packed-bit workload is frozen at k=8')
    root = Path(root)
    base = load(root / case['base'], case['N'])
    query = load(root / case['query'])
    nq = len(query)
    if len(base) < ORACLE_K:
        raise ValueError('CPU top10 oracle requires at least ten indexed rows')
    if expected_rows is not None and expected_rows != nq:
        raise ValueError('E3 bit output must cover the complete query file')
    queries = [feature_int(row) for row in query]
    cache = {}

    def indexed(i):
        if i not in cache:
            cache[i] = feature_int(base[i])
        return cache[i]

    # The exhaustive oracle's provenance is frozen by the campaign. Recompute
    # its selected distances independently, without reusing its popcount code.
    _, oracle = oracle_values(root / case['oracle'], len(base), indexed, queries)
    ids_path, dist_path = Path(str(result) + '.ids'), Path(str(result) + '.dist')
    if ids_path.stat().st_size != nq * k * 4 or dist_path.stat().st_size != nq * k * 8:
        raise ValueError('incomplete packed-bit output')
    ids = np.fromfile(ids_path, dtype='<i4').reshape(nq, k)
    reported = np.fromfile(dist_path, dtype='<f8').reshape(nq, k)
    invalid = duplicates = failures = mismatches = 0
    for row, got in enumerate(ids):
        duplicates += int(len(set(map(int, got))) != k)
        for col, obj in enumerate(got):
            obj = int(obj)
            if obj < 0 or obj >= len(base):
                invalid += 1
                failures += 1
                continue
            exact = distance(indexed(obj), queries[row])
            if exact > float(oracle[row, k - 1]) * (1 + 1e-5):
                failures += 1
            if not math.isclose(float(reported[row, col]), exact, rel_tol=0.0, abs_tol=1e-12):
                mismatches += 1
    out = {'results': int(ids.size), 'rows': nq, 'invalid_ids': invalid,
           'duplicate_rows': duplicates, 'distance_failures': failures,
           'reported_distance_mismatches': mismatches,
           'tie_aware_recall': 1 - failures / ids.size,
           'correct': not (failures or duplicates or mismatches), 'oracle_k': k,
           'tolerance': 1e-5, 'empty_union_distance': 0,
           'oracle': 'independent exhaustive CPU uint64-popcount top10',
           'candidate_distance_check': 'Python arbitrary-precision int bit_count'}
    with Path(str(result) + '.audit.json').open('x') as f:
        json.dump(out, f, indent=2)
        f.write('\n')
    return out


if __name__ == '__main__':
    if len(sys.argv) != 4:
        raise SystemExit('usage: audit_bits.py ROOT CASE_JSON RESULT_PREFIX')
    print(json.dumps(audit(sys.argv[1], json.loads(Path(sys.argv[2]).read_text()), sys.argv[3])))
