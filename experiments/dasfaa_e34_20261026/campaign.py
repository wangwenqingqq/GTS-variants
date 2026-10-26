"""One fail-closed E4 vector epoch; every child process has its own resource guard."""
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import lock_support as L
from audit import audit


def execute(root, epoch, index, gpu, label, cmd):
    run = epoch / label
    run.mkdir()
    prefix = run / 'result'
    cmd = [str(x).replace('{out}', str(prefix)) for x in cmd]
    guard_cmd = L.guarded_command(run / 'guard.jsonl', cmd, timeout=600)
    rec = {'command': cmd, 'guard_command': guard_cmd, 'label': label,
           'gpu_uuid': gpu, 'start': time.time(), 'valid': False}
    known, checks, problem, p = {}, [], None, None
    try:
        before, history = L.stable_idle(index)
        L.save(run / 'before.json', before)
        L.save(run / 'admission_wait.json', history)
        if not before['idle'] or before['uuid'] != gpu:
            raise L.Contaminated('occupied or UUID changed before ' + label)
        L.preflight()
        env = {**os.environ, 'CUDA_VISIBLE_DEVICES': gpu, 'OMP_NUM_THREADS': '1',
               'OPENBLAS_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1',
               'NUMEXPR_NUM_THREADS': '1'}
        with (run / 'stdout.log').open('x') as out, (run / 'stderr.log').open('x') as err:
            p = subprocess.Popen(guard_cmd, cwd=root, env=env,
                                 start_new_session=True, stdout=out, stderr=err)
            rec['pid'] = p.pid
            identity = L.proc_identity(p.pid)
            known[p.pid] = identity[1] if identity else None
            next_check = time.monotonic() + L.POLL_SECONDS
            while p.poll() is None:
                L.remember_target(run, known)
                L.remember_descendants(p.pid, known)
                if time.monotonic() >= next_check:
                    state = L.snapshot(index)
                    L.remember_target(run, known)
                    bad = L.foreign_apps(state, p.pid, known)
                    checks.append({'time_utc': state['time_utc'], 'apps': state['apps'],
                                   'foreign': bad, 'owned': dict(known)})
                    if bad or state['uuid'] != gpu:
                        raise L.Contaminated('foreign process or changed UUID during ' + label)
                    next_check = time.monotonic() + L.POLL_SECONDS
                time.sleep(0.2)
            rec['exit_code'] = p.wait()
        if rec['exit_code'] != 0:
            raise L.SafetyStop(f'{label}: guarded process exited {rec["exit_code"]}; no retry')
        # Never call NVML after a terminal process/guard failure.
        after, settling = L.stable_idle(index, group=p.pid, known=known)
        L.save(run / 'after.json', after)
        L.save(run / 'settling.json', settling)
        if not after['idle'] or after['uuid'] != gpu:
            raise L.Contaminated('not settled or UUID changed after ' + label)
        rec['valid'] = True
    except BaseException as error:
        problem = error
        rec['exception'] = repr(error)
        if p is not None and p.poll() is None:
            L.remember_target(run, known)
            L.terminate_owned(p, known)
            rec['exit_code'] = p.returncode
    finally:
        rec['elapsed_s'] = time.time() - rec['start']
        rec['files'] = {f.name: L.sha(f) for f in run.glob('result*') if f.is_file()}
        L.save(run / 'checks.json', checks)
        L.save(run / 'receipt.json', rec)
        print(label, 'exit', rec.get('exit_code'), 'seconds',
              round(rec['elapsed_s'], 3), flush=True)
    if problem:
        raise problem
    return prefix, rec


def build_dir(root):
    path = Path(os.environ['E34_BUILD_DIR']).resolve()
    if not path.is_relative_to(root / 'builds'):
        raise L.SafetyStop('build must be in the task-owned builds directory')
    if not (path / 'BUILD_MANIFEST.json').is_file():
        raise L.SafetyStop('corrected build manifest is missing')
    return path


def tree_infeasible(root, case):
    if case['N'] > 10_000_000 or case.get('tree_h', 0) >= 8:
        return 'infeasible: workspace chunking (tree_h=8)'
    return None


def command(root, case, q, arm, reps=0, warm=0, count=False):
    if arm == 'P':
        reason = tree_infeasible(root, case)
        if reason:
            raise L.SafetyStop(reason)
        return [build_dir(root) / 'bin' / ('tree_count' if count else 'tree'),
                root / case['base'], root / case['query'], case['N'], q, reps, warm,
                '{out}', build_dir(root) / f'cache_disabled_{case["family"]}_{case["N"]}.index']
    if arm != 'S':
        raise ValueError('planner supports P/S; G requires its separately frozen height adapter')
    return [os.environ['FAISS_PYTHON'], root / 'scan.py', root / case['base'],
            root / case['query'], case['N'], q, reps, warm, '{out}']


