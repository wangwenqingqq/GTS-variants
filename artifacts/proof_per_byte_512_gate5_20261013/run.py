#!/usr/bin/env python3
"""Two gated CPU populations. Private input/output paths are CLI-only."""
import argparse
import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import platform
import struct
import subprocess
import sys
import time
import traceback

import numpy as np

from test_probe import golden, load, oracle, same_bits, subset

ROOT = Path(__file__).resolve().parent


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(8 << 20), b''):
            h.update(block)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as f:
        json.dump(value, f, indent=2, sort_keys=True, allow_nan=False)
        f.write('\n')


def gate_a(o1, b0):
    if o1*2 <= b0:
        return 'STRONG_HEADROOM'
    return 'WEAK_HEADROOM' if o1*5 <= b0*4 else 'NO_COORDINATE_HEADROOM'


def distribution(v):
    v = np.asarray(v, dtype=np.float64)
    if not len(v):
        return {'count': 0, 'min': None, 'p10': None, 'median': None,
                'p90': None, 'max': None}
    return dict(zip(('min', 'p10', 'median', 'p90', 'max'),
                    map(float, np.quantile(v, (0, .1, .5, .9, 1), method='linear'))),
                count=len(v))


def quality(partial, reference, cutoff):
    require(np.all(np.isfinite(partial)) and np.all(partial >= 0), 'invalid partial')
    require(np.all(np.isfinite(reference)), 'nonfinite oracle')
    unsafe = int(np.count_nonzero(partial > reference))
    false = int(np.count_nonzero((partial > cutoff) & (reference <= cutoff)))
    require(unsafe == false == 0, 'unsafe certificate or false rejection')
    return {'pairs': len(partial), 'survivors': int(np.count_nonzero(partial <= cutoff)),
            'hits': int(np.count_nonzero(reference <= cutoff)),
            'false_rejections': false, 'unsafe_partial_bounds': unsafe,
            'min_absolute_cutoff_margin': float(np.min(np.abs(partial-cutoff)))}


def keep_array(work, qid, name, array, manifest):
    file = f'{qid}.{name}.f64'
    path = work/'raw'/file
    with path.open('xb') as f:
        array.tofile(f)
    manifest[file] = {'bytes': path.stat().st_size, 'sha256': sha(path)}


def moments(x):
    n, d = x.shape
    mean = np.zeros(d, dtype='<f8')
    for start in range(0, n, 8192):
        chunk = np.asarray(x[start:start+8192], dtype=np.float64)
        require(np.all(np.isfinite(chunk)), 'nonfinite statistics input')
        mean += chunk.sum(axis=0, dtype=np.float64)
    mean /= n
    variance = np.zeros(d, dtype='<f8')
    for start in range(0, n, 8192):
        delta = np.asarray(x[start:start+8192], dtype=np.float64)-mean
        variance += (delta*delta).sum(axis=0, dtype=np.float64)
    variance /= n
    stats = np.ascontiguousarray([mean, variance], dtype='<f4')
    require(np.all(np.isfinite(stats)) and np.all(stats[1] >= 0), 'invalid persisted moments')
    return stats


def selection(q, stats):
    score = (q.astype(np.float64)-stats[0].astype(np.float64))**2+stats[1].astype(np.float64)
    require(np.all(np.isfinite(score)), 'invalid moment score')
    ranked = np.argsort(-score, kind='stable')[:128].astype('<u2')
    ordered = np.sort(ranked)
    return ordered, {'ranked_dimensions': ranked.tolist(), 'scan_dimensions': ordered.tolist(),
                     'scores_sha256': hashlib.sha256(score.astype('<f8').tobytes()).hexdigest(),
                     '128th_score': float(score[ranked[-1]]),
                     'cutoff_score_ties': int(np.count_nonzero(score == score[ranked[-1]]))}


