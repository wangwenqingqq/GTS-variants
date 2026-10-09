#!/usr/bin/env python3
"""Prepare, build and verify one pinned shared kNN/range/update executor."""
import argparse
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE.parent / 'par_range_update'))
from reproduce import prepare as prepare_legacy, sha, read, save, command, select_gpu, validate_guard
from protocol import generate, check, self_test


def replace_once(text, before, after):
    assert text.count(before) == 1, ('integration anchor changed', before)
    return text.replace(before, after, 1)


def identities(source):
    return {str(p.relative_to(source)): sha(p) for p in sorted(source.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}


def prepare(work, upstream):
    legacy = work / 'legacy'; legacy.mkdir(); parent = prepare_legacy(legacy, upstream)
    shutil.copytree(legacy / 'source', work / 'source'); source = work / 'source'
    public = read(HERE / 'KNN_PARENT.json')
    for name, record in public.items():
        assert sha(HERE / 'kernels' / name) == record['sha256']
        shutil.copy2(HERE / 'kernels' / name, source / 'include' / name)
    path = source / 'include/knn_cutoff.cuh'
    path.write_text(replace_once(path.read_text(), 'struct TN { int pid; float min_dis; int size; int lid; int is_leaf; };\n', ''))
    shutil.copy2(HERE / 'knn_live.cuh', source / 'include/knn_live.cuh')
    path = source / 'include/update.cuh'; text = path.read_text()
    text = replace_once(text, '#include "region_bridge.cuh"', '#include "region_bridge.cuh"\n#include "knn_live.cuh"')
    start = text.index('void updateIndexRnn('); before = text[:start]; body = text[start:]
    body = replace_once(body, '\t\t\t\tu10.end_rebuild();', '\t\t\t\tuk::live.refresh(data_d,data_info[1]);\n\t\t\t\tu10.end_rebuild();')
    anchor = '\n\t\telse\n\t\t{\n\t\t\tcount_update_s++;'
    branch = '''
        else if(update_list[i].update_flag==3) {
            count_update_s++;qid_list[0]=update_list[i].update_id;
            uk::live.search(data_d,is_delete,is_delete_prefix,insert_list,tree_size,in_size,qid_list);
            u10.deliver(i,qid_list[0],tree_size,in_size,uk::live.k,uk::live.ids,uk::live.distances);
        }
'''
    body = replace_once(body, anchor, branch + anchor); path.write_text(before + body)
    path = source / 'include/region_bridge.cuh'
    path.write_text(replace_once(path.read_text(), 'std::string s=p?p:"NATIVE";', 'std::string s=p?p:"PAR_STRONG";'))
    path = source / 'src/main.cu'; text = path.read_text(); marker = 'int main(int argc,char** argv)'
    assert text.count(marker) == 1
    path.write_text(text[:text.index(marker)] + (HERE / 'main.inc').read_text())
    cases = generate(work / 'cases')
    manifest = dict(parent=parent, sources=identities(source), cases=cases,
                    artifact_files=identities(HERE), contract_sha256=sha(HERE / 'DESIGN.md'))
    save(work / 'PREPARED.json', manifest); return manifest


def verify_sources(work, manifest):
    assert identities(work / 'source') == manifest['sources']
    assert identities(work / 'legacy/source') == manifest['parent']['sources']
    assert identities(HERE) == manifest['artifact_files'], 'recipe changed after preparation'


def build(work):
    manifest = read(work / 'PREPARED.json'); verify_sources(work, manifest)
    nvcc = str(Path(shutil.which('nvcc')).resolve())
    (work / 'bin').mkdir()
    commands = {}
    for name, source in [('unified', work / 'source'), ('legacy', work / 'legacy/source')]:
        cmd = [nvcc, '-std=c++17', '-O3', '-arch=sm_120', '-lineinfo', '-rdc=true',
               '-Xnvlink=--ignore-host-info', '--ptxas-options=-v', '-I' + str(source / 'include'),
               source / 'src/main.cu', '-o', work / 'bin' / name]
        command(cmd, work / ('BUILD_' + name + '.log')); commands[name] = list(map(str, cmd))
    built = dict(commands=commands, binary_sha256={name: sha(work / 'bin' / name) for name in commands},
                 nvcc_version=subprocess.check_output([nvcc, '--version'], text=True))
    save(work / 'BUILD.json', built); return built


def malformed_checks(work):
    root = work / 'malformed'; root.mkdir(); source = work / 'cases/boundary0'
    good_data = (source / 'data.txt').read_text(); good_events = (source / 'events.txt').read_text()
    jobs = [dict(name='flag', events='1\n4 0\n'), dict(name='delete_rank', events='1\n1 1000\n'),
            dict(name='physical_rank', events='1\n3 1000\n'), dict(name='negative', events='1\n0 -1\n'),
            dict(name='truncated_data', data='128 1000 2\n0\n'), dict(name='trailing_event', events=good_events+'3 0\n'),
            dict(name='noninteger_data', data=good_data.replace('108 ', '108.5 ', 1)),
            dict(name='shape', data=good_data.replace('128 1000 2', '128 999 2', 1)),
            dict(name='capacity', events='12\n2 0\n'+ '0 0\n'*11),
            dict(name='k', k=7), dict(name='radius', radius=1)]
    for job in jobs:
        directory = root / job['name']; directory.mkdir()
        (directory / 'data.txt').write_text(job.get('data', good_data)); (directory / 'events.txt').write_text(job.get('events', good_events))
        cmd = [work / 'bin/unified', directory / 'data.txt', directory / 'events.txt', '2',
               str(job.get('radius', 0)), directory / 'output', str(job.get('k', 8))]
        env = {**os.environ, 'CUDA_VISIBLE_DEVICES': '', 'REGION_MODE': 'PAR_STRONG', 'KNN_MODE': 'BOUND'}
        p = subprocess.run(list(map(str, cmd)), env=env, capture_output=True, text=True)
        (directory / 'stdout.log').write_text(p.stdout); (directory / 'stderr.log').write_text(p.stderr)
        assert p.returncode == 1 and 'FAIL: ' in p.stderr and 'CUDA' not in p.stderr and 'device' not in p.stderr.lower(), (job, p.stderr)
        assert not list(directory.glob('output*'))
    save(work / 'CPU_MALFORMED.json', dict(passed=len(jobs), gpu_allocation=False))


def jobs():
    result = []
    for case in ('boundary0', 'boundary10000', 'ties8', 'ties32', 'sparse8', 'sparse32'):
        for mode, knn in [('PAR_STRONG', 'BOUND'), ('PAR_STRONG', 'FULL'), ('NATIVE', 'FULL')]:
            result.append(dict(label=f'{case}_{mode}_{knn}', case=case, mode=mode, knn=knn, target='unified', tool=None))
    for tool in ('memcheck', 'racecheck', 'synccheck'):
        result.append(dict(label='sanitize_'+tool, case='boundary10000', mode='PAR_STRONG', knn='BOUND', target='unified', tool=tool))
    result.append(dict(label='sparse_memcheck', case='sparse32', mode='PAR_STRONG', knn='BOUND', target='unified', tool='memcheck'))
    for case, knn in [('full8', 'BOUND'), ('full32', 'BOUND'), ('full8', 'FULL')]:
        result.append(dict(label=case+'_'+knn, case=case, mode='PAR_STRONG', knn=knn, target='unified', tool=None))
    for round_index, order in enumerate([['legacy', 'unified'], ['unified', 'legacy'], ['legacy', 'unified']], 1):
        for target in order:
            result.append(dict(label=f'regression_{round_index}_{target}', case='legacy', mode='PAR_STRONG',
                               knn='BOUND' if target=='unified' else None, target=target, tool=None, round=round_index))
    return result


def verify(work, requested_gpu):
    manifest = read(work / 'PREPARED.json'); built = read(work / 'BUILD.json'); verify_sources(work, manifest)
    for name, digest in built['binary_sha256'].items(): assert sha(work / 'bin' / name) == digest
    self_test(); malformed_checks(work)
    gpu = select_gpu(requested_gpu); sanitizer = str(Path(shutil.which('compute-sanitizer')).resolve())
    runner = REPO / 'diagnostics/native_knn_faiss_ivf_20261003/run_locked.py'
    registered = dict(jobs=jobs(), gpu=gpu, prepared_sha256=sha(work / 'PREPARED.json'), build_sha256=sha(work / 'BUILD.json'),
                      contract_sha256=sha(HERE / 'DESIGN.md'), guard_sha256=sha(runner),
                      driver=subprocess.check_output(['nvidia-smi', '--query-gpu=driver_version', '--format=csv,noheader', '-i', gpu['uuid']], text=True).strip(),
                      estimator='process-paired geometric mean; 20000 bootstrap replicates seed202610090913',
                      nonregression='upper95 CI<=1.05 and each ratio<=1.05', paper_speedup_claim=False)
    save(work / 'REGISTERED.json', registered); (work / 'outputs').mkdir()
    rows = []; guards = []; identity = {}
    for job in registered['jobs']:
        label = job['label']; metadata = manifest['cases'][job['case']]; case = work / 'cases' / job['case']
        for name in ('data', 'events'): assert sha(case / (name+'.txt')) == metadata[name+'_sha256']
        target = work / 'bin' / job['target']; assert sha(target) == built['binary_sha256'][job['target']]
        cmd = [target, case/'data.txt', case/'events.txt', '2', str(metadata['radius']), work/'outputs'/label]
        if job['target']=='unified': cmd += [str(metadata['k'])]
        if job['tool']: cmd = [sanitizer, '--tool', job['tool'], '--error-exitcode', '77', *cmd]
        env = {**os.environ, 'REGION_MODE': job['mode'], 'KNN_MODE': job['knn'] or 'BOUND', 'U10_OBSERVE': '1', 'U10_TREE_AUDIT': '0'}
        run = work / 'runs' / label
        command([sys.executable, runner, '--gpu', gpu['uuid'], '--numa-node', str(gpu['numa_node']),
                 '--output', run, '--', *cmd], work/(label+'.runner.log'), env=env)
        validate_guard(run, cmd[0]); logs = (run/'stdout.log').read_text() + (run/'stderr.log').read_text()
        if job['tool']:
            needle = ('RACECHECK SUMMARY: 0 hazards displayed (0 errors, 0 warnings)' if job['tool']=='racecheck' else 'ERROR SUMMARY: 0 errors')
            assert needle in logs, (label, logs[-2000:])
        result = check(work/'outputs'/label, case, metadata, job['mode'], job['knn'])
        value = [result['outputs'][s] for s in ('.ids.i32', '.dist.f32', '.queries.csv')]
        assert identity.setdefault(job['case'], value) == value, 'ordered cross-mode output differs'
        rows.append(dict(**job, **result)); guards.append(dict(label=label, receipt_sha256=sha(run/'receipt.json'),
                     target_binary_sha256=sha(target), guard_valid=True))
        save(work/'ROWS.json', rows); save(work/'GUARDS.json', guards); print(label, 'PASS', flush=True)
    verify_sources(work, manifest)
    for name, digest in built['binary_sha256'].items(): assert sha(work/'bin'/name) == digest
    ratios = []
    for round_index in range(1,4):
        pair = {r['target']: r['summary']['trace_ms'] for r in rows if r.get('round')==round_index}
        ratios.append(pair['unified']/pair['legacy'])
    logs = np.log(ratios); rng = np.random.default_rng(202610090913)
    ci = np.quantile(np.exp(logs[rng.integers(0,3,(20000,3))].mean(1)), [.025,.975]).tolist()
    admitted = ci[1]<=1.05 and max(ratios)<=1.05
    result = dict(functional_integration=True, default_keeper_promoted=admitted, paper_speedup_claim=False,
                  processes=len(rows), queries_checked=sum(r['queries_checked'] for r in rows),
                  events_checked=sum(r['events_checked'] for r in rows),
                  regression=dict(ratios=ratios, geomean=math.exp(logs.mean()), CI95=ci, passed=admitted),
                  all_ordered_outputs_identical=True, all_guard_receipts_valid=True,
                  rows_sha256=sha(work/'ROWS.json'), guards_sha256=sha(work/'GUARDS.json'))
    save(work/'COMPLETE.json', result); print(result, flush=True)


def main():
    if not __debug__: raise RuntimeError('Python -O disables verification; unsupported')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path); parser.add_argument('--upstream', type=Path)
    parser.add_argument('--gpu'); parser.add_argument('--phase', choices=['all','prepare','build','verify'], default='all')
    args = parser.parse_args(); self_test()
    if args.work is None:
        assert args.phase in ('all','prepare'); args.work = Path(tempfile.mkdtemp(prefix='gts-unified-'))
    else:
        args.work = args.work.resolve()
        if args.phase in ('all','prepare'): args.work.mkdir(parents=True, exist_ok=False)
    if any((p/'.git').exists() for p in [args.work, *args.work.parents]): raise RuntimeError('raw work must be outside Git')
    print('WORK', args.work, flush=True)
    if args.phase in ('all','prepare'): prepare(args.work, args.upstream)
    if args.phase in ('all','build'): build(args.work)
    if args.phase in ('all','verify'): verify(args.work, args.gpu)


if __name__ == '__main__': main()
