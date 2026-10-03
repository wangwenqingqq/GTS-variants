#!/usr/bin/env python3
"""Post-collection validation additions; does not rewrite frozen timing records."""
import hashlib
import json
from pathlib import Path
import struct
import sys

import numpy as np
import native_ivf

ROOT = Path(__file__).resolve().parent
original_quality = native_ivf.quality


def output_fields(ids, distances, data, reference):
    valid = (ids >= 0) & (ids < len(data))
    delivered = distances[valid].astype(np.float64)
    adjacent = valid[:, :-1] & valid[:, 1:]
    nonnegative = bool(np.all(delivered >= 0))
    sorted_fields = bool(np.all(np.diff(distances, axis=1)[adjacent] >= 0))
    point_ids = ids[valid]
    qids = np.broadcast_to(np.array([r['qid'] for r in reference['records']])[:, None], ids.shape)[valid]
    squared = np.zeros(len(point_ids), dtype=np.float64)
    for j in range(data.shape[1]):
        delta = data[point_ids, j].astype(np.float64)-data[qids, j].astype(np.float64)
        squared += delta*delta
    truth = np.sqrt(squared); difference = np.abs(delivered-truth)
    nonzero = truth > 0
    return {'nonnegative_pass': nonnegative, 'nondecreasing_distance_pass': sorted_fields,
            'distance_max_relative_nonzero': float((difference[nonzero]/truth[nonzero]).max()) if nonzero.any() else 0.,
            'zero_distance_max_abs': float(difference[~nonzero].max()) if (~nonzero).any() else 0.,
            'zero_distance_slots': int((~nonzero).sum())}


def quality(ids, distances, reference, data, k, allow_missing=False):
    q = original_quality(ids, distances, reference, data, k, allow_missing)
    q.update(output_fields(ids, distances, data, reference))
    q['distance_tolerance_pass'] &= q['nonnegative_pass'] and q['nondecreasing_distance_pass']
    return q


def verify_cache(path):
    with path.open('rb') as f:
        n, d, h, count = struct.unpack('<iiii', f.read(16))
        ids = np.fromfile(f, dtype='<i4', count=n)
        dtype = np.dtype([('pid','<i4'), ('min_dis','<f4'), ('size','<i4'), ('lid','<i4'), ('is_leaf','<i4')])
        nodes = np.fromfile(f, dtype=dtype, count=count)
        flags = np.fromfile(f, dtype='<i4', count=count)
        assert f.read(1) == b'' and len(flags) == count
    assert np.array_equal(np.sort(ids), np.arange(n))
    leaves = nodes[(flags == 0) & (nodes['is_leaf'] != 0)]
    leaves = leaves[np.argsort(leaves['lid'])]
    assert leaves['lid'][0] == 0 and np.all((leaves['size'] > 0) & (leaves['size'] <= 20))
    ends = leaves['lid']+leaves['size']
    assert np.array_equal(ends[:-1], leaves['lid'][1:]) and ends[-1] == n
    return {'N': n, 'D': d, 'height': h, 'node_count': count, 'leaf_count': len(leaves),
            'permutation_pass': True, 'exact_disjoint_partition_pass': True,
            'cache_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def postcheck():
    checks = {}; caches = {}
    for name in ('GIST', 'Deep', 'synthetic96', 'synthetic960'):
        caches[name] = verify_cache(ROOT/f'{name}.index')
    for path in sorted(ROOT.glob('*gts*.bin')):
        n, d, k, ids, distances = native_ivf.read_gts(path)
        assert np.all(distances >= 0) and np.all(np.diff(distances, axis=1) >= 0), path
        checks[path.name] = {'N': n, 'D': d, 'K': k, 'Q': len(ids),
                            'nonnegative_pass': True, 'nondecreasing_distance_pass': True,
                            'result_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    required={f'qual_gts_d{d}_k{k}_b{b}.bin' for d in (96,960) for k in (8,32) for b in (1,32)}
    required.update(f'formal_r{r}_gts_{dataset}_k{k}_b{b}.bin'
                    for r in range(1,7) for dataset in ('GIST','Deep') for k in (8,32) for b in (1,32))
    assert required <= checks.keys(), sorted(required-checks.keys())
    (ROOT/'POST_VALIDATION.json').write_text(json.dumps({'caches': caches, 'gts_outputs': checks,
        'scope': 'Offline GTS signed/sorted fields and exact cache partition; native signed/sorted and raw-relative errors are checked by separate validation replays and exhaustive-control runs.'}, indent=2)+'\n')
    print('PASS exact cache partitions and all retained GTS signed/sorted fields')


if __name__ == '__main__':
    if sys.argv[1:] == ['postcheck']:
        postcheck()
    else:
        native_ivf.quality = quality
        native_ivf.main()
