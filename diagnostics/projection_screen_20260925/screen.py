#!/usr/bin/env python3
"""Screen safe low-dimensional L2 bounds against the million-point workloads."""
import json
from pathlib import Path
import numpy as np

ROOT = Path('/home/data/wangxuran/tmp/gts_20260922_cpu_io/leaf_early_l2_20260924/data')
HERE = Path(__file__).resolve().parent
SEED = 250925
TRAIN_N = 8192
TEST_N = 20000
K_LIST = (8, 16, 32, 64, 96, 128, 256)


def pca_basis(train, width, rng):
    centered = train - train.mean(axis=0)
    omega = rng.standard_normal((centered.shape[1], min(width + 16, centered.shape[1])))
    y = centered @ omega
    q, _ = np.linalg.qr(y, mode='reduced')
    b = q.T @ centered
    _, _, vt = np.linalg.svd(b, full_matrices=False)
    p = vt[:width].T.copy()
    assert np.max(np.abs(p.T @ p - np.eye(p.shape[1]))) < 1e-9
    return p


def run_dataset(name, rng):
    fixture = ROOT / name / '1000000' / 'fixtures'
    with (fixture / 'data.f32bin').open('rb') as f:
        dim, n, metric = np.fromfile(f, dtype='<i4', count=3)
    dim, n = int(dim), int(n)
    assert n == 1000000 and int(metric) == 2
    data = np.memmap(fixture / 'data.f32bin', dtype='<f4', mode='r', offset=12, shape=(n, dim))
    radius = float(json.loads((fixture / 'oracle.json').read_text())['radii']['normal'])
    qids = np.loadtxt(fixture / 'queries.qid', dtype=np.int64, skiprows=1)
    assert len(qids) == 8
    sample = rng.choice(n, size=TRAIN_N + TEST_N, replace=False)
    train = np.asarray(data[sample[:TRAIN_N]], dtype=np.float64)
    test = np.asarray(data[sample[TRAIN_N:]], dtype=np.float64)
    queries = np.asarray(data[qids], dtype=np.float64)
    width = min(256, dim)
    basis = pca_basis(train, width, rng)
    projected = test @ basis
    projected_q = queries @ basis
    variance_order = np.argsort(-train.var(axis=0), kind='stable')
    ks = [k for k in K_LIST if k <= dim]
    rows = []
    for qid, qvec, pqvec in zip(qids, queries, projected_q):
        diff = test - qvec
        true2 = np.einsum('ij,ij->i', diff, diff)
        true_empty = true2 > radius ** 2
        assert dim % 32 == 0
        block_sums = np.sum((diff * diff).reshape(TEST_N, dim // 32, 32), axis=2)
        crossed = np.cumsum(block_sums, axis=1) > radius ** 2
        first_crossing = np.argmax(crossed, axis=1)
        baseline_dims = 32 * np.where(np.any(crossed, axis=1), first_crossing + 1, dim // 32)
        pdiff = projected - pqvec
        row = {'qid': int(qid), 'true_empty': int(true_empty.sum()),
               'true_distance_median': float(np.median(np.sqrt(true2))),
               'baseline_scalar_dims': int(baseline_dims.sum()), 'bounds': []}
        for k in ks:
            pca2 = np.einsum('ij,ij->i', pdiff[:, :k], pdiff[:, :k])
            first2 = np.einsum('ij,ij->i', diff[:, :k], diff[:, :k])
            sorted_diff = diff[:, variance_order[:k]]
            variance2 = np.einsum('ij,ij->i', sorted_diff, sorted_diff)
            assert np.all(pca2 <= true2 + 1e-7)
            assert np.all(first2 <= true2 + 1e-7)
            assert np.all(variance2 <= true2 + 1e-7)
            row['bounds'].append({'dimensions': k,
                                  'pca_pruned': int(np.sum(pca2 > radius ** 2)),
                                  'pca_filter_plus_exact_scalar_dims': int(k * TEST_N +
                                      baseline_dims[pca2 <= radius ** 2].sum()),
                                  'original_prefix_pruned': int(np.sum(first2 > radius ** 2)),
                                  'variance_order_pruned': int(np.sum(variance2 > radius ** 2)),
                                  'pca_bound_median': float(np.median(np.sqrt(pca2)))})
        rows.append(row)
    return {'n': n, 'dimensions': dim, 'radius': radius, 'train_points': TRAIN_N,
            'test_points': TEST_N, 'query_ids': qids.astype(int).tolist(), 'rows': rows}


def main():
    rng = np.random.default_rng(SEED)
    out = {'seed': SEED, 'datasets': {}}
    for name in ('GIST', 'Deep'):
        out['datasets'][name] = run_dataset(name, rng)
        rows = out['datasets'][name]['rows']
        print(name, 'true_empty', sum(r['true_empty'] for r in rows), '/', len(rows) * TEST_N, flush=True)
        for i, b in enumerate(rows[0]['bounds']):
            print(b['dimensions'], *(sum(r['bounds'][i][m] for r in rows)
                                     for m in ('pca_pruned', 'original_prefix_pruned', 'variance_order_pruned')),
                  flush=True)
    (HERE / 'EVIDENCE.json').write_text(json.dumps(out, indent=2) + '\n')


if __name__ == '__main__':
    main()
