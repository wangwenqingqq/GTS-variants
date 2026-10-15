"""CPU-only immutable input/oracle preparation, then explicit source-bound compilation."""
if not __debug__:
    raise SystemExit('Optimized Python disables mandatory checks; run without -O/PYTHONOPTIMIZE.')
import argparse
import ctypes
import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path
import numpy as np
from common import HERE, REPO, MODES, sha, load, save, sources, ends, requests


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def input_prefix(w, n, workload): return w/'inputs'/f'N{n}_W{workload}'


def cpu(a):
    c = load(HERE/'CONTRACT.json'); parent = load(a.parent/'REGISTERED.json')
    assert all(sha(REPO/n) == h for n, h in c['parents'].items())
    assert parent['q32'] == c['qids'] and parent['radius'] == c['radius']
    assert sha(parent['data']) == c['data_sha256']
    assert sha(Path(parent['cpu'])/'raw/global_means.f32') == c['global_means_sha256']
    for n, h in parent['reference_hashes'].items(): assert sha(Path(parent['reference'])/n) == h
    w = a.work.resolve(); assert not w.exists() and REPO not in w.parents; w.mkdir()
    for folder in ('inputs', 'cache', 'references', 'build'): (w/folder).mkdir()
    save(w/'CPU_REGISTERED.json', dict(before_GPU=True, parent=str(a.parent.resolve()), parent_registration_sha256=sha(a.parent/'REGISTERED.json'),
         sources={n: h for n, h in sources().items()}, data=parent['data'], reference=parent['reference'], reference_hashes=parent['reference_hashes'],
         environment=parent['environment'], global_means_sha256=c['global_means_sha256'], CPU_threads=8))
    shutil.copyfile(Path(parent['cpu'])/'raw/global_means.f32', w/'inputs/initial_mean.f32')
    (w/'inputs/full_qids.txt').write_text('\n'.join(map(str, c['qids']))+'\n')
    (w/'inputs/bounded_qids.txt').write_text('\n'.join(map(str, range(32)))+'\n')
    cmd = ['g++', '-std=c++17', '-O3', '-shared', '-fPIC', '-fopenmp', '-ffp-contract=off', '-fno-fast-math', '-fno-associative-math',
           str(REPO/'artifacts/progressive_dynamic_gate3_20261013/oracle.cpp'), '-o', str(w/'build/scores.so')]
    subprocess.run(cmd, check=True); lib = ctypes.CDLL(str(w/'build/scores.so')); fn = lib.exact_scores
    fn.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_void_p]; fn.restype = None
    os.environ['OMP_NUM_THREADS'] = '8'
    x = np.memmap(parent['data'], '<f4', mode='r', offset=12, shape=(1000000, 960))
    assert np.isfinite(x).all() and np.max(np.abs(x)) <= 16
    mu0 = np.fromfile(w/'inputs/initial_mean.f32', '<f4'); assert mu0.shape == (960,)
    records = []; cutoff = c['radius']**2
    for n in (4096, 1000000):
        qids = list(range(32)) if n == 4096 else c['qids']
        maxcount = n//2; victims = np.random.default_rng(2026101501).permutation(n)[:maxcount].astype('<i4')
        source = np.random.default_rng(2026101502).permutation(n)[:64]
        true_mean = np.mean(x[:n], axis=0, dtype=np.float64)
        for workload in range(3):
            points = ends(workload, n); k = points[-1]; prefix = input_prefix(w, n, workload)
            victims[:k].tofile(str(prefix)+'.victims.i32'); Path(str(prefix)+'.ends.txt').write_text(' '.join(map(str, points))+'\n')
            inc = np.memmap(str(prefix)+'.incoming.f32', '<f4', mode='w+', shape=(k, 960))
            for start in range(0, k, 8192):
                stop = min(k, start+8192)
                if workload == 2: inc[start:stop] = np.roll(np.array(x[victims[start:stop]]), -480, axis=1)
                else: inc[start:stop] = x[source[start:stop]]
            inc.flush(); assert np.isfinite(inc).all() and np.max(np.abs(inc)) <= 16
            means = []; diagnostic = []
            for count in points:
                delta = np.sum(inc[:count], axis=0, dtype=np.float64)-np.sum(x[victims[:count]], axis=0, dtype=np.float64)
                anchor = (mu0.astype(np.float64)*n+delta)/n; actual = true_mean+delta/n
                means.append(anchor.astype('<f4'))
                diagnostic.append(dict(replaced=count, mutation_fraction=count/n,
                    true_live_mean_drift_relative_L2=float(np.linalg.norm(actual-true_mean)/np.linalg.norm(true_mean)),
                    anchored_live_mean_drift_relative_L2=float(np.linalg.norm(anchor-mu0)/np.linalg.norm(mu0)),
                    anchor_minus_true_mean_max_abs=float(np.max(np.abs(anchor-actual)))))
            np.asarray(means, '<f4').tofile(str(prefix)+'.expected_means.f32')
            folder = w/'cache'/f'N{n}_W{workload}'; folder.mkdir()
            for qi, q in enumerate(qids):
                if workload == 2 or n == 4096:
                    scores = np.empty(k, '<f8'); qv = np.ascontiguousarray(x[q])
                    fn(inc.ctypes.data, qv.ctypes.data, k, 960, scores.ctypes.data)
                    select = np.linspace(0, k-1, min(k, 7), dtype=int); check = np.zeros(len(select))
                    sample = np.asarray(inc[select], dtype=np.float64)
                    for j in range(960): d = sample[:, j]-float(qv[j]); check = check+d*d
                    assert np.array_equal(scores[select].view('<u8'), check.view('<u8'))
                else:
                    base = np.memmap(Path(parent['reference'])/f'{q}.f64', '<f8', mode='r', shape=(n,)); scores = np.asarray(base[source[:k]])
                scores.tofile(folder/f'{q}.incoming.f64')
                if n == 4096:
                    base_scores = np.empty(n, '<f8'); qv = np.ascontiguousarray(x[q]); fn(x.ctypes.data, qv.ctypes.data, n, 960, base_scores.ctypes.data)
                    base_scores.tofile(folder/f'{q}.base.f64')
                else: base_scores = np.memmap(Path(parent['reference'])/f'{q}.f64', '<f8', mode='r', shape=(n,))
                assert np.isfinite(scores).all() and np.isfinite(base_scores).all()
                if workload == 2 and qi % 8 == 0: print('CPU_ORACLE', n, workload, qi, flush=True)
            refs = []; rid = []; rsq = []; off = 0
            rank = np.full(n, k, '<i4'); rank[victims[:k]] = np.arange(k)
            for event in requests(workload, n):
                q = qids[event['slot']]; count = event['mutation']
                base = np.memmap(folder/f'{q}.base.f64' if n == 4096 else Path(parent['reference'])/f'{q}.f64', '<f8', mode='r', shape=(n,))
                new = np.memmap(folder/f'{q}.incoming.f64', '<f8', mode='r', shape=(k,))
                original = np.flatnonzero(base <= cutoff); original = original[rank[original] >= count]
                added = np.flatnonzero(new[:count] <= cutoff)
                ids = np.concatenate([original, n+added]).astype('<i4'); sq = np.concatenate([base[original], new[added]])
                refs.append(dict(**event, qid=q, offset=off, count=len(ids))); off += len(ids); rid.append(ids); rsq.append(sq)
            np.concatenate(rid).tofile(w/'references'/f'N{n}_W{workload}.ids.i32')
            np.concatenate(rsq).tofile(w/'references'/f'N{n}_W{workload}.scores.f64')
            save(w/'references'/f'N{n}_W{workload}.json', refs)
            record = dict(N=n, workload=workload, replacements=k, point_updates=2*k, formal_queries=160,
                synthetic_distribution_shift=workload == 2, windows=diagnostic,
                input_hashes={p.name: dict(sha256=sha(p), bytes=p.stat().st_size) for p in (w/'inputs').glob(prefix.name+'.*')})
            records.append(record); print('CPU_INPUTS_READY', n, workload, flush=True)
    files = {str(p.relative_to(w)): dict(sha256=sha(p), bytes=p.stat().st_size) for folder in ('inputs', 'cache', 'references') for p in (w/folder).rglob('*') if p.is_file()}
    executed = {str((HERE/n).relative_to(REPO)): sha(HERE/n) for n in ('CONTRACT.json', 'prepare.py', 'common.py')}
    executed['artifacts/progressive_dynamic_gate3_20261013/oracle.cpp'] = sha(REPO/'artifacts/progressive_dynamic_gate3_20261013/oracle.cpp')
    save(w/'CPU_READY.json', dict(passed=True, GPU_starts=0, records=records, files=files, contract_sha256=sha(HERE/'CONTRACT.json'),
         oracle_binary_sha256=sha(w/'build/scores.so'), oracle_command=cmd, source_hashes=executed, GPU_drafts_not_executed=True))
    print('CPU_READY: all inputs,ordered exact references,and drift diagnostics;GPU starts0', flush=True)


