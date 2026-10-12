"""Fail-closed serialized batch campaign; original successful observations are never replaced."""
import argparse
import csv
import fcntl
import json
import math
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time
import traceback
import numpy as np
from prepare import HERE, EXT, read, save, sha, sources

if not __debug__: raise RuntimeError('Assertions required')
BS = [1,2,4,8,16,32,64,128]
STAGES = ['qualification','keeper','primary','ncu']

def jobs(stage):
    if stage == 'qualification':
        return [dict(label=f'bounded_B{b}',B=b,N=4096,kind='batch',diagnostic=0) for b in BS]+[
            dict(label=f'B128_{t}',B=128,N=4096,kind='batch',tool=t,diagnostic=0)
            for t in ('memcheck','racecheck','synccheck')]+[
            dict(label='target_B1',B=1,N=1000000,kind='batch',diagnostic=0),
            dict(label='target_B128_nsys',B=128,N=1000000,kind='batch',tool='nsys',diagnostic=1)]
    if stage == 'keeper':
        return [dict(label=f'keeper_r{r}',B=1,N=1000000,kind='keeper',round=r,diagnostic=0) for r in range(1,7)]
    if stage == 'primary':
        return [dict(label=f'r{r}_B{b}',B=b,N=1000000,kind='batch',round=r,order='forward' if r%2 else 'reverse',diagnostic=0) for r in range(1,7) for b in (BS if r%2 else list(reversed(BS)))]
    return [dict(label=f'B{b}',B=b,N=1000000,kind='batch',tool='ncu',diagnostic=1) for b in BS]

def table(path):
    with Path(path).open() as f:return list(csv.DictReader(f))

def vector(prefix,suffix,dtype):
    p=Path(str(prefix)+suffix);assert p.stat().st_size%np.dtype(dtype).itemsize==0,'partial payload'
    return np.fromfile(p,dtype)

def check(prefix,job,w,reg):
    B,N=job['B'],job['N'];pool=reg['q32'] if B<=32 else reg['q128'];old=job['kind']=='keeper'
    if old:
        original=table(str(prefix)+'.queries.csv');assert len(original)==40
        rows=[dict(invocation=i,query_in_batch=0,qid=r['qid'],warmup=int(i<8),count=r['count'],offset=r['offset']) for i,r in enumerate(original)]
        inv=[dict(invocation=i,warmup=int(i<8),B=1,ack_ms=r['ack_ms']) for i,r in enumerate(original)]
        meta=read(str(prefix)+'.static.json');assert meta['queries']==40 and meta['warmup_per_task']==8 and meta['measured_per_task']==32 and meta['raw_squared_observer_included'];pass_ms=meta['range_pass_ms']
    else:
        rows=table(str(prefix)+'.rows.csv');inv=table(str(prefix)+'.invocations.csv');meta=read(str(prefix)+'.meta.json')
        assert (meta['N'],meta['D'],meta['B'],meta['diagnostic'])==(N,960,B,bool(job['diagnostic']))
        assert meta['squared_bytes']==N*B*4 and meta['query_bytes']==B*960*4
        pass_ms=meta['measured_pass_ms']
    assert len(rows)==40*B and len(inv)==40
    for name in ('build_ms','warmup_ms','release_ms','context_ms'):assert math.isfinite(meta[name]) and meta[name]>=0
    for i,r in enumerate(inv):
        assert int(r['invocation'])==i and int(r['warmup'])==int(i<8) and int(r['B'])==B
        assert math.isfinite(float(r['ack_ms'])) and float(r['ack_ms'])>0
    values=[float(r['ack_ms']) for r in inv[8:]]
    assert math.isfinite(pass_ms) and pass_ms>0 and pass_ms+1e-5>=sum(values)
    ids=vector(prefix,'.ids.i32','<i4');fields=vector(prefix,'.dist.f32','<f4');native=vector(prefix,'.native_squared.f64','<f8')
    assert len(ids)==len(fields)==len(native)
    expected={}
    for q in pool:
        v=np.memmap(w/'reference'/f'{q}.f64',dtype='<f8',mode='r')[:N]
        hit=np.flatnonzero(v<=reg['radius']**2);expected[q]=(hit,np.array(v[hit]))
    at=0;max_error=0.0;counts=[]
    for k,r in enumerate(rows):
        i,j=divmod(k,B);start=(i if i<8 else i-8)*B%len(pool);qid=pool[start+j]
        assert int(r['invocation'])==i and int(r['query_in_batch'])==j and int(r['qid'])==qid and int(r['warmup'])==int(i<8)
        z=int(r['count']);assert int(r['offset'])==at and z>=0 and at+z<=len(ids)
        hit,score=expected[qid];actual=ids[at:at+z];f=fields[at:at+z];v=native[at:at+z]
        assert np.array_equal(hit,actual),('complete members',job['label'],i,j,qid)
        assert np.isfinite(f).all() and np.isfinite(v).all() and (f>=0).all()
        error=max(np.max(np.abs(f.astype(float)**2-score)/np.maximum(1,score),initial=0),np.max(np.abs(v-score)/np.maximum(1,score),initial=0));assert error<=5e-5
        max_error=max(max_error,float(error));at+=z;counts.append(z)
    assert at==len(ids)
    payload_hashes={suffix:sha(str(prefix)+suffix) for suffix in ('.ids.i32','.dist.f32','.native_squared.f64')}
    if B==1 and N==1000000:
        prior=read(HERE.parent/'exact_scan_breakdown_20261011/evidence/NATIVE_IDENTITY.json')['payloads']
        assert all(v==prior[k]['sha256'] for k,v in payload_hashes.items()),'B1 original payload identity'
    return dict(passed=True,all_complete_members=True,max_native_scale_error=max_error,B1_original_payload_identity=B==1 and N==1000000,mean_invocation_ms=sum(values)/32,mean_query_ms=sum(values)/32/B,pass_ms=pass_ms,invocation_ms=values,mean_measured_hits=float(np.mean(counts[8*B:])),meta=meta,payload_hashes=payload_hashes,output_hashes={p.name:sha(p) for p in prefix.parent.glob(prefix.name+'.*') if p.is_file()})

