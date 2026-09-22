#!/usr/bin/env python3
"""Read-only, CPU-only characterization under CONTRACT.md; no input defaults."""
import argparse
from collections import Counter
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import sys
import time

import numpy as np
import scipy
from scipy.spatial.distance import cdist
from scipy.stats import ks_2samp
import rapidfuzz
from rapidfuzz import process
from rapidfuzz.distance import Levenshtein

SEEDS = [20260922, 20260923, 20260924]
FILES = {
    'SIFT-1M': ('sift1m/sift_base.fvecs', 'sift1m/sift_query.fvecs', 'vector'),
    'Deep-1M': ('deep1m/deep1M_base.fvecs', 'deep1m/deep1M_queries.fvecs', 'vector'),
    'GIST-1M': ('gist1m/gist_base.fvecs', 'gist1m/gist_query.fvecs', 'vector'),
    'Word': ('word/word.txt', 'word/word_qid.txt', 'word'),
    'T-loc-1M': ('T-loc/1_million_location_gts.txt', 'T-loc/tloc_1m_qid.txt', 'spatial'),
}


def summary(a):
    a = np.asarray(a, dtype=np.float64)
    v = a[np.isfinite(a)]
    return {'count': int(a.size), 'valid': int(v.size), 'invalid': int(a.size-v.size),
            'mean': float(v.mean()) if v.size else None,
            'std': float(v.std()) if v.size else None,
            **dict(zip(['min', 'p10', 'p50', 'p90', 'p95', 'p99', 'max'],
                       map(float, np.percentile(v, [0, 10, 50, 90, 95, 99, 100]))
                       if v.size else [None]*7))}


def divide(a, b):
    a, b = np.broadcast_arrays(np.asarray(a, float), np.asarray(b, float))
    return np.divide(a, b, out=np.full(a.shape, np.nan), where=b > 0)


def hoyer(x):
    d = x.shape[1]
    return (np.sqrt(d)-divide(np.abs(x).sum(1), np.linalg.norm(x, axis=1)))/(np.sqrt(d)-1)


def lid(r, k):
    a = r[:, :k]
    good = (a[:, 0] > 0) & (a[:, -1] > 0)
    ans = np.full(len(a), np.nan)
    logsum = np.log(a[good]/a[good, -1:]).sum(1)
    ans[good] = divide(k, -logsum)
    return ans


def entropy(counts):
    a = np.asarray(list(counts), float)
    p = a[a > 0]/a.sum()
    return float(-np.sum(p*np.log2(p)))


def write_json(path, obj):
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(obj, indent=2, allow_nan=False)+'\n')
    tmp.replace(path)


def fingerprint(path):
    stat = path.stat()
    h = hashlib.sha256()
    with path.open('rb') as f:
        while b := f.read(8*1024*1024):
            h.update(b)
    assert (stat.st_size, stat.st_mtime_ns) == (path.stat().st_size, path.stat().st_mtime_ns)
    return {'relative_name': path.name, 'bytes': stat.st_size,
            'mtime_ns': stat.st_mtime_ns, 'sha256': h.hexdigest()}


def fvec_shape(path):
    with path.open('rb') as f:
        d = int(np.frombuffer(f.read(4), '<i4')[0])
    assert 0 < d < 100000
    n, rem = divmod(path.stat().st_size, 4*(d+1))
    assert rem == 0 and n > 0, (path, n, rem)
    return n, d


def read_fvec(path):
    n, d = fvec_shape(path)
    a = np.fromfile(path, '<f4').reshape(n, d+1)
    assert np.all(a[:, :1].copy().view('<i4') == d)
    assert np.isfinite(a[:, 1:]).all()
    return a[:, 1:].copy()


def distances(a, b, word=False):
    if word:
        return process.cdist(a, b, scorer=Levenshtein.distance, dtype=np.int32, workers=1).astype(float)
    return cdist(np.asarray(a, float), np.asarray(b, float), metric='euclidean')


def make_plan(n):
    runs = []
    ids = []
    for seed in SEEDS:
        chosen = np.random.default_rng(seed).choice(n, 50512, replace=False)
        runs.append((chosen[:50000], chosen[50000:]))
        ids.append(chosen)
    rng = np.random.default_rng(8402)
    pca = rng.choice(n, 10000, replace=False)
    graph = rng.choice(n, 2048, replace=False)
    pairs = rng.integers(0, n, (20000, 2))
    pairs[:, 1] = np.where(pairs[:, 1] == pairs[:, 0], (pairs[:, 1]+1) % n, pairs[:, 1])
    return runs, pca, graph, pairs, np.unique(np.concatenate(ids+[pca, graph, pairs.ravel()]))


