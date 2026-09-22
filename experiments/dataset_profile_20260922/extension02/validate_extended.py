#!/usr/bin/env python3
"""Independent small-matrix oracles and complete-run consistency gates."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from scipy.spatial.distance import cdist
import profile_extended as e


def fixtures():
    e.self_test()
    rng = np.random.default_rng(185)
    # Compare each optimized metric with independent scalar-library oracles.
    for metric, x in [('Angular-degrees', rng.normal(size=(253, 7))),
                      ('Tanimoto', rng.integers(0, 2, (253, 7)).astype(float)),
                      ('Euclidean', rng.normal(size=(253, 7)))]:
        direct = cdist(x[:5], x, 'cosine' if metric == 'Angular-degrees' else
                       'jaccard' if metric == 'Tanimoto' else 'euclidean')
        if metric == 'Angular-degrees':
            direct = np.degrees(np.arccos(np.clip(1-direct, -1, 1)))
        stats, raw = e.geometry(x, x[:5], metric, np.arange(253), np.arange(5))
        for i in range(5):
            v = np.delete(direct[i], i)
            assert np.allclose(raw['nearest200'][i], np.sort(v)[:200], atol=2e-6)
            assert np.isclose(raw['mean_distance'][i], v.mean())
        assert np.all(raw['self_excluded_count'] == 1)
    print('INDEPENDENT_METRIC_ORACLES_PASS')


def validate(run, previous_run):
    env = json.loads((run/'environment.local.json').read_text())
    for key, path in [('source_sha256', Path(e.__file__)), ('helper_sha256', Path(e.p.__file__)),
                      ('contract_sha256', Path(e.__file__).with_name('CONTRACT_EXTENDED.md'))]:
        assert env[key] == hashlib.sha256(path.read_bytes()).hexdigest(), key
    records = []
    for folder in sorted(run.iterdir()):
        if not folder.is_dir():
            continue
        name = folder.name
        r = json.loads((folder/'results.json').read_text())
        assert r['dataset'] == name and r['contract'] == 'native_metric_v2'
        n = r['full']['n']
        expected_n = 611756 if name == 'Word' else 1000000
        if name in e.EXTRA:
            expected_n = e.EXTRA[name][-1][1]
        assert n == expected_n
        assert len(r['geometry_runs']) == 3
        plan = np.load(folder/'sample_plan.npz')
        expected_plan = e.plan(n)
        for idx, (g, seed) in enumerate(zip(r['geometry_runs'], e.p.SEEDS)):
            rid, qid = plan[f'ref_{seed}'], plan[f'query_{seed}']
            assert np.array_equal(rid, expected_plan[0][idx][0])
            assert np.array_equal(qid, expected_plan[0][idx][1])
            assert len(np.unique(rid)) == 20000 and len(np.unique(qid)) == 512
            assert not np.intersect1d(rid, qid).size and min(rid.min(), qid.min()) >= 0
            assert max(rid.max(), qid.max()) < n
            assert (g['seed'], g['reference_n'], g['query_n']) == (seed, 20000, 512)
            raw = np.load(folder/f'geometry_{seed}.npz')
            assert raw['nearest200'].shape == (512, 200)
            assert np.isfinite(raw['nearest200']).all() and np.all(raw['nearest200'] >= 0)
            assert np.all(np.diff(raw['nearest200'], axis=1) >= 0)
            assert np.all(raw['self_excluded_count'] == 0)
            if r['metric'] in ['Levenshtein', 'Tanimoto']:
                assert 'lid50' not in raw.files and 'lid50' not in g
            if r['metric'] == 'Tanimoto':
                assert np.all(raw['nearest200'] <= 1)
            if r['metric'] == 'Angular-degrees':
                assert np.all(raw['nearest200'] <= 180)
            for k in raw.files:
                if k == 'nearest200':
                    continue
                actual = e.p.summary(raw[k])
                for key, v in actual.items():
                    assert (v is None and g[k][key] is None) or np.isclose(v, g[k][key]), (name, k, key)
            assert np.all(raw['expansion10'][np.isfinite(raw['expansion10'])] >= 1)
        assert np.array_equal(plan['pca_ids'], expected_plan[1])
        assert np.array_equal(plan['graph_ids'], expected_plan[2])
        assert np.array_equal(plan['random_pairs'], expected_plan[3])
        if name in e.p.FILES:
            oldpath = previous_run/name/'results.json'
            old = json.loads(oldpath.read_text())
            assert r['reused_v1_result_sha256'] == hashlib.sha256(oldpath.read_bytes()).hexdigest()
            assert r['source']['sha256'] == old['source']['sha256']
            for key in ['full', 'row_order', 'hubness_sample', 'covariance_sample']:
                assert r.get(key) == old.get(key), key
        assert r['row_order']['adjacent_distance']['count'] == n-1
        assert r['row_order']['random_pair_distance']['count'] == 20000
        assert 'N/A' in r['row_order']['temporal_periodicity']
        if r['kind'] != 'word':
            c = r['covariance_sample']
            assert 1 <= c['pca90'] <= c['pca95'] <= r['full']['dimension']
            assert np.isclose(sum(c['variance_shares']), 1)
            assert 0 <= r['full']['zero_fraction'] <= 1
        nq = r['native_query_profile']
        native = np.load(folder/'native_queries.npz')
        assert nq['sampled_queries'] == min(512, nq['available_queries'])
        assert native['nearest200'].shape == (nq['sampled_queries'], 200)
        for key in native.files:
            if key in ['nearest200', 'selected_query_positions']:
                continue
            actual = e.p.summary(native[key])
            for k, v in actual.items():
                assert (v is None and nq[key][k] is None) or np.isclose(v, nq[key][k])
        records.append(dict(dataset=name, status='PASS', n=n, input_sha256=r['source']['sha256'],
            result_sha256=hashlib.sha256((folder/'results.json').read_bytes()).hexdigest()))
    assert records
    return records


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', type=Path)
    ap.add_argument('--previous-run', type=Path)
    args = ap.parse_args()
    fixtures()
    if args.run:
        records = validate(args.run, args.previous_run)
        result = dict(fixtures='PASS', datasets=records, scope='listed datasets only')
        e.p.write_json(args.run/'VALIDATION.json', result)
        print(json.dumps(result, indent=2))