def run(args):
    c = read(ROOT/'CONTRACT.json'); w = c['workload']
    require(os.environ.get('CUDA_VISIBLE_DEVICES') == '', 'GPU visibility must be disabled')
    require(os.environ.get('OMP_NUM_THREADS') == '4' and os.environ.get('OMP_DYNAMIC') == 'FALSE',
            'four static native workers required')
    require(os.nice(0) >= 10, 'nice>=10 required')
    for name in ('OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
        require(os.environ.get(name) == '1', 'limit auxiliary threads: '+name)
    work = args.work.resolve()
    work.mkdir(); (work/'raw').mkdir(); (work/'queries').mkdir()
    args.created_work = True
    frozen = {name: sha(ROOT/name) for name in ('CONTRACT.json', 'probe.cpp', 'run.py', 'test_probe.py')}
    identity = read(args.repo/'artifacts/progressive_gpu_gate2_20261013/evidence/INPUT_IDENTITY.json')
    references = identity['reference_hashes']
    require(identity['query_ids'] == w['query_ids'], 'query identities differ')
    if args.stage == 'B':
        require(args.stage_a is not None, 'Gate5A receipt required')
        admission = read(args.stage_a/'RESULTS.json')
        require(admission['complete'] and admission['gate'] == 'STRONG_HEADROOM', 'Gate5B not admitted')
        require(read(args.stage_a/'REGISTRATION.json')['source_sha256'] == frozen, 'Gate5A sources differ')
        require(admission['numerical_boundary_pairs'] == 0, 'oracle numerical boundary unresolved')
    registration = {'stage': args.stage, 'base_commit': c['base_commit'],
                    'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    'contract_sha256': frozen['CONTRACT.json'], 'source_sha256': frozen,
                    'CPU_workers': 4, 'nice': os.nice(0), 'GPU_starts': 0, 'NCU_starts': 0,
                    'reference_hashes': references, 'data_sha256': w['data_sha256'],
                    'population_processes_this_stage': 1, 'query_ids': w['query_ids']}
    save(work/'REGISTRATION.json', registration)
    start = time.monotonic()
    for name, digest in c['parent_files'].items():
        require(sha(args.repo/name) == digest, 'frozen parent differs: '+name)
    require(sha(args.data) == w['data_sha256'], 'data identity differs')
    n, d = w['N'], w['D']; cutoff = float.fromhex(w['cutoff_hex'])
    require(args.data.stat().st_size == 12+n*d*4, 'dataset size differs')
    with args.data.open('rb') as f:
        require(struct.unpack('<iii', f.read(12)) == (d,n,2), 'dataset header differs')
    for name, digest in references.items():
        p = args.cache/name
        require(p.stat().st_size == n*8 and sha(p) == digest, 'frozen oracle differs: '+name)
    save(work/'INPUT_CHECK.json', {'all_hashes_match': True, 'data_sha256': w['data_sha256'],
                                 'parent_files': c['parent_files'], 'reference_hashes': references})
    if args.stage == 'A':
        binary = work/'probe.so'
        result = subprocess.run(['g++', *c['execution']['compiler_flags'], str(ROOT/'probe.cpp'),
                                 '-o', str(binary)], text=True, capture_output=True)
        receipt = {'compiler': subprocess.check_output(['g++','--version'], text=True).splitlines()[0],
                   'flags': c['execution']['compiler_flags'], 'returncode': result.returncode,
                   'stdout': result.stdout, 'stderr': result.stderr}
        save(work/'BUILD_LOG.json', receipt)
        require(result.returncode == 0, 'native build failed')
        save(work/'BUILD.json', {**receipt, 'binary_sha256': sha(binary), 'binary_bytes': binary.stat().st_size})
    else:
        binary = args.stage_a/'probe.so'
        require(sha(binary) == read(args.stage_a/'BUILD.json')['binary_sha256'], 'admitted binary differs')
        save(work/'BUILD.json', {'reused_Gate5A_binary': True, 'binary_sha256': sha(binary)})
    result = subprocess.run([sys.executable, str(ROOT/'test_probe.py'), '--library', str(binary)],
                             capture_output=True, text=True)
    save(work/'FIXTURES.json', {'returncode': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr})
    require(result.returncode == 0, 'native fixture qualification failed')
    lib = load(binary)
    x = np.memmap(args.data, mode='r', dtype='<f4', offset=12, shape=(n,d))
    queries = np.array(x[w['query_ids']], dtype='<f4', order='C', copy=True)
    if args.stage == 'B':
        stats = moments(x)
        with (work/'moments.f32').open('xb') as f:
            stats.tofile(f)
        save(work/'DATASET_STATS.json', {'population_rows': n, 'D': d, 'ddof': 0,
                                       'metadata_bytes': stats.nbytes, 'sha256': sha(work/'moments.f32'),
                                       'mean': stats[0].tolist(), 'variance': stats[1].tolist(),
                                       'preprocess_passes': 2, 'preprocess_logical_input_bytes': 2*n*d*4})
        selections = [selection(q,stats) for q in queries]
        save(work/'ROUTING_SELECTIONS.json', [{'query_id': qid, **s[1]} for qid,s in zip(w['query_ids'],selections)])
    qualification = []
    for idx, (qid, q) in enumerate(zip(w['query_ids'], queries)):
        ref = np.memmap(args.cache/f'{qid}.f64', mode='r', dtype='<f8', shape=(n,))
        if args.stage == 'A':
            outputs = oracle(lib,x[:4096],q)
            wants = golden(x[:4096],q,128)
            require(all(same_bits(a,b) for a,b in zip(outputs,wants)), 'independent stable-top128 qualification differs')
            require(same_bits(outputs[2],ref[:4096]), 'qualified full-score bits differ')
            record = {'B0': quality(outputs[0],ref[:4096],cutoff), 'O1': quality(outputs[1],ref[:4096],cutoff)}
        else:
            indices = selections[idx][0]
            part = subset(lib,x[:4096],q,indices)
            want = np.zeros(4096,dtype='<f8')
            for j in indices:
                delta = x[:4096,j].astype(np.float64)-float(q[j]); want += delta*delta
            require(same_bits(part,want), 'independent C1 qualification bits differ')
            record = {'C1': quality(part,ref[:4096],cutoff)}
        qualification.append({'query_id': qid, **record})
        ref._mmap.close()
    save(work/'QUALIFICATION.json', {'queries': qualification, 'pairs': 131072, 'passed': True})
    save(work/'START.json', {'qualified_before_full_population': True, 'source_sha256': frozen,
                            'query_bytes_sha256': hashlib.sha256(queries.tobytes()).hexdigest()})
    rows = []; manifest = {}; boundary = 0
    u = 2.**-53; gamma = 960*u/(1-960*u)
    print('Qualification passed; starting Gate5'+args.stage+' 32 x 1M',flush=True)
    for idx, (qid,q) in enumerate(zip(w['query_ids'],queries)):
        tick = time.monotonic()
        if args.stage == 'A':
            b0, top, full = oracle(lib,x,q)
        else:
            part = subset(lib,x,q,selections[idx][0])
        # A validation-only frozen full-score file is not a candidate argument.
        ref = np.memmap(args.cache/f'{qid}.f64', mode='r', dtype='<f8', shape=(n,))
        if args.stage == 'A':
            require(same_bits(full,ref), 'full-population full-score bits differ')
            r = {'B0': quality(b0,ref,cutoff), 'O1': quality(top,ref,cutoff)}
            expect = c['baseline']['expected_queries'][idx]
            require(r['B0']['survivors'] == expect['survivors'] and r['B0']['hits'] == expect['hits'],
                    'remeasured B0 differs from exact frozen parent')
            near = int(np.count_nonzero(np.abs(top-cutoff) <= gamma*np.maximum(top,cutoff)))
            r['oracle_numerical_boundary_pairs'] = near; boundary += near
            r['full_distance_bit_mismatches'] = 0
            for name,array in [('B0',b0),('O1',top)]: keep_array(work,qid,name,array,manifest)
        else:
            r = {'C1': quality(part,ref,cutoff)}
            keep_array(work,qid,'C1',part,manifest)
        ref._mmap.close()
        r.update(query_id=qid, query_index=idx, operational_seconds=time.monotonic()-tick)
        rows.append(r); save(work/'queries'/f'q{idx:02}.json',r)
        print('PASS',idx+1,'/',32,qid,{k:v['survivors'] for k,v in r.items() if k in ('B0','O1','C1')},flush=True)
    x._mmap.close()
    require(frozen == {name: sha(ROOT/name) for name in frozen}, 'measurement source changed')
    require(sha(args.data) == w['data_sha256'], 'data changed during run')
    for name,digest in references.items(): require(sha(args.cache/name) == digest, 'reference changed during run')
    save(work/'QUERY_RESULTS.json',rows); save(work/'RAW_MANIFEST.json',{'files':manifest})
    if args.stage == 'A':
        total_b0 = sum(r['B0']['survivors'] for r in rows)
        total_o1 = sum(r['O1']['survivors'] for r in rows)
        gate = 'UNCLASSIFIED' if boundary else gate_a(total_o1,total_b0)
        totals = {'B0_total_survivors': total_b0, 'O1_total_survivors': total_o1,
                  'ratio': total_o1/total_b0, 'numerical_boundary_pairs': boundary, 'gate': gate}
    else:
        total = sum(r['C1']['survivors'] for r in rows); b0total = c['baseline']['expected_total_survivors']
        ratios = [r['C1']['survivors']/b['survivors'] for r,b in zip(rows,c['baseline']['expected_queries'])]
        p90 = distribution(ratios)['p90']
        if total*10 <= b0total*7 and p90 <= .80: gate = 'GO_PROOF_PER_BYTE_ROUTING'
        elif total*10 <= b0total*7: gate = 'UNCLASSIFIED'
        elif total*20 <= b0total*17: gate = 'CONDITIONAL'
        else: gate = 'NO_GO_PROOF_PER_BYTE_ROUTING'
        totals = {'C1_total_survivors': total, 'ratio': total/b0total,
                  'per_query_ratio_distribution': distribution(ratios), 'gate': gate}
    save(work/'RESULTS.json', {'complete': True, 'stage': args.stage, 'pairs': n*len(rows),
                             'CPU_workers': 4, 'GPU_starts': 0, 'NCU_starts': 0,
                             'operational_seconds': time.monotonic()-start, **totals})
    save(work/'CLOSURE.json', {'all_input_source_reference_hashes_unchanged': True,
                             'query_count': len(rows), 'population_processes': 1,
                             'CPU_workers': 4, 'GPU_starts': 0, 'NCU_starts': 0,
                             'python': platform.python_version(), 'numpy': np.__version__,
                             'finished_utc': datetime.datetime.now(datetime.timezone.utc).isoformat()})
    print(json.dumps(totals,sort_keys=True),flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--stage', choices=['A','B'], required=True)
    for name in ('data','cache','repo','work'):
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--stage-a', type=Path)
    args = p.parse_args()
    try:
        with (args.work.parent/'campaign.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            run(args)
    except Exception:
        if getattr(args,'created_work',False):
            save(args.work/'FAILURE.json', {'error': traceback.format_exc(), 'GPU_starts': 0,
                                          'stop': 'No automatic retry or source replacement'})
        raise
