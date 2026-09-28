#!/usr/bin/env python3
"""Screen multi-pivot metric lower bounds on actual GTS candidate leaves."""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'pruning_bound_20260924'))
from analyze_tree import ROOT, read_candidates, read_tree  # noqa: E402

SEED = 240926
LEAVES_PER_QUERY = 256
MAX_PIVOTS = 64
PIVOT_COUNTS = (1, 2, 4, 8, 16, 32, 64)


def distances(a, b):
    """Euclidean distance matrix, using float64 arithmetic."""
    aa = np.einsum('ij,ij->i', a, a)
    bb = np.einsum('ij,ij->i', b, b)
    squared = np.maximum(aa[:, None] + bb[None, :] - 2 * a @ b.T, 0)
    return np.sqrt(squared)


def farthest_first(data, rng):
    pool_ids = rng.choice(len(data), size=512, replace=False)
    pool = np.asarray(data[pool_ids], dtype=np.float64)
    d = distances(pool, pool)
    chosen = [0]
    nearest = d[0].copy()
    for _ in range(1, MAX_PIVOTS):
        nearest[chosen[-1]] = -1
        new = int(np.argmax(nearest))
        assert new not in chosen
        chosen.append(new)
        nearest = np.minimum(nearest, d[new])
    return pool_ids[chosen]


def screen(ds, rng):
    base = ROOT / 'data' / ds / '1000000'
    run = base / 'runs' / 'prune_dump_Q'
    n, dim, tree, _empty, id_list = read_tree(run / 'result.tree.bin')
    fixture = base / 'fixtures'
    radius = float(json.loads((fixture / 'oracle.json').read_text())['radii']['normal'])
    data = np.memmap(fixture / 'data.f32bin', mode='r', dtype='<f4', offset=12, shape=(n, dim))
    candidate_lists = read_candidates(run / 'result.candidates.bin')
    sampled = [rng.choice(cands, size=LEAVES_PER_QUERY, replace=False)
               for _qid, cands in candidate_lists]
    sampled_all = np.concatenate(sampled)
    assert np.all(tree['size'][sampled_all] == 10)
    leaf_point_ids = id_list[tree['lid'][sampled_all, None] + np.arange(10)[None, :]]
    points = np.asarray(data[leaf_point_ids.reshape(-1)], dtype=np.float64)
    queries = np.asarray(data[[qid for qid, _ in candidate_lists]], dtype=np.float64)
    exact = distances(queries, points)
    exact = exact.reshape(len(queries), len(sampled_all), 10)
    own = np.array([exact[i, i * LEAVES_PER_QUERY:(i + 1) * LEAVES_PER_QUERY].min(axis=1)
                    for i in range(len(queries))])
    empty = own > radius
    strategies = {
        'random': rng.choice(n, size=MAX_PIVOTS, replace=False),
        'farthest_first_512_pool': farthest_first(data, rng),
    }
    result = {'n': n, 'dimensions': dim, 'radius': radius,
              'candidate_counts': [len(cands) for _, cands in candidate_lists],
              'sampled_candidate_leaves': int(len(sampled_all)),
              'empty_sampled_leaves': int(empty.sum()),
              'median_true_leaf_min': float(np.median(own)),
              'query_ids': [int(qid) for qid, _ in candidate_lists],
              'strategies': {}}
    for name, pivot_ids in strategies.items():
        pivot_points = np.asarray(data[pivot_ids], dtype=np.float64)
        pd = distances(points, pivot_points).reshape(len(sampled_all), 10, MAX_PIVOTS)
        qp = distances(queries, pivot_points)
        leaves = np.stack([pd[i * LEAVES_PER_QUERY:(i + 1) * LEAVES_PER_QUERY]
                           for i in range(len(queries))])
        lo = leaves.min(axis=2)
        hi = leaves.max(axis=2)
        dq = qp[:, None, :]
        interval_gap = np.maximum(np.maximum(lo - dq, dq - hi), 0)
        interval_bound = np.maximum.accumulate(interval_gap, axis=-1)
        point_gap = np.abs(leaves - qp[:, None, None, :])
        # The point bound for k pivots is min over leaf points of max over the first k pivots.
        point_bound = np.maximum.accumulate(point_gap, axis=-1).min(axis=2)
        assert np.all(interval_bound <= own[:, :, None] + 1e-7)
        assert np.all(point_bound <= own[:, :, None] + 1e-7)
        levels = []
        for k in PIVOT_COUNTS:
            node_pruned = interval_bound[:, :, k - 1] > radius
            point_pruned = point_bound[:, :, k - 1] > radius
            assert not np.any(node_pruned & ~empty)
            assert not np.any(point_pruned & ~empty)
            levels.append({'pivots': k,
                           'interval_pruned': int(node_pruned.sum()),
                           'point_table_pruned': int(point_pruned.sum()),
                           'median_interval_bound': float(np.median(interval_bound[:, :, k - 1])),
                           'median_point_table_bound': float(np.median(point_bound[:, :, k - 1])),
                           'interval_pruned_per_query': node_pruned.sum(axis=1).astype(int).tolist(),
                           'point_table_pruned_per_query': point_pruned.sum(axis=1).astype(int).tolist()})
        result['strategies'][name] = {'pivot_ids': pivot_ids.astype(int).tolist(),
                                      'levels': levels}
    return result


def main():
    rng = np.random.default_rng(SEED)
    results = {'seed': SEED, 'candidate_leaves_per_query': LEAVES_PER_QUERY,
               'pivots': list(PIVOT_COUNTS), 'datasets': {}}
    for ds in ('GIST', 'Deep'):
        results['datasets'][ds] = screen(ds, rng)
        x = results['datasets'][ds]
        print(ds, 'empty', x['empty_sampled_leaves'], '/', x['sampled_candidate_leaves'], flush=True)
        for name, value in x['strategies'].items():
            print(' ', name, [(r['pivots'], r['interval_pruned'], r['point_table_pruned'])
                               for r in value['levels']], flush=True)
    (HERE / 'EVIDENCE.json').write_text(json.dumps(results, indent=2) + '\n')


if __name__ == '__main__':
    main()
