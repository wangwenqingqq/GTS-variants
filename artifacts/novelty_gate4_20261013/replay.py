"""One bounded CPU-only population replay. Paths and full arrays remain private."""
import argparse
import ctypes
import json
import os
import struct
import subprocess
import sys
import time
from pathlib import Path
import numpy as np
from model import HERE, ROOT, read, save, sha


def build(work):
    (work / 'build').mkdir()
    command = ['g++', *read(HERE / 'CONTRACT.json')['execution']['compiler_flags'],
               str(HERE / 'replay.cpp'), '-o', str(work / 'build/replay.so')]
    with (work / 'build/compile.log').open('x') as log:
        subprocess.run(command, stdout=log, stderr=log, check=True)
    return work / 'build/replay.so', command


def functions(binary):
    lib = ctypes.CDLL(str(binary)); ptr = ctypes.c_void_p
    f = lib.interval_prefix
    f.argtypes = [ptr, ptr, ptr, ptr, ctypes.c_size_t, ctypes.c_double,
                  ptr, ptr, ptr, ptr, ptr]; f.restype = ctypes.c_int
    g = lib.knn_crossings
    g.argtypes = [ptr, ptr, ctypes.c_size_t, ctypes.c_int, ctypes.c_double,
                  ctypes.c_double, ptr, ptr, ptr, ptr, ptr, ptr, ptr]
    g.restype = ctypes.c_int
    return f, g


def encode(x):
    lo = np.min(x[:, :256], axis=0).astype('<f8')
    hi = np.max(x[:, :256], axis=0).astype('<f8')
    edges = lo[:, None] + (hi - lo)[:, None] * np.arange(257) / 256
    edges[:, 0] = -np.inf; edges[:, -1] = np.inf
    width = np.where(hi > lo, hi - lo, 1.)
    code = np.empty((len(x), 256), dtype=np.uint8); cols = np.arange(256)
    for start in range(0, len(x), 8192):
        v = x[start:start + 8192, :256].astype('<f8')
        c = np.clip(np.floor((v - lo) * 256 / width), 0, 255).astype(np.int16)
        c -= (v < edges[cols, c]).astype(np.int16)
        c += (v > edges[cols, c + 1]).astype(np.int16)
        assert np.all((c >= 0) & (c <= 255))
        assert np.all(v >= edges[cols, c]) and np.all(v <= edges[cols, c + 1])
        code[start:start + len(v)] = c
    return np.ascontiguousarray(code), np.ascontiguousarray(edges)


def table(q, edges):
    delta = np.maximum(0., np.maximum(edges[:, :-1] - q[:256, None],
                                     q[:256, None] - edges[:, 1:]))
    delta = np.nextafter(delta, 0.)
    return np.ascontiguousarray(np.nextafter(delta * delta, 0.))


def interval(f, x, q, codes, edges, threshold):
    out = [np.empty(len(x), dtype='<f8') for _ in range(5)]
    lut = table(q.astype('<f8'), edges)
    assert f(x.ctypes.data, q.ctypes.data, codes.ctypes.data, lut.ctypes.data,
             len(x), threshold, *(v.ctypes.data for v in out)) == 0
    return out


def crossings(g, x, q, t0, t1):
    full = np.empty(len(x), '<f8')
    dims = [np.empty(len(x), '<u2') for _ in range(2)]
    bc = [np.empty(len(x), '<f8') for _ in range(4)]
    assert g(x.ctypes.data, q.ctypes.data, len(x), x.shape[1], t0, t1,
             full.ctypes.data, *(v.ctypes.data for v in dims + bc)) == 0
    return full, dims, bc


def exact_k(scores, k=8):
    t = float(np.partition(scores, k - 1)[k - 1])
    ids = np.flatnonzero(scores <= t)
    return ids[np.lexsort((ids, scores[ids]))[:k]], t


def validate_interval(out, reference, threshold):
    r128, r256, l128, l256, fallback = out
    assert np.all(l128 <= r128) and np.all(l256 <= r256)
    assert np.all(l128 >= 0.) and np.all(l256 >= l128)
    assert np.all(r128 <= r256) and np.all(r256 <= reference)
    truth = np.flatnonzero(reference <= threshold)
    assert np.all(l128[truth] <= threshold) and np.all(l256[truth] <= threshold)
    got = np.flatnonzero(fallback <= threshold)
    assert np.array_equal(truth, got)
    assert np.array_equal(fallback[got].view('<u8'), reference[got].view('<u8'))
    return dict(n=len(reference), exact_survivors128=int(np.count_nonzero(r128 <= threshold)),
                exact_survivors256=int(np.count_nonzero(r256 <= threshold)),
                code_survivors128=int(np.count_nonzero(l128 <= threshold)),
                code_survivors256=int(np.count_nonzero(l256 <= threshold)),
                hits=len(truth), bound_violations=0, false_negative=0, false_positive=0,
                fallback_score_bit_mismatch=0)


