"""One immutable CPU population run; raw placement and per-pair arrays stay private."""
if not __debug__:
    raise SystemExit('Optimized Python disables mandatory checks; run without -O/PYTHONOPTIMIZE.')
import argparse
import concurrent.futures
import ctypes
import fcntl
import hashlib
import json
import os
import platform
import struct
import subprocess
import time
import traceback
from fractions import Fraction
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
NAMES = ('CONTRACT.json', 'oracles.cpp', 'run.py', 'test_oracles.py', 'NUMERICS.md', 'PRIOR_ART_LIMITS.md', 'SOURCES.json')


def load(path):
    return json.loads(Path(path).read_text())


def save(path, value):
    with Path(path).open('x') as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write('\n')


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def sources():
    return {name: sha(HERE / name) for name in NAMES}


def guard_threshold(threshold, d):
    # Outward rounding of T*(1+gamma_D)/(1-gamma_D) = T/(1-2*D*u).
    exact = Fraction.from_float(threshold) / (1 - Fraction(2 * d, 2**53))
    value = float(exact)
    if Fraction.from_float(value) < exact:
        value = float(np.nextafter(value, np.inf))
    return float(np.nextafter(value, np.inf))


def functions(library):
    lib = ctypes.CDLL(str(library))
    p = ctypes.c_void_p
    lib.pair_oracle.argtypes = [p, p, ctypes.c_size_t, ctypes.c_int, ctypes.c_double, ctypes.c_double] + [p] * 6
    lib.global_oracle.argtypes = [p, p, p, ctypes.c_size_t, ctypes.c_int, ctypes.c_double, ctypes.c_double] + [p] * 4
    lib.pair_oracle.restype = lib.global_oracle.restype = ctypes.c_int
    return lib


def pair_call(lib, x, q, threshold, sums=None):
    d = x.shape[1]
    assert x.dtype == q.dtype == np.float32 and x.flags.c_contiguous and q.flags.c_contiguous
    assert x.ndim == 2 and q.shape == (d,) and len(x)
    full = np.empty(len(x), '<f8')
    original, nominal, safe = [np.empty(len(x), '<u2') for _ in range(3)]
    if sums is None:
        sums = np.zeros(d, '<f8')
    audit = np.zeros(3, '<u8')
    rc = lib.pair_oracle(x.ctypes.data, q.ctypes.data, len(x), d, threshold, guard_threshold(threshold, d),
                         full.ctypes.data, original.ctypes.data, nominal.ctypes.data, safe.ctypes.data,
                         sums.ctypes.data, audit.ctypes.data)
    assert rc == 0, ('pair_oracle', rc)
    return full, original, nominal, safe, sums, audit


def global_call(lib, x, q, reference, threshold, order):
    assert reference.dtype == np.float64 and order.dtype == np.int32
    assert reference.flags.c_contiguous and order.flags.c_contiguous
    nominal, safe = [np.empty(len(x), '<u2') for _ in range(2)]
    audit = np.zeros(3, '<u8')
    rc = lib.global_oracle(x.ctypes.data, q.ctypes.data, reference.ctypes.data, len(x), x.shape[1],
                           threshold, guard_threshold(threshold, x.shape[1]), order.ctypes.data,
                           nominal.ctypes.data, safe.ctypes.data, audit.ctypes.data)
    assert rc == 0, ('global_oracle', rc)
    return nominal, safe, audit


def order_from_sums(sums, nonhits):
    assert nonhits > 0 and np.isfinite(sums).all()
    means = sums / nonhits
    return np.asarray(sorted(range(len(sums)), key=lambda j: (-float(means[j]), j)), '<i4'), means


def histogram(v, d):
    return np.bincount(v.astype(np.int64), minlength=d + 1).tolist()


