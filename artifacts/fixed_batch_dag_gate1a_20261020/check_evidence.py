"""Bind the sealed execution, exact commands and data rows, independently of self-checks."""
if not __debug__:
    raise SystemExit('Mandatory checks require ordinary Python.')
import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import tarfile
import gate1a as g

EXCLUDED = {'archives', 'postrun', 'published'}


def validate_raw(work, anchors):
    """Fail before expensive identity reads if any sealed observation was changed."""
    expected = dict(anchors['raw_files'])
    bundle = g.load(work/'SOURCE_BUNDLE_R1.json')
    canonical = {'PREFLIGHT.json','SOURCE_BUNDLE_R1.tar','SOURCE_BUNDLE_R1.json',
                 'gate1a.py.preflight.stdout','gate1a.py.preflight.stderr',
                 'test_gate1a.py.preflight.stdout','test_gate1a.py.preflight.stderr',
                 'LAUNCH_REGISTERED.json','DRIVER_START.json','DRIVER_R1.stdout','DRIVER_R1.stderr'}
    canonical |= {'source/'+n for n in bundle['files']}
    old = g.load(g.PARENT/'evidence/ANCHORS.json')['raw_files']
    for prefix, dest in [('campaign/','run/dev_campaign/'),('inputs/','run/dev_inputs/'),('analysis/','run/dev_analysis/')]:
        canonical |= {dest+n[len(prefix):] for n in old if n.startswith(prefix)}
    canonical |= {'run/REGISTERED.json','run/PROOF.json','run/heldout/INPUT_MANIFEST.json','run/heldout/HELDOUT_QUERIES.f32'}
    canonical |= {'run/'+name+'.'+ext for name in ('prepare','run','analyze')
                  for ext in ('command.json','stdout','stderr','exit.json')}
    assert set(expected) == canonical and len(expected) == 450, 'Unexpected sealed file roles'
    files, dirs = set(), set()
    for p in work.rglob('*'):
        rel = p.relative_to(work)
        if rel.parts[0] in EXCLUDED:
            continue
        assert not p.is_symlink(), 'Symlink in raw census'
        (files if p.is_file() else dirs).add(str(rel))
    assert files == canonical, 'Missing or extra raw observation/attempt'
    parents = {str(p) for n in canonical for p in Path(n).parents if str(p) != '.'}
    assert dirs == parents, 'Unexpected empty raw directory'
    for n, item in expected.items():
        assert g.identity(work/n) == item, 'Sealed identity mismatch: '+n
    assert g.sha(work/'SOURCE_BUNDLE_R1.tar') == bundle['archive_sha256']
    with tarfile.open(work/'SOURCE_BUNDLE_R1.tar') as t:
        assert len(t.getmembers()) == len(bundle['files']) == 39
        assert {x.name for x in t.getmembers()} == set(bundle['files'])
        for x in t.getmembers():
            assert x.isfile() and not Path(x.name).is_absolute() and '..' not in Path(x.name).parts
            b = t.extractfile(x).read()
            assert dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest()) == bundle['files'][x.name]
            assert g.identity(work/'source'/x.name) == bundle['files'][x.name]
    return expected


