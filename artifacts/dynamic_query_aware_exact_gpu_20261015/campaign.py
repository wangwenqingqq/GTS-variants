"""Serialize the frozen exploratory matrix; retain first failure without replacement."""
if not __debug__:
    raise SystemExit('Optimized Python disables mandatory checks; run without -O/PYTHONOPTIMIZE.')
import argparse
import fcntl
import json
import os
import subprocess
import sys
import traceback
from pathlib import Path
from common import HERE, REPO, MODES, sha, load, save, expected_jobs
from prepare import input_prefix
from quality import check

STAGES = ('qualification', 'primary', 'query_ncu', 'maintenance_ncu')


def stamp(path):
    s = Path(path).stat(); return (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)


def prepared(w):
    reg, ready = load(w/'REGISTERED.json'), load(w/'READY.json')
    assert ready['passed'] and sha(w/'REGISTERED.json') == ready['registration_sha256']
    assert sha(HERE/'CONTRACT.json') == reg['contract_sha256']
    assert sha(w/'CPU_READY.json') == reg['cpu_ready_sha256']
    for n, h in reg['sources'].items(): assert sha(REPO/n) == h
    for n, h in reg['generated_sources'].items(): assert sha(w/n) == h
    for m, h in ready['binaries'].items(): assert sha(w/'build'/m/'service') == h
    assert sha(w/'build/replay.so') == ready['replay_binary_sha256']
    return reg, ready


def command(job, w, reg, prefix):
    cmd = [str(w/'build'/job['mode']/'service')]
    if job.get('kind') == 'selftest': cmd += ['--selftest']
    else:
        cmd += [reg['data'], str(input_prefix(w, job['N'], job['workload'])), str(w/'inputs'/('bounded_qids.txt' if job['N'] == 4096 else 'full_qids.txt')),
                str(load(HERE/'CONTRACT.json')['radius']), str(prefix), str(job['workload']), str(job['diagnostic']), str(job['N'])]
    if job.get('tool') in ('memcheck', 'racecheck', 'synccheck'):
        cmd = ['/usr/local/cuda-13.1/bin/compute-sanitizer', '--tool', job['tool'], '--error-exitcode', '97', *cmd]
    if job.get('tool') == 'ncu':
        report = prefix.parent.parent/'reports'/job['label']
        cmd = ['/usr/bin/sudo', '-n', 'env', 'CUDA_VISIBLE_DEVICES='+reg['gpu'], 'LD_LIBRARY_PATH='+reg['environment']['LD_LIBRARY_PATH'],
               'PDX_MEANS='+reg['environment']['PDX_MEANS'], 'OMP_NUM_THREADS=8', 'OPENBLAS_NUM_THREADS=1', 'MKL_NUM_THREADS=1',
               '/usr/local/bin/ncu', '--profile-from-start', 'off', '--kernel-name-base', 'demangled', '--cache-control', 'none', '--clock-control', 'none',
               '--section', 'LaunchStats', '--metrics', ','.join(load(HERE/'CONTRACT.json')['NCU_metrics']), '-o', str(report), *cmd]
    return cmd