def input_report_path(root):
    return root / 'resume_20261026/INPUT_CHECK.json'


def checked_cases(root):
    manifest = json.loads((root / 'DATA_MANIFEST.json').read_text())
    report = json.loads(input_report_path(root).read_text())
    for name, expected in manifest['files'].items():
        if report['files'].get(name) != expected:
            raise L.SafetyStop('input provenance report does not match frozen file: ' + name)
    cases = []
    for original in manifest['cases']:
        row = next((r for r in report['cases']
                    if (r['family'], r['N']) == (original['family'], original['N'])), None)
        if row is None or row.get('prefix_sha256') != original['prefix_sha256']:
            raise L.SafetyStop('input provenance report is incomplete or mismatched')
        if not row.get('oracle_shape_and_distances_valid'):
            raise L.SafetyStop('input report has not structurally validated the oracle')
        case = dict(original)
        case['input_gate'] = ('pass' if row['holdout']['disjoint']
                              else 'not-run: query-isolation-failed')
        case['matching_base_rows'] = row['holdout']['matching_base_rows']
        case['oracle_sha256'] = row['oracle_sha256']
        cases.append(case)
    return cases


def plan(cases, epoch, root):
    tasks = []
    for family in ('tloc', 'deep'):
        c = next(c.copy() for c in cases if c['family'] == family)
        c['N'] = 2000
        c.pop('oracle_sha256', None)
        c['oracle'] = str(epoch.relative_to(root) / f'{family}_bounded.oracle')
        tasks.append({'kind': 'oracle', 'case': c, 'label': f'{family}_bounded_oracle'})
        for arm in 'PS':
            for tool in ('memcheck', 'synccheck'):
                for q in (1, 32, 1024):
                    tasks.append({'kind': 'sanitize', 'case': c, 'arm': arm,
                                  'tool': tool, 'Q': q,
                                  'label': f'sanitize_{family}_{arm}_{tool}_q{q}'})
    for c in cases:
        for q in (1, 32, 1024):
            key = f'{c["family"]}_{c["N"]}_q{q}'
            for arm in 'PS':
                tasks.append({'kind': 'gate', 'case': c, 'arm': arm, 'Q': q,
                              'key': key, 'label': 'gate_' + key + '_' + arm})
            tasks.append({'kind': 'count', 'case': c, 'arm': 'P', 'Q': q,
                          'key': key, 'label': 'count_' + key})
    for r in range(6):
        for c in cases:
            for q in (1, 32, 1024):
                key = f'{c["family"]}_{c["N"]}_q{q}'
                for arm in ('PS' if r % 2 == 0 else 'SP'):
                    tasks.append({'kind': 'time', 'case': c, 'arm': arm, 'Q': q,
                                  'round': r, 'key': key,
                                  'label': f'time_r{r}_{key}_{arm}'})
    return tasks


