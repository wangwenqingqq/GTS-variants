#!/usr/bin/env python3
"""Small independent fixture checks and complete-run consistency checks."""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile
import numpy as np
import profile_datasets as p


def fixture_checks():
    p.self_test()
    rng = np.random.default_rng(152)
    # Crosses the streaming chunk boundary and includes zeros and signed values.
    x = rng.integers(-3, 4, size=(8200, 3)).astype('<f4')
    x[0] = 0
    ids = np.array([0, 5, 8191, 8192, 8199])
    with tempfile.TemporaryDirectory() as td:
        path = Path(td)/'fixture.fvecs'
        a = np.empty((len(x), 4), '<f4')
        a[:, 0] = np.array([3], '<i4').view('<f4')[0]
        a[:, 1:] = x
        a.tofile(path)
        pool, stat, meta, steps, signals = p.numeric_scan(path, ids, 'vector', Path(td))
        assert np.array_equal(pool, x[ids])
        assert np.isclose(stat['zero_fraction'], (x == 0).mean())
        assert np.isclose(stat['negative_fraction'], (x < 0).mean())
        assert np.allclose(stat['coordinate_mean'], x.astype(float).mean(0))
        assert np.allclose(stat['coordinate_std'], x.astype(float).std(0))
        assert np.allclose(steps, np.linalg.norm(np.diff(x.astype(float), axis=0), axis=1))
        assert meta['sha256'] == hashlib.sha256(path.read_bytes()).hexdigest()
    x = np.array([[0., 0.], [1., 0.], [-1., 0.], [0., 1.], [0., -1.]])
    xx = np.tile(x, (50, 1))
    _, raw = p.geometry(xx, x)
    direct = np.sqrt(((x[:, None, :]-xx[None, :, :])**2).sum(2))
    assert np.allclose(raw['nearest200'], np.sort(direct, axis=1)[:, :200])
    assert np.allclose(raw['mean_distance'], direct.mean(1))
    assert np.all(np.isnan(raw['lid50']))  # Exact duplicates are not dequantized.
    return 'PASS: parsing, stream boundary, moments, distances, ties, invalids, MMD and spectrum'


def validate_run(run):
    env = json.loads((run/'environment.local.json').read_text())
    assert env['source_sha256'] == hashlib.sha256(Path(p.__file__).read_bytes()).hexdigest()
    records = []
    for name in p.FILES:
        root = run/name
        r = json.loads((root/'results.json').read_text())
        assert r['dataset'] == name
        assert r['full']['n'] == (611756 if name == 'Word' else 1000000)
        assert len(r['geometry_runs']) == 3
        for g, seed in zip(r['geometry_runs'], p.SEEDS):
            assert g['seed'] == seed and g['reference_n'] == 50000 and g['query_n'] == 512
            raw = np.load(root/f'geometry_{seed}.npz')
            assert raw['nearest200'].shape == (512, 200)
            assert np.all(np.diff(raw['nearest200'], axis=1) >= 0)
            assert np.all(raw['nearest200'] >= 0)
            assert np.all(raw['self_excluded_count'] == 0)
            for key in ['rc10', 'expansion10', 'gap10', 'distance_cv']:
                v = raw[key]
                valid = v[np.isfinite(v)]
                assert len(valid) == g[key]['valid']
                assert np.isclose(valid.mean(), g[key]['mean'])
                assert np.isclose(np.median(valid), g[key]['p50'])
            if name != 'Word':
                assert np.all(raw['lid50'][np.isfinite(raw['lid50'])] > 0)
            assert np.all(raw['expansion10'][np.isfinite(raw['expansion10'])] >= 1)
            plan = np.load(root/'sample_plan.npz')
            rid, qid = plan[f'ref_{seed}'], plan[f'query_{seed}']
            assert len(np.unique(rid)) == 50000 and len(np.unique(qid)) == 512
            assert not np.intersect1d(rid, qid).size
            assert np.all(rid < r['full']['n']) and np.all(qid < r['full']['n'])
        if r['kind'] == 'vector':
            assert 0 <= r['full']['zero_fraction'] <= 1
            assert 0 <= r['full']['hoyer']['mean'] <= 1
        if r['kind'] != 'word':
            c = r['covariance_sample']
            assert 1 <= c['pca90'] <= c['pca95'] <= r['full']['dimension']
            assert np.isclose(sum(c['variance_shares']), 1)
        assert r['row_order']['adjacent_distance']['count'] == r['full']['n']-1
        assert r['row_order']['random_pair_distance']['count'] == 20000
        assert 'N/A' in r['row_order']['temporal_periodicity']
        records.append({'dataset': name, 'status': 'PASS', 'input_sha256': r['source']['sha256'],
                        'result_sha256': hashlib.sha256((root/'results.json').read_bytes()).hexdigest()})
    return records


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', type=Path)
    a = ap.parse_args()
    res = {'fixtures': fixture_checks()}
    if a.run:
        res['datasets'] = validate_run(a.run)
        (a.run/'VALIDATION.json').write_text(json.dumps(res, indent=2)+'\n')
    print(json.dumps(res, indent=2))
