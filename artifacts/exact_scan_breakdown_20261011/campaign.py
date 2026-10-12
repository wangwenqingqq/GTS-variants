#!/usr/bin/env python3
"""Fresh serialized native/control/scaling processes; retain first failure and stop."""
import argparse,csv,fcntl,json,math,os,subprocess,sys,time,traceback
from pathlib import Path
import numpy as np
from prepare import HERE,EXT,read,sources
sys.path.insert(0,str(EXT))
from pruning_value.build import sha,save,outside_repo
from pe_check import check as check_dynamic
if not __debug__:raise RuntimeError('Assertions required')
MODES=['READ_ONLY','DISTANCE_ONLY','THRESHOLD_COUNT','FULL_OUTPUT']

def table(p):
    with Path(p).open() as f:return list(csv.DictReader(f))

def vector(prefix,suffix,dtype):
    p=Path(str(prefix)+suffix);assert p.stat().st_size%np.dtype(dtype).itemsize==0,'partial payload element'
    return np.fromfile(p,dtype)

def metadata(prefix,job,rows):
    old=job['kind']=='keeper';meta=read(str(prefix)+('.static.json' if old else '.meta.json'))
    if old:assert meta['queries']==40 and meta['warmup_per_task']==8 and meta['measured_per_task']==32 and meta['raw_squared_observer_included']
    else:assert (meta['N'],meta['D'],meta['mode'],meta['diagnostic'])==(job['N'],job['D'],job['mode'],bool(job.get('diagnostic',0)))
    for k in ('build_ms','warmup_ms','release_ms','context_ms'):
        assert math.isfinite(float(meta[k])) and float(meta[k])>=0
    pass_ms=float(meta['range_pass_ms'] if old else meta['measured_pass_ms']);values=[float(r['ack_ms']) for r in rows[8:]]
    assert math.isfinite(pass_ms) and pass_ms>0 and pass_ms+1e-5>=sum(values)
    return meta,pass_ms,values

def check_copy(prefix,job,qids):
    rows=table(str(prefix)+'.rows.csv');assert len(rows)==40
    for i,row in enumerate(rows):
        assert int(row['query'])==i and int(row['qid'])==qids[i if i<8 else i-8] and int(row['warmup'])==int(i<8)
        assert int(row['count'])==int(row['offset'])==0
        ack,event=float(row['ack_ms']),float(row['p0']);assert math.isfinite(ack) and math.isfinite(event) and ack>0 and event>0 and ack+1e-4>=event
        assert all(float(row['p'+str(k)])==-1 for k in range(1,7))
    for suffix,dtype in (('.ids.i32','<i4'),('.dist.f32','<f4'),('.native_squared.f64','<f8')):assert len(vector(prefix,suffix,dtype))==0
    meta,pass_ms,values=metadata(prefix,job,rows)
    return dict(passed=True,meta=meta,rows=rows,process_mean_query_ms=sum(values)/32,process_pass_ms=pass_ms,scope='native D2D CUDA-event interval; binary validates first/last endpoints outside timing')

