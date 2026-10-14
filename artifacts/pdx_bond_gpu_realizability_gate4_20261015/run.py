"""One frozen full-population CPU diagnostic; never a GPU or latency benchmark."""
if not __debug__:
    raise SystemExit('Optimized Python disables mandatory checks; run without -O/PYTHONOPTIMIZE.')
import argparse
import concurrent.futures
import ctypes
import fcntl
import importlib.util
import json
import os
import platform
import struct
import subprocess
import sys
import time
import traceback
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('parent_oracles', HERE.parent/'exact_gpu_limits_gate1_20261014/run.py')
old = importlib.util.module_from_spec(spec)
spec.loader.exec_module(old)
sha, load, save = old.sha, old.load, old.save
FILES = ('CONTRACT.json', 'PDX_BASELINE_SPEC.md', 'NUMERICS.md', 'SOURCES.json', 'pdx.cpp', 'run.py', 'test_pdx.py')


def identities():
    c = load(HERE/'CONTRACT.json')
    repo = HERE.parent.parent
    return {**{n: sha(HERE/n) for n in FILES},
            **{n: sha(repo/n) for n in c['parents']}}


def library(path):
    lib = old.functions(path)
    p = ctypes.c_void_p
    lib.pdx_zone_order.argtypes = [p]*6
    lib.pdx_zone_order.restype = ctypes.c_int
    lib.validate_ordered_scores.argtypes = [p, p, p, ctypes.c_size_t, p]
    lib.validate_ordered_scores.restype = ctypes.c_int
    return lib


def order_call(lib, q, means):
    assert q.shape == means.shape == (960,) and q.dtype == means.dtype == np.float32
    assert q.flags.c_contiguous and means.flags.c_contiguous
    order, zones, ranks = np.empty(960, '<i4'), np.empty(30, '<i4'), np.empty(30, '<f4')
    tie = np.zeros(1, '<i4')
    rc = lib.pdx_zone_order(q.ctypes.data, means.ctypes.data, order.ctypes.data,
                            ranks.ctypes.data, zones.ctypes.data, tie.ctypes.data)
    assert rc == 0, ('zone_order', rc)
    assert sorted(order.tolist()) == list(range(960))
    assert sorted(zones.tolist()) == list(range(30))
    return order, zones, ranks, int(tie[0])


