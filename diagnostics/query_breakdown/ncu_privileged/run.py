#!/usr/bin/env python3
"""Explicitly authorized, locked NCU diagnostic; never changes driver settings."""
import argparse
import fcntl
import importlib.util
import json
import os
import hashlib
import re
from pathlib import Path
import subprocess
import time

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('base', HERE.parents[1] / 'original_tree_profile/run.py')
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
SECTIONS = ['SpeedOfLight', 'ComputeWorkloadAnalysis', 'MemoryWorkloadAnalysis_Tables',
            'LaunchStats', 'Occupancy', 'SchedulerStats', 'WarpStateStats', 'SourceCounters', 'InstructionStats']

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('parent', type=Path); p.add_argument('output', type=Path)
    p.add_argument('--gpu', required=True); p.add_argument('--ncu', type=Path, required=True)
    a = p.parse_args(); parent = a.parent.resolve(); out = a.output.resolve()
    assert a.ncu.is_absolute() and a.ncu.is_file()
    ncu_core = a.ncu.resolve().parent / 'target/linux-desktop-glibc_2_11_3-x64/ncu'
    assert ncu_core.is_file(), 'Pass the versioned NCU installation launcher, not the CUDA toolkit dispatcher'
    e = json.loads((HERE.parent / 'EVIDENCE.json').read_text()); binary = parent / 'bin/bench5'
    digest = base.sha(binary); assert digest == e['binary_sha256']['bench5']
    fixture = parent / 'fixtures/n65536'
    m = json.loads((fixture / 'manifest.json').read_text()); assert m == e['fixtures']['n65536']
    for f, h in m['file_sha256'].items(): assert base.sha(fixture / f) == h
    for q, r in [(128, 500), (32, 300)]:
        for tool in ['check', 'memcheck', 'synccheck']:
            rec = e['runs'][f'{tool}_n65536_q{q}_r{r}_D']
            assert rec['exit_code'] == 0 and rec['correct'] and rec['post_clear'] and rec['binary_sha256'] == digest
    out.mkdir(exist_ok=False)
    lock = open('/tmp/gtspp_gpu0.lock', 'a'); fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    initial = base.snapshot(a.gpu); assert initial['gpu'].split(',')[0].strip() == '0' and not initial['apps'].strip()
    params = Path('/proc/driver/nvidia/params').read_text()
    assert 'RmProfilingAdminOnly: 1' in params
    (out / 'contract.sha256').write_text(base.sha(HERE / 'CONTRACT.md') + '\n')
    provenance = {'ncu_version': subprocess.check_output([str(a.ncu), '--version'], text=True),
                  'ncu_executable_sha256': base.sha(ncu_core), 'bench5_sha256': digest,
                  'collection_runner_sha256': base.sha(Path(__file__)), 'contract_sha256': base.sha(HERE / 'CONTRACT.md'),
                  'driver_restriction': next(l for l in params.splitlines() if 'RmProfilingAdminOnly' in l), 'static_functions': {}}
    for part in (parent / 'logs/bench5.sass').read_text().split('Function : ')[1:]:
        name = part.splitlines()[0].strip()
        if name not in e['static_functions'] and name != '__internal_accurate_pow': continue
        ins = [re.sub(r'/\*.*?\*/', '', l).strip() for l in part.splitlines() if re.match(r'\s*/\*[0-9a-f]+\*/', l)]
        provenance['static_functions'][name] = {'normalized_instruction_sha256': hashlib.sha256(('\n'.join(ins) + '\n').encode()).hexdigest(), 'instruction_count': len(ins)}
    (out / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
    for label, q, radius, kernel, count in [
        ('check_q128_r500', 128, 500, None, 0), ('check_q32_r300', 32, 300, None, 0),
        ('leaf_q128_r500_0', 128, 500, 'dataProcessRnn', 1), ('leaf_q128_r500_1', 128, 500, 'dataProcessRnn', 1),
        ('leaf_q32_r300', 32, 300, 'dataProcessRnn', 1), ('aggregate_q128_r500', 128, 500, 'mergeResRnn', 1),
        ('node_q128_r500', 128, 500, 'nodeProcessRnn', 4)]:
        run = out / label; run.mkdir(); (run / 'home').mkdir()
        before = base.snapshot(a.gpu); (run / 'before.json').write_text(json.dumps(before, indent=2) + '\n')
        assert not before['apps'].strip(), 'GPU0 occupied; stop without touching foreign work'
        app = [str(binary), str(fixture / 'data.txt'), str(fixture / f'q{q}.txt'), str(radius), 'D', 'profile' if kernel else 'check']
        cmd = ['/usr/bin/timeout', '--signal=TERM', '--kill-after=10s', '600s'] + app
        if kernel:
            cmd = ['sudo', '-n', '/usr/bin/timeout', '--signal=TERM', '--kill-after=10s', '600s', '/usr/bin/env',
                   'CUDA_VISIBLE_DEVICES=' + a.gpu, 'HOME=' + str(run / 'home'), str(a.ncu),
                   '--profile-from-start', 'off', '--clock-control', 'none', '--cache-control', 'none',
                   '--replay-mode', 'kernel', '--kernel-name-base', 'function', '--kernel-name', kernel,
                   '--launch-count', str(count), '--export', str(run / 'trace')]
            for section in SECTIONS: cmd += ['--section', section]
            cmd += app
        start = time.time()
        with (run / 'stdout.log').open('w') as stdout, (run / 'stderr.log').open('w') as stderr:
            rc = subprocess.run(cmd, cwd=run, env={**os.environ, 'CUDA_VISIBLE_DEVICES': a.gpu}, stdout=stdout, stderr=stderr).returncode
        text = (run / 'stdout.log').read_text() + (run / 'stderr.log').read_text()
        after = base.snapshot(a.gpu); (run / 'after.json').write_text(json.dumps(after, indent=2) + '\n')
        rec = {'label': label, 'command': cmd, 'start': start, 'wall_s': time.time() - start, 'exit_code': rc,
               'correct': 'correct,full_integer_oracle' in text and 'pass' in text.splitlines(),
               'post_clear': not after['apps'].strip(), 'binary_sha256': digest,
               'contract_sha256': base.sha(HERE / 'CONTRACT.md'), 'profiling_restriction_unchanged': Path('/proc/driver/nvidia/params').read_text() == params}
        (run / 'receipt.json').write_text(json.dumps(rec, indent=2) + '\n')
        print(label, {k: rec[k] for k in ['exit_code', 'correct', 'post_clear', 'wall_s']}, flush=True)
        assert rc == 0 and rec['correct'] and rec['post_clear'] and rec['profiling_restriction_unchanged'], 'Failed attempt retained; stop'
        if kernel:
            for page in ['raw', 'details', 'source']:
                export = [str(a.ncu), '--import', str(run / 'trace.ncu-rep'), '--page', page]
                if page == 'raw': export += ['--csv', '--print-units', 'base']
                if page == 'details': export += ['--print-details', 'all']
                if page == 'source': export += ['--print-source', 'sass', '--csv']
                with (run / (page + ('.csv' if page != 'details' else '.txt'))).open('w') as f:
                    subprocess.run(export, stdout=f, stderr=subprocess.STDOUT, check=True)
    final = base.snapshot(a.gpu); provenance.update(gpu_after=final['gpu'], apps_after=final['apps'])
    (out / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
    print('PASS: all diagnostic processes and final permission invariant', flush=True)

if __name__ == '__main__': main()
