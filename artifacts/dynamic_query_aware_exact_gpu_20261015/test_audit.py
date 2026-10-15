"""CPU-only adversarial regression for the postmeasurement directory/command gate."""
if not __debug__:
    raise SystemExit('Optimized Python disables mandatory checks; run without -O/PYTHONOPTIMIZE.')
import argparse
import json
from pathlib import Path
from audit_stage import stage_census, output_files, report_files, GUARD_FILES
from campaign import command
from common import save


def rejects(fn):
    try: fn()
    except AssertionError: return
    raise AssertionError('negative fixture was accepted')


def main():
    p = argparse.ArgumentParser(); p.add_argument('--out', type=Path, required=True); a = p.parse_args()
    w = a.out.resolve(); w.mkdir(parents=True, exist_ok=False)
    stage = 'qualification'; root = w/stage; root.mkdir()
    for n in ('guards', 'outputs', 'reports'): (root/n).mkdir()
    jobs = [dict(label='S0_selftest', mode='S0', kind='selftest'),
            dict(label='S2_INC_W2', mode='S2_INC', workload=2, N=1000000, diagnostic=1, tool='ncu')]
    reg = dict(numa=0, gpu='fixture', data=str(w/'data.f32bin'),
               environment={'LD_LIBRARY_PATH': str(w/'lib'), 'PDX_MEANS': str(w/'mean.f32')})
    rows = []
    for n in ('REGISTERED.json', 'RESULTS.json'): save(root/n, {})
    for job in jobs:
        label = job['label']; g = root/'guards'/label; g.mkdir()
        wanted = command(job, w, reg, root/'outputs'/label)
        guarded = ['numactl', '--cpunodebind=0', '--membind=0', *wanted]
        for n in GUARD_FILES:
            save(g/n, guarded if n == 'command.json' else dict(command=guarded) if n == 'receipt.json' else {})
        save(root/(label+'.command.json'), dict(command=wanted))
        save(root/(label+'.checked.json'), dict(raw_outputs={n: {} for n in output_files(job)}))
        (root/(label+'.outer.log')).touch()
        for n in output_files(job): (root/'outputs'/n).touch()
        for n in report_files(job): (root/'reports'/n).touch()
        rows.append(dict(guard_files=dict.fromkeys(GUARD_FILES, ''), reports=dict.fromkeys(report_files(job), {})))
    run = lambda: stage_census(w, stage, jobs, rows, reg)
    assert run()['passed']
    label = jobs[0]['label']; c = root/(label+'.command.json'); g = root/'guards'/label
    original = c.read_text(); guard_original = (g/'command.json').read_text(); receipt_original = (g/'receipt.json').read_text()
    bad = command(jobs[0], w, reg, root/'outputs'/label)+['--unexpected']
    c.write_text(json.dumps(dict(command=bad)))
    guarded = ['numactl', '--cpunodebind=0', '--membind=0', *bad]
    (g/'command.json').write_text(json.dumps(guarded)); (g/'receipt.json').write_text(json.dumps(dict(command=guarded)))
    rejects(run)
    c.write_text(original); (g/'command.json').write_text(guard_original); (g/'receipt.json').write_text(receipt_original)
    for directory, name in ((root/'guards', 'unregistered'), (root, 'extra.checked.json'),
                            (root/'outputs', 'extra.ids.i32'), (root/'reports', 'extra.ncu-rep'), (g, 'extra.log')):
        extra = directory/name
        if directory.name == 'guards': extra.mkdir()
        else: extra.touch()
        rejects(run)
        if extra.is_dir(): extra.rmdir()
        else: extra.unlink()
    target = g/'stdout.log'; held = target.read_bytes(); target.unlink(); target.symlink_to(g/'stderr.log')
    rejects(run); target.unlink(); target.write_bytes(held)
    assert run()['passed']
    save(w/'RECEIPT.json', dict(passed=True, consistent_wrong_command_rejected=True,
        extra_guard_checked_output_report_and_log_rejected=True, symlink_rejected=True, GPU_starts=0))
    print('PASS:source-derived command,exact census and adversarial negative fixtures;0 GPU starts')


if __name__ == '__main__': main()
