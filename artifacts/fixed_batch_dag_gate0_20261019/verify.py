"""Post-run full execution binding, independent input/result rebuilding; no GPU."""
if not __debug__:
    raise SystemExit('Mandatory checks require ordinary Python.')
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import analyze
import prepare
import run_cpu
from prepare import load, save, sha

HERE = Path(__file__).resolve().parent
EXCLUDE = {'postrun','published','archives'}


def inventory(work):
    files = {str(f.relative_to(work)):dict(bytes=f.stat().st_size,sha256=sha(f))
             for f in sorted(work.rglob('*'))
             if f.is_file() and f.relative_to(work).parts[0] not in EXCLUDE}
    assert all(not (work/n).is_symlink() for n in files)
    return files


def compare(left,right):
    a = {str(f.relative_to(left)) for f in left.rglob('*') if f.is_file()}
    b = {str(f.relative_to(right)) for f in right.rglob('*') if f.is_file()}
    assert a == b
    assert all((left/n).read_bytes() == (right/n).read_bytes() for n in a)


def binding(work):
    anchors = load(HERE/'evidence/ANCHORS.json')
    assert inventory(work) == anchors['raw_files'], 'Changed,extra or missing observation'
    source = work/'execution_source/artifacts'/HERE.name
    expected = anchors['source_sha256']
    assert expected == {n:sha(HERE/n) for n in run_cpu.FILES}
    assert expected == {n:sha(source/n) for n in run_cpu.FILES}
    reg = load(work/'campaign/REGISTERED.json')
    start,build = load(work/'campaign/START.json'),load(work/'campaign/BUILD.json')
    c,prep = load(HERE/'CONTRACT.json'),load(work/'inputs/PREPARE.json')
    assert reg['source_sha256'] == start['source_sha256'] == expected
    assert reg['nice'] == start['nice'] == 10 and reg['before_build_and_targets'] and start['before_28_targets']
    assert reg['GPU_starts'] == start['GPU_starts'] == build['GPU_starts'] == 0
    assert reg['contract_sha256'] == prep['contract_sha256'] == sha(HERE/'CONTRACT.json')
    assert reg['prepare_sha256'] == start['input_prepare_sha256'] == sha(work/'inputs/PREPARE.json')
    assert build['passed'] and build['binary_sha256'] == start['binary_sha256'] == anchors['binary_sha256'] == sha(work/'campaign/build/solver')
    authority = load(HERE.parent/'pdx_bond_gpu_realizability_gate4_20261015_recovery_01/evidence/INPUT_IDENTITY.json')
    assert anchors['parent_results_sha256'] == prep['parent_results_sha256'] == authority['cpu_results_sha256'] == sha(work/'parent_raw/RESULTS.json')
    compile_command = ['c++','-std=c++17','-O2','-Wall','-Wextra','-pedantic',str(source/'solver.cpp'),'-o',str(work/'campaign/build/solver')]
    assert reg['compile_command'] == compile_command
    assert not (work/'campaign/build/compile.stderr').read_bytes()
    qual = load(work/'campaign/QUALIFICATION.json')
    assert qual == load(work/'campaign/qualification/TESTS.json') == json.loads((work/'campaign/qualification.stdout').read_text())
    assert qual['passed'] and qual['oracle_brackets_checked'] == 1344 and qual['bounded_search_branches'] > 0
    assert start['qualification_sha256'] == sha(work/'campaign/QUALIFICATION.json')
    assert not (work/'campaign/qualification.stderr').read_bytes()
    ledger = [json.loads(l) for l in (work/'campaign/STARTS.jsonl').read_text().splitlines()]
    assert ledger == [dict(label=b['label'],GPU=False) for b in prep['batches']]
    result = load(work/'campaign/RUNS.json')
    assert result['passed'] and result['CPU_processes'] == 28 and result['GPU_starts'] == 0
    assert len(result['records']) == len(prep['batches']) == 28
    expected_receipts = set()
    for b,r in zip(prep['batches'],result['records']):
        label = b['label'];base = work/'campaign/receipts'/label
        cmd = [str(work/'campaign/build/solver'),str(work/'inputs'/(label+'.bin')),
               str(work/'campaign/runs'/(label+'.csv')),str(c['oracle']['max_expansions_per_context']),
               str(c['oracle']['max_expansions_per_batch'])]
        command = dict(command=cmd,input_sha256=b['input_sha256'],binary_sha256=anchors['binary_sha256'],contract_sha256=sha(HERE/'CONTRACT.json'))
        assert load(Path(str(base)+'.command.json')) == command
        assert r == load(Path(str(base)+'.result.json'))
        assert r['label'] == label and r['returncode'] == 0 and r['wall_seconds'] >= 0 and r['GPU_starts'] == 0
        assert r['binary_sha256'] == anchors['binary_sha256']
        assert r['input_sha256'] == b['input_sha256'] == sha(work/'inputs'/(label+'.bin'))
        assert r['output_sha256'] == sha(work/'campaign/runs'/(label+'.csv'))
        stdout = Path(str(base)+'.stdout').read_text()
        match = re.fullmatch(r'SHARING_PASS contexts=(\d+) sectors=(\d+) expansions=(\d+) GPU_starts=0\n',stdout)
        assert match and int(match[1]) == b['contexts'] and int(match[2]) == b['sectors']
        assert int(match[3]) <= c['oracle']['max_expansions_per_batch']
        assert not Path(str(base)+'.stderr').read_bytes()
        expected_receipts.update(label+suffix for suffix in ('.command.json','.result.json','.stdout','.stderr'))
    assert {f.name for f in (work/'campaign/receipts').iterdir()} == expected_receipts
    return anchors


