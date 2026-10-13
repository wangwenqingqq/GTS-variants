"""Serialized, append-only Gate2 qualification/timing/all-kernel diagnostics."""
import argparse,csv,fcntl,importlib.util,json,math,os,subprocess,sys,time,traceback
from pathlib import Path
import numpy as np
from prepare import HERE,ART,read,save,sha,sources
from analyze import summarize
if not __debug__:raise RuntimeError('Assertions required')
STAGES=('qualification','primary','ncu','breakdown','nsys')
METRICS=read(HERE/'CONTRACT.json')['diagnostics']['metrics']
def jobs(stage,w):
    if stage=='qualification':
        return [dict(label='fixtures',mode='P1',kind='fixtures'),dict(label='bounded_P1',mode='P1',N=4096,diag=2),dict(label='target_B1',mode='B1',N=1000000),dict(label='target_P1',mode='P1',N=1000000,diag=2),dict(label='bounded_B0',mode='B0',N=4096)]+[dict(label=kind+'_'+tool,mode='P1',kind='fixtures',tool=tool) if kind=='fixtures' else dict(label=kind+'_'+tool,mode='P1',N=4096,diag=2,tool=tool) for kind in ('fixtures','bounded') for tool in ('memcheck','racecheck','synccheck')]
    if stage=='primary':return [dict(label=f'r{r}_{m}',mode=m,N=1000000,round=r,order='forward' if r%2 else 'reverse') for r in range(1,7) for m in (['B0','B1','P1'] if r%2 else ['P1','B1','B0'])]
    if stage=='ncu':return [dict(label=m,mode=m,N=1000000,diag=1,tool='ncu') for m in ('B1','P1')]
    if stage=='breakdown':return [dict(label='P1_events',mode='P1',N=1000000,diag=3)]
    assert stage=='nsys'
    rows=read(w/'primary/RESULTS.json')['rows'];pairs=[]
    for r in range(1,7):pairs.append({m:read(w/'primary'/(f'r{r}_{m}.checked.json'))['mean_query_ms'] for m in ('B0','B1','P1')})
    stats=summarize(pairs)
    return [dict(label='P1_trace',mode='P1',N=1000000,diag=1,tool='nsys')] if stats['latency_ratio']>.80 or stats['paired_95_CI'][1]>=.90 else []
def table(p):
    with Path(p).open() as f:return list(csv.DictReader(f))
def checkpoint_ids(path,want):
    assert Path(path).stat().st_size==len(want)*4,'complete checkpoint payload length'
    assert np.array_equal(np.fromfile(path,dtype='<i4'),want),'complete checkpoint IDs'
def legacy_quality(prefix,job,reg):
    spec=importlib.util.spec_from_file_location('legacy_gate0',ART/'non_padded_b1_baseline_20261012/campaign.py');legacy=importlib.util.module_from_spec(spec);spec.loader.exec_module(legacy)
    old=read(Path(reg['keeper_directory'])/'REGISTERED.json')
    return legacy.quality(prefix,{**job,'mode':'R0' if job['mode']=='B0' else 'N1','diagnostic':job.get('diag',0)},Path(reg['keeper_directory']),old)
