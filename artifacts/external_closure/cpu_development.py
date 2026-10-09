#!/usr/bin/env python3
"""Frozen disjoint-query leaf development; no formal rows enter selection."""
import argparse, hashlib, json, os, subprocess, sys, time
from pathlib import Path
from common import outside_repo
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'rebuild_tree_baselines'))
import cpu
ORDER = [('CPU_KD',32),('CPU_BALL',128),('CPU_KD',512),('CPU_BALL',32),('CPU_KD',128),('CPU_BALL',512)]

def prepare(a):
    a.work=outside_repo(a.work);a.work.mkdir(parents=True,exist_ok=False)
    data=cpu.validate.load(a.data); excluded=set()
    snapshots={}
    for name in ('initial','first_rebuilt'):
        spec=json.loads((a.snapshots/name/'SNAPSHOT.json').read_text())
        source=a.data if name=='initial' else a.snapshots/name/'data.f32bin'
        assert cpu.sha(source)==spec['data_sha256']
        snapshots[name]=dict(manifest_sha256=cpu.sha(a.snapshots/name/'SNAPSHOT.json'),data_sha256=spec['data_sha256'])
        other=data if name=='initial' else cpu.validate.load(source)
        for q in spec['queries']: excluded.add(hashlib.sha256(other[q['physical_qid']].tobytes()).hexdigest())
    assert cpu.sha(a.data)==json.loads((a.snapshots/'initial/SNAPSHOT.json').read_text())['data_sha256']
    rng=np.random.default_rng(2026101001); ids=[]; hashes=[]
    for i in rng.permutation(len(data)):
        h=hashlib.sha256(data[i].tobytes()).hexdigest()
        if h not in excluded and h not in hashes: ids.append(int(i));hashes.append(h)
        if len(ids)==32:break
    spec=dict(N=len(data),D=data.shape[1],Q=32,B=1,K=8,data_sha256=cpu.sha(a.data),queries=[dict(physical_qid=i) for i in ids])
    cpu.save(a.work/'SNAPSHOT.json',spec)
    cpu.save(a.work/'REGISTERED.json',dict(seed=2026101001,coordinate_sha256=hashes,excluded_sha256=sorted(excluded),
        snapshots=snapshots,jobs=ORDER,script_sha256=cpu.sha(__file__),executor_sha256=cpu.sha(HERE.parent/'rebuild_tree_baselines/cpu.py'),
        contract_sha256=cpu.sha(HERE/'CONTRACT.md'),registered_unix=time.time(),numa_node=a.numa_node,selection='min sum of equal-count full Host-ready passes, then smaller leaf',
        snapshot_sha256=cpu.sha(a.work/'SNAPSHOT.json')))

def run(a):
    a.work=outside_repo(a.work)
    reg=json.loads((a.work/'REGISTERED.json').read_text())
    assert a.numa_node==reg['numa_node']
    assert reg['script_sha256']==cpu.sha(__file__) and reg['executor_sha256']==cpu.sha(HERE.parent/'rebuild_tree_baselines/cpu.py')
    assert reg['snapshot_sha256']==cpu.sha(a.work/'SNAPSHOT.json')
    env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1')
    results=[]
    for method,leaf in ORDER:
        out=a.work/f'{method}_{leaf}'; log=a.work/'logs'/out.name; log.parent.mkdir(exist_ok=True);assert not Path(str(out)+'.receipt.json').exists()
        cmd=['numactl',f'--cpunodebind={a.numa_node}',f'--membind={a.numa_node}','timeout','900',sys.executable,str(HERE.parent/'rebuild_tree_baselines/cpu.py'),
            'execute','--method',method,'--leaf-size',str(leaf),'--data',str(a.data),'--snapshot',str(a.work),'--output',str(out)]
        start=time.monotonic()
        with Path(str(log)+'.stdout').open('x') as stdout,Path(str(log)+'.stderr').open('x') as stderr:
            rc=subprocess.run(cmd,env=env,stdout=stdout,stderr=stderr).returncode
        cpu.save(str(out)+'.receipt.json',dict(returncode=rc,wall_s=time.monotonic()-start,command=cmd))
        assert rc==0, (method,leaf,rc)
        meta=json.loads(Path(str(out)+'.native.json').read_text())
        results.append(dict(method=method,leaf=leaf,cost_ms=meta['timing']['knn_pass_ms']+meta['timing']['range_pass_ms'],
            output_sha256={p.name:cpu.sha(p) for p in a.work.glob(out.name+'.*')}))
        print(method,leaf,results[-1]['cost_ms'],flush=True)
    cpu.save(a.work/'SELECTION.json',dict(rows=results,selected={method:min((x for x in results if x['method']==method),key=lambda x:(x['cost_ms'],x['leaf']))['leaf'] for method in ('CPU_KD','CPU_BALL')},status='selection frozen; independent quality admission still required'))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--numa-node',type=int,required=True);p.add_argument('action',choices=('prepare','run'));p.add_argument('--work',type=Path,required=True);p.add_argument('--data',type=Path,required=True);p.add_argument('--snapshots',type=Path)
    a=p.parse_args();assert __debug__;a.work=outside_repo(a.work); (prepare if a.action=='prepare' else run)(a)