def query_job(index, qid, w, parent, c, count):
    """Each query has one deterministic row order and one CPU worker; no shared reduction."""
    w = Path(w)
    assert sources() == load(w / 'REGISTERED.json')['sources']
    assert sha(w / 'build/oracles.so') == load(w / 'BUILD.json')['sha256']
    lib = functions(w / 'build/oracles.so')
    n, d = c['N'], c['D']
    threshold = float.fromhex(c['threshold_hex'])
    x = np.memmap(parent['data'], '<f4', mode='r', offset=12, shape=(n, d))
    ref_path = Path(parent['reference']) / f'{qid}.f64'
    assert sha(ref_path) == c['reference_hashes'][ref_path.name]
    ref = np.memmap(ref_path, '<f8', mode='r', shape=(n,))[:count]
    q = np.ascontiguousarray(x[qid])
    arrays = {name: np.empty(count, '<u2') for name in ('original', 'pair_nominal', 'pair_safe', 'global_nominal', 'global_safe')}
    sums, pair_audit = np.zeros(d, '<f8'), np.zeros(3, '<u8')
    start = time.time()
    for a in range(0, count, c['chunk_rows']):
        if (w / 'FAILURE.json').exists():
            raise RuntimeError('Another task-owned worker failed; stop before the next chunk.')
        b = min(a + c['chunk_rows'], count)
        full, orig, nominal, safe, sums, audit = pair_call(lib, x[a:b], q, threshold, sums)
        assert np.array_equal(full.view('<u8'), ref[a:b].view('<u8')), ('ordered full score mismatch', qid, a)
        for name, v in [('original', orig), ('pair_nominal', nominal), ('pair_safe', safe)]:
            arrays[name][a:b] = v
        pair_audit += audit
    nonhits = int(np.count_nonzero(ref > threshold))
    order, means = order_from_sums(sums, nonhits)
    global_audit = np.zeros(3, '<u8')
    for a in range(0, count, c['chunk_rows']):
        if (w / 'FAILURE.json').exists():
            raise RuntimeError('Another task-owned worker failed; stop before the next chunk.')
        b = min(a + c['chunk_rows'], count)
        nominal, safe, audit = global_call(lib, x[a:b], q, np.ascontiguousarray(ref[a:b]), threshold, order)
        arrays['global_nominal'][a:b], arrays['global_safe'][a:b] = nominal, safe
        global_audit += audit
    hits = ref <= threshold
    for name, v in arrays.items():
        assert ((v >= 1) & (v <= d)).all() and (v[hits] == d).all(), name
    assert (arrays['pair_safe'] >= arrays['pair_nominal']).all()
    assert (arrays['global_safe'] >= arrays['global_nominal']).all()
    raw = {}
    if count == n:
        for name, v in {**arrays, 'global_order': order, 'nonhit_means': means}.items():
            path = w / 'raw' / f'q{index:02}_{name}.bin'
            with path.open('xb') as f:
                v.tofile(f)
            raw[path.name] = {'sha256': sha(path), 'bytes': path.stat().st_size}
    return {'query_index': index, 'qid': qid, 'N': count, 'D': d, 'hits': count - nonhits,
            'histograms': {name: histogram(v, d) for name, v in arrays.items()},
            'pair_audit_nominal_hit_cross_guard_fallback_difference': pair_audit.tolist(),
            'global_audit_nominal_hit_cross_guard_fallback_difference': global_audit.tolist(),
            'pair_safe_gt_global_safe_pairs': int(np.count_nonzero(arrays['pair_safe'] > arrays['global_safe'])),
            'full_score_bit_mismatches': 0, 'safe_false_rejections': 0,
            'global_order_sha256': hashlib.sha256(order.tobytes()).hexdigest(),
            'global_nonhit_means_sha256': hashlib.sha256(means.tobytes()).hexdigest(),
            'diagnostic_wall_seconds_not_search_latency': time.time() - start, 'raw': raw}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--parent', type=Path, required=True, help='Private immutable parent REGISTERED.json')
    p.add_argument('--work', type=Path, required=True, help='Fresh private scratch directory')
    a = p.parse_args()
    c = load(HERE / 'CONTRACT.json')
    parent = load(a.parent)
    assert parent['data_sha256'] == c['data_sha256'] and parent['qids'] == c['qids']
    assert parent['reference_hashes'] == c['reference_hashes']
    assert sha(parent['data']) == c['data_sha256']
    with Path(parent['data']).open('rb') as f:
        assert struct.unpack('<iii', f.read(12)) == (c['D'], c['N'], 2)
    assert Path(parent['data']).stat().st_size == 12 + c['N'] * c['D'] * 4
    for name, digest in c['reference_hashes'].items():
        assert sha(Path(parent['reference']) / name) == digest
    assert (parent['radius'] * parent['radius']).hex() == c['threshold_hex']
    w = a.work.resolve()
    assert not w.exists() and HERE not in w.parents
    w.mkdir()
    for directory in ('build', 'raw', 'scalars'):
        (w / directory).mkdir()
    command = ['g++', *c['compiler_flags'], str(HERE / 'oracles.cpp'), '-o', str(w / 'build/oracles.so')]
    save(w / 'REGISTERED.json', {'sources': sources(), 'contract_sha256': sha(HERE / 'CONTRACT.json'),
         'before_measurement': True, 'registered_unix': time.time(), 'parent_registration_sha256': sha(a.parent),
         'data_sha256': c['data_sha256'], 'compile_command': command,
         'compiler_version': subprocess.check_output(['g++', '--version'], text=True).splitlines()[0],
         'machine': platform.uname()._asdict(), 'python': platform.python_version(), 'numpy': np.__version__,
         'CPU_workers': c['CPU_workers'], 'GPU_starts': 0})
    try:
        with (w / 'campaign.lock').open('x') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with (w / 'build/compile.log').open('x') as log:
                subprocess.run(command, stdout=log, stderr=log, check=True)
            save(w / 'BUILD.json', {'sha256': sha(w / 'build/oracles.so')})
            env = {**os.environ, 'ORACLES_LIBRARY': str(w / 'build/oracles.so'), 'PYTHONDONTWRITEBYTECODE': '1'}
            with (w / 'FIXTURES.log').open('x') as log:
                subprocess.run(['python3', '-m', 'unittest', '-v', 'test_oracles'], cwd=HERE, env=env, stdout=log, stderr=log, check=True)
            bounded = [query_job(i, q, w, parent, c, 4096) for i, q in enumerate(c['qids'])]
            save(w / 'QUALIFICATION.json', {'passed': True, 'queries': 32, 'rows_per_query': 4096, 'records': bounded})
            save(w / 'START.json', {'sources': sources(), 'qualified_sha256': sha(w / 'QUALIFICATION.json'),
                 'before_full_population': True, 'started_unix': time.time(), 'GPU_starts': 0,
                 'CPU_workers': c['CPU_workers'], 'pairs': 32 * c['N']})
            records, next_index = {}, 0
            with concurrent.futures.ProcessPoolExecutor(max_workers=c['CPU_workers']) as pool:
                pending = {}
                while next_index < c['CPU_workers']:
                    q = c['qids'][next_index]
                    pending[pool.submit(query_job, next_index, q, w, parent, c, c['N'])] = next_index
                    next_index += 1
                while pending:
                    done, _ = concurrent.futures.wait(pending, return_when=concurrent.futures.FIRST_COMPLETED)
                    # Completion order is retained separately, never used to change query weighting.
                    for future in sorted(done, key=lambda f: pending[f]):
                        index = pending.pop(future)
                        record = future.result()
                        records[index] = record
                        save(w / 'scalars' / f'q{index:02}.json', record)
                        print('PASSED', len(records), '/32 index', index, 'pair_mean',
                              sum(k * v for k, v in enumerate(record['histograms']['pair_safe'])) / c['N'], flush=True)
                        if next_index < len(c['qids']):
                            q = c['qids'][next_index]
                            pending[pool.submit(query_job, next_index, q, w, parent, c, c['N'])] = next_index
                            next_index += 1
            assert len(records) == 32 and sources() == load(w / 'REGISTERED.json')['sources']
            assert sha(parent['data']) == c['data_sha256']
            for name, digest in c['reference_hashes'].items():
                assert sha(Path(parent['reference']) / name) == digest
            save(w / 'RESULTS.json', {'complete': True, 'records': [records[i] for i in range(32)],
                 'contract_sha256': sha(HERE / 'CONTRACT.json'), 'GPU_starts': 0, 'CPU_workers': c['CPU_workers'],
                 'pairs': 32 * c['N'], 'finished_unix': time.time(), 'start_sha256': sha(w / 'START.json')})
    except Exception:
        if not (w / 'FAILURE.json').exists():
            save(w / 'FAILURE.json', {'error': traceback.format_exc(), 'stop': 'No automatic retry or source replacement', 'GPU_starts': 0})
        raise


if __name__ == '__main__':
    main()