def audit(work, data, anchors):
    c, s = g.check_sources()
    raw = validate_raw(work, anchors)
    code = work/'source/artifacts/fixed_batch_dag_gate0_20261019'
    new = work/'source/artifacts/fixed_batch_dag_gate1a_20261020'
    run = work/'run'
    frozen = g.load(g.HERE/'SOURCE_FREEZE.json')
    for n, item in frozen['files'].items():
        assert g.identity(work/'source'/n) == item
    assert g.identity(new/'SOURCE_FREEZE.json') == g.identity(g.HERE/'SOURCE_FREEZE.json')
    reg = g.load(run/'REGISTERED.json')
    assert reg['data_path'] == str(data) and reg['output_path'] == str(run)
    assert g.load(work/'PREFLIGHT.json')['dataset_path'] == str(data)
    parent_raw = Path(reg['parent_raw_path'])
    assert parent_raw.is_dir()
    prep = g.load(run/'dev_inputs/PREPARE.json')
    assert g.sha(parent_raw/'RESULTS.json') == prep['parent_results_sha256']
    for n, item in prep['source_files'].items():
        assert g.identity(parent_raw/'raw'/n) == item
    expected_launch = ['nice','-n','10','python3',str(new/'gate1a.py'),'replay',
                       '--data',str(data),'--parent-raw',str(parent_raw),'--out',str(run)]
    launch = g.load(work/'LAUNCH_REGISTERED.json')
    assert launch['command'] == g.load(work/'DRIVER_START.json')['command'] == expected_launch
    assert launch['registered_before_process'] and launch['heldout_evaluation_budget'] == launch['GPU_start_budget'] == 0
    assert launch['source_bundle_sha256'] == g.load(work/'SOURCE_BUNDLE_R1.json')['archive_sha256']
    assert (work/'DRIVER_R1.stdout').read_text() == 'GATE1A_PASS:128 held-out identities;28 exact development replays;0 held-out evaluations;0 GPU\n'
    assert (work/'DRIVER_R1.stderr').read_bytes() == b''
    steps = {
        'prepare':['python3',str(code/'prepare.py'),'--parent-raw',str(parent_raw),'--out',str(run/'dev_inputs')],
        'run':['python3',str(code/'run_cpu.py'),'--inputs',str(run/'dev_inputs'),'--work',str(run/'dev_campaign')],
        'analyze':['python3',str(code/'analyze.py'),'--inputs',str(run/'dev_inputs'),'--runs',str(run/'dev_campaign'),'--out',str(run/'dev_analysis')]}
    for name, cmd in steps.items():
        assert g.load(run/(name+'.command.json')) == dict(command=cmd,before_start=True)
        assert g.load(run/(name+'.exit.json'))['returncode'] == 0
        assert (run/(name+'.stderr')).read_bytes() == b''
    campaign = run/'dev_campaign'
    original_sources = g.load(g.PARENT/'evidence/EXECUTED_SOURCE_FREEZE.json')['source_sha256']
    assert len(original_sources) == 8
    registration = g.load(campaign/'REGISTERED.json')
    start = g.load(campaign/'START.json')
    assert registration['before_build_and_targets'] and start['before_28_targets']
    assert registration['source_sha256'] == start['source_sha256'] == original_sources
    assert registration['nice'] == start['nice'] == 10 and registration['CPU_workers'] == 4
    assert registration['compiler'] == g.load(work/'PREFLIGHT.json')['compiler']
    build_command = ['c++','-std=c++17','-O2','-Wall','-Wextra','-pedantic',str(code/'solver.cpp'),'-o',str(campaign/'build/solver')]
    assert registration['compile_command'] == build_command
    assert (campaign/'build/compile.stdout').read_bytes() == (campaign/'build/compile.stderr').read_bytes() == b''
    binary_hash = g.sha(campaign/'build/solver')
    assert g.load(campaign/'BUILD.json') == dict(passed=True,binary_sha256=binary_hash,GPU_starts=0)
    assert start['binary_sha256'] == binary_hash
    expected_qualification = g.load(g.PARENT/'evidence/QUALIFICATION.json')
    assert g.load(campaign/'QUALIFICATION.json') == g.load(campaign/'qualification/TESTS.json') == expected_qualification
    assert start['qualification_sha256'] == g.sha(campaign/'QUALIFICATION.json')
    assert (campaign/'qualification.stdout').read_text() == json.dumps(expected_qualification,sort_keys=True)+'\n'
    assert (campaign/'qualification.stderr').read_bytes() == b''
    oldraw = g.load(g.PARENT/'evidence/ANCHORS.json')['raw_files']
    for n, item in oldraw.items():
        if n.startswith('campaign/qualification/'):
            assert g.identity(campaign/n[len('campaign/'):]) == item
    execution = g.load(campaign/'RUNS.json')
    results = g.load(run/'dev_analysis/RESULTS.json')
    records = {x['label']:x for x in execution['records']}
    batches = {x['label']:x for x in results['batch_results']}
    starts = [json.loads(x) for x in (campaign/'STARTS.jsonl').read_text().splitlines()]
    assert starts == [dict(label=x['label'],GPU=False) for x in prep['batches']]
    assert len(records) == len(execution['records']) == 28
    for b in prep['batches']:
        name = b['label']
        cmd = [str(campaign/'build/solver'),str(run/'dev_inputs'/(name+'.bin')),str(campaign/'runs'/(name+'.csv')),'4096','2000000']
        receipt = g.load(campaign/'receipts'/(name+'.command.json'))
        assert receipt == dict(command=cmd,input_sha256=b['input_sha256'],binary_sha256=binary_hash,contract_sha256=g.sha(g.PARENT/'CONTRACT.json'))
        assert g.load(campaign/'receipts'/(name+'.result.json')) == records[name]
        assert records[name]['binary_sha256'] == binary_hash and records[name]['returncode'] == records[name]['GPU_starts'] == 0
        stdout = f"SHARING_PASS contexts={b['contexts']} sectors={b['sectors']} expansions={batches[name]['expansions']} GPU_starts=0\n"
        assert (campaign/'receipts'/(name+'.stdout')).read_text() == stdout
        assert (campaign/'receipts'/(name+'.stderr')).read_bytes() == b''
    # Identity-only re-extraction from the authority, not agreement of two mutable exports.
    assert data.stat().st_size == c['dataset']['file_bytes'] and g.sha(data) == c['dataset']['sha256']
    payload = (run/'heldout/HELDOUT_QUERIES.f32').read_bytes()
    hashes = set()
    with data.open('rb') as f:
        assert f.read(12) == struct.pack('<iii',960,1000000,2)
        for q in c['development_qids']:
            f.seek(12+q*3840)
            hashes.add(hashlib.sha256(f.read(3840)).hexdigest())
        for i,q in enumerate(s['qids']):
            f.seek(12+q*3840)
            row = f.read(3840)
            assert row == payload[i*3840:(i+1)*3840]
            h = hashlib.sha256(row).hexdigest()
            assert h not in hashes
            hashes.add(h)
    assert g.sha(data) == c['dataset']['sha256']
    proof = g.verify_run(run)
    assert proof == g.load(run/'PROOF.json')
    return dict(passed=True,raw_files=len(raw),raw_bytes=sum(x['bytes'] for x in raw.values()),
                raw_anchors_sha256=hashlib.sha256(g.encoded(anchors)).hexdigest(),
                executed_source_files=18,exact_development_commands=28,
                original_rows_byte_equal=128,qualified_oracle_brackets=1344,
                all_raw_commands_logs_exits_qualification_bound=True,
                heldout_evaluation_starts=0,GPU_starts=0,
                scope='Sealed Gate1A execution only;not a historical CPU timing equivalence or heldout outcome')