def verify_prepared(w):
    reg=read(w/'REGISTERED.json');ready=read(w/'READY.json');build=read(w/'build/BUILD.json')
    assert ready['passed'] and ready['registration_sha256']==build['registration_sha256']==sha(w/'REGISTERED.json')
    assert ready['contract_sha256']==reg['contract_sha256']==sha(HERE/'CONTRACT.json') and ready['source_hashes']==reg['source_hashes']==sources()
    assert ready['build_sha256']==sha(w/'build/BUILD.json') and sha(w/'build/batch')==build['binary_sha256'] and sha(reg['keeper_binary'])==reg['keeper_sha256']
    assert sha(reg['data'])==reg['data_sha256']
    for name,h in ready['pool_hashes'].items():assert sha(w/name)==h
    for name,h in ready['reference_hashes'].items():assert sha(w/'reference'/name)==h
    return reg,ready,build

def verify_stage(w,stage,gpu,numa):
    p=w/stage;registration=read(p/'REGISTERED.json');result=read(p/'RESULTS.json')
    assert result['complete'] and result['registration_sha256']==sha(p/'REGISTERED.json')
    assert registration['jobs']==jobs(stage) and registration['source_hashes']==sources() and registration['gpu']==gpu and registration['numa']==numa and registration['READY_sha256']==sha(w/'READY.json')
    assert len(result['rows'])==len(registration['jobs'])
    for job,row in zip(registration['jobs'],result['rows']):
        assert all(row[k]==v for k,v in job.items()) and row['status']=='passed'
        guard=p/'guards'/job['label']/'receipt.json';checked=p/(job['label']+'.checked.json')
        assert row['guard_sha256']==sha(guard) and row['checked_sha256']==sha(checked)
        g=read(guard);c=read(checked);assert g['runtime_valid'] and c['passed'] and g['gpu']==gpu
        original=read(w/'REGISTERED.json');assert read(p/'guards'/job['label']/'before.json')['device'].split(',')[1].strip()==original['GPU_UUID']
        for name,h in row['report_hashes'].items():assert sha(p/'reports'/name)==h
        assert g['command']==read(p/(job['label']+'.command.json'))['guarded_command']
        actual={x.name for x in (p/'outputs').glob(job['label']+'.*') if x.is_file()}
        assert set(c['output_hashes'])==actual
        for name,h in c['output_hashes'].items():assert sha(p/'outputs'/name)==h

def command(w,job,reg,prefix,report):
    if job['kind']=='keeper':cmd=[reg['keeper_binary'],reg['data'],str(w/'native_requests.txt'),str(prefix)]
    else:cmd=[str(w/'build/batch'),reg['data'],str(w/('pool32.txt' if job['B']<=32 else 'pool128.txt')),str(job['N']),str(job['B']),str(reg['radius']),str(prefix),str(job['diagnostic'])]
    if job.get('tool') in ('memcheck','racecheck','synccheck'):
        return ['/usr/local/cuda-13.1/bin/compute-sanitizer','--tool',job['tool'],'--error-exitcode','97',*cmd]
    if job.get('tool')=='nsys':
        return ['/usr/local/bin/nsys','profile','--trace=cuda,nvtx','--sample=none','--cpuctxsw=none','--capture-range=cudaProfilerApi','--capture-range-end=stop','-o',str(report),*cmd]
    if job.get('tool')=='ncu':
        metrics=read(HERE/'CONTRACT.json').get('metrics')
        assert metrics
        return ['/usr/bin/sudo','-n','env','CUDA_VISIBLE_DEVICES='+reg['gpu'],'LD_LIBRARY_PATH='+reg['environment']['LD_LIBRARY_PATH'],'/usr/local/bin/ncu','--profile-from-start','off','--kernel-name-base','demangled','--kernel-name','regex:.*(pairwise|distance).*','--cache-control','none','--clock-control','none','--section','LaunchStats','--metrics',','.join(metrics),'-o',str(report),*cmd]
    return cmd

