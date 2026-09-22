#!/usr/bin/env python3
"""Read-only matched-sample extension; see CONTRACT_EXTENDED.md."""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import time

import numpy as np
from scipy.spatial.distance import cdist
from scipy.stats import ks_2samp
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import profile_datasets as p

EXTRA = {
    'T-loc-10M': ('T-loc/10_million_location_gts.txt', 'T-loc/tloc_10m_qid.txt', 'spatial', 'Euclidean', (2, 10000000, 2)),
    'Vector-200K': ('vector/vector.txt', 'vector/vector_qid.txt', 'vector', 'Angular-degrees', (300, 200000, 5)),
    'Protein': ('dna_barcode/protein.txt', 'dna_barcode/protein_qid.txt', 'word', 'Levenshtein', (100, 52799, 6)),
    'ChEMBL': ('chembl/chembl_50k.txt', 'chembl/chembl_50k_qid.txt', 'binary', 'Tanimoto', (2048, 50000, 8)),
}
NAMES = list(p.FILES)+list(EXTRA)


def distance(a, b, metric):
    if metric == 'Levenshtein':
        return p.distances(a, b, True)
    a, b = np.asarray(a, float), np.asarray(b, float)
    if metric == 'Euclidean':
        return cdist(a, b)
    if metric == 'Angular-degrees':
        na, nb = np.linalg.norm(a, axis=1), np.linalg.norm(b, axis=1)
        assert np.all(na > 0) and np.all(nb > 0), 'zero-norm angular input'
        # Chord form is algebraically equivalent and preserves exact duplicate zeros.
        chord = cdist(a/na[:, None], b/nb[:, None])
        return np.degrees(2*np.arcsin(np.clip(chord/2, 0, 1)))
    assert metric == 'Tanimoto'
    dot = a@b.T
    union = a.sum(1)[:, None]+b.sum(1)-dot
    return np.divide(union-dot, union, out=np.zeros_like(dot), where=union > 0)


def pair_distance(a, b, metric):
    if metric == 'Levenshtein':
        return np.fromiter((p.Levenshtein.distance(x, y) for x, y in zip(a, b)), float, len(a))
    a, b = np.asarray(a, float), np.asarray(b, float)
    if metric == 'Euclidean':
        return np.linalg.norm(a-b, axis=1)
    dot = np.einsum('ij,ij->i', a, b)
    if metric == 'Angular-degrees':
        norms = np.linalg.norm(a, axis=1)*np.linalg.norm(b, axis=1)
        assert np.all(norms > 0)
        chord = np.linalg.norm(a/np.linalg.norm(a, axis=1)[:, None]-
                               b/np.linalg.norm(b, axis=1)[:, None], axis=1)
        return np.degrees(2*np.arcsin(np.clip(chord/2, 0, 1)))
    union = a.sum(1)+b.sum(1)-dot
    return np.divide(union-dot, union, out=np.zeros_like(dot), where=union > 0)


def geometry(ref, queries, metric, rid=None, qid=None):
    near = np.empty((len(queries), 200))
    avg, std, ties = (np.empty(len(queries)) for _ in range(3))
    excluded = np.zeros(len(queries), int)
    for lo in range(0, len(queries), 32):
        d = distance(queries[lo:lo+32], ref, metric)
        for j, row in enumerate(d):
            mask = np.zeros(len(ref), bool) if qid is None else rid == qid[lo+j]
            v = row[~mask]
            excluded[lo+j] = mask.sum()
            assert np.isfinite(v).all() and np.all(v >= 0)
            near[lo+j] = np.sort(np.partition(v, 199)[:200])
            avg[lo+j], std[lo+j] = v.mean(), v.std()
            ties[lo+j] = np.mean(v == near[lo+j, 9])
    raw = dict(nearest200=near, mean_distance=avg, std_distance=std,
               boundary10_tie_fraction=ties, self_excluded_count=excluded,
               distance_cv=p.divide(std, avg))
    for k in [1, 10, 100]:
        raw[f'rc{k}'] = p.divide(avg, near[:, k-1])
    for k in [10, 50, 100]:
        raw[f'expansion{k}'] = p.divide(near[:, 2*k-1], near[:, k-1])
    raw['gap10'] = p.divide(near[:, 10]-near[:, 9], near[:, 9])
    if metric not in ['Levenshtein', 'Tanimoto']:
        for k in [20, 50, 100]:
            raw[f'lid{k}'] = p.lid(near, k)
    stats = {k: p.summary(v) for k, v in raw.items() if k != 'nearest200'}
    stats.update(nearest_distance=p.summary(near[:, 0]), r10=p.summary(near[:, 9]),
                 r100=p.summary(near[:, 99]), zero_nearest_fraction=float(np.mean(near[:, 0] == 0)))
    return stats, raw


