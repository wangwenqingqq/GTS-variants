#!/usr/bin/env python3
"""Build pinned PAR source and verify serialized range/update traces on one idle GPU."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import numpy as np

from fixtures import generate, load_case

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
REGION = REPO / 'diagnostics/region_exec_20261008'
sys.path.insert(0, str(REGION))
from audit_closure import integer_oracle


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + '\n')


def command(args, log=None, cwd=None, env=None):
    args = list(map(str, args))
    if log:
        with Path(log).open('w') as output:
            subprocess.run(args, cwd=cwd, env=env, stdout=output, stderr=subprocess.STDOUT, check=True)
    else:
        subprocess.run(args, cwd=cwd, env=env, check=True)


def prepare(work, upstream=None):
    pins = read(HERE / 'SOURCE_PINS.json')
    if upstream is None:
        upstream = work / 'upstream'
        command(['git', 'init', upstream], work / 'FETCH.log')
        command(['git', '-C', upstream, 'fetch', '--depth=1', pins['upstream']['repository'],
                 pins['upstream']['commit']], work / 'FETCH_COMMIT.log')
        command(['git', '-C', upstream, 'checkout', '--detach', 'FETCH_HEAD'], work / 'CHECKOUT.log')
    source = Path(upstream) / pins['upstream']['subdirectory']
    for name, digest in pins['upstream']['files'].items():
        assert sha(source / name) == digest, ('upstream identity', name)
    destination = work / 'source'
    (destination / 'include').mkdir(parents=True)
    (destination / 'src').mkdir()
    for name in pins['upstream']['files']:
        shutil.copy2(source / name, destination / name)
    command(['git', 'apply', '--no-index', '--check', HERE / 'adapter.patch'], cwd=destination)
    command(['git', 'apply', '--no-index', HERE / 'adapter.patch'], cwd=destination)
    path = destination / 'src/main.cu'
    original = path.read_text()
    marker = 'int main(int argc, char **argv)'
    assert original.count(marker) == 1
    path.write_text('#include "u10_trace.hpp"\n' + original[:original.index(marker)]
                    + (HERE / 'main.inc').read_text())
    shutil.copy2(HERE / 'u10_trace.hpp', destination / 'include/u10_trace.hpp')
    for extension in ('*.cuh', '*.hpp'):
        for path in REGION.glob(extension):
            shutil.copy2(path, destination / 'include' / path.name)
    actual = {str(path.relative_to(destination)): sha(path)
              for path in destination.rglob('*') if path.is_file()}
    assert actual == pins['prepared_sources'], 'qualified source identity changed'
    historical = read(REPO / pins['historical_source_manifest'])['sources']
    assert actual == historical, 'publication and source pin disagree'
    cases = generate(work / 'cases')
    manifest = dict(sources=actual, source_pins_sha256=sha(HERE / 'SOURCE_PINS.json'),
                    artifact_files={p.name: sha(p) for p in HERE.iterdir() if p.is_file()},
                    shared_files={str(p.relative_to(REPO)): sha(p) for p in [
                        REGION / 'audit_closure.py', REGION / 'test_plan.cpp',
                        REGION / 'test_region.cu',
                        REPO / 'diagnostics/native_knn_faiss_ivf_20261003/run_locked.py']},
                    cases={name: dict(radius=case['radius'], events=len(case['operations']),
                                     queries=sum(f == 2 for f, _ in case['operations']),
                                     data_sha256=sha(work / 'cases' / name / 'data.txt'),
                                     events_sha256=sha(work / 'cases' / name / 'events.txt'))
                           for name, case in cases.items()})
    save(work / 'PREPARED.json', manifest)
    return manifest


def select_gpu(requested=None):
    fields = 'index,uuid,name,pci.bus_id,compute_cap'
    text = subprocess.check_output(['nvidia-smi', '--query-gpu=' + fields,
                                    '--format=csv,noheader'], text=True)
    devices = [[s.strip() for s in line.split(',')] for line in text.splitlines()]
    for index, uuid, name, bus, capability in devices:
        if requested is not None and requested not in (index, uuid):
            continue
        if capability != '12.0':
            continue
        apps = subprocess.check_output(['nvidia-smi', '-i', uuid, '--query-compute-apps=pid',
                                       '--format=csv,noheader'], text=True).strip()
        if apps:
            continue
        domain, rest = bus.lower().split(':', 1)
        node = int((Path('/sys/bus/pci/devices') / f'{int(domain, 16):04x}:{rest}' / 'numa_node').read_text())
        if node < 0:
            raise RuntimeError('Unknown PCI NUMA mapping; no implicit node binding')
        return dict(index=int(index), uuid=uuid, name=name, capability=capability, numa_node=node)
    raise RuntimeError('No requested idle sm_120 GPU; existing processes are never stopped')


def build(work, nvcc):
    include = work / 'source/include'
    base = [nvcc, '-std=c++17', '-O3', '-arch=sm_120', '-lineinfo', '-I' + str(include)]
    commands = {
        'par': [*base, '-rdc=true', '-Xnvlink=--ignore-host-info', '--ptxas-options=-v',
                work / 'source/src/main.cu', '-o', work / 'bin/par'],
        'test_region': [*base, REGION / 'test_region.cu', '-o', work / 'bin/test_region'],
        'test_plan': ['g++', '-std=c++17', '-O2', '-I' + str(include),
                      REGION / 'test_plan.cpp', '-o', work / 'bin/test_plan'],
    }
    (work / 'bin').mkdir()
    for name, cmd in commands.items():
        command(cmd, work / f'BUILD_{name}.log')
    command([work / 'bin/test_plan'], work / 'CPU_PLAN.log')
    result = dict(commands={k: list(map(str, v)) for k, v in commands.items()},
                  binary_sha256={name: sha(work / 'bin' / name) for name in commands})
    save(work / 'BUILD.json', result)
    return result


def validate_output(work, label, case, radius, mode):
    prefix = work / 'outputs' / label
    data, ops = load_case(work / 'cases' / case)
    queries, states, rebuilt = integer_oracle(data, ops, radius)
    ids = np.fromfile(str(prefix) + '.ids.i32', dtype='<i4')
    distances = np.fromfile(str(prefix) + '.dist.f32', dtype='<f4')
    with open(str(prefix) + '.queries.csv') as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == len(queries)
    offset = 0
    for row, (step, qid, n, buffer, expected) in zip(rows, queries):
        assert [int(row[k]) for k in ('step', 'qid', 'tree_size', 'buffer')] == [step, qid, n, buffer]
        count = int(row['count'])
        assert int(row['offset']) == offset and count == len(expected)
        actual = dict(zip(map(int, ids[offset:offset + count]), map(bytes, distances[offset:offset + count])))
        assert len(actual) == count and actual == expected, (label, step, 'IDs/FP32 fields')
        offset += count
    assert offset == len(ids) == len(distances)
    assert Path(str(prefix) + '.ids.i32').stat().st_size == offset * 4
    assert Path(str(prefix) + '.dist.f32').stat().st_size == offset * 4
    with open(str(prefix) + '.ops.csv') as stream:
        op_rows = list(csv.DictReader(stream))
    assert len(op_rows) == len(states)
    for step, (row, state) in enumerate(zip(op_rows, states)):
        assert int(row['step']) == step and int(row['flag']) == ops[step][0]
        assert tuple(int(row[k]) for k in ('base_before', 'buffer_before', 'base_after', 'buffer_after')) == state[:4]
        assert (float(row['rebuild_ms']) > 0) == state[4]
        assert float(row['ack_ms']) >= float(row['rebuild_ms']) >= 0
    region = read(str(prefix) + '.region.json')
    assert region['mode'] == {'PAR_STRONG': 1, 'NATIVE': 0}[mode], 'wrong dispatch'
    assert region['final_owned_bytes'] == 0
    assert region['refreshes'] == (rebuilt + 1 if mode == 'PAR_STRONG' else 0)
    summary = read(str(prefix) + '.summary.json')
    assert summary['observe'] and not summary['tree_audit'] and summary['results'] == offset
    assert np.isfinite(summary['trace_ms']) and summary['trace_ms'] > 0
    outputs = {suffix: sha(str(prefix) + suffix) for suffix in
               ('.ids.i32', '.dist.f32', '.queries.csv', '.ops.csv', '.summary.json', '.region.json')}
    return dict(label=label, case=case, mode=mode, queries_checked=len(queries),
                events_checked=len(states), rebuilds=rebuilt, outputs=outputs,
                summary=summary, region=region)


def validate_guard(run, executable):
    receipt = read(run / 'receipt.json')
    assert receipt['runtime_valid'] and receipt['exit_code'] == 0 and receipt['stop_reason'] is None
    assert receipt['binary_sha256'] == sha(executable)
    assert not read(run / 'before.json')['apps'] and not read(run / 'after.json')['apps']
    assert all(not check['foreign'] for check in read(run / 'checks.json'))


def verify(work, manifest, built, gpu, sanitizer):
    runner = REPO / 'diagnostics/native_knn_faiss_ivf_20261003/run_locked.py'
    jobs = [('structural', None, 'PAR_STRONG', None)]
    for case in ('boundary0', 'boundary10000'):
        jobs += [(case + '_' + mode, case, mode, None) for mode in ('PAR_STRONG', 'NATIVE')]
    jobs += [('sanitize_' + tool, 'boundary10000', 'PAR_STRONG', tool)
             for tool in ('memcheck', 'racecheck', 'synccheck')]
    jobs += [('native_memcheck', 'boundary10000', 'NATIVE', 'memcheck')]
    jobs += [('full_' + mode, 'full', mode, None) for mode in ('PAR_STRONG', 'NATIVE')]
    save(work / 'REGISTERED.json', dict(prepared_sha256=sha(work / 'PREPARED.json'),
         build_sha256=sha(work / 'BUILD.json'), gpu=gpu, jobs=jobs,
         purpose='fresh-source correctness/reproduction, not a new performance campaign',
         scope='fixed synthetic N1000 D128 B1 range + serialized reference reinsertion/live-rank deletion',
         kernel_change=False, timing_claim_admitted=False))
    (work / 'outputs').mkdir()
    rows = []; guards = []
    for label, case, mode, tool in jobs:
        target = work / 'bin' / ('par' if case else 'test_region')
        assert sha(target) == built['binary_sha256'][target.name]
        cmd = [target]
        if case:
            metadata = manifest['cases'][case]
            for name in ('data', 'events'):
                assert sha(work / 'cases' / case / (name + '.txt')) == metadata[name + '_sha256']
            cmd += [work / 'cases' / case / 'data.txt', work / 'cases' / case / 'events.txt',
                    '2', str(metadata['radius']), work / 'outputs' / label]
        if tool:
            cmd = [sanitizer, '--tool', tool, '--error-exitcode', '77', *cmd]
        env = {**os.environ, 'REGION_MODE': mode, 'U10_OBSERVE': '1', 'U10_TREE_AUDIT': '0'}
        run = work / 'runs' / label
        command([sys.executable, runner, '--gpu', gpu['uuid'], '--numa-node', str(gpu['numa_node']),
                 '--output', run, '--', *cmd], work / (label + '.runner.log'), env=env)
        validate_guard(run, cmd[0])
        logs = (run / 'stdout.log').read_text() + (run / 'stderr.log').read_text()
        if tool:
            needle = ('RACECHECK SUMMARY: 0 hazards displayed (0 errors, 0 warnings)' if tool == 'racecheck'
                      else 'ERROR SUMMARY: 0 errors')
            assert needle in logs, (label, logs[-2000:])
        if not case:
            assert 'STRUCTURAL_PASS: 9 topologies x6 states x2 modes' in logs
        else:
            row = validate_output(work, label, case, metadata['radius'], mode)
            row['sanitizer'] = tool; rows.append(row)
        guards.append(dict(label=label, receipt_sha256=sha(run / 'receipt.json'),
                           guard_valid=True, target_binary_sha256=sha(target)))
        save(work / 'ROWS.json', rows); save(work / 'GUARDS.json', guards)
        print(label, 'PASS', flush=True)
    identity = {}
    for row in rows:
        value = [row['outputs'][s] for s in ('.ids.i32', '.dist.f32', '.queries.csv')]
        assert identity.setdefault(row['case'], value) == value, 'ordered native/PAR outputs differ'
    for name, digest in manifest['sources'].items():
        assert sha(work / 'source' / name) == digest, 'source changed during replay'
    for name, digest in built['binary_sha256'].items():
        assert sha(work / 'bin' / name) == digest, 'binary changed during replay'
    result = dict(state='scoped_artifact_verified', jobs_completed=len(jobs),
                  queries_checked=sum(row['queries_checked'] for row in rows),
                  events_checked=sum(row['events_checked'] for row in rows),
                  all_ordered_outputs_identical_per_case=True, all_guard_receipts_valid=True,
                  prepared_sha256=sha(work / 'PREPARED.json'), build_sha256=sha(work / 'BUILD.json'),
                  registered_sha256=sha(work / 'REGISTERED.json'), rows_sha256=sha(work / 'ROWS.json'),
                  guards_sha256=sha(work / 'GUARDS.json'), timing_claim_admitted=False,
                  whole_gtspp_artifact=False)
    save(work / 'COMPLETE.json', result)
    print(json.dumps(result, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, default=Path(tempfile.gettempdir()) / 'par-reproduction',
                        help='New output directory outside Git; never overwritten')
    parser.add_argument('--upstream', type=Path, help='Optional read-only pinned GTS checkout; otherwise fetched')
    parser.add_argument('--gpu', help='Idle GPU index or UUID; default selects the first idle sm_120 GPU')
    parser.add_argument('--prepare-only', action='store_true', help='Regenerate source/inputs without CUDA or GPU execution')
    args = parser.parse_args()
    if not __debug__:
        raise RuntimeError('Run without Python -O: evidence assertions must remain enabled')
    for dependency in (['git'] if args.prepare_only else ['git', 'g++', 'nvcc', 'compute-sanitizer', 'nvidia-smi', 'numactl']):
        if shutil.which(dependency) is None:
            raise RuntimeError('Missing installed dependency: ' + dependency)
    work = args.work.resolve()
    parent = work
    while not parent.exists():
        parent = parent.parent
    in_git = subprocess.run(['git', '-C', str(parent), 'rev-parse', '--is-inside-work-tree'],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
    if in_git:
        raise RuntimeError('Raw work directory must be outside any Git checkout')
    gpu = None if args.prepare_only else select_gpu(args.gpu)
    work.mkdir(parents=True, exist_ok=False)
    manifest = prepare(work, args.upstream)
    if args.prepare_only:
        print('PREPARED: 16 exact source identities and three deterministic cases; no GPU run')
        return
    # CUDA tools locate headers/helper binaries relative to their real toolkit directory.
    nvcc = str(Path(shutil.which('nvcc')).resolve())
    sanitizer = str(Path(shutil.which('compute-sanitizer')).resolve())
    save(work / 'ENVIRONMENT.json', dict(gpu=gpu, python=sys.version, numpy=np.__version__,
         nvcc=subprocess.check_output([nvcc, '--version'], text=True),
         driver=subprocess.check_output(['nvidia-smi', '-i', gpu['uuid'], '--query-gpu=driver_version',
                                         '--format=csv,noheader'], text=True).strip()))
    built = build(work, nvcc)
    verify(work, manifest, built, gpu, sanitizer)


if __name__ == '__main__':
    main()