def validate_crossings(full, dims, bc, reference, thresholds, k=8):
    assert np.array_equal(full.view('<u8'), reference.view('<u8'))
    truth, _ = exact_k(reference, k); result = []
    for index, (required, threshold) in enumerate(zip(dims, thresholds)):
        b, at = bc[2 * index:2 * index + 2]
        reject = full > threshold
        assert np.all((required >= 1) & (required <= 960))
        assert np.all(b[reject] <= threshold) and np.all(at[reject] > threshold)
        assert np.all(required[~reject] == 960)
        assert np.all(required[truth] == 960)
        retained = np.flatnonzero(~reject)
        got = retained[exact_k(full[retained], k)[0]]
        assert np.array_equal(got, truth)
        hist = np.bincount(required, minlength=961).astype('<u8')
        count = [int(np.count_nonzero(required > stage)) if stage < 960 else len(retained)
                 for stage in (128, 256, 512, 960)]
        consumption = (512 * len(full) + 512 * count[0] + 1024 * count[1] + 1792 * count[2])
        result.append(dict(threshold_hex=threshold.hex(), retained=len(retained),
                           exact_k_ids=truth.tolist(), exact_k_scores_hex=[float(full[i]).hex() for i in truth],
                           required_dims_histogram=hist.tolist(), mean_required_dims=float(np.mean(required)),
                           required_dims_quantiles=dict(zip(('p10', 'p50', 'p90'),
                               np.percentile(required, (10, 50, 90), method='linear').tolist())),
                           coordinate_bytes=int(np.sum(required, dtype=np.uint64)) * 4,
                           four_stage_survivors=count, four_stage_coordinate_bytes=consumption,
                           false_negative=0, false_positive=0, full_score_bit_mismatch=0,
                           first_crossing_violation=0))
    return result