def numeric_scan(path, sampled_ids, word_kind, out):
    start = time.monotonic()
    spatial = word_kind == 'spatial'
    before = path.stat()
    if spatial:
        with path.open() as f:
            header = list(map(int, f.readline().split()))
            n, d = header[1], header[0]
            full = np.loadtxt(f, dtype=np.float64)
        assert full.shape == (n, d), full.shape
    else:
        n, d = fvec_shape(path)
    pool = np.empty((len(sampled_ids), d), dtype=np.float64 if spatial else np.float32)
    norms, hs, steps = np.empty(n), np.empty(n), np.empty(n-1)
    means, m2 = np.zeros(d), np.zeros(d)
    minima, maxima = np.full(d, np.inf), np.full(d, -np.inf)
    zero = negative = allzero = processed = 0
    nearzero = np.zeros(3, np.int64)
    digest = hashlib.sha256()
    last = None
    with path.open('rb') as f:
        for lo in range(0, n, 8192):
            hi = min(n, lo+8192)
            if spatial:
                x = full[lo:hi]
            else:
                b = f.read((hi-lo)*(d+1)*4)
                assert len(b) == (hi-lo)*(d+1)*4, 'short fvecs read'
                digest.update(b)
                a = np.frombuffer(b, '<f4').reshape(-1, d+1)
                assert np.all(a[:, :1].copy().view('<i4') == d), 'inconsistent row dimension'
                x = a[:, 1:].astype(np.float64)
            assert np.isfinite(x).all(), 'non-finite numeric input'
            i, j = np.searchsorted(sampled_ids, [lo, hi])
            pool[i:j] = x[sampled_ids[i:j]-lo]
            norm = np.linalg.norm(x, axis=1)
            norms[lo:hi] = norm
            hs[lo:hi] = hoyer(x)
            zero += int((x == 0).sum())
            negative += int((x < 0).sum())
            allzero += int((norm == 0).sum())
            absx = np.abs(x)
            for z, eps in enumerate([.001, .01, .05]):
                nearzero[z] += int((absx <= eps*(norm/np.sqrt(d))[:, None]).sum())
            minima = np.minimum(minima, x.min(0))
            maxima = np.maximum(maxima, x.max(0))
            delta = x.mean(0)-means
            nn = len(x)
            m2 += ((x-x.mean(0))**2).sum(0)+delta**2*processed*nn/(processed+nn)
            means += delta*nn/(processed+nn)
            processed += nn
            steps[lo:hi-1] = np.linalg.norm(np.diff(x, axis=0), axis=1)
            if last is not None:
                steps[lo-1] = np.linalg.norm(x[0]-last)
            last = x[-1].copy()
            if lo % 131072 == 0:
                print(f'{path.name}: scanned {hi}/{n}', flush=True)
        if not spatial:
            assert f.read(1) == b''
    after = path.stat()
    assert (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns), 'input changed'
    meta = fingerprint(path) if spatial else {
        'relative_name': path.name, 'bytes': before.st_size, 'mtime_ns': before.st_mtime_ns,
        'sha256': digest.hexdigest()}
    stats = {'n': n, 'dimension': d, 'nonfinite_values': 0, 'coordinate_count': n*d,
             'zero_fraction': zero/(n*d), 'negative_fraction': negative/(n*d),
             'allzero_rows': allzero, 'min': float(minima.min()), 'max': float(maxima.max()),
             'constant_dimensions': int((minima == maxima).sum()),
             'coordinate_mean': means.tolist(), 'coordinate_std': np.sqrt(m2/n).tolist(),
             'coordinate_min': minima.tolist(), 'coordinate_max': maxima.tolist(),
             'norm': summary(norms), 'full_scan_seconds': time.monotonic()-start}
    if spatial:
        stats['duplicate_fraction_full'] = 1-len(np.unique(full, axis=0))/n
        stats['spatial_grid'] = {}
        for bins in [16, 32, 64, 128]:
            counts, _, _ = np.histogram2d(full[:, 0], full[:, 1], bins=bins)
            stats['spatial_grid'][str(bins)] = {
                'occupied_fraction': float((counts > 0).mean()),
                'normalized_entropy': entropy(counts.ravel())/np.log2(bins*bins),
                'max_cell_share': float(counts.max()/n)}
        signals = {'coordinate_0': full[:, 0], 'coordinate_1': full[:, 1]}
    else:
        stats['hoyer'] = summary(hs)
        stats['relative_nearzero_fraction'] = dict(zip(['0.001', '0.01', '0.05'], (nearzero/(n*d)).tolist()))
        signals = {'l2_norm': norms}
    return pool, stats, meta, steps, signals