def check_static(prefix,job,w,qids,read_sum):
    old=job['kind']=='keeper';suffix='.queries.csv' if old else '.rows.csv';rows=table(str(prefix)+suffix);assert len(rows)==40
    full=old or job['mode']=='FULL_OUTPUT';N,D,r=job['N'],job['D'],job['radius'];mode=job['mode'];at=0
    ids=vector(prefix,'.ids.i32','<i4');fields=vector(prefix,'.dist.f32','<f4');native=vector(prefix,'.native_squared.f64','<f8')
    assert len(ids)==len(fields)==len(native)
    reports=[]
    for i,row in enumerate(rows):
        qi=i if i<8 else i-8;q=qids[qi];assert int(row['query'])==i and int(row['qid'])==q and int(row['offset'])==at
        if not old:assert int(row['warmup'])==int(i<8)
        assert math.isfinite(float(row['ack_ms'])) and float(row['ack_ms'])>0
        ref=np.memmap(w/'reference'/str(D)/f'{q}.f64',dtype='<f8',mode='r')[:N];expected=np.flatnonzero(ref<=r*r);z=int(row['count'])
        if full:
            actual=ids[at:at+z];f=fields[at:at+z];raw=native[at:at+z];assert np.array_equal(actual,expected),(job['label'],i,'complete IDs')
            assert np.isfinite(f).all() and np.isfinite(raw).all() and (f>=0).all()
            error=max(np.max(np.abs(f.astype(float)**2-ref[actual])/np.maximum(1,ref[actual]),initial=0),np.max(np.abs(raw-ref[actual])/np.maximum(1,ref[actual]),initial=0));assert error<=5e-5
            at+=z
        elif mode=='THRESHOLD_COUNT':assert z==len(expected)
        elif mode in ('READ_ONLY','DISTANCE_ONLY'):
            assert z==0
            actual=float(row['checksum']);target=read_sum if mode=='READ_ONLY' else float(ref.sum());assert np.isfinite(actual) and abs(actual-target)<=1e-4*max(1,abs(target)),(job['label'],i,'aggregate',actual,target)
        reports.append(dict(query=i,qid=q,reference_hit_count=len(expected),delivered_count=z,quality='complete members/fields' if full else 'aggregate-only control'))
    assert at==len(ids)
    if not full:assert len(ids)==0
    meta,pass_ms,values=metadata(prefix,job,rows)
    return dict(passed=True,query_rows=40,measured_rows=32,process_mean_query_ms=sum(values)/32,process_pass_ms=pass_ms,per_query_ms=values,meta=meta,quality=reports,output_hashes={p.name:sha(p) for p in prefix.parent.glob(prefix.name+'.*') if p.is_file()})


def jobs(cal,stage):
    radius=cal['960']['mid']['radius'];base=dict(N=1000000,D=960,radius=radius,kind='probe',diagnostic=0)
    out=[]
    def add(label,mode,**kw):out.append(dict(base,label=label,mode=mode,**kw))
    if stage=='qualification':
        for m in MODES:add('bounded_'+m,m,N=4096)
        for tool in ('memcheck','racecheck','synccheck'):add('read_'+tool,'READ_ONLY',N=4096,tool=tool)
        add('target_full','FULL_OUTPUT')
    elif stage=='keeper':
        for round in range(1,7):add(f'keeper_r{round}','FULL_OUTPUT',kind='keeper',round=round)
    elif stage=='primary':
        for round in range(1,7):
            variants=[(m,m,'probe') for m in MODES]
            if round%2==0:variants.reverse()
            for label,mode,kind in variants:add(f'r{round}_{label}',mode,kind=kind,round=round,order='forward' if round%2 else 'reverse')
    elif stage=='scaling':
        for round in range(1,7):
            cases=[(f'D{d}',1000000,d,cal[str(d)]['mid']['radius']) for d in (128,256,512)]+[(f'N{n}',n,960,radius) for n in (100000,250000,500000)]+[(f'R_{r}',1000000,960,cal['960'][r]['radius']) for r in ('low','high')]+[('bandwidth',1000000,960,radius)]
            if round%2==0:cases.reverse()
            for label,n,d,r in cases:add(f'r{round}_{label}','COPY' if label=='bandwidth' else 'FULL_OUTPUT',N=n,D=d,radius=r,round=round,order='forward' if round%2 else 'reverse')
    elif stage=='dynamic':
        for round in range(1,7):add(f'dynamic_r{round}','FULL_OUTPUT',kind='dynamic',round=round)
    return out


def command_for(w,original,job,prefix,requests,trace):
    if job['kind']=='keeper':cmd=[original['keeper_binary'],original['data'],str(requests),str(prefix)]
    elif job['kind']=='dynamic':cmd=[original['dynamic_keeper_binary'],original['data'],str(trace),str(job['radius']),str(prefix)]
    else:cmd=[str(w/'build/probe'),original['data'],str(w/'qids.txt'),str(job['N']),str(job['D']),str(job['radius']),job['mode'],str(prefix),str(job['diagnostic'])]
    if job.get('tool'):cmd=['/usr/local/cuda-13.1/bin/compute-sanitizer','--tool',job['tool'],'--error-exitcode','97',*cmd]
    return cmd