def main():
    p = argparse.ArgumentParser(); p.add_argument('--work', type=Path, required=True); p.add_argument('--stage', choices=('static', *STAGES), required=True)
    a = p.parse_args(); w = a.work.resolve(); c = load(HERE/'CONTRACT.json'); reg, ready = prepared(w)
    if a.stage == 'static':
        from static import run
        run(w); return
    assert load(w/'STATIC.json')['passed']
    for stage in STAGES[:STAGES.index(a.stage)]: assert load(w/stage/'RESULTS.json')['complete']
    if a.stage == 'primary':
        assert not (w/'ANALYSIS_FREEZE.json').exists()
        save(w/'ANALYSIS_FREEZE.json', dict(before_primary=True, contract_sha256=sha(HERE/'CONTRACT.json'), analyzer_sha256=sha(HERE/'analyze.py'), jobs_sha256=__import__('hashlib').sha256(json.dumps(expected_jobs('primary'), sort_keys=True).encode()).hexdigest()))
    stage = w/a.stage; stage.mkdir(exist_ok=False)
    for n in ('guards', 'outputs', 'reports'): (stage/n).mkdir()
    jobs = expected_jobs(a.stage); rows = [{**j, 'status': 'not_executed'} for j in jobs]
    save(stage/'REGISTERED.json', dict(before_starts=True, jobs=jobs, contract_sha256=sha(HERE/'CONTRACT.json'), executor_sha256=sha(Path(__file__))))
    inputs = {Path(reg['data']): c['data_sha256']}
    for name, r in load(w/'CPU_READY.json')['files'].items(): inputs[w/name] = r['sha256']
    for name, h in reg['reference_hashes'].items(): inputs[Path(reg['reference'])/name] = h
    stamps = {}
    for path, h in inputs.items(): assert sha(path) == h; stamps[path] = stamp(path)
    env = {**os.environ, **reg['environment'], 'CUDA_VISIBLE_DEVICES': reg['gpu'], 'PYTHONDONTWRITEBYTECODE': '1'}
    with (w/'campaign.lock').open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        for job, row in zip(jobs, rows):
            try:
                assert all(stamp(path) == value for path, value in stamps.items()), 'registered input changed inside stage'
                assert all(sha(REPO/n) == h for n, h in reg['sources'].items())
                assert sha(w/'build'/job['mode']/'service') == ready['binaries'][job['mode']]
                prefix = stage/'outputs'/job['label']; cmd = command(job, w, reg, prefix)
                save(stage/(job['label']+'.command.json'), dict(command=cmd))
                ledger = w/'STARTS.jsonl'; count = len(ledger.read_text().splitlines()) if ledger.exists() else 0
                assert count < c['max_GPU_starts']
                with ledger.open('a') as f: f.write(json.dumps(dict(start=count+1, stage=a.stage, label=job['label'], command_sha256=sha(stage/(job['label']+'.command.json'))))+'\n')
                guard = stage/'guards'/job['label']
                guard_cmd = [sys.executable, str(REPO/'artifacts/external_closure/static_guard.py'), '--gpu', reg['gpu'], '--numa-node', str(reg['numa']), '--output', str(guard), '--', *cmd]
                with (stage/(job['label']+'.outer.log')).open('x') as f: subprocess.run(guard_cmd, env=env, stdout=f, stderr=f, check=True)
                receipt = load(guard/'receipt.json')
                assert receipt['runtime_valid'] and receipt['exit_code'] == 0 and receipt['stop_reason'] is None
                assert receipt['observer'] == 'two-sided-starttime-v1' and receipt['gpu'] == reg['gpu']
                assert load(guard/'command.json') == receipt['command'] == ['numactl', f"--cpunodebind={reg['numa']}", f"--membind={reg['numa']}", *cmd]
                for name in ('before', 'after'): assert not load(guard/(name+'.json'))['apps']
                assert all(not x['foreign'] for x in load(guard/'checks.json'))
                if job.get('kind') == 'selftest':
                    checked = next(json.loads(line) for line in reversed((guard/'stdout.log').read_text().splitlines()) if line.startswith('{'))
                    assert checked['passed'] and checked['iterations'] == 100 and checked['stream_slots'] == 2 and checked['max_batch'] == 512
                    assert checked['query_checks'] == 400 and checked['empty_answers'] > 0 and checked['full_hit_FP64_bit_checks'] > 0
                else: checked = check(prefix, job, w, reg)
                if job.get('tool') in ('memcheck', 'racecheck', 'synccheck'):
                    text = (guard/'stdout.log').read_text()+(guard/'stderr.log').read_text()
                    assert 'ERROR SUMMARY: 0 errors' in text or 'RACECHECK SUMMARY: 0 hazards' in text
                    checked['sanitizer_summary_zero'] = True
                if job.get('tool') == 'ncu':
                    report = stage/'reports'/job['label']
                    with Path(str(report)+'.csv').open('x') as f:
                        subprocess.run(['/usr/local/bin/ncu', '--import', str(report)+'.ncu-rep', '--page', 'raw', '--csv', '--print-units', 'base'], env=env, stdout=f, check=True)
                save(stage/(job['label']+'.checked.json'), checked)
                row.update(status='passed', checked_sha256=sha(stage/(job['label']+'.checked.json')), guard_sha256=sha(guard/'receipt.json'),
                    guard_files={p.name: sha(p) for p in guard.iterdir() if p.is_file()},
                    reports={p.name: dict(sha256=sha(p), bytes=p.stat().st_size) for p in (stage/'reports').glob(job['label']+'*') if p.is_file()})
                print('PASSED', a.stage, job['label'], 'start', count+1, flush=True)
            except BaseException:
                row.update(status='failed', error=traceback.format_exc()); save(stage/'RESULTS.json', dict(complete=False, rows=rows, stop='first failure;no automatic retry'))
                raise
        save(stage/'RESULTS.json', dict(complete=True, rows=rows))


if __name__ == '__main__': main()