def p1_quality(prefix,job,reg):
    n=job['N'];rows=table(str(prefix)+'.rows.csv');inv=table(str(prefix)+'.invocations.csv');meta=read(str(prefix)+'.meta.json')
    assert len(rows)==len(inv)==40
    assert meta['N']==n and meta['D']==960 and meta['B']==1
    assert meta['diagnostic']==bool(job.get('diag',0)) and meta['diagnostic_mode']==job.get('diag',0)
    for k,v in dict(squared_bytes=0,state_buffer_bytes=32*n,flags_bytes=n,output_capacity_bytes=16*n,count_bytes=4,query_bytes=3840).items():assert meta[k]==v,('actual allocation',k)
    assert meta['select_workspace_bytes']>0
    values=[float(r['ack_ms']) for r in inv[8:]]
    assert all(math.isfinite(v) and v>0 for v in values)
    assert math.isfinite(meta['measured_pass_ms']) and meta['measured_pass_ms']+1e-5>=sum(values)
    payloads={};vectors=[]
    for suffix,dtype in (('.ids.i32','<i4'),('.dist.f32','<f4'),('.native_squared.f64','<f8')):
        path=Path(str(prefix)+suffix);assert path.stat().st_size%np.dtype(dtype).itemsize==0
        vectors.append(np.fromfile(path,dtype));payloads[suffix]=sha(path)
    ids,fields,native=vectors;assert len(ids)==len(fields)==len(native)
    expected={};margin=None
    for q in reg['q32']:
        full=np.memmap(Path(reg['reference'])/f'{q}.f64',dtype='<f8',mode='r')[:n]
        hit=np.flatnonzero(full<=reg['radius']**2);expected[q]=(hit,np.array(full[hit]))
        gap=float(np.min(np.abs(full-reg['radius']**2)));margin=gap if margin is None else min(margin,gap)
    at=0;counts=[];maxerror=0.
    for i,r in enumerate(rows):
        q=reg['q32'][i if i<8 else i-8]
        assert int(r['qid'])==q and int(r['warmup'])==int(i<8) and int(r['invocation'])==i and int(r['query_in_batch'])==0
        assert int(inv[i]['invocation'])==i and int(inv[i]['warmup'])==int(i<8) and int(inv[i]['B'])==1
        z=int(r['count']);assert z>=0 and int(r['offset'])==at and at+z<=len(ids)
        hit,score=expected[q];actual=ids[at:at+z];f=fields[at:at+z];v=native[at:at+z]
        assert np.array_equal(actual,hit),('complete membership/order',job['label'],i,q)
        assert np.isfinite(f).all() and np.isfinite(v).all() and (f>=0).all() and (v>=0).all()
        assert np.array_equal(v,score.astype('<f4').astype('<f8')),'P1 retained hit ordered replay and exact FP32 observer'
        error=float(np.max(np.abs(f.astype(float)**2-score)/np.maximum(1,score),initial=0));assert error<=5e-5
        maxerror=max(maxerror,error);at+=z;counts.append(z)
    assert at==len(ids)
    return dict(passed=True,mode='P1',N=n,queries=40,measured_queries=32,all_complete_members=True,false_negatives=0,false_positives=0,max_ordered_FP64_field_error=maxerror,min_ordered_boundary_margin=margin,counts=counts,mean_query_ms=sum(values)/32,query_ack_ms=values,pass_ms=meta['measured_pass_ms'],meta=meta,payload_hashes=payloads)
def quality(prefix,job,reg,w):
    if job['mode']!='P1':
        checked=legacy_quality(prefix,job,reg);checked['mode']=job['mode'];return checked
    checked=p1_quality(prefix,job,reg)
    rows=table(str(prefix)+'.stages.csv');assert len(rows)==160
    identity=read(ART/'exact_representation_gate1_20261012/evidence/RAW_IDENTITY.json')['files']
    expected={};counts=[];replay=[];n=job['N'];cutoff=reg['radius']**2
    for q in reg['q32']:
        p=Path(reg['gate1_directory'])/'raw'/f'{q}.required.u16';assert sha(p)==identity[p.name]['sha256']
        dims=np.memmap(p,dtype='<u2',mode='r')[:n]
        full=np.memmap(Path(reg['reference'])/f'{q}.f64',dtype='<f8',mode='r')[:n]
        expected[q]=[np.flatnonzero(dims>k).astype('<i4') if k<960 else np.flatnonzero(full<=cutoff).astype('<i4') for k in (128,256,512,960)]
    for i in range(40):
        q=reg['q32'][i if i<8 else i-8];active=n;cs=[];rs=[]
        for s in range(4):
            r=rows[i*4+s];assert int(r['invocation'])==i and int(r['stage'])==s+1
            want=expected[q][s];assert int(r['input'])==active and int(r['output'])==len(want)
            if job.get('diag')==2:
                checkpoint_ids(str(prefix)+f'.checkpoint.{i}.{s+1}.i32',want)
            value=int(r['replay_coordinates']);assert value>=0 and value%(128,256,512,960)[s]==0
            cs.append(len(want));rs.append(value);active=len(want)
        counts.append(cs);replay.append(rs)
    checked['checkpoint_counts']=counts;checked['checkpoint_complete_IDs_checked']=job.get('diag')==2
    checked['replay_coordinates']=replay if job.get('diag')==2 else None
    if n==1000000:
        keeper=w/'qualification/outputs/target_B1'
        ids=np.fromfile(str(prefix)+'.ids.i32','<i4');kid=np.fromfile(str(keeper)+'.ids.i32','<i4');assert np.array_equal(ids,kid)
        score=np.fromfile(str(keeper)+'.native_squared.f64','<f8');candidate=np.fromfile(str(prefix)+'.native_squared.f64','<f8')
        err=float(np.max(np.abs(candidate-score)/np.maximum(1,score),initial=0));assert err<=5e-5;checked['same_campaign_B1_score_error']=err
    if job.get('diag')==2:
        upper=read(HERE/'cost/REPLAY_SCREEN.json')['rows']
        for i in range(40):
            ui=i if i<8 else i-8
            assert all(replay[i][s]<=(128,256,512,960)[s]*upper[ui]['replay_upper_counts'][s] for s in range(4))
    checked['output_hashes']={p.name:sha(p) for p in prefix.parent.glob(prefix.name+'.*') if p.is_file()}
    return checked