def hubness(x, metric):
    d = distance(x, x, metric)
    np.fill_diagonal(d, np.inf)
    radius = np.partition(d, 9, axis=1)[:, 9]
    strict, tied = d < radius[:, None], d == radius[:, None]
    count = strict.sum(0)+(tied*((10-strict.sum(1))/tied.sum(1))[:, None]).sum(0)
    assert np.isclose(count.sum(), len(x)*10)
    sd = count.std()
    return dict(sample_n=len(x), k=10, tie_policy='fractional_at_boundary', incoming=p.summary(count),
                skewness=float(np.mean(((count-count.mean())/sd)**3)) if sd else None,
                top1pct_share=float(np.sort(count)[-int(np.ceil(.01*len(x))):].sum()/count.sum()))


def read_text(path, expected, strings=False):
    with path.open() as f:
        header = tuple(map(int, f.readline().split()))
        assert header == expected, (header, expected)
        if strings:
            rows, _, _ = p.read_words(path)
            return rows
        x = np.loadtxt(f, dtype=np.float64, ndmin=2)
    assert x.shape == (header[1], header[0]) and np.isfinite(x).all()
    if header[2] == 8:
        assert np.all((x == 0) | (x == 1)), 'nonbinary fingerprint'
    if header[2] == 5:
        assert np.all(np.linalg.norm(x, axis=1) > 0), 'zero-norm angular input'
    return x


def numeric_full(x, kind, metric):
    n, d = x.shape
    means, m2 = np.zeros(d), np.zeros(d)
    minima, maxima = x.min(0), x.max(0)
    zero = neg = processed = 0
    nearzero = np.zeros(3, np.int64)
    norms, hs, steps = np.empty(n), np.empty(n), np.empty(n-1)
    for lo in range(0, n, 8192):
        hi = min(n, lo+8192)
        z = x[lo:hi]
        norm = np.linalg.norm(z, axis=1)
        norms[lo:hi], hs[lo:hi] = norm, p.hoyer(z)
        zero += int((z == 0).sum()); neg += int((z < 0).sum())
        for j, eps in enumerate([.001, .01, .05]):
            nearzero[j] += int((np.abs(z) <= eps*norm[:, None]/np.sqrt(d)).sum())
        delta, nn = z.mean(0)-means, len(z)
        m2 += ((z-z.mean(0))**2).sum(0)+delta**2*processed*nn/(processed+nn)
        means += delta*nn/(processed+nn); processed += nn
        if hi > 1:
            start = max(0, lo-1)
            steps[start:hi-1] = pair_distance(x[start:hi-1], x[start+1:hi], metric)
    stat = dict(n=n, dimension=d, coordinate_count=n*d, nonfinite_values=0,
                zero_fraction=zero/(n*d), negative_fraction=neg/(n*d), allzero_rows=int((norms == 0).sum()),
                min=float(minima.min()), max=float(maxima.max()), constant_dimensions=int((minima == maxima).sum()),
                coordinate_mean=means.tolist(), coordinate_std=np.sqrt(m2/n).tolist(),
                coordinate_min=minima.tolist(), coordinate_max=maxima.tolist(), norm=p.summary(norms))
    if kind == 'spatial':
        stat['duplicate_fraction_full'] = 1-len(np.unique(x, axis=0))/n
        stat['spatial_grid'] = {}
        for bins in [16, 32, 64, 128]:
            counts = np.histogram2d(x[:, 0], x[:, 1], bins=bins)[0]
            stat['spatial_grid'][str(bins)] = dict(occupied_fraction=float((counts > 0).mean()),
                normalized_entropy=p.entropy(counts.ravel())/np.log2(bins*bins), max_cell_share=float(counts.max()/n))
        signals = dict(coordinate_0=x[:, 0], coordinate_1=x[:, 1])
    else:
        stat['hoyer'] = p.summary(hs)
        stat['relative_nearzero_fraction'] = dict(zip(['0.001', '0.01', '0.05'], (nearzero/(n*d)).tolist()))
        dup = np.packbits(x.astype(np.uint8), axis=1) if kind == 'binary' else x
        stat['duplicate_fraction_full'] = 1-len(np.unique(dup, axis=0))/n
        signals = dict(l2_norm=norms)
        if kind == 'binary':
            bits = x.sum(1)
            ent = np.zeros(d)
            good = (means > 0) & (means < 1)
            q = means[good]
            ent[good] = -q*np.log2(q)-(1-q)*np.log2(1-q)
            stat['active_bits'] = p.summary(bits)
            stat['bit_marginal_entropy_bits'] = p.summary(ent)
            signals = dict(active_bits=bits)
    return stat, steps, signals


