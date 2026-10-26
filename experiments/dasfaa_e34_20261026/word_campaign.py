"""Explicit, bounded Word E4 phase; reuse the frozen vector safety executor."""
from contextlib import contextmanager
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import sys
import time

import campaign as C
import lock_support as L

NS = (61000, 150000, 300000, 611000)
QS = (1, 32, 1024)
REQUIRED_PATHS = ('word_manifest', 'tree_binary', 'count_binary', 'scan_script', 'audit_script',
                  'oracle_binary', 'oracle_source', 'tree_source', 'source_build_manifest', 'word_build_manifest')


def task_file(root, name):
    path = (root / name).resolve()
    if not path.is_relative_to(root):
        raise L.SafetyStop('Word artifact is outside the task root: ' + str(name))
    return path


def freeze_path(root):
    return Path(os.environ.get('E34_WORD_FREEZE', root / 'resume_20261026/WORD_PHASE_FREEZE.json')).resolve()


def check_stops(root):
    if any((root / name).exists() for name in ('STOP_CAMPAIGN.json', 'SSH_FAILED.json', 'STOP_SSH')):
        raise L.SafetyStop('global campaign/SSH stop is latched; Word must not run')
    if os.environ.get('E34_SSH_FAILED', '0') != '0':
        raise L.SafetyStop('caller reported an SSH failure; Word must not run')
    marker = os.environ.get('E34_SSH_STOP_FILE')
    if marker and Path(marker).exists():
        raise L.SafetyStop('caller SSH-failure marker exists; Word must not run')


def vector_epoch(root):
    path = task_file(root, Path((root / 'logs/active_epoch.txt').read_text().strip()))
    complete = path / 'COMPLETE.json'
    if ((path / 'FAILED.json').exists() or not complete.is_file()
            or not json.loads(complete.read_text()).get('plan_processed')):
        raise L.SafetyStop('vector plan must be processed before the Word phase')
    return path


def verify_word_build(root, proof):
    paths, files = proof['paths'], proof['files']
    record = json.loads(task_file(root, paths['word_build_manifest']).read_text())
    for name, expected in record['files'].items():
        task_file(root, name)
        if files.get(name) != expected:
            raise L.SafetyStop('Word build artifact is not bound to the phase: ' + name)
    if not str(record['toolchain']['cuda']).startswith('13.1.') or record['toolchain']['target_sm'] != 120:
        raise L.SafetyStop('Word build toolchain/architecture differs from the contract')
    for key in ('tree_binary', 'count_binary', 'oracle_binary'):
        source = paths['oracle_source' if key == 'oracle_binary' else 'tree_source']
        if record['binaries'][key] != paths[key] or record['sources'][key] != source:
            raise L.SafetyStop('Word build binary/source binding mismatch: ' + key)
        log = record['guard_logs'][key]
        for name in (paths[key], source, log):
            if name not in record['files'] or files.get(name) != record['files'][name]:
                raise L.SafetyStop('Word binary/source/guard log is not build-frozen: ' + name)
        cmd = record['commands'][key]
        if not isinstance(cmd, list) or not cmd or not all(isinstance(x, str) for x in cmd):
            raise L.SafetyStop('invalid Word compile command: ' + key)
        source_args = [(Path(arg) if Path(arg).is_absolute() else root / arg).resolve()
                       for arg in cmd if not arg.startswith('-')]
        if task_file(root, source) not in source_args:
            raise L.SafetyStop('Word compile command did not use the bound source: ' + key)
        if '-o' not in cmd or cmd.index('-o') + 1 >= len(cmd) or task_file(root, cmd[cmd.index('-o') + 1]) != task_file(root, paths[key]):
            raise L.SafetyStop('Word compile command output is not the bound binary: ' + key)
        defines = [arg for arg in cmd if arg.startswith('-DINSTRUMENT')]
        if (key == 'count_binary' and defines != ['-DINSTRUMENT=1']) or (key == 'tree_binary' and any(arg != '-DINSTRUMENT=0' for arg in defines)):
            raise L.SafetyStop('Word timing/count instrumentation binding is invalid: ' + key)
        events = [json.loads(line) for line in task_file(root, log).read_text().splitlines() if line.strip()]
        if (not events or events[0].get('event') != 'start' or events[0].get('cmd') != cmd
                or events[-1].get('event') != 'end' or events[-1].get('exit_code') != 0
                or sum(e.get('event') == 'start' for e in events) != 1
                or sum(e.get('event') == 'end' for e in events) != 1
                or any(e.get('event') in ('killed', 'refused') for e in events)):
            raise L.SafetyStop('Word successful guarded compile evidence mismatch: ' + key)