def job(index, w, parent, c, count):
    w = Path(w)
    assert identities() == load(w/'REGISTERED.json')['sources']
    assert sha(w/'build/pdx.so') == load(w/'BUILD.json')['sha256']
    lib = library(w/'build/pdx.so')
    x = np.memmap(parent['data'], '<f4', mode='r', offset=12, shape=(c['N'], 960))
    qid = c['qids'][index]
    q = np.ascontiguousarray(x[qid])
    means = np.fromfile(w/'raw/global_means.f32', '<f4')
    assert sha(w/'raw/global_means.f32') == load(w/'MEANS.json')['sha256']
    order, zones, ranks, tie = order_call(lib, q, means)
    reference_path = Path(parent['reference'])/f'{qid}.f64'
    assert sha(reference_path) == c['reference_hashes'][reference_path.name]
    ref = np.memmap(reference_path, '<f8', mode='r', shape=(c['N'],))
    nominal, safe = np.empty(count, '<u2'), np.empty(count, '<u2')
    audit = np.zeros(3, '<u8')
    for a in range(0, count, c['chunk_rows']):
        if (w/'FAILURE.json').exists():
            raise RuntimeError('A task-owned worker failed; stop before next chunk.')
        b = min(a+c['chunk_rows'], count)
        scores = np.ascontiguousarray(ref[a:b])
        mismatch = np.zeros(1, '<u8')
        rc = lib.validate_ordered_scores(x[a:b].ctypes.data, q.ctypes.data,
                                         scores.ctypes.data, b-a, mismatch.ctypes.data)
        assert rc == 0 and mismatch[0] == 0, ('ordered authority', rc, qid, a)
        pn, ps, pa = old.global_call(lib, x[a:b], q, scores, float.fromhex(c['threshold_hex']), order)
        nominal[a:b], safe[a:b] = pn, ps
        audit += pa
    hits = ref[:count] <= float.fromhex(c['threshold_hex'])
    assert (safe >= nominal).all() and (safe[hits] == 960).all()
    raw = {}
    if count == c['N']:
        for name, array in [('nominal', nominal), ('safe', safe), ('order', order), ('ranks', ranks)]:
            path = w/'raw'/f'q{index:02}_{name}.bin'
            with path.open('xb') as f:
                array.tofile(f)
            raw[path.name] = {'bytes': path.stat().st_size, 'sha256': sha(path)}
    return {'query_index': index, 'qid': qid, 'N': count, 'D': 960,
            'hits': int(hits.sum()), 'zone_ids': zones.tolist(), 'cutoff_tie_count': tie,
            'histograms': {'nominal': old.histogram(nominal, 960), 'safe': old.histogram(safe, 960)},
            'survivors': {str(s): int((safe > s).sum()) for s in (128, 256, 512)},
            'nominal_hit_cross_guard_fallback_difference': audit.tolist(),
            'full_score_bit_mismatches': 0, 'safe_false_rejections': 0, 'raw': raw}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--parent', type=Path, required=True)
    p.add_argument('--work', type=Path, required=True, help='Fresh private task scratch')
    a = p.parse_args()
    c, parent = load(HERE/'CONTRACT.json'), load(a.parent)
    assert c['state'] == 'SOURCE_ADAPTED_APPROVED_CPU_DESIGNED'
    assert sha(parent['data']) == c['data_sha256'] == parent['data_sha256']
    assert parent['qids'] == c['qids'] and parent['reference_hashes'] == c['reference_hashes']
    assert (parent['radius']*parent['radius']).hex() == c['threshold_hex']
    with Path(parent['data']).open('rb') as f:
        assert struct.unpack('<iii', f.read(12)) == (960, c['N'], 2)
    assert Path(parent['data']).stat().st_size == 12+c['N']*960*4
    for name, digest in c['reference_hashes'].items():
        assert sha(Path(parent['reference'])/name) == digest
    repo = HERE.parent.parent
    assert all(sha(repo/n) == digest for n, digest in c['parents'].items())
    w = a.work.resolve()
    assert not w.exists() and HERE not in w.parents
    w.mkdir()
    for name in ('build', 'raw', 'scalars'):
        (w/name).mkdir()
    command = ['g++', *c['compiler_flags'], str(HERE/'pdx.cpp'), '-o', str(w/'build/pdx.so')]
    save(w/'REGISTERED.json', {'sources': identities(), 'before_measurement': True,
        'contract_sha256': sha(HERE/'CONTRACT.json'), 'parent_registration_sha256': sha(a.parent),
        'registered_unix': time.time(), 'compile_command': command,
        'compiler_version': subprocess.check_output(['g++', '--version'], text=True).splitlines()[0],
        'machine': platform.uname()._asdict(), 'python': platform.python_version(), 'numpy': np.__version__,
        'CPU_workers': 4, 'GPU_starts': 0})
    try:
        with (w/'campaign.lock').open('x') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with (w/'build/compile.log').open('x') as log:
                subprocess.run(command, stdout=log, stderr=log, check=True)
            save(w/'BUILD.json', {'sha256': sha(w/'build/pdx.so')})
            env = {**os.environ, 'PDX_LIBRARY': str(w/'build/pdx.so'), 'PYTHONDONTWRITEBYTECODE': '1'}
            with (w/'FIXTURES.log').open('x') as log:
                subprocess.run([sys.executable, '-m', 'unittest', '-v', 'test_pdx'],
                               cwd=HERE, env=env, stdout=log, stderr=log, check=True)
            x = np.memmap(parent['data'], '<f4', mode='r', offset=12, shape=(c['N'], 960))
            means = x.mean(axis=0, dtype=np.float32)
            assert means.shape == (960,) and np.isfinite(means).all()
            with (w/'raw/global_means.f32').open('xb') as f:
                means.tofile(f)
            save(w/'MEANS.json', {'sha256': sha(w/'raw/global_means.f32'),
                'bytes': 3840, 'operation': 'numpy mean(axis=0,dtype=FP32);whole original data;no test labels'})
            records = [job(i, w, parent, c, 4096) for i in range(32)]
            save(w/'QUALIFICATION.json', {'passed': True, 'queries': 32, 'rows_per_query': 4096, 'records': records})
            save(w/'START.json', {'before_full_population': True, 'sources': identities(),
                'qualified_sha256': sha(w/'QUALIFICATION.json'), 'pairs': 32000000, 'GPU_starts': 0})
            records, next_index = {}, 0
            with concurrent.futures.ProcessPoolExecutor(max_workers=4) as pool:
                pending = {}
                for _ in range(4):
                    pending[pool.submit(job, next_index, w, parent, c, c['N'])] = next_index
                    next_index += 1
                while pending:
                    done, _ = concurrent.futures.wait(pending, return_when=concurrent.futures.FIRST_COMPLETED)
                    for future in sorted(done, key=lambda f: pending[f]):
                        index = pending.pop(future)
                        try:
                            record = future.result()
                        except BaseException:
                            save(w/'FAILURE.json', {'traceback': traceback.format_exc(), 'GPU_starts': 0})
                            raise
                        records[index] = record
                        save(w/'scalars'/f'q{index:02}.json', record)
                        print('PASSED', len(records), '/32 index', index, flush=True)
                        if next_index < 32:
                            pending[pool.submit(job, next_index, w, parent, c, c['N'])] = next_index
                            next_index += 1
            assert sha(parent['data']) == c['data_sha256']
            assert all(sha(Path(parent['reference'])/n) == v for n, v in c['reference_hashes'].items())
            assert identities() == load(w/'REGISTERED.json')['sources']
            save(w/'RESULTS.json', {'complete': True, 'pairs': 32000000, 'GPU_starts': 0,
                'contract_sha256': sha(HERE/'CONTRACT.json'), 'CPU_workers': 4,
                'records': [records[i] for i in range(32)], 'means_sha256': sha(w/'raw/global_means.f32')})
    except BaseException:
        if not (w/'FAILURE.json').exists():
            save(w/'FAILURE.json', {'traceback': traceback.format_exc(), 'GPU_starts': 0})
        raise


if __name__ == '__main__':
    main()