def plan(n):
    runs = []
    for seed in p.SEEDS:
        ids = np.random.default_rng(seed).choice(n, 20512, replace=False)
        runs.append((ids[:20000], ids[20000:]))
    rng = np.random.default_rng(8402)
    pc, graph = rng.choice(n, 10000, False), rng.choice(n, 2048, False)
    pairs = rng.integers(0, n, (20000, 2))
    pairs[:, 1] = np.where(pairs[:, 0] == pairs[:, 1], (pairs[:, 1]+1) % n, pairs[:, 1])
    return runs, pc, graph, pairs


def run_one(args, name):
    out = args.out/name
    out.mkdir()
    baseline = name in p.FILES
    root = args.supplementary_root if name in ['Protein', 'ChEMBL'] else args.root
    assert root is not None, 'supplementary data require explicit root'
    if baseline:
        oldpath = args.previous_run/name/'results.json'
        old = json.loads(oldpath.read_text())
        rel, qrel, kind = p.FILES[name]
        metric = old['metric']
    else:
        rel, qrel, kind, metric, expected = EXTRA[name]
    path = root/rel
    before = path.stat()
    print(f'{name}: validating input identity', flush=True)
    meta = p.fingerprint(path)
    if baseline:
        assert meta['sha256'] == old['source']['sha256'], 'baseline input changed'
        if kind == 'vector':
            n, d = p.fvec_shape(path)
            a = np.memmap(path, dtype='<f4', mode='r', shape=(n, d+1))
            assert np.all(a[:, :1].copy().view('<i4') == d)
            x = a[:, 1:]
        elif kind == 'word':
            x = p.read_words(path)[0]
        else:
            x = read_text(path, (2, 1000000, 2))
        r = {k: v for k, v in old.items() if k in ['dataset', 'kind', 'metric', 'source_relative_path',
             'full', 'covariance_sample', 'vector_duplicate_sample', 'hubness_sample', 'row_order']}
        r['reused_v1_result_sha256'] = hashlib.sha256(oldpath.read_bytes()).hexdigest()
    else:
        print(f'{name}: full scan', flush=True)
        x = read_text(path, expected, kind == 'word')
        if kind == 'word':
            _, stat, _, steps, signals = p.word_scan(path)
            stat['max_length_header'] = expected[0]
        else:
            stat, steps, signals = numeric_full(x, kind, metric)
        r = dict(dataset=name, kind=kind, metric=metric, source_relative_path=rel, full=stat)
    n = len(x)
    runs, pc, graph, pairs = plan(n)
    def get(ids):
        return [x[int(i)] for i in ids] if kind == 'word' else x[ids]
    r.update(source=meta, source_root_role='supplementary' if name in ['Protein', 'ChEMBL'] else 'primary',
             contract='native_metric_v2', geometry_runs=[], temporal_burstiness='N/A: no arrival trace')
    if not baseline:
        if kind != 'word':
            r['covariance_sample'] = p.covariance_profile(get(pc))
        r['hubness_sample'] = hubness(get(graph), metric)
        rnd = pair_distance(get(pairs[:, 0]), get(pairs[:, 1]), metric)
        r['row_order'] = p.order_profile(steps, rnd, signals)
    p.write_json(out/'checkpoint.json', dict(stage='descriptors_complete', full=r['full']))
    np.savez_compressed(out/'sample_plan.npz', pca_ids=pc, graph_ids=graph, random_pairs=pairs,
        **{f'ref_{s}': ids[0] for s, ids in zip(p.SEEDS, runs)},
        **{f'query_{s}': ids[1] for s, ids in zip(p.SEEDS, runs)})
    for seed, (rid, qid) in zip(p.SEEDS, runs):
        print(f'{name}: matched geometry seed={seed}', flush=True)
        stats, raw = geometry(get(rid), get(qid), metric)
        r['geometry_runs'].append(dict(seed=seed, reference_n=20000, query_n=512, **stats))
        np.savez_compressed(out/f'geometry_{seed}.npz', **raw)
        p.write_json(out/'checkpoint.json', dict(stage=f'geometry_{seed}_complete'))
    qp, rid = root/qrel, runs[0][0]
    qmeta = p.fingerprint(qp)
    rng = np.random.default_rng(p.SEEDS[0]+71)
    if baseline and kind == 'vector':
        native = p.read_fvec(qp)
        selected = rng.choice(len(native), min(512, len(native)), False)
        q, qid, source_type = native[selected], None, 'external_query_file'
    else:
        with qp.open() as f:
            declared = int(f.readline()); native = np.loadtxt(f, dtype=np.int64, ndmin=1)
        assert len(native) == declared and np.all((native >= 0) & (native < n))
        selected = rng.choice(len(native), min(512, len(native)), False)
        qid = native[selected]
        q, source_type = get(qid), 'base_object_ids'
        r['native_id_range'] = [int(native.min()), int(native.max())]
        r['native_ids_sha256'] = hashlib.sha256(native.astype('<i8').tobytes()).hexdigest()
    print(f'{name}: native queries ({len(q)})', flush=True)
    stats, raw = geometry(get(rid), q, metric, rid, qid)
    r['native_query_profile'] = dict(query_source=qmeta, source_type=source_type,
        available_queries=len(native), sampled_queries=len(q), **stats)
    np.savez_compressed(out/'native_queries.npz', selected_query_positions=selected, **raw)
    base = get(pc[:512])
    if kind == 'word':
        sq, sb, signal = list(map(len, q)), list(map(len, base)), 'sequence_length'
    else:
        sq, sb, signal = np.linalg.norm(np.asarray(q, float), axis=1), np.linalg.norm(np.asarray(base, float), axis=1), 'stored_l2_norm'
        if kind == 'binary':
            sq, sb, signal = np.asarray(q).sum(1), np.asarray(base).sum(1), 'active_bit_count'
        if metric == 'Euclidean':
            r['native_query_mmd'] = p.mmd_test(q, base)
    r['native_scalar_shift'] = dict(signal=signal, ks_distance=float(ks_2samp(sq, sb).statistic),
                                    query=p.summary(sq), base=p.summary(sb))
    assert p.fingerprint(qp) == qmeta, 'query source changed'
    after = path.stat()
    assert (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns), 'source changed'
    p.write_json(out/'results.json', r)
    print(f'{name}: complete', flush=True)