def prepared(w):
    reg=read(w/'REGISTERED.json');ready=read(w/'READY.json')
    assert ready['passed'] and ready['registration_sha256']==sha(w/'REGISTERED.json')
    assert sources()==ready['source_hashes']==reg['source_hashes']
    assert reg['contract_sha256']==sha(HERE/'CONTRACT.json')
    assert reg['dependency_preflight_sha256']==sha(w/'DEPENDENCY_PREFLIGHT.json')
    preflight=read(w/'DEPENDENCY_PREFLIGHT.json');assert preflight['passed'] and preflight['CUDA_initializations']==0
    assert all(reg['source_hashes'][k]==v for k,v in preflight['source_hashes'].items())
    assert sha(reg['keeper_binary'])==reg['keeper_sha256'] and sha(reg['readonly_binary'])==reg['readonly_sha256']
    for name,h in ready['binaries'].items():assert sha(w/'build'/name)==h
    for name,h in reg['generated_sources'].items():assert sha(w/'build'/name)==h
    if reg['recovery']:
        prior=Path(reg['recovery']['prior_work']);recovery=reg['recovery']
        assert recovery['human_approved'] and recovery['prior_ledger_sha256']==sha(prior/'STARTS.jsonl') and recovery['prior_failure_sha256']==sha(prior/'qualification/RESULTS.json')
    assert sha(reg['data'])==reg['data_sha256']
    for name,h in reg['reference_hashes'].items():assert sha(Path(reg['reference'])/name)==h
    return reg
def validate_static_record(record,registration_sha256,binaries,tool_sha256):
    assert record['passed'] and record['no_GPU_starts'] and record['registration_sha256']==registration_sha256
    assert record['static_tool_sha256']==tool_sha256
    assert set(record['records'])==set(binaries)
    for name,h in binaries.items():assert record['records'][name]['container_sha256']==h
def static_gate(w,reg):
    record=read(w/'build/STATIC.json');ready=read(w/'READY.json')
    validate_static_record(record,sha(w/'REGISTERED.json'),dict(keeper=reg['keeper_sha256'],**ready['binaries']),sha(HERE/'static_evidence.py'))
    for name,row in record['records'].items():
        assert sha(w/'build'/(name+'.sass.txt'))==row['sass_dump_sha256'] and sha(w/'build'/(name+'.resources.txt'))==row['resources_sha256']
def validate_job_rows(actual,expected):
    assert len(actual)==len(expected)
    keys=set().union(*(set(j) for j in expected)) if expected else set()
    for row,job in zip(actual,expected):
        assert {k:v for k,v in row.items() if k in keys}==job and row['status']=='passed','exact registered job/order required'
def checked_identity(checked,job):
    assert checked['passed'] and checked['job']==job
    if job.get('kind')=='fixtures':
        assert checked['iterations']==100 and checked['stream_slots']==2 and checked['empty_answers']>0 and checked['exact_boundary_pairs']>0
        assert len(checked['stage_rejects'])==4 and all(checked['stage_rejects']) and checked['subnormal_cases']
    else:
        assert checked['mode']==job['mode'] and checked['N']==job['N'] and checked['queries']==40 and checked['measured_queries']==32
        if job['mode']!='B0':assert checked['all_complete_members'] and checked['false_negatives']==checked['false_positives']==0
        if job['mode']=='P1':assert checked['checkpoint_complete_IDs_checked']==(job.get('diag')==2)
    if job.get('tool') in ('memcheck','racecheck','synccheck'):assert checked['sanitizer_summary_zero']
