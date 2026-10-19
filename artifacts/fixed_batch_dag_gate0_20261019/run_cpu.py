"""Frozen, bounded CPU combinatorial study. Never invoke a GPU."""
if not __debug__:
    raise SystemExit('Mandatory checks require ordinary Python.')
import argparse
import concurrent.futures
import json
import os
from pathlib import Path
import platform
import subprocess
import time
from prepare import load, save, sha

HERE = Path(__file__).resolve().parent
FILES = ('CONTRACT.json','CLARIFICATIONS.json','PRIOR_ART.md','solver.cpp','prepare.py','test_solver.py','run_cpu.py','analyze.py')


def identities():
    return {n:sha(HERE/n) for n in FILES}


def main(work,inputs):
    c,prep = load(HERE/'CONTRACT.json'),load(inputs/'PREPARE.json')
    assert os.getpriority(os.PRIO_PROCESS,0) == c['resource']['nice'] == 10
    assert prep['passed'] and prep['contract_sha256'] == sha(HERE/'CONTRACT.json')
    assert len(prep['batches']) == c['resource']['CPU_target_processes'] == 28
    assert all(sha(inputs/(b['label']+'.bin')) == b['input_sha256'] for b in prep['batches'])
    work.mkdir()
    for name in ('build','runs','receipts'):
        (work/name).mkdir()
    binary = work/'build/solver'
    command = ['c++','-std=c++17','-O2','-Wall','-Wextra','-pedantic',str(HERE/'solver.cpp'),'-o',str(binary)]
    save(work/'REGISTERED.json',dict(before_build_and_targets=True,source_sha256=identities(),
        contract_sha256=sha(HERE/'CONTRACT.json'),prepare_sha256=sha(inputs/'PREPARE.json'),
        compiler=subprocess.check_output(['c++','--version'],text=True),python=platform.python_version(),
        platform=platform.uname()._asdict(),compile_command=command,CPU_workers=4,
        nice=os.getpriority(os.PRIO_PROCESS,0),GPU_starts=0))
    try:
        r = subprocess.run(command,capture_output=True,text=True)
        (work/'build/compile.stdout').write_text(r.stdout);(work/'build/compile.stderr').write_text(r.stderr)
        assert r.returncode == 0 and not r.stderr,(r.returncode,r.stderr)
        binary_hash = sha(binary)
        save(work/'BUILD.json',dict(passed=True,binary_sha256=binary_hash,GPU_starts=0))
        env = {**os.environ,'PYTHONDONTWRITEBYTECODE':'1','OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1'}
        r = subprocess.run(['python3',str(HERE/'test_solver.py'),'--binary',str(binary),'--out',str(work/'qualification')],capture_output=True,text=True,env=env)
        (work/'qualification.stdout').write_text(r.stdout);(work/'qualification.stderr').write_text(r.stderr)
        assert r.returncode == 0,(r.stdout,r.stderr)
        save(work/'QUALIFICATION.json',load(work/'qualification/TESTS.json'))
        save(work/'START.json',dict(before_28_targets=True,source_sha256=identities(),binary_sha256=binary_hash,
             input_prepare_sha256=sha(inputs/'PREPARE.json'),qualification_sha256=sha(work/'QUALIFICATION.json'),
             nice=os.getpriority(os.PRIO_PROCESS,0),GPU_starts=0))
        def job(b):
            assert identities() == load(work/'REGISTERED.json')['source_sha256']
            assert sha(binary) == binary_hash and sha(inputs/(b['label']+'.bin')) == b['input_sha256']
            assert os.getpriority(os.PRIO_PROCESS,0) == 10
            label = b['label'];output = work/'runs'/(label+'.csv')
            cmd = [str(binary),str(inputs/(label+'.bin')),str(output),
                   str(c['oracle']['max_expansions_per_context']),str(c['oracle']['max_expansions_per_batch'])]
            save(work/'receipts'/(label+'.command.json'),dict(command=cmd,input_sha256=b['input_sha256'],
                 binary_sha256=binary_hash,contract_sha256=sha(HERE/'CONTRACT.json')))
            start = time.monotonic();r = subprocess.run(cmd,capture_output=True,text=True)
            (work/'receipts'/(label+'.stdout')).write_text(r.stdout);(work/'receipts'/(label+'.stderr')).write_text(r.stderr)
            result = dict(label=label,returncode=r.returncode,input_sha256=b['input_sha256'],binary_sha256=binary_hash,
                          output_sha256=sha(output) if output.exists() else None,wall_seconds=time.monotonic()-start,GPU_starts=0)
            save(work/'receipts'/(label+'.result.json'),result)
            return result
        results,next_index = {},0
        with (work/'STARTS.jsonl').open('x') as ledger,concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            pending = {}
            def submit():
                nonlocal next_index
                b = prep['batches'][next_index];next_index += 1
                ledger.write(json.dumps(dict(label=b['label'],GPU=False))+'\n');ledger.flush()
                pending[pool.submit(job,b)] = b['label']
            for _ in range(4):submit()
            while pending:
                done,_ = concurrent.futures.wait(pending,return_when=concurrent.futures.FIRST_COMPLETED)
                completed = [f.result() for f in sorted(done,key=lambda f:pending[f])]
                assert all(r['returncode'] == 0 for r in completed),completed
                for future,r in zip(sorted(done,key=lambda f:pending[f]),completed):
                    pending.pop(future);results[r['label']] = r
                    print('CPU_PASS',len(results),'/28',r['label'],flush=True)
                for _ in completed:
                    if next_index < 28:submit()
        assert identities() == load(work/'REGISTERED.json')['source_sha256'] and sha(binary) == binary_hash
        save(work/'RUNS.json',dict(passed=True,CPU_processes=28,GPU_starts=0,
             records=[results[b['label']] for b in prep['batches']]))
    except BaseException as e:
        save(work/'FAILURE.json',dict(error=repr(e),GPU_starts=0))
        raise


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--work',type=Path,required=True)
    p.add_argument('--inputs',type=Path,required=True)
    a = p.parse_args()
    main(a.work.resolve(),a.inputs.resolve())