def identity(root):
    build = build_dir(root)
    return {'build_dir': str(build), 'build_manifest_sha256': L.sha(build / 'BUILD_MANIFEST.json'),
            'binaries': {p.name: L.sha(p) for p in (build / 'bin').iterdir() if p.is_file()},
            'runner_sha256': L.sha(__file__), 'lock_support_sha256': L.sha(L.__file__),
            'data_manifest_sha256': L.sha(root / 'DATA_MANIFEST.json'),
            'audit_sha256': L.sha(root / 'audit.py'), 'scan_sha256': L.sha(root / 'scan.py'),
            'oracle_binary_sha256': L.sha(root / 'bin/oracle'),
            'guard_sha256': L.sha(L.GUARD),
            'input_report_sha256': L.sha(input_report_path(root)),
            'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip()}


def acquire_same(index, gpu):
    handle = open(f'/tmp/gtspp_gpu{index}.lock', 'r')
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        state = L.snapshot(index)
        if not state['idle'] or state['uuid'] != gpu:
            raise L.Contaminated('the same epoch GPU is no longer idle/the same UUID')
        return handle
    except BaseException:
        handle.close()
        raise


def initialize(root, epoch):
    frozen = identity(root)
    cases = checked_cases(root)
    index, state, lock = L.acquire(root)
    try:
        L.save(epoch / 'admission.json', state)
        L.save(epoch / 'PLAN.json', plan(cases, epoch, root))
        frozen['plan_sha256'] = L.sha(epoch / 'PLAN.json')
        L.save(epoch / 'corrected_build_identity.json', frozen)
        (root / 'logs/active_epoch.txt').write_text(str(epoch) + '\n')
    finally:
        lock.close()


def run_task(root, epoch, index, gpu, task):
    kind, c, label = task['kind'], task['case'], task['label']
    if c.get('input_gate') != 'pass':
        scale_reason = tree_infeasible(root, c) if task.get('arm') == 'P' else None
        quality = {'correct': False, 'not_run': True,
                   'state': scale_reason or c.get('input_gate', 'not-run: input isolation proof missing'),
                   'input_gate': c.get('input_gate'),
                   'matching_base_rows': c.get('matching_base_rows')}
        if kind == 'gate':
            L.save(epoch / f'quality_{task["key"]}_{task["arm"]}.json', quality)
        return {'state': quality['state'], 'quality': quality}
    if kind == 'oracle':
        L.guarded_run(epoch / f'{label}.guard.jsonl',
                      [root / 'bin/oracle', root / c['base'], root / c['query'],
                       '2000', root / c['oracle']], check=False,
                      env={**os.environ, 'OMP_NUM_THREADS': '2',
                           'OPENBLAS_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1'},
                      timeout_s=600)
        oracle = root / c['oracle']
        if oracle.stat().st_size != 120000:
            raise L.SafetyStop('bounded oracle is incomplete')
        frozen = {'path': c['oracle'], 'bytes': 120000, 'sha256': L.sha(oracle)}
        L.save(epoch / f'{c["family"]}_bounded_oracle_manifest.json', frozen)
        return {'state': 'generated-bounded-oracle', 'frozen': frozen}
    arm, q = task['arm'], task['Q']
    reason = tree_infeasible(root, c) if arm == 'P' else None
    quality_path = epoch / f'quality_{task.get("key", label)}_{arm}.json'
    if kind in ('count', 'time'):
        quality = json.loads(quality_path.read_text())
        if not quality['correct']:
            return {'state': 'not-run: correctness/infeasibility gate', 'gate': quality}
    oracle = root / c['oracle']
    if not oracle.exists() or oracle.stat().st_size != 120000:
        raise L.SafetyStop(f'oracle missing/incomplete: {oracle}')
    if reason:
        quality = {'correct': False, 'state': reason, 'not_run': True}
    else:
        verify_oracle(root, epoch, c)
        cmd = command(root, c, q, arm, reps=3 if kind == 'time' else 0,
                      warm=1 if kind == 'time' else 0, count=kind == 'count')
        if kind == 'sanitize':
            cmd = ['compute-sanitizer', '--tool', task['tool'], '--error-exitcode', '90', *cmd]
        prefix, rec = execute(root, epoch, index, gpu, label, cmd)
        expected_rows = 1024 if q == 1024 else 1000
        if Path(str(prefix) + '.ids').stat().st_size != expected_rows * 8 * 4:
            raise L.SafetyStop(f'wrong complete-output row count: {label}; expected {expected_rows}')
        verify_oracle(root, epoch, c)
        quality = audit(root, c, prefix)
        if kind == 'sanitize':
            logs = prefix.with_name('stdout.log').read_text() + prefix.with_name('stderr.log').read_text()
            if 'ERROR SUMMARY: 0 errors' not in logs or not quality['correct']:
                raise L.SafetyStop('sanitizer or bounded correctness failed: ' + label)
        elif kind in ('count', 'time') and not quality['correct']:
            raise L.SafetyStop('post-run correctness failed: ' + label)
    if kind == 'gate':
        L.save(quality_path, quality)
    return {'state': 'complete', 'quality': quality}


def verify_oracle(root, epoch, case):
    oracle = root / case['oracle']
    if case['N'] == 2000:
        record = json.loads((epoch / f'{case["family"]}_bounded_oracle_manifest.json').read_text())
        if record['path'] != case['oracle'] or record['bytes'] != 120000:
            raise L.SafetyStop('bounded oracle manifest identity mismatch')
        expected = record['sha256']
    else:
        expected = case['oracle_sha256']
    if oracle.stat().st_size != 120000 or L.sha(oracle) != expected:
        raise L.SafetyStop('frozen oracle changed: ' + str(oracle))


def requires_gpu(root, epoch, task):
    c = task['case']
    if c.get('input_gate') != 'pass' or task['kind'] == 'oracle':
        return False
    if task.get('arm') == 'P' and tree_infeasible(root, c):
        return False
    if task['kind'] in ('count', 'time'):
        gate = epoch / f'quality_{task["key"]}_{task["arm"]}.json'
        return json.loads(gate.read_text())['correct']
    return True


def step(root, epoch):
    frozen = json.loads((epoch / 'corrected_build_identity.json').read_text())
    plan_sha = frozen.pop('plan_sha256')
    if L.sha(epoch / 'PLAN.json') != plan_sha:
        raise L.SafetyStop('frozen plan changed')
    if identity(root) != frozen:
        raise L.SafetyStop('frozen build/runner/input identity changed')
    tasks = json.loads((epoch / 'PLAN.json').read_text())
    completed = len(list(epoch.glob('STEP_*_DONE.json')))
    if completed == len(tasks):
        L.save(epoch / 'COMPLETE.json', {'gpu_uuid': json.loads((epoch / 'admission.json').read_text())['uuid'],
                                        'rounds': 6, 'steps': completed,
                                        'plan_processed': True,
                                        'all_required_workloads_measured': all(json.loads((epoch / f"quality_{t['key']}_{t['arm']}.json").read_text())['correct'] for t in tasks if t['kind'] == 'gate'),
                                        'input_gate_failures': sorted({f"{t['case']['family']}_{t['case']['N']}" for t in tasks if t['case'].get('input_gate') != 'pass'}),
                                        'missing_scope': 'G, Word and E3 remain separately tracked; see input_gate_failures'})
        return {'state': 'complete', 'remaining_steps': 0}
    if completed > len(tasks):
        raise L.SafetyStop('invalid step count')
    for i in range(completed):
        if not (epoch / f'STEP_{i:04d}_DONE.json').exists():
            raise L.SafetyStop('non-contiguous step checkpoint')
    task = tasks[completed]
    state = json.loads((epoch / 'admission.json').read_text())
    lock = None
    if requires_gpu(root, epoch, task):
        lock = acquire_same(state['index'], state['uuid'])
    try:
        result = run_task(root, epoch, state['index'], state['uuid'], task)
        L.save(epoch / f'STEP_{completed:04d}_DONE.json', {'task': task, 'result': result})
        if task['kind'] == 'sanitize' and not any(t['kind'] == 'sanitize' for t in tasks[completed + 1:]):
            L.save(epoch / 'SANITIZER_STATUS.json',
                   {'processed': True, 'input_gate_skipped_families': sorted({t['case']['family'] for t in tasks if t['kind'] == 'sanitize' and t['case'].get('input_gate') != 'pass'})})
        return {'state': result['state'], 'step': completed,
                'remaining_steps': len(tasks) - completed - 1}
    finally:
        if lock:
            lock.close()


def main(root, mode, epoch_arg=None):
    root = Path(root).resolve()
    if mode not in ('init', 'step'):
        raise ValueError('use init once, then bounded step invocations; there is no auto-retry/all mode')
    with (root / 'campaign.lock').open('a') as task_lock:
        fcntl.flock(task_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (root / 'STOP_CAMPAIGN.json').exists():
            raise L.SafetyStop('campaign is latched stopped; no automatic resume/new epoch')
        if mode == 'init':
            active = root / 'logs/active_epoch.txt'
            # Historical epochs are retained. A successful corrected init is never replaced.
            if active.exists():
                old = Path(active.read_text().strip())
                if (old / 'corrected_build_identity.json').exists():
                    raise L.SafetyStop('corrected epoch already exists; use step with its path')
            epoch = root / 'runs' / f'epoch_{time.time_ns()}'
            epoch.mkdir(parents=True)
        else:
            if epoch_arg is None:
                raise ValueError('step requires the explicit epoch path')
            epoch = Path(epoch_arg).resolve()
            if not epoch.is_relative_to(root / 'runs') or not epoch.is_dir():
                raise ValueError('epoch must be an existing task-owned run directory')
            if (epoch / 'FAILED.json').exists():
                raise L.SafetyStop('failed epoch cannot be resumed')
            if (epoch / 'COMPLETE.json').exists():
                print(json.dumps({'state': 'already-complete'}), flush=True)
                return
        L.configure(epoch / 'telemetry')
        try:
            L.preflight()
            result = initialize(root, epoch) if mode == 'init' else step(root, epoch)
        except BaseException as error:
            evidence = {'reason': repr(error), 'epoch': epoch.name,
                        'all_timing_ineligible': True, 'automatic_retry': False}
            L.save(epoch / 'FAILED.json', evidence)
            L.save(root / 'STOP_CAMPAIGN.json', evidence)
            raise
        print(json.dumps({'epoch': str(epoch), 'mode': mode, 'result': result}), flush=True)


if __name__ == '__main__':
    main(*sys.argv[1:])