def self_test():
    import tempfile
    p.self_test()
    axes = np.array([[1., 0], [0, 1], [-1, 0]])
    assert np.allclose(distance(axes, axes*3, 'Angular-degrees'), [[0, 90, 180], [90, 0, 90], [180, 90, 0]])
    try:
        distance(np.zeros((1, 2)), axes, 'Angular-degrees')
    except AssertionError:
        pass
    else:
        raise AssertionError('zero norm accepted')
    duplicate = np.random.default_rng(22).normal(size=(32, 300))
    assert np.all(np.diag(distance(duplicate, duplicate.copy(), 'Angular-degrees')) == 0)
    assert np.all(pair_distance(duplicate, duplicate.copy(), 'Angular-degrees') == 0)
    b = np.array([[0., 0, 0], [1, 0, 0], [0, 1, 0], [1, 1, 0]])
    assert np.allclose(distance(b, b, 'Tanimoto'), cdist(b, b, 'jaccard'))
    for metric, x in [('Angular-degrees', axes), ('Tanimoto', b), ('Euclidean', axes)]:
        assert np.allclose(pair_distance(x, x[::-1], metric), np.diag(distance(x, x[::-1], metric)))
    for metric in ['Euclidean', 'Angular-degrees', 'Tanimoto']:
        x = np.tile(axes if metric != 'Tanimoto' else b, (90, 1))
        _, raw = geometry(x, x[:3], metric)
        d = distance(x[:3], x, metric)
        assert np.allclose(raw['nearest200'], np.sort(d, axis=1)[:, :200])
        assert np.allclose(raw['mean_distance'], d.mean(1))
    rng = np.random.default_rng(9)
    z = rng.integers(0, 2, (8200, 3)).astype(float)
    stat, steps, _ = numeric_full(z, 'binary', 'Tanimoto')
    assert np.allclose(stat['coordinate_std'], z.std(0))
    assert np.allclose(steps, pair_distance(z[:-1], z[1:], 'Tanimoto'))
    assert np.isclose(stat['zero_fraction'], (z == 0).mean())
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp)/'bad.txt'; path.write_text('2 2 8\n0 2\n1 0\n')
        try:
            read_text(path, (2, 2, 8))
        except AssertionError:
            pass
        else:
            raise AssertionError('nonbinary accepted')
    for rid, qid in plan(50000)[0]:
        assert len(rid) == 20000 and len(qid) == 512 and not np.intersect1d(rid, qid).size
    print('EXTENSION_SELF_TEST_PASS', flush=True)