def verify_runtime_files(proof):
    runtime = proof.get('runtime_files')
    if not isinstance(runtime, dict) or not runtime:
        raise L.SafetyStop('Word read-only runtime dependency freeze is missing')
    for name, expected in runtime.items():
        path = Path(name)
        if (not path.is_absolute() or not path.is_file()
                or path.stat().st_size != expected['bytes'] or L.sha(path) != expected['sha256']):
            raise L.SafetyStop('Word runtime dependency changed or was not absolute: ' + name)


def python_identity():
    invocation = os.environ['FAISS_PYTHON']
    if not Path(invocation).is_absolute():
        raise L.SafetyStop('FAISS_PYTHON must be an absolute, exact invocation path')
    resolved = Path(invocation).resolve()
    return {'python_invocation': invocation, 'python': str(resolved),
            'python_sha256': L.sha(resolved)}


def verified_inputs(root):
    proof_file = freeze_path(root)
    if not proof_file.is_relative_to(root):
        raise L.SafetyStop('Word phase freeze must be task-local')
    proof = json.loads(proof_file.read_text())
    if proof.get('python_invocation') != os.environ['FAISS_PYTHON']:
        raise L.SafetyStop('Word interpreter invocation differs from runtime provenance')
    files, paths = proof['files'], proof['paths']
    verify_runtime_files(proof)
    for name, record in files.items():
        path = task_file(root, name)
        if path.stat().st_size != record['bytes'] or L.sha(path) != record['sha256']:
            raise L.SafetyStop('Word frozen artifact changed: ' + name)
    for key in REQUIRED_PATHS:
        if paths[key] not in files:
            raise L.SafetyStop('unfrozen Word artifact: ' + key)
    verify_word_build(root, proof)
    manifest = json.loads(task_file(root, paths['word_manifest']).read_text())
    if (manifest['seed'] != 20261026 or manifest['query_rows'] != 1000
            or manifest['stride'] != 109 or manifest['maximum_length'] >= 109
            or tuple(c['N'] for c in manifest['cases']) != NS):
        raise L.SafetyStop('Word workload differs from the frozen contract')
    for name, record in manifest['files'].items():
        if files.get(name) != record:
            raise L.SafetyStop('Word input manifest is not covered by the phase freeze: ' + name)
    build_file = task_file(root, paths['source_build_manifest'])
    build = json.loads(build_file.read_text())
    for name, digest in build['compiled_sources'].items():
        if name.startswith('source_p/include/'):
            relative = str((build_file.parent / name).relative_to(root))
            if files.get(relative, {}).get('sha256') != digest:
                raise L.SafetyStop('Word compiled P header is not frozen: ' + relative)
    cases = []
    for original in manifest['cases']:
        c = dict(original)
        for key in ('base', 'query'):
            task_file(root, c[key])
            if c[key] not in manifest['files'] or files.get(c[key]) != manifest['files'][c[key]]:
                raise L.SafetyStop('Word case input is not frozen by both manifests: ' + c[key])
        if c['k'] != 8 or tuple(c['Q']) != QS or c['D'] != 109:
            raise L.SafetyStop('Word k/Q/stride mismatch')
        if c['N'] > manifest['available_base_rows']:
            if not c['state'].startswith('infeasible:'):
                raise L.SafetyStop('unavailable Word load was marked runnable')
        elif not c['query_isolation']['isolated']:
            c['state'] = 'blocked: query/index exact-value overlap'
        elif c['state'] != 'feasible':
            raise L.SafetyStop('unrecognized feasible Word load state')
        if c['state'] == 'feasible':
            digest = proof['oracle_sha256'][str(c['N'])]
            if files.get(c['oracle'], {}).get('sha256') != digest or files[c['oracle']]['bytes'] != 120000:
                raise L.SafetyStop('Word oracle is not frozen: ' + c['oracle'])
            c['oracle_sha256'] = digest
        cases.append(c)
    return proof, cases