def guard_identity(p,job,w,reg):
    guard=p/'guards'/job['label'];receipt=read(guard/'receipt.json')
    cmd=command(job,w,reg,p/'outputs'/job['label'],p/'reports'/job['label'])
    want=['numactl',f"--cpunodebind={reg['numa']}",f"--membind={reg['numa']}",*cmd]
    assert read(p/(job['label']+'.command.json'))==dict(command=cmd)
    assert read(guard/'command.json')==want and receipt['command']==want
    assert receipt['gpu']==reg['gpu'] and receipt['binary_sha256']==sha(cmd[0])
    assert receipt['runtime_valid'] and receipt['exit_code']==0 and receipt['stop_reason'] is None and receipt['observer']=='two-sided-starttime-v1'
    for name in ('before','after'):
        snapshot=read(guard/(name+'.json'));assert not snapshot['apps'] and snapshot['device'].split(',')[1].strip()==reg['gpu']
def previous(w,stage):
    p=w/stage;r=read(p/'RESULTS.json');registration=read(p/'REGISTERED.json');reg=read(w/'REGISTERED.json')
    assert r['complete'] and r['registration_sha256']==sha(p/'REGISTERED.json') and registration['source_hashes']==sources()
    assert registration['ready_sha256']==sha(w/'READY.json') and registration['gpu']==reg['gpu'] and registration['numa']==reg['numa']
    assert registration['static_sha256']==sha(w/'build/STATIC.json')
    assert registration['jobs']==jobs(stage,w);validate_job_rows(r['rows'],registration['jobs'])
    for row,job in zip(r['rows'],registration['jobs']):
        assert row['status']=='passed';guard=p/'guards'/row['label']/'receipt.json';check=p/(row['label']+'.checked.json')
        assert sha(guard)==row['guard_sha256'] and read(guard)['runtime_valid'] and sha(check)==row['checked_sha256'] and read(check)['passed']
        guard_identity(p,job,w,reg);checked_identity(read(check),job)
        for name,h in row['guard_hashes'].items():assert sha(guard.parent/name)==h
        for name,h in read(check).get('output_hashes',{}).items():assert sha(p/'outputs'/name)==h
        for name,h in row['report_hashes'].items():assert sha(p/'reports'/name)==h
def command(job,w,reg,prefix,report):
    mode=job['mode'];diag=str(job.get('diag',0))
    binary=w/'build/candidate' if mode=='P1' else w/'build/keeper_diagnostic' if job.get('tool')=='ncu' else Path(reg['keeper_binary'])
    if job.get('kind')=='fixtures':cmd=[str(binary),'--fixtures']
    elif mode=='B0':cmd=[reg['readonly_binary'],reg['data'],str(w/'pool32.txt'),str(job['N']),'960',str(reg['radius']),'READ_ONLY',str(prefix),diag]
    else:cmd=[str(binary),reg['data'],str(w/'pool32.txt'),str(job['N']),'1',str(reg['radius']),str(prefix),diag]
    tool=job.get('tool')
    if tool in ('memcheck','racecheck','synccheck'):cmd=['/usr/local/cuda-13.1/bin/compute-sanitizer','--tool',tool,'--error-exitcode','97',*cmd]
    if tool=='ncu':cmd=['/usr/bin/sudo','-n','env','CUDA_VISIBLE_DEVICES='+reg['gpu'],'LD_LIBRARY_PATH='+reg['environment']['LD_LIBRARY_PATH'],'/usr/local/bin/ncu','--profile-from-start','off','--kernel-name-base','demangled','--cache-control','none','--clock-control','none','--section','LaunchStats','--metrics',','.join(METRICS),'-o',str(report),*cmd]
    if tool=='nsys':cmd=['/usr/local/bin/nsys','profile','--trace=cuda,nvtx','--sample=none','--cpuctxsw=none','--capture-range=cudaProfilerApi','--capture-range-end=repeat:32','--cuda-memory-usage=false','--force-overwrite=false','-o',str(report),*cmd]
    return cmd
