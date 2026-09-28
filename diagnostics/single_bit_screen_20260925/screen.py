#!/usr/bin/env python3
"""Optimistic one-bit PCA hyperplane screen on the real 1M-point GTS leaves.

For each query, this lets an oracle choose any of 64 PCA axes, either side, and
a query-specific threshold. A fixed precomputed bit can only prune fewer leaves.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


TREE_DTYPE = np.dtype([
    ('pid', '<i4'), ('min_dis', '<f4'), ('size', '<i4'),
    ('lid', '<i4'), ('is_leaf', '<i4'),
])


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def read_tree(path):
    with path.open('rb') as stream:
        n, dim, nodes, height, order = np.fromfile(stream, '<i4', count=5)
        tree = np.fromfile(stream, TREE_DTYPE, count=nodes)
        empty = np.fromfile(stream, '<i4', count=nodes)
        ids = np.fromfile(stream, '<i4', count=n)
        assert not stream.read(1)
    leaves = tree[(tree['is_leaf'] == 1) & (empty == 0)]
    assert n == 1_000_000 and height == 6 and order == 20
    assert len(leaves) == 100_000 and np.all(leaves['size'] == 10)
    assert np.array_equal(np.sort(ids), np.arange(n))
    slots = leaves['lid'][:, None] + np.arange(10)[None, :]
    assert np.array_equal(np.sort(slots.ravel()), np.arange(n))
    return int(n), int(dim), ids[slots]


def main(args):
    result = {'method': 'oracle chooses one of 64 PCA axes, one side, and a '
                         'query-specific threshold; fixed one-bit schemes cannot do better',
              'datasets': {}}
    for name in ('GIST', 'Deep'):
        fixture = args.root / 'data' / name / '1000000' / 'fixtures'
        oracle = json.loads((fixture / 'oracle.json').read_text())
        radius = float(oracle['radii']['normal'])
        qids = oracle['query_source_ids']
        tree_path = args.trees / f'{name}.tree.bin'
        n, dim, leaf_ids = read_tree(tree_path)
        projection_path = args.root / 'projection' / f'{name}.f32bin.pca64'
        with projection_path.open('rb') as stream:
            assert tuple(np.fromfile(stream, '<i4', count=3)) == (n, dim, 64)
        projection = np.memmap(projection_path, '<f4', mode='r', offset=12,
                               shape=(n, 64))
        queries = np.asarray(projection[qids], dtype=np.float64)
        best = np.zeros(len(qids), dtype=np.int64)
        best_axis = np.zeros(len(qids), dtype=np.int64)
        first_axis = []
        fixed_median_axis0 = []
        axis0_threshold = float(np.median(np.asarray(projection[:, 0])))
        for axis in range(64):
            values = np.asarray(projection[leaf_ids, axis])
            low = values.min(axis=1)
            high = values.max(axis=1)
            counts = [max(int(np.count_nonzero(high < queries[i, axis] - radius)),
                          int(np.count_nonzero(low > queries[i, axis] + radius)))
                      for i in range(len(qids))]
            if axis == 0:
                first_axis = counts
                for i in range(len(qids)):
                    q = queries[i, axis]
                    if q > axis0_threshold + radius:
                        count = int(np.count_nonzero(high < axis0_threshold))
                    elif q < axis0_threshold - radius:
                        count = int(np.count_nonzero(low >= axis0_threshold))
                    else:
                        count = 0
                    fixed_median_axis0.append(count)
            for i, count in enumerate(counts):
                if count > best[i]:
                    best[i] = count
                    best_axis[i] = axis
        result['datasets'][name] = {
            'radius': radius, 'leaves': len(leaf_ids), 'leaf_size': 10,
            'source_sha256': oracle['source_sha256'],
            'tree_sha256': sha256(tree_path),
            'projection_sha256': sha256(projection_path),
            'axis0_median_threshold': axis0_threshold,
            'queries': [{'qid': int(qid), 'axis0_leaf_upper': int(first_axis[i]),
                         'fixed_median_axis0_leaf_count': int(fixed_median_axis0[i]),
                         'best_64_axis_leaf_upper': int(best[i]),
                         'best_axis': int(best_axis[i])}
                        for i, qid in enumerate(qids)],
        }
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(args.output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path,
                        default=Path('/home/ls/tmp/gts_pca_end_to_end_20260925'))
    parser.add_argument('--trees', type=Path,
                        default=Path('/tmp/gts_onebit_20260925'))
    parser.add_argument('--output', type=Path, default=Path('EVIDENCE.json'))
    main(parser.parse_args())