def identity(root):
    proof, cases = verified_inputs(root)
    vector = vector_epoch(root)
    python = python_identity()
    return {'phase_freeze_sha256': L.sha(freeze_path(root)),
            'runner_sha256': L.sha(__file__), 'executor_sha256': L.sha(C.__file__),
            'lock_support_sha256': L.sha(L.__file__), 'guard_sha256': L.sha(L.GUARD),
            **python,
            'vector_epoch': str(vector), 'vector_complete_sha256': L.sha(vector / 'COMPLETE.json'),
            'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip()}


def plan(cases, root, epoch):
    bounded = dict(next(c for c in cases if c['state'] == 'feasible'))
    bounded.update(N=2000, oracle=str((epoch / 'word_bounded.oracle').relative_to(root)))
    bounded.pop('oracle_sha256', None)
    tasks = [{'kind': 'dependency', 'label': 'cupy_import'},
             {'kind': 'oracle', 'label': 'word_bounded_oracle', 'case': bounded}]
    for arm in 'PS':
        for tool in ('memcheck', 'synccheck'):
            for q in QS:
                tasks.append({'kind': 'sanitize', 'case': bounded, 'arm': arm, 'Q': q,
                              'tool': tool, 'label': f'sanitize_word_{arm}_{tool}_q{q}'})
    for c in cases:
        for q in QS:
            key = f'word_{c["N"]}_q{q}'
            for arm in 'PS':
                tasks.append({'kind': 'gate', 'case': c, 'arm': arm, 'Q': q,
                              'key': key, 'label': f'gate_{key}_{arm}'})
            tasks.append({'kind': 'count', 'case': c, 'arm': 'P', 'Q': q,
                          'key': key, 'label': 'count_' + key})
            tasks.append({'kind': 'work', 'case': c, 'Q': q, 'key': key, 'label': 'work_' + key})
    for r in range(6):
        for c in cases:
            for q in QS:
                key = f'word_{c["N"]}_q{q}'
                for arm in ('PS' if r % 2 == 0 else 'SP'):
                    tasks.append({'kind': 'time', 'case': c, 'arm': arm, 'Q': q,
                                  'round': r, 'key': key, 'label': f'time_r{r}_{key}_{arm}'})
    return tasks


def quality_path(epoch, task):
    return epoch / f'quality_{task["key"]}_{task["arm"]}.json'


def requires_gpu(epoch, task):
    if task['kind'] in ('dependency', 'oracle', 'work') or task['case']['state'] != 'feasible':
        return False
    return task['kind'] not in ('count', 'time') or json.loads(quality_path(epoch, task).read_text())['correct']


def command(root, proof, task):
    c, q, arm = task['case'], task['Q'], task['arm']
    if c['state'] != 'feasible' or not 8 <= c['N'] <= 10_000_000:
        raise L.SafetyStop('attempt to launch an unavailable/unsafe Word load')
    for key in ('base', 'query'):
        task_file(root, c[key])
        if c[key] not in proof['files']:
            raise L.SafetyStop('Word command input is not frozen: ' + c[key])
    args = [task_file(root, c['base']), task_file(root, c['query']), c['N'], q,
            3 if task['kind'] == 'time' else 0, 1 if task['kind'] == 'time' else 0, '{out}']
    paths = proof['paths']
    if arm == 'P':
        binary = paths['count_binary' if task['kind'] == 'count' else 'tree_binary']
        cmd = [root / binary, *args, 'unused_cache_disabled']
    elif arm == 'S':
        cmd = [os.environ['FAISS_PYTHON'], root / paths['scan_script'], *args]
    else:
        raise ValueError('only P/S are authorized in Word E4')
    if task['kind'] == 'sanitize':
        cmd = ['compute-sanitizer', '--tool', task['tool'], '--error-exitcode', '90', *cmd]
    return cmd


def verify_oracle(root, epoch, case):
    expected = case.get('oracle_sha256')
    if case['N'] == 2000:
        record = json.loads((epoch / 'word_bounded_oracle_manifest.json').read_text())
        if record['path'] != case['oracle'] or record['bytes'] != 120000:
            raise L.SafetyStop('bounded Word oracle identity mismatch')
        expected = record['sha256']
    path = root / case['oracle']
    if not expected or path.stat().st_size != 120000 or L.sha(path) != expected:
        raise L.SafetyStop('Word oracle changed: ' + str(path))


def jit_files(cache):
    files = {}
    for path in sorted(cache.rglob('*')):
        if path.suffix not in ('.cubin', '.cu'):
            continue
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(cache.resolve()):
            raise L.SafetyStop('unsafe CuPy cache artifact: ' + str(path))
        files[str(path.relative_to(cache))] = {'bytes': path.stat().st_size, 'sha256': L.sha(path)}
    return files


def completed_jit_anchors(epoch):
    anchors = []
    for path in sorted(epoch.glob('STEP_*_DONE.json')):
        checkpoint = json.loads(path.read_text())
        task, result = checkpoint['task'], checkpoint['result']
        if task.get('arm') != 'S':
            continue
        anchor = result.get('jit_manifest')
        skipped = (result['state'].startswith('not-run:')
                   or result.get('quality', {}).get('not_run')
                   or task['case']['state'] != 'feasible')
        if skipped:
            if anchor is not None:
                raise L.SafetyStop('skipped Word S step has a fabricated JIT anchor')
            continue
        if (anchor is None or anchor['manifest'] != task['label'] + '/jit_manifest.json'
                or anchor['sequence'] != len(anchors) + 1):
            raise L.SafetyStop('completed Word S step is missing its immutable JIT anchor')
        anchors.append(anchor)
    return anchors


def checked_jit_cache(epoch):
    cache = epoch / 'cupy_cache'
    if cache.is_symlink():
        raise L.SafetyStop('CuPy cache namespace must not be a symlink')
    cache.mkdir(exist_ok=True)
    head_path = epoch / 'jit_head.json'
    current = jit_files(cache)
    anchors = completed_jit_anchors(epoch)
    if not head_path.exists():
        if anchors or current or list(epoch.glob('*/jit_manifest.json')):
            raise L.SafetyStop('untracked CuPy cache artifacts or manifest history')
        return None, current
    head = json.loads(head_path.read_text())
    if not anchors or head['sequence'] != len(anchors) or head != anchors[-1]:
        raise L.SafetyStop('CuPy JIT head does not match completed S step anchors')
    references = {}
    reference, expected_sequence, latest, newer = head, head['sequence'], None, None
    seen = set()
    while reference is not None:
        path = (epoch / reference['manifest']).resolve()
        if (not path.is_relative_to(epoch) or path.name != 'jit_manifest.json'
                or path in seen or L.sha(path) != reference['sha256']):
            raise L.SafetyStop('CuPy JIT manifest chain changed')
        seen.add(path)
        references[expected_sequence] = reference
        record = json.loads(path.read_text())
        if (record['sequence'] != expected_sequence or reference['sequence'] != expected_sequence
                or record['cache'] != 'cupy_cache' or not record['valid']):
            raise L.SafetyStop('invalid CuPy JIT manifest sequence')
        if newer is not None and any(newer.get(name) != value for name, value in record['files'].items()):
            raise L.SafetyStop('CuPy JIT history rewrote an existing artifact')
        if latest is None:
            latest = record
        newer = record['files']
        reference = record['previous']
        expected_sequence -= 1
    if expected_sequence != 0 or len(seen) != len(list(epoch.glob('*/jit_manifest.json'))):
        raise L.SafetyStop('CuPy JIT history is incomplete or was rewound')
    if any(references.get(i + 1) != anchor for i, anchor in enumerate(anchors)):
        raise L.SafetyStop('CuPy JIT chain does not match completed S step anchors')
    if current != latest['files']:
        raise L.SafetyStop('previously frozen CuPy JIT artifacts changed, disappeared, or appeared outside an S run')
    return head, current


@contextmanager
def jit_environment(cache):
    configured = {'CUPY_CACHE_DIR': str(cache), 'CUPY_CACHE_IN_MEMORY': '0',
                  'CUPY_CACHE_SAVE_CUDA_SOURCE': '1'}
    old = {name: os.environ.get(name) for name in configured}
    os.environ.update(configured)
    try:
        yield
    finally:
        for name, value in old.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def execute_scan(root, epoch, state, label, cmd):
    previous, before = checked_jit_cache(epoch)
    try:
        with jit_environment(epoch / 'cupy_cache'):
            prefix, receipt = C.execute(root, epoch, state['index'], state['uuid'], label, cmd)
    except BaseException as error:
        # Failed-process artifacts are diagnostic only; never advance the valid chain.
        run = epoch / label
        if run.is_dir() and not (run / 'jit_manifest.json').exists():
            L.save(run / 'jit_manifest.json', {'valid': False, 'cache': 'cupy_cache',
                   'previous': previous, 'files': jit_files(epoch / 'cupy_cache'),
                   'reason': repr(error)})
        raise
    after = jit_files(epoch / 'cupy_cache')
    unchanged = all(after.get(name) == value for name, value in before.items())
    has_binary = any(Path(name).suffix == '.cubin' for name in after)
    valid = bool(receipt.get('valid') and unchanged and has_binary)
    record = {'valid': valid, 'cache': 'cupy_cache',
              'sequence': 1 if previous is None else previous['sequence'] + 1,
              'previous': previous, 'files': after, 'new_files': sorted(set(after) - set(before)),
              'binary_container': 'CuPy .cubin disk-cache container; whole-file SHA256',
              'scope': 'cumulative phase cache, including RawKernel and CuPy internal compiled kernels',
              'environment': {'CUPY_CACHE_IN_MEMORY': '0', 'CUPY_CACHE_SAVE_CUDA_SOURCE': '1'},
              'previous_artifacts_unchanged': unchanged, 'compiled_binary_present': has_binary}
    manifest = prefix.parent / 'jit_manifest.json'
    L.save(manifest, record)
    if not valid:
        raise L.SafetyStop('CuPy compiled-binary provenance failed: missing binary, changed cache, or invalid process')
    head = {'manifest': str(manifest.relative_to(epoch)), 'sha256': L.sha(manifest),
            'sequence': record['sequence']}
    temporary = epoch / 'jit_head.next.json'
    L.save(temporary, head)
    os.replace(temporary, epoch / 'jit_head.json')
    return prefix, {**receipt, 'jit_manifest': head}


def run_task(root, epoch, state, proof, task):
    kind, label = task['kind'], task['label']
    if kind in ('dependency', 'oracle'):
        run = epoch / label
        run.mkdir()
        env = {**os.environ, 'CUDA_VISIBLE_DEVICES': '', 'OMP_NUM_THREADS': '16',
               'OPENBLAS_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1', 'NUMEXPR_NUM_THREADS': '1'}
        cmd = ([os.environ['FAISS_PYTHON'], '-c', 'import cupy; print(cupy.__version__, flush=True)']
               if kind == 'dependency' else [root / proof['paths']['oracle_binary'],
                   root / task['case']['base'], root / task['case']['query'], 2000,
                   root / task['case']['oracle']])
        with (run / 'stdout.log').open('x') as out, (run / 'stderr.log').open('x') as err:
            L.guarded_run(run / 'guard.jsonl', cmd, timeout_s=600, check=False,
                          cwd=root, env=env, stdout=out, stderr=err)
        result = {'state': 'complete'}
        if kind == 'oracle':
            path = root / task['case']['oracle']
            if path.stat().st_size != 120000:
                raise L.SafetyStop('incomplete bounded Word oracle')
            record = {'path': task['case']['oracle'], 'bytes': 120000, 'sha256': L.sha(path)}
            L.save(epoch / 'word_bounded_oracle_manifest.json', record)
            result['frozen_oracle'] = record
        return result
    c = task['case']
    if c['state'] != 'feasible':
        quality = {'correct': False, 'state': c['state'], 'not_run': True}
        if kind == 'gate':
            L.save(quality_path(epoch, task), quality)
        return {'state': c['state'], 'quality': quality}
    if kind == 'work':
        record = {'P_count_scope_record': 'count_' + task['key'] + '.scope.json',
                  'P_count_state': 'separate instrumented process, gated on P correctness',
                  'S_logical_padded_character_bytes_per_batch': task['Q'] * c['N'] * 109,
                  'S_logical_index_length_bytes_per_batch': task['Q'] * c['N'] * 4,
                  'scope': 'logical padded indexed input per batch; not measured DRAM traffic'}
        L.save(epoch / (label + '.json'), record)
        return {'state': 'S logical bytes recorded; P uses separate count process', 'work': record}
    if kind in ('count', 'time') and not json.loads(quality_path(epoch, task).read_text())['correct']:
        return {'state': 'not-run: correctness-failed gate'}
    verify_oracle(root, epoch, c)
    cmd = command(root, proof, task)
    if task['arm'] == 'S':
        prefix, rec = execute_scan(root, epoch, state, label, cmd)
    else:
        prefix, rec = C.execute(root, epoch, state['index'], state['uuid'], label, cmd)
    rows = 1024 if task['Q'] == 1024 else 1000
    if Path(str(prefix) + '.ids').stat().st_size != rows * 8 * 4:
        raise L.SafetyStop('wrong Word complete-output row count: ' + label)
    verify_oracle(root, epoch, c)
    spec = importlib.util.spec_from_file_location('word_frozen_audit', root / proof['paths']['audit_script'])
    auditor = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(auditor)
    quality = auditor.audit(root, c, prefix, k=8, expected_rows=rows)
    if kind == 'sanitize':
        logs = prefix.with_name('stdout.log').read_text() + prefix.with_name('stderr.log').read_text()
        if 'ERROR SUMMARY: 0 errors' not in logs or not quality['correct']:
            raise L.SafetyStop('Word sanitizer/correctness failed: ' + label)
    elif kind in ('count', 'time') and not quality['correct']:
        raise L.SafetyStop('Word post-timing correctness failed: ' + label)
    if kind == 'gate':
        L.save(quality_path(epoch, task), quality)
    elif kind == 'count':
        raw = json.loads(Path(str(prefix) + '.json').read_text())
        names = ('distance_calls', 'candidate_leaves', 'leaf_distances')
        if raw.get('instrumented') != 1 or any(type(raw.get(n)) is not int or raw[n] <= 0 for n in names):
            raise L.SafetyStop('missing/uninstrumented Word work counts: ' + label)
        L.save(epoch / (label + '.scope.json'),
               {'raw_counts': {n: raw[n] for n in names},
                'queries_in_correctness_pass': rows, 'unique_held_out_queries': 1000,
                'Q': task['Q'], 'scope': 'one entire correctness pass; no timed observations',
                'ragged_batch_included': task['Q'] == 32,
                'repeated_query_rows': 24 if task['Q'] == 1024 else 0})
    result = {'state': 'complete', 'quality': quality}
    if task['arm'] == 'S':
        result['jit_manifest'] = rec['jit_manifest']
    return result


def initialize(root, epoch):
    frozen = identity(root)
    proof, cases = verified_inputs(root)
    prior = json.loads((vector_epoch(root) / 'admission.json').read_text())
    index = prior['index']
    lock = C.acquire_same(index, prior['uuid'])
    try:
        state = L.snapshot(index)
        if not state['idle'] or state['uuid'] != prior['uuid']:
            raise L.Contaminated('Word requires the prior vector UUID to remain idle')
        L.save(epoch / 'admission.json', state)
        L.save(epoch / 'PLAN.json', plan(cases, root, epoch))
        frozen['plan_sha256'] = L.sha(epoch / 'PLAN.json')
        L.save(epoch / 'word_phase_identity.json', frozen)
        (root / 'logs/active_word_epoch.txt').write_text(str(epoch) + '\n')
    finally:
        lock.close()


def step(root, epoch):
    frozen = json.loads((epoch / 'word_phase_identity.json').read_text())
    plan_sha = frozen.pop('plan_sha256')
    if L.sha(epoch / 'PLAN.json') != plan_sha or identity(root) != frozen:
        raise L.SafetyStop('Word phase/plan/source/data identity changed')
    proof, cases = verified_inputs(root)
    checked_jit_cache(epoch)
    tasks = json.loads((epoch / 'PLAN.json').read_text())
    completed = len(list(epoch.glob('STEP_*_DONE.json')))
    if completed > len(tasks) or any(not (epoch / f'STEP_{i:04d}_DONE.json').exists() for i in range(completed)):
        raise L.SafetyStop('non-contiguous Word step checkpoint')
    if completed == len(tasks):
        L.save(epoch / 'COMPLETE.json', {'phase': 'E4 Word', 'plan_processed': True,
                 'gpu_uuid': json.loads((epoch / 'admission.json').read_text())['uuid'],
                 'rounds': 6, 'steps': completed,
                 'P_counters': 'separate processes for correctness-passed feasible loads; raw pass denominators in count scope records',
                 'infeasible_Ns': [c['N'] for c in cases if c['state'].startswith('infeasible:')],
                 'uncompleted_scope': ['G', 'E3', 'optional E4 Protein/ChEMBL']})
        return {'state': 'plan-processed', 'remaining_steps': 0}
    task = tasks[completed]
    state = json.loads((epoch / 'admission.json').read_text())
    lock = C.acquire_same(state['index'], state['uuid']) if requires_gpu(epoch, task) else None
    try:
        result = run_task(root, epoch, state, proof, task)
        L.save(epoch / f'STEP_{completed:04d}_DONE.json', {'task': task, 'result': result})
        return {'step': completed, 'remaining_steps': len(tasks) - completed - 1, **result}
    finally:
        if lock:
            lock.close()


def main(root, mode, epoch_arg=None):
    root = Path(root).resolve()
    if mode not in ('init', 'step'):
        raise ValueError('Word requires explicit init or one bounded step; no all/retry mode')
    with (root / 'campaign.lock').open('a') as task_lock:
        fcntl.flock(task_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        check_stops(root)
        vector_epoch(root)
        if mode == 'init':
            active = root / 'logs/active_word_epoch.txt'
            if active.exists():
                raise L.SafetyStop('Word phase already initialized; never create a replacement epoch')
            epoch = root / 'runs' / f'word_epoch_{time.time_ns()}'
            epoch.mkdir(parents=True)
        else:
            if epoch_arg is None:
                raise ValueError('step requires an explicit Word epoch path')
            epoch = task_file(root, Path(epoch_arg))
            if not epoch.is_relative_to(root / 'runs') or not (epoch / 'word_phase_identity.json').is_file():
                raise ValueError('not an initialized Word phase')
            if (epoch / 'FAILED.json').exists():
                raise L.SafetyStop('failed Word phase cannot be resumed')
            if (epoch / 'COMPLETE.json').exists():
                print(json.dumps({'state': 'already-complete'}), flush=True)
                return
        L.configure(epoch / 'telemetry')
        if mode == 'init':
            previous = vector_epoch(root) / 'telemetry/.last_snapshot_monotonic'
            if previous.exists():
                (epoch / 'telemetry/.last_snapshot_monotonic').write_text(previous.read_text())
        try:
            L.preflight()
            result = initialize(root, epoch) if mode == 'init' else step(root, epoch)
        except BaseException as error:
            evidence = {'reason': repr(error), 'epoch': str(epoch), 'phase': 'E4 Word',
                        'all_timing_ineligible': True, 'automatic_retry': False}
            L.save(epoch / 'FAILED.json', evidence)
            L.save(root / 'STOP_CAMPAIGN.json', evidence)
            raise
        print(json.dumps({'epoch': str(epoch), 'mode': mode, 'result': result}), flush=True)


if __name__ == '__main__':
    main(*sys.argv[1:])
