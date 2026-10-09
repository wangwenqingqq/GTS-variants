#!/usr/bin/env python3
"""One fixed snapshot full-output qualification of labeled CPU Flat inclusion adapter."""
import argparse,csv,json,time
from pathlib import Path
import numpy as np
from native_cpu import NativeCPU
import qualify
from common import outside_repo

def main(a):
    work=outside_repo(a.work);work.mkdir(parents=True,exist_ok=False)
    spec=json.loads((a.snapshot/'SNAPSHOT.json').read_text());assert qualify.cpu.sha(a.data)==spec['data_sha256']
    assert (spec['N'],spec['D'],spec['Q'])==(1000000,960,32)
    requests=[(task,q['physical_qid'],0.705625057220459,8) for task in (0,1) for q in spec['queries']]
    query=work/'queries.txt';query.write_text('64\n'+''.join(f'{t} {q} {r} {k}\n' for t,q,r,k in requests))
    qualify.save(work/'REGISTERED.json',dict(method='CPU_FLAT_INCLUSIVE_ADAPT',snapshot_sha256=qualify.cpu.sha(a.snapshot/'SNAPSHOT.json'),data_sha256=spec['data_sha256'],request_sha256=qualify.cpu.sha(query),
        script_sha256=qualify.cpu.sha(__file__),adapter_sha256=qualify.cpu.sha(Path(__file__).with_name('native_cpu.py')),scope='qualification only, no primary latency'))
    data=qualify.cpu.validate.load(a.data);api=NativeCPU('CPU_FLAT',inclusive=True);api.build(data);cols=[];rows=[];at=0
    for i,(task,qid,r,k) in enumerate(requests):
        t=time.perf_counter();result=api.knn(data[qid],k) if task==0 else api.range(data[qid],r);elapsed=(time.perf_counter()-t)*1000
        ids,fields,raw=result;cols.append(result);rows.append(dict(task='knn' if task==0 else 'range',query=i,qid=qid,count=len(ids),offset=at,ack_ms=elapsed));at+=len(ids)
    api.release();prefix=work/'result'
    for i,suffix,dtype in ((0,'.ids.i32','<i4'),(1,'.dist.f32','<f4'),(2,'.native_squared.f64','<f8')):
        np.concatenate([c[i] for c in cols]).astype(dtype).tofile(str(prefix)+suffix)
    with Path(str(prefix)+'.queries.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    qualify.save(work/'DELIVERED.json',dict(complete=True,queries=64,items=at,output_sha256={p.name:qualify.cpu.sha(p) for p in work.glob('result.*')}))
    print('delivered',work.name,at,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('work','snapshot','data'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();main(a)