def run(a):
    w=a.work.resolve();reg=prepared(w);assert a.gpu==reg['gpu'] and a.numa==reg['numa']
    static_gate(w,reg)
    for s in STAGES[:STAGES.index(a.stage)]:previous(w,s)
    p=w/a.stage;p.mkdir(exist_ok=False)
    for name in ('outputs','guards','reports'):(p/name).mkdir()
    registration=dict(before_GPU=True,source_hashes=sources(),ready_sha256=sha(w/'READY.json'),static_sha256=sha(w/'build/STATIC.json'),gpu=a.gpu,numa=a.numa,jobs=jobs(a.stage,w),registered_unix=time.time());save(p/'REGISTERED.json',registration)
    rows=[]
    with (w/'campaign.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        for job in registration['jobs']:
            row={**job,'status':'not_executed'};rows.append(row)
            try:
                assert sources()==registration['source_hashes']
                ledger=w/'STARTS.jsonl';count=len(ledger.read_text().splitlines()) if ledger.exists() else 0;assert count<33
                recovery=reg['recovery'];prior_starts=recovery['prior_starts'] if recovery else 0
                assert count+prior_starts<(recovery['max_total_starts'] if recovery else 33)
                prefix=p/'outputs'/job['label'];report=p/'reports'/job['label'];cmd=command(job,w,reg,prefix,report)
                save(p/(job['label']+'.command.json'),dict(command=cmd))
                with ledger.open('a') as f:f.write(json.dumps(dict(start=count+1,global_start=prior_starts+count+1,stage=a.stage,label=job['label'],command_sha256=sha(p/(job['label']+'.command.json')),started_unix=time.time()))+'\n')
                guard=[sys.executable,str(ART/'external_closure/static_guard.py'),'--gpu',a.gpu,'--numa-node',str(a.numa),'--output',str(p/'guards'/job['label']),'--',*cmd]
                with (p/(job['label']+'.outer.log')).open('x') as log:subprocess.run(guard,env={**os.environ,**reg['environment']},stdout=log,stderr=log,check=True)
                receipt=p/'guards'/job['label']/'receipt.json';assert read(receipt)['runtime_valid']
                guard_identity(p,job,w,reg)
                if job.get('kind')=='fixtures':
                    stdout=(p/'guards'/job['label']/'stdout.log').read_text();checked=next(json.loads(s) for s in reversed(stdout.splitlines()) if s.startswith('{'))
                    assert checked['passed'] and checked['iterations']==100 and checked['stream_slots']==2 and all(checked['stage_rejects'])
                else:checked=quality(prefix,job,reg,w)
                if job.get('tool') in ('memcheck','racecheck','synccheck'):
                    logs=''.join((p/'guards'/job['label']/n).read_text() for n in ('stdout.log','stderr.log'))
                    assert 'ERROR SUMMARY: 0 errors' in logs or 'RACECHECK SUMMARY: 0 hazards' in logs
                    checked['sanitizer_summary_zero']=True
                checked['job']=job;checked_identity(checked,job)
                if job.get('tool')=='ncu':
                    with Path(str(report)+'.base.csv').open('x') as out:subprocess.run(['/usr/local/bin/ncu','--import',str(report)+'.ncu-rep','--page','raw','--csv','--print-units','base'],env={**os.environ,**reg['environment']},stdout=out,check=True)
                if job.get('tool')=='nsys':
                    reports=sorted(p.glob('reports/*.nsys-rep'));assert reports
                    for rep in reports:subprocess.run(['/usr/local/bin/nsys','export','--type=sqlite','--output',str(rep)+'.sqlite',str(rep)],check=True)
                save(p/(job['label']+'.checked.json'),checked)
                row.update(status='passed',guard_sha256=sha(receipt),guard_hashes={x.name:sha(x) for x in receipt.parent.iterdir() if x.is_file()},checked_sha256=sha(p/(job['label']+'.checked.json')),report_hashes={x.name:sha(x) for x in (p/'reports').glob(job['label']+'*') if x.is_file()})
                save(p/'PROGRESS.json',dict(rows=rows));print('PASSED',a.stage,job['label'],flush=True)
            except Exception:
                row.update(status='failed',error=traceback.format_exc());save(p/'RESULTS.json',dict(complete=False,rows=rows,registration_sha256=sha(p/'REGISTERED.json'),stop='first failure;no automatic retry'));raise
    assert sources()==registration['source_hashes'];save(p/'RESULTS.json',dict(complete=True,rows=rows,registration_sha256=sha(p/'REGISTERED.json'),conditional_skip=not bool(rows)))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);p.add_argument('--stage',choices=STAGES,required=True)
    p.add_argument('--gpu',required=True);p.add_argument('--numa',type=int,required=True);run(p.parse_args())