def build(a):
    w = a.work.resolve(); c = load(HERE/'CONTRACT.json'); cpu = load(w/'CPU_READY.json'); reg = load(w/'CPU_REGISTERED.json')
    assert cpu['passed'] and cpu['contract_sha256'] == sha(HERE/'CONTRACT.json')
    for n, h in cpu['source_hashes'].items(): assert sha(REPO/n) == h
    for n, h in cpu['files'].items(): assert sha(w/n) == h['sha256']
    parent = load(Path(reg['parent'])/'REGISTERED.json'); base = load(Path(parent['parent'])/'REGISTERED.json')
    assert not subprocess.check_output(['nvidia-smi', '-i', a.gpu, '--query-compute-apps=pid', '--format=csv,noheader'], text=True).strip()
    subprocess.run([sys.executable, '-c', 'import static_guard;assert callable(static_guard.snapshot)'], cwd=REPO/'artifacts/external_closure',
                   env={**os.environ, 'CUDA_VISIBLE_DEVICES': '', 'PYTHONDONTWRITEBYTECODE': '1'}, check=True)
    generator = module('frozen_pdx_generator', REPO/'artifacts/pdx_bond_gpu_realizability_gate4_20261015_recovery_01/gpu_prepare.py')
    keeper, pdx, fixture = generator.headers(REPO)
    full = generator.replace(keeper, 'for(int stage=0;stage<4;stage++)', 'for(int stage=0;stage<1;stage++)')
    full = generator.replace(full, 'progressive_stage<0,128>', 'progressive_stage<0,960>')
    commands = {}; generated = {}; binaries = {}; libraries = None
    env = {**os.environ, **reg['environment'], 'CUDA_VISIBLE_DEVICES': a.gpu, 'OMP_NUM_THREADS': '8', 'PDX_MEANS': str(w/'inputs/initial_mean.f32'), 'PYTHONDONTWRITEBYTECODE': '1'}
    shutil.copyfile(REPO/'artifacts/external_closure/range_service.cu', w/'build/range_base.cuh')
    for i, mode in enumerate(MODES):
        folder = w/'build'/mode; folder.mkdir(); (folder/'selected.cuh').write_text(full if i == 0 else keeper if i == 1 else pdx)
        cmd = [str(HERE/'service.cu') if v == str(Path(parent['parent'])/'build/candidate.cu') else str(folder/'service') if v == str(Path(parent['parent'])/'build/candidate') else v for v in base['commands']['candidate']]
        assert str(HERE/'service.cu') in cmd and str(folder/'service') in cmd
        cmd += ['-I'+str(folder), '-I'+str(w/'build'), '-DMODE='+str(i)]; commands[mode] = cmd
    state = subprocess.check_output(['nvidia-smi', '-i', a.gpu, '--query-gpu=index,uuid,name', '--format=csv,noheader'], text=True).strip()
    save(w/'REGISTERED.json', dict(before_GPU=True, contract_sha256=sha(HERE/'CONTRACT.json'), sources=sources(), generated_sources={str(p.relative_to(w)): sha(p) for p in (w/'build').rglob('*.cuh')},
         cpu_ready_sha256=sha(w/'CPU_READY.json'), data=parent['data'], data_sha256=c['data_sha256'], reference=parent['reference'], reference_hashes=parent['reference_hashes'],
         environment={k: env[k] for k in ('LD_LIBRARY_PATH', 'OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'PDX_MEANS', 'PYTHONDONTWRITEBYTECODE')},
         gpu=a.gpu, gpu_state=state, numa=a.numa, commands=commands))
    for mode, cmd in commands.items():
        with (w/'build'/mode/'compile.log').open('x') as f: subprocess.run(cmd, env=env, stdout=f, stderr=f, check=True)
        linked = subprocess.check_output(['ldd', str(w/'build'/mode/'service')], env=env, text=True); assert 'not found' not in linked
        (w/'build'/mode/'ldd.txt').write_text(linked); libs = {}
        for line in linked.splitlines():
            words = line.split()
            if '=>' in words and len(words) > 2 and words[2].startswith('/'): libs[words[0]] = dict(sha256=sha(words[2]))
        if libraries is None: libraries = libs
        else: assert libraries == libs
        assert libraries == load(Path(reg['parent'])/'READY.json')['libraries']
        binaries[mode] = sha(w/'build'/mode/'service')
    cmd = ['g++', '-std=c++17', '-O2', '-shared', '-fPIC', str(HERE/'oracle.cpp'), '-o', str(w/'build/replay.so')]
    subprocess.run(cmd, check=True)
    save(w/'READY.json', dict(passed=True, GPU_starts=0, registration_sha256=sha(w/'REGISTERED.json'), binaries=binaries,
         libraries=libraries, replay_binary_sha256=sha(w/'build/replay.so'), replay_command=cmd))
    print('BUILT all four source-bound adapters;GPU starts0', flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--stage', choices=('cpu', 'build'), required=True)
    p.add_argument('--work', type=Path, required=True); p.add_argument('--parent', type=Path); p.add_argument('--gpu'); p.add_argument('--numa', type=int)
    a = p.parse_args()
    if a.stage == 'cpu': assert a.parent; cpu(a)
    else: assert a.gpu and a.numa is not None; build(a)