def run(a):
    w=a.work.resolve();reg,ready,build=verify_prepared(w);assert reg['gpu']==a.gpu and reg['numa']==a.numa
    for stage in STAGES[:STAGES.index(a.stage)]:verify_stage(w,stage,a.gpu,a.numa)
    p=w/a.stage;p.mkdir(exist_ok=False);(p/'outputs').mkdir();(p/'reports').mkdir();(p/'guards').mkdir()
    env={**os.environ,**reg['environment'],'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1'}
    register=dict(before_execution=True,source_hashes=sources(),READY_sha256=sha(w/'READY.json'),jobs=jobs(a.stage),gpu=a.gpu,numa=a.numa,binary_sha256=build['binary_sha256'],registered_unix=time.time())
    save(p/'REGISTERED.json',register);rows=[]
    with (w/'campaign.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        for job in register['jobs']:
            item={**job,'status':'not_executed'};rows.append(item)
            try:
                assert register['source_hashes']==sources()
                ledger=w/'STARTS.jsonl';previous=ledger.read_text().splitlines() if ledger.exists() else []
                assert len(previous)<80,'hard process budget'
                prefix=p/'outputs'/job['label'];report=p/'reports'/job['label'];cmd=command(w,job,reg,prefix,report)
                guarded=['numactl','--cpunodebind='+str(a.numa),'--membind='+str(a.numa),*cmd]
                save(p/(job['label']+'.command.json'),dict(command=cmd,guarded_command=guarded))
                with ledger.open('a') as f:f.write(json.dumps(dict(start=len(previous)+1,stage=a.stage,label=job['label'],command_sha256=sha(p/(job['label']+'.command.json')),registered_unix=time.time()))+'\n')
                guard=[sys.executable,str(EXT/'static_guard.py'),'--gpu',a.gpu,'--numa-node',str(a.numa),'--output',str(p/'guards'/job['label']),'--',*cmd]
                with (p/(job['label']+'.outer.log')).open('x') as f:subprocess.run(guard,env=env,stdout=f,stderr=f,check=True)
                receipt=p/'guards'/job['label']/'receipt.json';assert read(receipt)['runtime_valid']
                assert read(p/'guards'/job['label']/'before.json')['device'].split(',')[1].strip()==reg['GPU_UUID']
                checked=check(prefix,job,w,reg);save(p/(job['label']+'.checked.json'),checked)
                if job.get('tool')=='nsys':
                    subprocess.run(['/usr/local/bin/nsys','export','--type','sqlite','--output',str(report)+'.sqlite',str(report)+'.nsys-rep'],env=env,check=True,capture_output=True)
                    con=sqlite3.connect(str(report)+'.sqlite');names=[(n,c) for n,c in con.execute('select s.value,count(*) from CUPTI_ACTIVITY_KIND_KERNEL k join StringIds s on k.demangledName=s.id group by s.value')];con.close()
                    native=[(n,c) for n,c in names if 'pairwise' in n.lower() or 'distance' in n.lower()];assert native and sum(c for _,c in native)==1,'native invocation launch coverage';save(p/'NATIVE_LAUNCH_INVENTORY.json',dict(names=names,native=native,scope='one full-N B128 selected invocation'))
                if job.get('tool')=='ncu':
                    with (Path(str(report)+'.base.csv')).open('x') as f:subprocess.run(['/usr/local/bin/ncu','--import',str(report)+'.ncu-rep','--page','raw','--csv','--print-units','base'],stdout=f,env=env,check=True)
                    with (Path(str(report)+'.sass.txt')).open('x') as f:subprocess.run(['/usr/local/bin/ncu','--import',str(report)+'.ncu-rep','--page','source','--print-source','sass'],stdout=f,env=env,check=True)
                    parsed=list(csv.reader(Path(str(report)+'.base.csv').read_text().splitlines()));assert len(parsed)==3,'selected invocation native launch coverage';assert parsed[2][parsed[0].index('Kernel Name')]=='pairwise_matrix_kernel'
                item.update(status='passed',checked_sha256=sha(p/(job['label']+'.checked.json')),guard_sha256=sha(receipt),report_hashes={x.name:sha(x) for x in (p/'reports').glob(job['label']+'.*') if x.is_file()})
                save(p/f'PROGRESS_{len(rows):03}.json',dict(rows=rows));print('PASSED',a.stage,job['label'],flush=True)
            except Exception:
                item.update(status='failed',error=traceback.format_exc());save(p/'RESULTS.json',dict(complete=False,rows=rows,registration_sha256=sha(p/'REGISTERED.json'),stop='first failure; no automatic retry'));raise
    save(p/'RESULTS.json',dict(complete=True,rows=rows,registration_sha256=sha(p/'REGISTERED.json')))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);p.add_argument('--stage',choices=STAGES,required=True);p.add_argument('--gpu',required=True);p.add_argument('--numa',type=int,required=True);run(p.parse_args())