def read_words(path):
    raw = path.read_bytes()
    encoding = 'utf-8'
    try:
        text = raw.decode(encoding)
    except UnicodeDecodeError:
        encoding = 'latin-1'
        text = raw.decode(encoding)
    lines = [s.removesuffix('\r') for s in text.split('\n')]
    if text.endswith('\n'):
        lines.pop()
    header = list(map(int, lines.pop(0).split()))
    assert len(lines) == header[1]
    lengths = np.asarray(list(map(len, lines)))
    assert lengths.max() <= header[0]
    return lines, lengths, encoding


def word_scan(path):
    words, lengths, encoding = read_words(path)
    n = len(words)
    chars = Counter(c for s in words for c in s)
    stat = {'n': n, 'max_length_header': 34, 'encoding': encoding,
            'length': summary(lengths), 'empty_words': int((lengths == 0).sum()),
            'nonascii_characters': sum(v for c, v in chars.items() if ord(c) > 127),
            'duplicate_fraction_full': 1-len(set(words))/n,
            'character_vocabulary': len(chars), 'character_entropy_bits': entropy(chars.values()),
            'lexicographic_nondecreasing_fraction': sum(a <= b for a, b in zip(words, words[1:]))/(n-1)}
    for size in [2, 3]:
        counts = Counter(s[i:i+size] for s in words for i in range(len(s)-size+1))
        stat[f'{size}gram_vocabulary'] = len(counts)
        stat[f'{size}gram_entropy_bits'] = entropy(counts.values())
    steps = np.fromiter((Levenshtein.distance(a, b) for a, b in zip(words, words[1:])), float, n-1)
    return words, stat, fingerprint(path), steps, {'length': lengths.astype(float)}


def geometry(ref, queries, word=False, ref_ids=None, query_ids=None):
    n = len(queries)
    near = np.empty((n, 200))
    avg, std, ties, excluded = np.empty(n), np.empty(n), np.empty(n), np.zeros(n, int)
    for lo in range(0, n, 32):
        hi = min(n, lo+32)
        d = distances(queries[lo:hi], ref, word)
        mask = np.zeros(d.shape, bool)
        if query_ids is not None:
            mask = query_ids[lo:hi, None] == ref_ids[None, :]
            excluded[lo:hi] = mask.sum(1)
        for j in range(hi-lo):
            valid = d[j, ~mask[j]]
            avg[lo+j], std[lo+j] = valid.mean(), valid.std()
            nearest = np.sort(np.partition(valid, 199)[:200])
            near[lo+j] = nearest
            ties[lo+j] = np.count_nonzero(valid == nearest[9])/len(valid)
    raw = {'nearest200': near, 'mean_distance': avg, 'std_distance': std, 'boundary10_tie_fraction': ties,
           'self_excluded_count': excluded, 'distance_cv': divide(std, avg)}
    for k in [1, 10, 100]:
        raw[f'rc{k}'] = divide(avg, near[:, k-1])
    for k in [10, 50, 100]:
        raw[f'expansion{k}'] = divide(near[:, 2*k-1], near[:, k-1])
    raw['gap10'] = divide(near[:, 10]-near[:, 9], near[:, 9])
    if not word:
        for k in [20, 50, 100]:
            raw[f'lid{k}'] = lid(near, k)
    stats = {key: summary(v) for key, v in raw.items() if key != 'nearest200'}
    stats['nearest_distance'] = summary(near[:, 0])
    stats['r10'] = summary(near[:, 9])
    stats['r100'] = summary(near[:, 99])
    stats['zero_nearest_fraction'] = float((near[:, 0] == 0).mean())
    return stats, raw