def main():
    ap = argparse.ArgumentParser()
    for key in ['root', 'supplementary-root', 'previous-run', 'out']:
        ap.add_argument('--'+key, type=Path)
    ap.add_argument('--datasets', nargs='+', choices=NAMES, default=NAMES[:7])
    ap.add_argument('--self-test', action='store_true')
    a = ap.parse_args()
    if a.self_test:
        self_test(); return
    assert a.root and a.previous_run and a.out and not a.out.exists()
    if any(n in a.datasets for n in ['Protein', 'ChEMBL']):
        assert a.supplementary_root is not None
    a.out.mkdir(parents=True)
    p.write_json(a.out/'environment.local.json', dict(time_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        host=platform.node(), platform=platform.platform(), python=sys.version, numpy=np.__version__,
        scipy=p.scipy.__version__, rapidfuzz=p.rapidfuzz.__version__, argv=sys.argv, gpu_used=False,
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        helper_sha256=hashlib.sha256(Path(p.__file__).read_bytes()).hexdigest(),
        contract_sha256=hashlib.sha256(Path(__file__).with_name('CONTRACT_EXTENDED.md').read_bytes()).hexdigest(),
        thread_environment={k: os.environ.get(k) for k in ['OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS']}))
    for name in a.datasets:
        try:
            run_one(a, name)
        except Exception as ex:
            p.write_json(a.out/'error.local.json', dict(dataset=name, error=repr(ex)))
            raise


if __name__ == '__main__':
    main()