def verify_stage(w,stage,ready_path,gpu,numa):
    """Follow exact completed job and evidence hashes; a pass boolean is insufficient."""
    root=w/stage;result=read(root/'RESULTS.json');registration=read(root/'REGISTERED.json');ready=read(ready_path)
    assert result['complete'] and result['registration_sha256']==sha(root/'REGISTERED.json')
    assert registration['prepared_sha256']==sha(w/'PREPARED.json') and registration['ready_sha256']==sha(ready_path)
    assert registration['contract_sha256']==ready['contract_sha256']==sha(HERE/'CONTRACT.json')
    assert registration['gpu']==gpu and registration['numa']==numa
    current=sources();assert registration['source_hashes'] and all(current.get(k)==v for k,v in registration['source_hashes'].items())
    expected=jobs(ready['calibration'],stage);assert registration['jobs']==expected
    assert len(result['rows'])==len(expected) and registration['binaries']==read(w/'build/BUILD.json')['binaries']
    for job,row in zip(expected,result['rows']):
        assert all(row[k]==v for k,v in job.items()) and row['status']=='passed'
        checked=root/(job['label']+'.checked.json');guard=root/'guards'/job['label']/'receipt.json'
        assert row['checked_sha256']==sha(checked) and row['guard_sha256']==sha(guard)
        proof=read(checked);receipt=read(guard);command=read(root/(job['label']+'.command.json'))['command']
        assert command==command_for(w,read(w/'REGISTERED.json'),job,root/'outputs'/job['label'],w/'native_requests.txt',registration['trace'])
        assert proof['passed'] and receipt['runtime_valid'] and receipt['gpu']==gpu
        assert receipt['command']==['numactl','--cpunodebind='+str(numa),'--membind='+str(numa),*command]
        assert receipt['binary_sha256']==sha(command[0])
        digests=proof['output_hashes'];actual={p.name for p in (root/'outputs').glob(job['label']+'.*') if p.is_file()};assert digests and set(digests)==actual
        for name,digest in digests.items():assert sha(root/'outputs'/name)==digest
    return registration