def covariance_profile(x):
    x = np.asarray(x, float)
    x = x-x.mean(0)
    vals = np.linalg.eigvalsh(x.T@x/(len(x)-1)).clip(0)[::-1]
    if vals.sum() == 0:
        return {'status': 'undefined_zero_variance'}
    p = vals/vals.sum()
    return {'rows': len(x), 'pca90': int(np.searchsorted(p.cumsum(), .90)+1),
            'pca95': int(np.searchsorted(p.cumsum(), .95)+1), 'pc1_share': float(p[0]),
            'covariance_effective_rank': float(np.exp(-np.sum(p[p > 0]*np.log(p[p > 0])))),
            'variance_shares': p.tolist()}


def hubness(x, word=False):
    d = distances(x, x, word)
    np.fill_diagonal(d, np.inf)
    radius = np.partition(d, 9, axis=1)[:, 9]
    strict, tied = d < radius[:, None], d == radius[:, None]
    count = strict.sum(0)+(tied*((10-strict.sum(1))/tied.sum(1))[:, None]).sum(0)
    assert np.isclose(count.sum(), len(x)*10)
    sd = count.std()
    top = int(np.ceil(len(x)*.01))
    return {'sample_n': len(x), 'k': 10, 'tie_policy': 'fractional_at_boundary',
            'incoming': summary(count), 'skewness': float(np.mean(((count-count.mean())/sd)**3)) if sd else None,
            'top1pct_share': float(np.sort(count)[-top:].sum()/count.sum())}


def mmd_test(a, b, seed=419):
    z = np.concatenate([a, b]).astype(float)
    n, m = len(a), len(b)
    dd = cdist(z, z, metric='sqeuclidean')
    vals = dd[np.triu_indices(len(z), 1)]
    positive = vals[vals > 0]
    if not len(positive):
        return {'status': 'undefined_zero_bandwidth'}
    sigma2 = float(np.median(positive))
    kernel = np.exp(-dd/(2*sigma2))
    weights = np.r_[np.full(n, 1/n), np.full(m, -1/m)]
    obs = float(weights@kernel@weights)
    rng = np.random.default_rng(seed)
    w = np.column_stack([rng.permutation(weights) for _ in range(99)])
    null = np.sum(w*(kernel@w), axis=0)
    return {'n_query': n, 'n_base': m, 'sigma_squared': sigma2, 'biased_mmd_squared': obs,
            'permutation_p': float((1+np.sum(null >= obs))/100), 'permutations': 99,
            'null': summary(null), 'exploratory_no_multiple_testing_claim': True}


def scalar_window(y):
    y = np.asarray(y, float)
    t = np.arange(len(y), dtype=float)
    t -= t.mean()
    y = y-y.mean()
    y -= t*np.dot(t, y)/np.dot(t, t)
    energy = np.dot(y, y)
    if energy == 0:
        return {'acf1': None, 'acf_peak_lag_2_1024': None, 'acf_peak_value': None,
                'dominant_bin_period_rows': None, 'dominant_bin_power_share': None}
    ac = np.fft.irfft(np.abs(np.fft.rfft(y, 2*len(y)))**2, 2*len(y))[:1025]/energy
    power = np.abs(np.fft.rfft(y*np.hanning(len(y))))**2
    power[0] = 0
    peak = int(np.argmax(power))
    lag = int(np.argmax(ac[2:])+2)
    return {'acf1': float(ac[1]), 'acf_peak_lag_2_1024': lag, 'acf_peak_value': float(ac[lag]),
            'dominant_bin_period_rows': len(y)/peak,
            'dominant_bin_power_share': float(power[peak]/power.sum())}