def check(work,out):
    anchors = binding(work)
    out.mkdir()
    prepare.prepare(work/'parent_raw',out/'inputs')
    compare(work/'inputs',out/'inputs')
    analyze.analyze(out/'inputs',work/'campaign',out/'analysis')
    compare(work/'analysis',out/'analysis')
    reg = load(work/'campaign/REGISTERED.json')
    command = reg['compile_command'][:-1]+[str(out/'solver')]
    r = subprocess.run(command,capture_output=True,text=True)
    (out/'compile.stdout').write_text(r.stdout);(out/'compile.stderr').write_text(r.stderr)
    assert r.returncode == 0 and not r.stderr
    assert sha(out/'solver') == anchors['binary_sha256']
    env = {**os.environ,'PYTHONDONTWRITEBYTECODE':'1','OPENBLAS_NUM_THREADS':'1'}
    r = subprocess.run(['python3',str(HERE/'test_solver.py'),'--binary',str(out/'solver'),'--out',str(out/'qualification')],capture_output=True,text=True,env=env)
    (out/'qualification.stdout').write_text(r.stdout);(out/'qualification.stderr').write_text(r.stderr)
    assert r.returncode == 0 and not r.stderr
    compare(work/'campaign/qualification',out/'qualification')
    binding(work)
    refs = {n:sha(HERE/n) for n in (*run_cpu.FILES,'verify.py','evidence/ANCHORS.json')}
    proof = dict(passed=True,CPU_processes_bound=28,GPU_starts=0,new_population_solver_targets=0,
                 all_sources_commands_build_exits_and_logs_bound=True,all_contexts_and_witnesses_checked=True,
                 inputs_and_results_independently_regenerated_byte_identically=True,
                 binary_recompiled_identically=True,qualification_independently_reproduced=True,
                 raw_files=len(anchors['raw_files']),checker_reference_sources=refs,
                 scope='Post-run reference binding,not pre-target signatures;finite source-cost model only')
    save(out/'PROOF.json',proof)
    print('FULL_EXECUTION_BINDING_PASS',len(anchors['raw_files']),'raw files;28 CPU targets;0 GPU')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--work',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a = p.parse_args()
    check(a.work.resolve(),a.out.resolve())
