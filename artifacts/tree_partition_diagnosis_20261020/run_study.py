"""One bounded CPU campaign; serial builders, at most four arithmetic threads."""
if not __debug__:
    raise SystemExit('Assertions are mandatory.')
import argparse
import os
from pathlib import Path
import platform
import subprocess
import time
import numpy as np
from tree_study import HERE,source_ids,load,sha,save,bind,stats,outside_repo,runtime_identity


def run(data,references,work):
    work=outside_repo(work)
    assert os.getpriority(os.PRIO_PROCESS,0)==10
    assert os.environ['OMP_THREAD_LIMIT']=='4' and os.environ['OPENBLAS_NUM_THREADS']=='1'
    c=load(HERE/'CONTRACT.json');assert source_ids()==load(HERE/'SOURCE_FREEZE.json')['files']
    bind(data,references)
    work.mkdir();(work/'build').mkdir();(work/'receipts').mkdir()
    sources=source_ids();lib=work/'build/geometry.so'
    command=['g++','-std=c++17','-O3','-fno-fast-math','-ffp-contract=off','-fopenmp','-shared','-fPIC',str(HERE/'geometry.cpp'),'-o',str(lib)]
    save(work/'REGISTERED.json',dict(before_build_and_targets=True,sources=sources,
         contract_sha256=sha(HERE/'CONTRACT.json'),source_freeze_sha256=sha(HERE/'SOURCE_FREEZE.json'),
         compile_command=command,data=str(data),references=str(references),Python=platform.python_version(),NumPy=np.__version__,
         compiler=subprocess.check_output(['g++','--version'],text=True),platform=platform.uname()._asdict(),nice=10,
         runtime=runtime_identity(),
         CPU_population_processes=3,GPU_starts=0,heldout_query_evaluations=0))
    try:
        p=subprocess.run(command,capture_output=True,text=True)
        (work/'build/compile.stdout').write_text(p.stdout);(work/'build/compile.stderr').write_text(p.stderr)
        assert p.returncode==0 and not p.stderr,(p.stdout,p.stderr)
        save(work/'BUILD.json',dict(passed=True,library_sha256=sha(lib)))
        p=subprocess.run(['python3',str(HERE/'test_study.py'),'--library',str(lib),'--out',str(work/'qualification')],capture_output=True,text=True)
        (work/'qualification.stdout').write_text(p.stdout);(work/'qualification.stderr').write_text(p.stderr)
        assert p.returncode==0,(p.stdout,p.stderr)
        save(work/'START.json',dict(before_population=True,sources=source_ids(),library_sha256=sha(lib),qualification_sha256=sha(work/'qualification/TESTS.json'),nice=10))
        records=[]
        with (work/'STARTS.jsonl').open('x') as ledger:
            for index,kind in enumerate(c['builders']):
                assert source_ids()==sources and sha(lib)==load(work/'BUILD.json')['library_sha256']
                cmd=['python3',str(HERE/'tree_study.py'),'--data',str(data),'--references',str(references),'--library',str(lib),'--kind',kind,'--out',str(work/kind)]
                save(work/'receipts'/(kind+'.command.json'),dict(command=cmd,before_start=True,source_hashes=sources,library_sha256=sha(lib)))
                ledger.write(__import__('json').dumps(dict(index=index,kind=kind,GPU=False))+'\n');ledger.flush()
                start=time.monotonic();p=subprocess.run(cmd,capture_output=True,text=True,timeout=1800)
                (work/'receipts'/(kind+'.stdout')).write_text(p.stdout);(work/'receipts'/(kind+'.stderr')).write_text(p.stderr)
                result=dict(kind=kind,returncode=p.returncode,wall_seconds=time.monotonic()-start,
                            complete_sha256=sha(work/kind/'COMPLETE.json') if (work/kind/'COMPLETE.json').exists() else None)
                save(work/'receipts'/(kind+'.exit.json'),result);records.append(result)
                assert p.returncode==0,(kind,p.stdout,p.stderr)
                print(p.stdout.strip(),flush=True)
        assert source_ids()==sources
        save(work/'COMPLETE.json',dict(passed=True,records=records,sources=sources,GPU_starts=0,heldout_query_evaluations=0))
        from verify_study import census
        save(work.with_name(work.name+'.ANCHORS.json'),dict(before_verification=True,files=census(work),sources=sources))
    except BaseException as e:
        save(work/'FAILURE.json',dict(error=repr(e),GPU_starts=0));raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--data',type=Path,required=True);p.add_argument('--references',type=Path,required=True);p.add_argument('--work',type=Path,required=True)
    a=p.parse_args();run(a.data.resolve(),a.references.resolve(),a.work.resolve())
