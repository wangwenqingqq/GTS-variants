#!/usr/bin/env python3
"""Bounded diagnostic continuation; failed native semantics never become admission."""
import argparse,json,os,subprocess,sys
from pathlib import Path
from common import outside_repo
import qualify
HERE=Path(__file__).resolve().parent
sha=qualify.cpu.sha;save=qualify.save

def main(a):
    a.work=outside_repo(a.work);a.work.mkdir(parents=True,exist_ok=False);(a.work/'outputs').mkdir();jobs=[]
    if a.kind in ('tree-diagnostic','tree-safe'):
        old=json.loads((a.previous/'REGISTERED.json').read_text())
        for j in old['jobs']:
            if j['label']=='tree_native_0':continue
            if a.kind=='tree-safe' and j['label'] not in ('tree_adapt_1','tree_adapt_memcheck','tree_adapt_racecheck','tree_adapt_synccheck'):continue
            jobs.append({**j,'binary':str((a.build/j['exe']).resolve()),'binary_sha256':sha(a.build/j['exe'])})
    else:
        for name in ('initial','first_rebuilt'):
            spec=json.loads((a.snapshots/name/'SNAPSHOT.json').read_text())
            data=a.data if name=='initial' else a.snapshots/name/'data.f32bin';assert sha(data)==spec['data_sha256']
            requests=a.work/(name+'.txt');requests.write_text('32\n'+''.join(f"1 {q['physical_qid']} 0.705625057220459 8\n" for q in spec['queries']))
            jobs.append(dict(label=name,binary=str((a.build/'range_service').resolve()),data=str(data.resolve()),requests=str(requests.resolve()),tool=None,
                data_sha256=sha(data),request_sha256=sha(requests),binary_sha256=sha(a.build/'range_service')))
    save(a.work/'REGISTERED.json',dict(jobs=jobs,kind=a.kind,numa_node=a.numa_node,script_sha256=sha(__file__),
        qualifier_sha256=sha(HERE/'qualify.py'),contract_sha256=sha(HERE/'CONTRACT.md'),
        scope='diagnostic only; native quality failure retained; no primary timing admission'))
    results=[]
    for j in jobs:
        assert sha(j['binary'])==j['binary_sha256'] and sha(j['data'])==j['data_sha256'] and sha(j['requests'])==j['request_sha256']
        out=a.work/'outputs'/j['label'];cmd=[j['binary'],j['data'],j['requests'],str(out.resolve())]
        if j['tool']:cmd=['/usr/local/cuda-13.1/bin/compute-sanitizer','--tool',j['tool'],'--error-exitcode','97',*cmd]
        guard=a.work/'guards'/j['label']
        result=subprocess.run([sys.executable,str(HERE.parents[1]/'diagnostics/native_knn_faiss_ivf_20261003/run_locked.py'),
            '--gpu',a.gpu,'--numa-node',str(a.numa_node),'--output',str(guard),'--',*cmd],capture_output=True,text=True)
        (a.work/(j['label']+'.outer.log')).write_text(result.stdout+result.stderr)
        row=dict(label=j['label'],guard_exit=result.returncode)
        if not result.returncode and a.kind.startswith('tree'):
            q=qualify.check(j['data'],j['requests'],out);save(str(out)+'.quality.json',q);row['quality_passed']=q['passed']
        elif not result.returncode:row['quality_status']='pending independent reference (not admitted)'
        results.append(row);save(a.work/'RESULTS.json',dict(rows=results));print(row,flush=True)
        # Runtime failure, unlike a retained numerical mismatch, stops this family.
        if result.returncode:break

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--numa-node',type=int,required=True);p.add_argument('--kind',choices=('tree-diagnostic','tree-safe','range-snapshots'),required=True)
    for k in ('work','build','previous','snapshots','data'):p.add_argument('--'+k,type=Path)
    p.add_argument('--gpu',required=True);a=p.parse_args();assert __debug__;a.work=outside_repo(a.work);main(a)
