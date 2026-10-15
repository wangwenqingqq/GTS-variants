"""Postmeasurement census and source-derived command check; never runs a command."""
if not __debug__:
    raise SystemExit('Optimized Python disables mandatory checks; run without -O/PYTHONOPTIMIZE.')
from pathlib import Path
from common import load, sha
from campaign import command

GUARD_FILES = {'command.json', 'before.json', 'after.json', 'checks.json',
               'receipt.json', 'stdout.log', 'stderr.log', 'gpu.csv'}
OUTPUT_SUFFIXES = {'queries.csv', 'ops.csv', 'ids.i32', 'dist.f32', 'squared.f64',
                   'authority.f64', 'physical.i32', 'reverse.i32', 'mutations.i32',
                   'final.json', 'stages.csv', 'output.csv', 'meta.json'}


def exact_directory(path, files, directories=()):
    files, directories = set(files), set(directories)
    assert not path.is_symlink() and path.is_dir()
    actual = {p.name: p for p in path.iterdir()}
    assert actual.keys() == files | directories, ('unexpected/missing entries', path, sorted(actual))
    for name, p in actual.items():
        assert not p.is_symlink() and (p.is_file() if name in files else p.is_dir()), ('unexpected type', p)


def output_files(job):
    if job.get('kind') == 'selftest': return set()
    suffixes = OUTPUT_SUFFIXES | ({'means.f32', 'ordering.csv'} if job['mode'].startswith('S2') else set())
    return {job['label']+'.'+s for s in suffixes}


def report_files(job):
    return {job['label']+s for s in ('.ncu-rep', '.csv')} if job.get('tool') == 'ncu' else set()


def stage_census(w, stage, jobs, rows, reg):
    """Reject off-ledger files and commands, including consistently edited receipts."""
    root = w/stage; labels = [j['label'] for j in jobs]
    assert len(labels) == len(set(labels)) == len(rows)
    root_files = {'REGISTERED.json', 'RESULTS.json'} | {label+s for label in labels for s in ('.command.json', '.checked.json', '.outer.log')}
    outputs = set().union(*(output_files(j) for j in jobs))
    reports = set().union(*(report_files(j) for j in jobs))
    exact_directory(root, root_files, ('guards', 'outputs', 'reports'))
    exact_directory(root/'guards', (), labels)
    exact_directory(root/'outputs', outputs)
    exact_directory(root/'reports', reports)
    commands = {}
    for job, row in zip(jobs, rows):
        label = job['label']; guard = root/'guards'/label
        exact_directory(guard, GUARD_FILES)
        assert set(row['guard_files']) == GUARD_FILES and set(row['reports']) == report_files(job)
        checked = load(root/(label+'.checked.json'))
        assert set(checked.get('raw_outputs', {})) == output_files(job)
        wanted = command(job, w, reg, root/'outputs'/label)
        assert load(root/(label+'.command.json')) == {'command': wanted}, ('source-derived command', label)
        guarded = ['numactl', f"--cpunodebind={reg['numa']}", f"--membind={reg['numa']}", *wanted]
        assert load(guard/'command.json') == load(guard/'receipt.json')['command'] == guarded
        commands[label] = sha(root/(label+'.command.json'))
    return dict(passed=True, jobs=len(jobs), root_files=len(root_files),
                guard_files=len(GUARD_FILES)*len(jobs), output_files=len(outputs),
                report_files=len(reports), source_derived_command_hashes=commands,
                no_extra_entries_or_symlinks=True)
