#!/usr/bin/env python3
"""Bounded adapter qualification with full payloads and guarded B1 processes."""
import argparse,csv,hashlib,json,math,os,struct,subprocess,sys
from pathlib import Path
from common import outside_repo
import numpy as np
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'rebuild_tree_baselines'))
import cpu

def save(p,v):cpu.save(p,v)
def prepare(a):
    a.work=outside_repo(a.work);a.work.mkdir(parents=True,exist_ok=False);rng=np.random.default_rng(2026101001)
    cases={}
    for n in (0,1,7,513,4096):
        d=17;data=rng.random((n,d),dtype=np.float32)
        if n>1:data[1]=data[0]
        p=a.work/f'n{n}.f32bin';p.write_bytes(struct.pack('<iii',d,n,2)+data.tobytes());cases[n]=p.resolve()
    jobs=[]
    def add(label,exe,n,requests,tool=None):
        q=a.work/(label+'.txt');q.write_text(str(len(requests))+'\n'+''.join(f'{t} {i} {r} {k}\n' for t,i,r,k in requests))
        jobs.append(dict(label=label,exe=exe,data=str(cases[n]),requests=str(q.resolve()),tool=tool,
            data_sha256=cpu.sha(cases[n]),request_sha256=cpu.sha(q)))
    for task in (0,1):
        first=[(task,0,0.705625057220459,8)]
        add('tree_native_'+str(task),'tree_native',4096,first)
        add('tree_adapt_'+str(task),'tree_adapt',4096,first*32)
    for n in cases:
        add('range_n'+str(n),'range_service',n,[(1,0,r,8) for r in (-1.,0.,0.705625057220459,100.)]*8)
    for exe in ('tree_adapt','range_service'):
        for tool in ('memcheck','racecheck','synccheck'):
            add(exe+'_'+tool,exe,4096,[(1,0,0.705625057220459,8)]*2,tool)
    jobs=[j for j in jobs if a.family=='both' or (j['exe'].startswith('tree') if a.family=='tree' else j['exe']=='range_service')]
    for j in jobs:j['binary_sha256']=cpu.sha(a.build/j['exe'])
    save(a.work/'REGISTERED.json',dict(jobs=jobs,script_sha256=cpu.sha(__file__),contract_sha256=cpu.sha(HERE/'CONTRACT.md'),
        before_execution=True,numa_node=a.numa_node,max_gpu_processes_including_future_snapshots=32))

def check(data,requests,prefix,native_squared_required=False):
    x=cpu.validate.load(data);requests=Path(requests).read_text().splitlines()[1:]
    with Path(str(prefix)+'.queries.csv').open() as f:rows=list(csv.DictReader(f))
    assert len(rows)==len(requests)
    total=sum(int(r['count']) for r in rows)
    assert all(int(r['count'])>=0 for r in rows)
    for suffix in ('.ids.i32','.dist.f32'):
        assert Path(str(prefix)+suffix).stat().st_size==total*4, 'incomplete or trailing output bytes'
    ids=np.fromfile(str(prefix)+'.ids.i32',dtype='<i4');fields=np.fromfile(str(prefix)+'.dist.f32',dtype='<f4')
    p=Path(str(prefix)+'.native_squared.f64')
    if native_squared_required:assert p.is_file(), 'required native squared payload missing'
    if p.exists():assert p.stat().st_size==total*8, 'malformed native squared payload'
    raw=np.fromfile(p,dtype='<f8') if p.exists() else fields.astype(np.float64)**2
    assert len(ids)==len(fields)==len(raw)==sum(int(r['count']) for r in rows)
    reports=[];at=0;scores={}
    for i,(r,request) in enumerate(zip(rows,requests)):
        assert math.isfinite(float(r['ack_ms'])) and float(r['ack_ms'])>=0
        task,qid,radius,k=request.split();qid=int(qid);task='knn' if task=='0' else 'range'
        assert r['task']==task and int(r['query'])==i and int(r['qid'])==qid and int(r['offset'])==at
        if qid not in scores:
            q=x[qid] if len(x) else np.zeros(x.shape[1],dtype=np.float32);sq=np.zeros(len(x),np.float64)
            if len(x)>8192:
                sys.path.insert(0,str(HERE.parent/'unified_target_workflow/phase_b'))
                import oracle
                from campaign import verify_cpu_library
                lib=Path(os.environ['CLOSURE_CPU_ORACLE']);verify_cpu_library(lib)
                sq=oracle.install(lib)(x,np.arange(len(x)),q)
            else:
                for d in range(x.shape[1]):sq+=(x[:,d].astype(np.float64)-float(q[d]))**2
            scores[qid]=sq
        z=int(r['count']);assert z>=0;sl=slice(at,at+z);sq=scores[qid]
        if float(radius)<0 and task=='range':report=dict(passed=z==0,negative_radius=True)
        else:report=cpu.quality(ids[sl],fields[sl],raw[sl],sq,task,float(radius))
        reports.append(dict(query=i,**report));at+=z
    return dict(passed=all(r['passed'] for r in reports),per_query=reports,native_squared_observed=p.is_file(),
        output_sha256={p.name:cpu.sha(p) for p in prefix.parent.glob(prefix.name+'.*')})

