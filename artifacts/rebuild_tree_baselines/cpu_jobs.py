#!/usr/bin/env python3
"""Six registered fresh-process CPU diagnostics, serialized on one NUMA node."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('work','tree-python','faiss-python'): p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--register', action='store_true')
    p.add_argument('--snapshots',type=Path);p.add_argument('--initial-data',type=Path)
    p.add_argument('--numa-node',type=int,required=True); a=p.parse_args()
    assert __debug__ and HERE.parents[1] not in a.work.resolve().parents
    if a.register:
        assert a.snapshots and a.initial_data and not (a.work/'CPU_REGISTERED.json').exists()
        a.work.mkdir(parents=True,exist_ok=True); jobs=[]
        for name in ('initial','first_rebuilt'):
            folder=a.snapshots/name;spec=json.loads((folder/'SNAPSHOT.json').read_text())
            assert spec['N']==1000000 and spec['D']==960 and spec['Q']==32
            data=a.initial_data if name=='initial' else folder/'data.f32bin'
            for method in ('CPU_KD','CPU_BALL','CPU_FLAT'):
                jobs.append(dict(label=name+'_'+method,method=method,snapshot=str(folder.resolve()),data=str(data.resolve()),
                    snapshot_sha256=sha(folder/'SNAPSHOT.json'),data_sha256=spec['data_sha256']))
        (a.work/'CPU_REGISTERED.json').write_text(json.dumps(dict(registered_unix=time.time(),script_sha256=sha(HERE/'cpu.py'),
            contract_sha256=sha(HERE/'CONTRACT.json'),jobs=jobs,stage='single static capability/quality diagnostics, not formal comparisons'),indent=2)+'\n')
        print('Registered six diagnostics before native execution');sys.exit(0)
    registration = json.loads((a.work/'CPU_REGISTERED.json').read_text())
    assert registration['script_sha256'] == sha(HERE/'cpu.py')
    assert registration['contract_sha256'] == sha(HERE/'CONTRACT.json')
    conf = json.loads((HERE/'CONTRACT.json').read_text())['baseline_diagnostic']
    env = dict(os.environ, OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1',PYTHONUNBUFFERED='1')
    with Path('/tmp/gts_rebuild_tree_cpu_diagnostics.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        (a.work/'cpu_outputs').mkdir(exist_ok=False)
        (a.work/'cpu_guards').mkdir(exist_ok=False)
        for job in registration['jobs']:
            name=job['label']; prefix=a.work/'cpu_outputs'/name; guard=a.work/'cpu_guards'/name;guard.mkdir()
            assert sha(Path(job['snapshot'])/'SNAPSHOT.json') == job['snapshot_sha256']
            python=a.faiss_python if job['method']=='CPU_FLAT' else a.tree_python
            command=['numactl',f'--cpunodebind={a.numa_node}',f'--membind={a.numa_node}','timeout','--signal=TERM',str(conf['timeout_seconds_per_job']),
                str(python.absolute()),str(HERE/'cpu.py'),'execute','--method',job['method'],'--data',job['data'],'--snapshot',job['snapshot'],'--output',str(prefix)]
            (guard/'command.json').write_text(json.dumps(command)+'\n')
            start=time.monotonic()
            with (guard/'stdout.log').open('w') as out,(guard/'stderr.log').open('w') as err:
                result=subprocess.run(command,env=env,stdout=out,stderr=err)
            receipt=dict(exit_code=result.returncode,wall_s=time.monotonic()-start,timed_out=result.returncode==124,
                runtime_valid=result.returncode==0,script_sha256=sha(HERE/'cpu.py'),registration_sha256=sha(a.work/'CPU_REGISTERED.json'),
                output_hashes={x.name:sha(x) for x in prefix.parent.glob(prefix.name+'.*')})
            (guard/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
            print(name,receipt['exit_code'],receipt['wall_s'],flush=True)
            if result.returncode:print('Failure retained; not a latency or zero-throughput sample',flush=True)