def run(a):
    w=outside_repo(a.work);prepared=read(w/'PREPARED.json');ready=read(a.ready);assert prepared['registration_sha256']==sha(w/'REGISTERED.json') and prepared['build_sha256']==sha(w/'build/BUILD.json');assert ready['passed'] and ready['prepared_sha256']==sha(w/'PREPARED.json')
    original=read(w/'REGISTERED.json');assert prepared['qids_sha256']==sha(w/'qids.txt');assert all(sha(w/'build'/k)==h for k,h in read(w/'build/BUILD.json')['binaries'].items() if k!='cpu');cal=ready['calibration'];qids=original['qids'];assert all(sha(w/'reference'/d/p)==h for d,files in prepared['reference_hashes'].items() for p,h in files.items())
    assert sha(original['data'])==original['data_sha256'];assert sha(HERE/'CONTRACT.json')==ready['contract_sha256']
    if a.stage!='qualification':
        prev={'keeper':'qualification','primary':'keeper','scaling':'primary','dynamic':'scaling'}[a.stage]
        verify_stage(w,prev,a.ready,a.gpu,a.numa_node)
    if a.stage=='primary':
        for name in ('nsys_static','ncu'):
            proof=read(w/name/'PROOF.json');assert proof['passed'] and proof['registration_sha256']==sha(w/name/'REGISTERED.json')
            assert read(w/name/'REGISTERED.json')['ready_sha256']==sha(a.ready)
            for file,digest in proof['raw_files'].items():assert sha(w/name/file)==digest
    if a.stage=='dynamic':assert read(w/'STATIC_DECISION.json')['static_complete']
    out=w/a.stage;out.mkdir(exist_ok=False);(out/'outputs').mkdir();selected=jobs(cal,a.stage);env={**os.environ,**original['environment'],'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1'}
    req=w/'native_requests.txt'
    if not req.exists():req.write_text('40\n'+''.join(f'1 {q} {cal["960"]["mid"]["radius"]:.17g} 8\n' for q in qids[:8]+qids))
    reg=dict(before_execution=True,trace=str(a.trace),source_hashes=sources(),contract_sha256=sha(HERE/'CONTRACT.json'),prepared_sha256=sha(w/'PREPARED.json'),ready_sha256=sha(a.ready),jobs=selected,gpu=a.gpu,numa=a.numa_node,binaries=read(w/'build/BUILD.json')['binaries'],keeper_sha256=original['keeper_sha256'],dynamic_keeper_sha256=original['dynamic_keeper_sha256'],registered_unix=time.time());save(out/'REGISTERED.json',reg)
    x=np.memmap(original['data'],dtype='<f4',offset=12,shape=(1000000,960));read_sums={4096:float(x[:4096].sum(dtype=np.float64)),1000000:float(x.sum(dtype=np.float64))} if a.stage in ('primary','qualification') else {};rows=[];failed=False
    lock=(w/'campaign.lock').open('a+');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    for j in selected:
        record={**j,'status':'not_executed_after_stop'};rows.append(record)
        if failed:continue
        try:
            assert reg['source_hashes']==sources();p=out/'outputs'/j['label']
            if j['kind']=='keeper':
                binary=Path(original['keeper_binary']);assert sha(binary)==reg['keeper_sha256']
            elif j['kind']=='dynamic':
                binary=Path(original['dynamic_keeper_binary']);assert sha(binary)==reg['dynamic_keeper_sha256']
            else:
                binary=w/'build/probe';assert sha(binary)==reg['binaries']['probe']
            cmd=command_for(w,original,j,p,req,a.trace)
            save(out/(j['label']+'.command.json'),dict(command=cmd,environment={k:env[k] for k in original['environment']}))
            guard=[sys.executable,str(EXT/'static_guard.py'),'--gpu',a.gpu,'--numa-node',str(a.numa_node),'--output',str(out/'guards'/j['label']),'--',*cmd]
            result=subprocess.run(guard,env=env,capture_output=True,text=True);(out/(j['label']+'.outer.log')).write_text(result.stdout+result.stderr);assert result.returncode==0,'runtime/isolation failure'
            receipt=read(out/'guards'/j['label']/'receipt.json');assert receipt['runtime_valid']
            if j.get('tool'):
                log=''.join((out/'guards'/j['label']/f).read_text() for f in ('stdout.log','stderr.log'));assert 'ERROR SUMMARY: 0 errors' in log or 'RACECHECK SUMMARY: 0 hazards' in log
            if j['kind']=='dynamic':
                quality={}
                for suffix,events in (('',a.trace.parent/'events.txt'),('.warmup',a.trace.parent/'warmup.events')):quality[suffix or 'measured']=check_dynamic(Path(original['data']),events,str(a.trace)+suffix,str(p)+suffix,'E',str(a.dynamic_reference)+suffix)
                checked=dict(passed=True,quality=quality,meta=read(str(p)+'.pe.json'),operations=table(str(p)+'.ops.csv'))
            elif j['mode']=='COPY':checked=check_copy(p,j,qids)
            else:checked=check_static(p,j,w,qids,read_sums.get(j['N']))
            checked['output_hashes']={f.name:sha(f) for f in p.parent.glob(p.name+'.*') if f.is_file()}
            save(out/(j['label']+'.checked.json'),checked);record.update(status='passed',checked_sha256=sha(out/(j['label']+'.checked.json')),guard_sha256=sha(out/'guards'/j['label']/'receipt.json'))
            print('PASSED',j['label'],flush=True)
        except Exception as e:
            failed=True;record.update(status='failed',reason=repr(e),traceback=traceback.format_exc());print('STOP',j['label'],repr(e),flush=True)
        # Append progress without rewriting any individual evidence or registration.
        progress=out/f'PROGRESS_{len(rows):03d}.json';save(progress,dict(rows=list(rows),failed=failed))
    assert reg['source_hashes']==sources();assert sha(original['data'])==original['data_sha256'];save(out/'RESULTS.json',dict(complete=not failed,rows=rows,registration_sha256=sha(out/'REGISTERED.json')))
    if failed:raise SystemExit(1)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--stage',choices=['qualification','keeper','primary','scaling','dynamic'],required=True);p.add_argument('--gpu',required=True);p.add_argument('--numa-node',type=int,required=True)
    for k in ('work','ready','trace','dynamic-reference'):p.add_argument('--'+k,type=Path,required=True)
    run(p.parse_args())
