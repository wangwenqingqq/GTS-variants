"""Post-run closure helper rejection fixtures; never mutate actual evidence."""
if not __debug__:
    raise SystemExit('Mandatory checks require ordinary Python.')
import argparse
import json
from pathlib import Path
import bind
import cost


def main(out):
    out.mkdir()
    rejected = 0

    def reject(call):
        nonlocal rejected
        try:
            call()
        except (AssertionError, KeyError, FileNotFoundError):
            rejected += 1
        else:
            raise AssertionError('Tampered fixture admitted')

    frozen = dict(passed=True, files={'case.bin': dict(sha256='original', bytes=8)}, GPU_starts=0)
    bind.input_identity(frozen, frozen)
    reject(lambda: bind.input_identity(dict(passed=True, files={'case.bin': dict(sha256='changed', bytes=8)}, GPU_starts=0), frozen))
    reject(lambda: bind.input_identity({**frozen, 'files': {}}, frozen))
    command = dict(command=['taskset', '-c', '999999', 'binary', 'case.bin', '0', 'out.csv'],
                   binary_sha256='binary', input_sha256='input', contract_sha256='contract')
    args = (command['command'], 'binary', 'input', 'contract')
    bind.command_identity(command, *args)
    for key in ('command', 'binary_sha256', 'input_sha256', 'contract_sha256'):
        reject(lambda key=key: bind.command_identity({**command, key: [] if key == 'command' else 'changed'}, *args))
    output = out/'complete.csv'
    output.write_text('A complete output can remain after a failed process.\n')
    record = dict(label='fixture', returncode=0, input_sha256='input', binary_sha256='binary',
                  output_sha256=bind.sha(output), wall_seconds=1, GPU_starts=0)
    bind.completed(record, 'fixture', 'input', 'binary', output)
    for key, bad in (('returncode', 1), ('label', 'wrong'), ('GPU_starts', 1),
                     ('output_sha256', 'changed')):
        reject(lambda key=key, bad=bad: bind.completed({**record, key: bad}, 'fixture', 'input', 'binary', output))
    raw = out/'raw'
    raw.mkdir()
    names = {'BUNDLE.json', 'BUILD.json', 'RUNS.json', 'CPU_STARTS.jsonl', 'CPU_COST_SUMMARY.json',
             'build/cpu_cost', 'build/compile.stdout', 'build/compile.stderr'}
    for book in cost.BOOKS:
        for r in range(6):
            label = f'{book}_r{r}'
            names.add('runs/'+label+'.csv')
            names.update('receipts/'+label+suffix for suffix in
                         ('.command.json', '.result.json', '.stdout', '.stderr'))
    for name in names:
        f = raw/name
        f.parent.mkdir(exist_ok=True)
        f.write_bytes(b'fixture')
    (raw/'BUNDLE.json').write_text('{"files":{}}')
    assert bind.raw_inventory(raw) == names
    for name in ('extra.csv', 'runs/CLOSED_IDENTITY.json'):
        extra = raw/name
        extra.write_text('unregistered')
        reject(lambda: bind.raw_inventory(raw))
        extra.unlink()
    missing = raw/'runs'/next(n.split('/')[1] for n in names if n.startswith('runs/'))
    original = missing.read_bytes()
    missing.unlink()
    reject(lambda: bind.raw_inventory(raw))
    missing.symlink_to(output)
    reject(lambda: bind.raw_inventory(raw))
    missing.unlink()
    missing.write_bytes(original)
    current = {'bind.py': 'public scrubbed checker', 'cost.py': 'unchanged'}
    previous = {**current, 'bind.py': 'archived checker'}
    proof = {'references': previous}
    receipt = {'proof_sha256': 'sealed proof', 'checker_reference_sources': previous}
    bind.checker_identity({'references': current}, current, receipt, 'fresh proof')
    bind.checker_identity(proof, current, receipt, 'sealed proof')
    reject(lambda: bind.checker_identity(proof, current, receipt, 'changed proof'))
    reject(lambda: bind.checker_identity(proof, current, {**receipt, 'checker_reference_sources': current}, 'sealed proof'))
    reject(lambda: bind.checker_identity(proof, {**current, 'cost.py': 'changed'}, receipt, 'sealed proof'))
    assert rejected == 17
    print(json.dumps(dict(passed=True, tamper_rejections=rejected,
                         self_reported_input_replacement_rejected=True,
                         failed_process_with_complete_CSV_rejected=True,
                         command_source_binary_and_contract_mismatch_rejected=True,
                         extra_missing_nested_proof_and_symlink_rejected=True,
                         archived_checker_bridge_tampering_rejected=True, fixture_only=True, GPU_starts=0), sort_keys=True))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    main(a.out)