def main(work, data, anchors_path, out):
    assert os.getpriority(os.PRIO_PROCESS,0) == 10
    proof = audit(work,data,g.load(anchors_path))
    out.mkdir()
    code = work/'source/artifacts/fixed_batch_dag_gate0_20261019'
    env = {**os.environ,'PYTHONDONTWRITEBYTECODE':'1','OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1'}
    commands = [
        ('rebuild',['c++','-std=c++17','-O2','-Wall','-Wextra','-pedantic',str(code/'solver.cpp'),'-o',str(out/'solver')]),
        ('qualification',['python3',str(code/'test_solver.py'),'--binary',str(out/'solver'),'--out',str(out/'qualification')]),
        ('reanalyze',['python3',str(code/'analyze.py'),'--inputs',str(work/'run/dev_inputs'),'--runs',str(work/'run/dev_campaign'),'--out',str(out/'analysis')])]
    for name,command in commands:
        p = subprocess.run(command,capture_output=True,text=True,env=env)
        g.save(out/(name+'.command.json'),dict(command=command,returncode=p.returncode))
        (out/(name+'.stdout')).write_text(p.stdout)
        (out/(name+'.stderr')).write_text(p.stderr)
        assert p.returncode == 0 and not p.stderr,(name,p.stdout,p.stderr)
    assert g.sha(out/'solver') == g.sha(work/'run/dev_campaign/build/solver')
    assert g.load(out/'qualification/TESTS.json') == g.load(work/'run/dev_campaign/QUALIFICATION.json')
    assert g.load(out/'analysis/RESULTS.json') == g.load(work/'run/dev_analysis/RESULTS.json')
    assert g.identity(out/'analysis/summary.csv') == g.identity(work/'run/dev_analysis/summary.csv')
    proof.update(identical_binary_rebuild=True,independent_qualification_repeated=True,
                 all_contexts_reanalyzed=True,checker_sha256=g.sha(Path(__file__)),
                 dataset_sha256=g.sha(data))
    g.save(out/'CHECK_PROOF.json',proof)
    print('SEALED_EXECUTION_PASS:450 raw files;128 authoritative rows;28 exact commands;identical rebuild;0 heldout evaluations;0 GPU')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work',type=Path,required=True)
    p.add_argument('--data',type=Path,required=True)
    p.add_argument('--anchors',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a = p.parse_args()
    main(a.work.resolve(),a.data.resolve(),a.anchors.resolve(),a.out.resolve())