def run(a):
    a.work=outside_repo(a.work)
    reg=json.loads((a.work/'REGISTERED.json').read_text());
    assert a.numa_node==reg['numa_node']
    assert reg['script_sha256']==cpu.sha(__file__)
    out=a.work/'outputs';out.mkdir(exist_ok=False);blocked=set();reports=[]
    for job in reg['jobs']:
        label=job['label'];family='tree' if job['exe'].startswith('tree') else 'range'
        if family in blocked:
            reports.append(dict(label=label,status='not_executed_after_family_gate_failure'));continue
        binary=a.build/job['exe'];assert cpu.sha(binary)==job['binary_sha256']
        assert cpu.sha(job['data'])==job['data_sha256'] and cpu.sha(job['requests'])==job['request_sha256']
        prefix=out/label;cmd=[str(binary.resolve()),job['data'],job['requests'],str(prefix.resolve())]
        if job['tool']:cmd=[a.sanitizer,'--tool',job['tool'],'--error-exitcode','97',*cmd]
        guard=a.work/'guards'/label
        result=subprocess.run([sys.executable,str(HERE.parents[1]/'diagnostics/native_knn_faiss_ivf_20261003/run_locked.py'),
            '--gpu',a.gpu,'--numa-node',str(a.numa_node),'--output',str(guard),'--',*cmd],capture_output=True,text=True)
        (a.work/(label+'.outer.log')).write_text(result.stdout+result.stderr)
        row=dict(label=label,status='runtime_failed' if result.returncode else 'complete',guard_exit=result.returncode)
        if not result.returncode:
            quality=check(job['data'],job['requests'],prefix,native_squared_required=job['exe']=='range_service');save(str(prefix)+'.quality.json',quality);row['quality_passed']=quality['passed']
            if not quality['passed']:row['status']='quality_failed'
        reports.append(row);save(a.work/'RESULTS.json',dict(rows=reports))
        print(row,flush=True)
        if row['status']!='complete':blocked.add(family)
    save(a.work/'RESULTS.json',dict(rows=reports,blocked=sorted(blocked)))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--numa-node',type=int,required=True);p.add_argument('action',choices=('prepare','run'));p.add_argument('--work',type=Path,required=True);p.add_argument('--build',type=Path,required=True);p.add_argument('--family',choices=('both','tree','range'),default='both');p.add_argument('--gpu');p.add_argument('--sanitizer',default='/usr/local/cuda-13.1/bin/compute-sanitizer');a=p.parse_args();assert __debug__;a.work=outside_repo(a.work); (prepare if a.action=='prepare' else run)(a)