def order_profile(steps, random_pair_dist, signals):
    median = np.median(steps)
    mad = np.median(np.abs(steps-median))
    threshold = median+6*1.4826*mad
    ans = {'semantics': 'file_row_order_not_time', 'adjacent_distance': summary(steps),
           'random_pair_distance': summary(random_pair_dist),
           'adjacent_to_random_median_ratio': float(median/np.median(random_pair_dist)) if np.median(random_pair_dist) > 0 else None,
           'mad_step_threshold': float(threshold) if mad > 0 else None,
           'excess_step_fraction': float((steps > threshold).mean()) if mad > 0 else None,
           'temporal_periodicity': 'N/A: no timestamp or verified time axis', 'signals': {}}
    for key, y in signals.items():
        blocks = y[:len(y)//5000*5000].reshape(-1, 5000)
        means, var = blocks.mean(1), blocks.var(1)
        sd = y.std()
        rng = np.random.default_rng(944)
        windows = []
        for lo in np.linspace(0, len(y)-8192, 8).astype(int):
            v = y[lo:lo+8192]
            windows.append({'start_row': int(lo), 'rows': 8192, 'original': scalar_window(v),
                            'shuffled': scalar_window(rng.permutation(v))})
        ans['signals'][key] = {'block_rows': 5000, 'window_means': means.tolist(),
                              'window_variances': var.tolist(),
                              'max_level_shift_in_global_sd': float(np.max(np.abs(np.diff(means)))/sd) if sd else None,
                              'spectral_windows': windows}
    return ans


def run_one(root, name, out):
    rel, queryrel, kind = FILES[name]
    path, qp = root/rel, root/queryrel
    word = kind == 'word'
    if word:
        allx, stat, meta, steps, signals = word_scan(path)
        n = len(allx)
    else:
        if kind == 'vector':
            n, _ = fvec_shape(path)
        else:
            with path.open() as f:
                n = int(f.readline().split()[1])
    runs, pca_ids, graph_ids, pairs, pool_ids = make_plan(n)
    if not word:
        pool, stat, meta, steps, signals = numeric_scan(path, pool_ids, kind, out)
    def get(ids):
        ids = np.asarray(ids)
        return [allx[int(i)] for i in ids] if word else pool[np.searchsorted(pool_ids, ids)]
    result = {'dataset': name, 'kind': kind, 'metric': 'Levenshtein' if word else 'Euclidean',
              'source_relative_path': rel, 'source': meta, 'full': stat, 'geometry_runs': [],
              'contract': 'native_metric_v1', 'temporal_burstiness': 'N/A: no arrival trace'}
    write_json(out/'checkpoint.json', {'stage': 'full_scan_complete', 'dataset': name, 'full': stat})
    if not word:
        result['covariance_sample'] = covariance_profile(get(pca_ids))
        if kind == 'vector':
            ref0 = get(runs[0][0])
            result['vector_duplicate_sample'] = {'rows': len(ref0),
                'duplicate_fraction': 1-len(np.unique(ref0, axis=0))/len(ref0)}
    result['hubness_sample'] = hubness(get(graph_ids), word)
    if word:
        rnd = np.fromiter((Levenshtein.distance(allx[a], allx[b]) for a, b in pairs), float, len(pairs))
    else:
        rnd = np.linalg.norm(get(pairs[:, 0]).astype(float)-get(pairs[:, 1]).astype(float), axis=1)
    result['row_order'] = order_profile(steps, rnd, signals)
    np.savez_compressed(out/'sample_plan.npz', pool_ids=pool_ids, pca_ids=pca_ids,
                        graph_ids=graph_ids, random_pairs=pairs,
                        **{f'ref_{s}': r for s, (r, q) in zip(SEEDS, runs)},
                        **{f'query_{s}': q for s, (r, q) in zip(SEEDS, runs)})
    for seed, (rid, qid) in zip(SEEDS, runs):
        print(f'{name}: geometry uniform seed={seed}', flush=True)
        assert np.intersect1d(rid, qid).size == 0
        stats, raw = geometry(get(rid), get(qid), word)
        result['geometry_runs'].append({'seed': seed, 'reference_n': len(rid), 'query_n': len(qid), **stats})
        np.savez_compressed(out/f'geometry_{seed}.npz', **raw)
        write_json(out/'checkpoint.json', {'stage': f'geometry_{seed}_complete', 'dataset': name})
    print(f'{name}: native query diagnostics', flush=True)
    rng = np.random.default_rng(SEEDS[0]+71)
    qmeta = fingerprint(qp)
    rid = runs[0][0]
    if kind == 'vector':
        native = read_fvec(qp)
        selected = rng.choice(len(native), 512, replace=False)
        q = native[selected]
        stats, raw = geometry(get(rid), q)
        native_count = len(native)
        native_type = 'external_query_file'
    else:
        with qp.open() as f:
            declared = int(f.readline())
            native_ids = np.loadtxt(f, dtype=np.int64)
        assert len(native_ids) == declared and np.all((native_ids >= 0) & (native_ids < n))
        selected = rng.choice(len(native_ids), 512, replace=False)
        queryids = native_ids[selected]
        native_count = len(native_ids)
        native_type = 'base_object_ids'
        if word:
            q = get(queryids)
        else:
            with path.open() as f:
                next(f)
                full = np.loadtxt(f)
            q = full[queryids]
        stats, raw = geometry(get(rid), q, word, rid, queryids)
        result['native_id_range'] = [int(native_ids.min()), int(native_ids.max())]
        result['native_ids_sha256'] = hashlib.sha256(native_ids.astype('<i8').tobytes()).hexdigest()
    result['native_query_profile'] = {'query_source': qmeta, 'source_type': native_type,
                                    'available_queries': native_count, 'sampled_queries': 512, **stats}
    np.savez_compressed(out/'native_queries.npz', selected_query_positions=selected, **raw)
    if word:
        result['native_query_length_shift'] = {'ks_distance': float(ks_2samp(
            list(map(len, q)), list(map(len, get(pca_ids[:512])))).statistic),
            'query_length': summary(list(map(len, q))), 'base_length': summary(list(map(len, get(pca_ids[:512]))))}
    else:
        result['native_query_mmd'] = mmd_test(q, get(pca_ids[:512]))
    write_json(out/'results.json', result)
    print(f'{name}: complete', flush=True)
    return result


def self_test():
    import tempfile
    assert np.allclose(hoyer(np.array([[1., 1.], [1., 0.]])), [0, 1])
    assert np.isnan(hoyer(np.zeros((1, 2)))[0])
    assert Levenshtein.distance('kitten', 'sitting') == 3
    assert np.allclose(distances([[0, 0]], [[3, 4]]), 5)
    assert distances(['kitten'], ['sitting'], True)[0, 0] == 3
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp)/'test.fvecs'
        x = np.arange(6, dtype='<f4').reshape(2, 3)
        with p.open('wb') as f:
            for row in x:
                f.write(np.array([3], '<i4').tobytes()+row.tobytes())
        assert fvec_shape(p) == (2, 3) and np.array_equal(read_fvec(p), x)
        bad = bytearray(p.read_bytes()); bad[16:20] = np.array([4], '<i4').tobytes(); p.write_bytes(bad)
        try:
            read_fvec(p)
        except AssertionError:
            pass
        else:
            raise AssertionError('malformed row accepted')
    rr = np.arange(1, 201, dtype=float)[None, :]
    assert lid(rr, 100)[0] > 0 and np.isnan(lid(rr*0, 100)[0])
    h = hubness(['a']*32, True)
    assert np.isclose(h['incoming']['mean'], 10) and h['skewness'] is None
    rng = np.random.default_rng(91)
    a, b = rng.normal(size=(64, 2)), rng.normal(size=(64, 2))+8
    assert mmd_test(a, b)['permutation_p'] == .01
    y = np.sin(2*np.pi*np.arange(8192)/64)
    assert scalar_window(y)['dominant_bin_period_rows'] == 64
    assert scalar_window(y)['dominant_bin_power_share'] > scalar_window(rng.permutation(y))['dominant_bin_power_share']
    ref = np.arange(250.)[:, None]
    g, raw = geometry(ref, np.array([[0.]]), ref_ids=np.arange(250), query_ids=np.array([0]))
    assert raw['nearest200'][0, 0] == 1 and raw['self_excluded_count'][0] == 1
    print('SELF_TEST_PASS', flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', type=Path)
    ap.add_argument('--out', type=Path)
    ap.add_argument('--datasets', nargs='+', default=list(FILES), choices=list(FILES))
    ap.add_argument('--self-test', action='store_true')
    args = ap.parse_args()
    if args.self_test:
        self_test()
        return
    assert args.root is not None and args.out is not None
    assert not args.out.exists(), 'use a new run directory; do not overwrite evidence'
    args.out.mkdir(parents=True)
    environment = {'time_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'host': platform.node(), 'platform': platform.platform(), 'python': sys.version,
        'numpy': np.__version__, 'scipy': scipy.__version__, 'rapidfuzz': rapidfuzz.__version__,
        'input_root': str(args.root), 'argv': sys.argv, 'seeds': SEEDS, 'gpu_used': False,
        'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'contract_sha256': hashlib.sha256(Path(__file__).with_name('CONTRACT.md').read_bytes()).hexdigest(),
        'thread_environment': {k: os.environ.get(k) for k in ['OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS']}}
    write_json(args.out/'environment.local.json', environment)
    for name in args.datasets:
        out = args.out/name
        out.mkdir()
        try:
            run_one(args.root, name, out)
        except Exception as ex:
            write_json(out/'error.json', {'type': type(ex).__name__, 'message': str(ex)})
            raise


if __name__ == '__main__':
    main()