def population(a):
    c = read(HERE / 'CONTRACT.json'); w = a.work.resolve()
    assert ROOT not in w.parents and w != ROOT and not w.exists()
    assert sys.byteorder == 'little'
    assert int(os.environ.get('OMP_NUM_THREADS', '0')) == c['execution']['CPU_workers']
    assert os.environ.get('CUDA_VISIBLE_DEVICES') == ''
    for p, digest in c['parent_files'].items():
        assert sha(ROOT / p) == digest, p
    expected = read(ROOT / 'artifacts/progressive_dynamic_gate3_20261013/evidence/INPUT_IDENTITY.json')
    trace = a.gate3 / 'inputs/A.source.json'
    assert sha(trace) == expected['input_hashes']['inputs/A.source.json']
    assert [s for f, _, s in read(trace) if f == 3][:32] == c['workload']['knn_qids']
    assert a.data.stat().st_size == 12 + 1000000 * 960 * 4
    with a.data.open('rb') as data:
        assert struct.unpack('<iii', data.read(12)) == (960, 1000000, 2)
    assert sha(a.data) == c['workload']['data_sha256']
    source = {str(p.relative_to(ROOT)): sha(p) for p in sorted(HERE.rglob('*'))
              if p.is_file() and '__pycache__' not in p.parts}
    qids = c['workload']['range_qids'] + c['workload']['knn_qids']
    references = {}
    for q in qids:
        path = a.gate3 / 'cache' / f'{q}.f64'
        assert path.stat().st_size == 1000000 * 8
        references[str(q)] = sha(path)
        assert references[str(q)] == expected['input_hashes'][f'cache/{q}.f64']
    w.mkdir(); started = time.time()
    try:
        (w / 'raw').mkdir()
        save(w / 'REGISTERED.json', dict(before_compile=True, before_population=True,
             source_hashes=source, data=str(a.data), data_sha256=sha(a.data),
             gate3=str(a.gate3), references=references, query_pools=c['workload'],
             CPU_workers=4, GPU_starts=0, started_unix=started))
        binary, command = build(w)
        with (w / 'build/self_test.log').open('x') as log:
            subprocess.run([sys.executable, str(HERE / 'test_gate4.py'), '--binary', str(binary)],
                           stdout=log, stderr=log, check=True)
        f, g = functions(binary)
        x = np.memmap(a.data, mode='r', offset=12, dtype='<f4', shape=(1000000, 960))
        for start in range(0, len(x), 8192):
            v = x[start:start + 8192]
            assert np.isfinite(v).all() and np.max(np.abs(v)) <= 16
        code, edges = encode(x); code.tofile(w / 'raw/codes.u8'); edges.tofile(w / 'raw/edges.f64')
        threshold = float.fromhex(c['workload']['range_threshold_hex'])
        qualification = []
        for category, pool in (('M2', c['workload']['range_qids']), ('M3', c['workload']['knn_qids'])):
            for q in pool:
                ref = np.memmap(a.gate3 / 'cache' / f'{q}.f64', '<f8', mode='r')[:4096]
                query = np.ascontiguousarray(x[q])
                if category == 'M2':
                    stats = validate_interval(interval(f, x[:4096], query, code[:4096], edges, threshold), ref, threshold)
                else:
                    _, t0 = exact_k(ref); _, t1 = exact_k(ref[:256])
                    full, dims, bc = crossings(g, x[:4096], query, t0, t1)
                    stats = validate_crossings(full, dims, bc, ref, (t0, t1))
                qualification.append(dict(category=category, qid=q, passed=True))
        save(w / 'QUALIFICATION.json', dict(queries=qualification, subset_rows=4096, complete=True))
        rows2, rows3 = [], []
        for category, pool in (('M2', c['workload']['range_qids']), ('M3', c['workload']['knn_qids'])):
            for query_index, q in enumerate(pool):
                ref = np.memmap(a.gate3 / 'cache' / f'{q}.f64', '<f8', mode='r')
                query = np.ascontiguousarray(x[q])
                prefix = f'{category}.{query_index:02d}.{q}'; begin = time.time()
                if category == 'M2':
                    out = interval(f, x, query, code, edges, threshold)
                    row = validate_interval(out, ref, threshold)
                    names = ('exact128', 'exact256', 'lower128', 'lower256', 'fallback')
                    for name, value in zip(names, out):
                        value.tofile(w / 'raw' / f'{prefix}.{name}.f64')
                    row.update(qid=q, query_index=query_index); rows2.append(row)
                else:
                    _, t0 = exact_k(ref); _, t1 = exact_k(ref[:256])
                    full, dims, bc = crossings(g, x, query, t0, t1)
                    variants = validate_crossings(full, dims, bc, ref, (t0, t1))
                    # The seed scan is read once; scan the other rows progressively.
                    variants[1]['seed_bytes'] = 256 * 960 * 4
                    variants[1]['seed_charged_coordinate_bytes'] = (variants[1]['coordinate_bytes']
                        - int(np.sum(dims[1][:256], dtype=np.uint64)) * 4 + variants[1]['seed_bytes'])
                    seed_stages = np.searchsorted((128, 256, 512, 960), dims[1][:256], side='left')
                    seed_rounded = np.array((128, 256, 512, 960))[seed_stages].sum()
                    variants[1]['seed_charged_four_stage_bytes'] = (variants[1]['four_stage_coordinate_bytes']
                        - int(seed_rounded) * 4 + variants[1]['seed_bytes'])
                    full.tofile(w / 'raw' / f'{prefix}.full.f64')
                    for name, value in zip(('oracle', 'seed'), dims):
                        value.tofile(w / 'raw' / f'{prefix}.{name}.required.u16')
                    for name, value in zip(('oracle.before', 'oracle.crossing', 'seed.before', 'seed.crossing'), bc):
                        value.tofile(w / 'raw' / f'{prefix}.{name}.f64')
                    row = dict(qid=q, query_index=query_index, variants=variants); rows3.append(row)
                save(w / f'{prefix}.json', row)
                with (w / 'progress.jsonl').open('a') as log:
                    log.write(json.dumps(dict(category=category, qid=q, seconds=time.time() - begin)) + '\n')
                print(category, query_index + 1, q, 'PASS', flush=True)
        assert all(sha(ROOT / p) == h for p, h in source.items())
        assert sha(a.data) == c['workload']['data_sha256']
        assert all(sha(a.gate3 / 'cache' / f'{q}.f64') == h for q, h in references.items())
        identity = {str(p.relative_to(w)): dict(bytes=p.stat().st_size, sha256=sha(p))
                    for p in sorted(w.rglob('*')) if p.is_file()}
        save(w / 'RAW_IDENTITY.json', dict(files=identity))
        result = dict(complete=True, CPU_workers=4, GPU_starts=0, full_population_processes=1,
                      M2=rows2, M3=rows3, code_bytes=code.nbytes, edges_bytes=edges.nbytes,
                      source_hashes=source, references=references, data_sha256=sha(a.data),
                      binary_sha256=sha(binary), build_command=command,
                      registration_sha256=sha(w / 'REGISTERED.json'),
                      raw_identity_sha256=sha(w / 'RAW_IDENTITY.json'),
                      qualification_sha256=sha(w / 'QUALIFICATION.json'),
                      finished_unix=time.time(), seconds=time.time() - started,
                      CPU_time_is_performance=False)
        save(w / 'RESULTS.json', result); print('COMPLETE CPU-ONLY GATE4', flush=True)
    except BaseException as error:
        save(w / 'FAILURE.json', dict(type=type(error).__name__, message=str(error),
             stopped_unix=time.time(), no_automatic_restart=True))
        raise


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    for key in ('data', 'gate3', 'work'):
        p.add_argument('--' + key, type=Path, required=True)
    population(p.parse_args())
