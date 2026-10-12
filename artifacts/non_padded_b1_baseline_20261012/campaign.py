"""Serialized fail-closed qualification, paired ACK and independent diagnostic stages."""
import argparse,csv,fcntl,json,math,os,subprocess,sys,time,traceback
from pathlib import Path
import numpy as np
from prepare import HERE,ART,read,save,sha,sources
if not __debug__:raise RuntimeError('Assertions required')
STAGES=['qualification','primary','ncu']
METRICS=['gpu__time_duration.avg','dram__bytes.sum','dram__bytes_op_read.sum','dram__bytes_op_write.sum',
 'sm__throughput.avg.pct_of_peak_sustained_elapsed','sm__warps_active.avg.pct_of_peak_sustained_active',
 'smsp__sass_thread_inst_executed_op_fadd_pred_on.sum','smsp__sass_thread_inst_executed_op_fmul_pred_on.sum',
 'smsp__sass_thread_inst_executed_op_ffma_pred_on.sum','lts__t_bytes.sum']
def jobs(stage):
    if stage=='qualification':
        return [dict(label='fixtures',mode='N1',kind='fixtures')]+[
            dict(label='fixtures_'+tool,mode='N1',kind='fixtures',tool=tool) for tool in ('memcheck','racecheck','synccheck')]+[
            dict(label='bounded_N1',mode='N1',N=4096),dict(label='target_N0',mode='N0',N=1000000),
            dict(label='target_N1',mode='N1',N=1000000),dict(label='bounded_R0',mode='R0',N=4096)]
    if stage=='primary':
        return [dict(label=f'r{r}_{m}',mode=m,N=1000000,round=r,order='forward' if r%2 else 'reverse')
            for r in range(1,7) for m in (['N0','N1','R0'] if r%2 else ['R0','N1','N0'])]
    assert stage=='ncu'
    return [dict(label=m,mode=m,N=1000000,tool='ncu',diagnostic=1) for m in ('N0','N1','R0')]
def table(p):
    with Path(p).open() as f:return list(csv.DictReader(f))
def vector(p,suffix,dtype):
    path=Path(str(p)+suffix);assert path.stat().st_size%np.dtype(dtype).itemsize==0
    return np.fromfile(path,dtype)

def quality(prefix,job,w,reg):
    mode=job['mode'];n=job['N'];old=mode=='R0'
    rows=table(str(prefix)+'.rows.csv');meta=read(str(prefix)+'.meta.json')
    assert len(rows)==40 and meta['N']==n and meta['D']==960 and meta['diagnostic']==bool(job.get('diagnostic',0))
    if old:
        assert meta['mode']=='READ_ONLY';inv=rows
    else:
        assert meta['B']==1;inv=table(str(prefix)+'.invocations.csv');assert len(inv)==40
        assert meta['squared_bytes']==n*4 and meta['query_bytes']==960*4
    values=[float(r['ack_ms']) for r in inv[8:]]
    assert all(math.isfinite(x) and x>0 for x in values)
    assert math.isfinite(meta['measured_pass_ms']) and meta['measured_pass_ms']+1e-5>=sum(values)
    ids=vector(prefix,'.ids.i32','<i4');fields=vector(prefix,'.dist.f32','<f4');native=vector(prefix,'.native_squared.f64','<f8')
    assert len(ids)==len(fields)==len(native)
    expected={};maxerror=0.;near_margin=None
    if not old:
        for q in reg['q32']:
            v=np.memmap(Path(reg['reference'])/f'{q}.f64',dtype='<f8',mode='r')[:n]
            hit=np.flatnonzero(v<=reg['radius']**2);expected[q]=(hit,np.array(v[hit]))
            margin=float(np.min(np.abs(v-reg['radius']**2)));near_margin=margin if near_margin is None else min(near_margin,margin)
    at=0;counts=[]
    for i,r in enumerate(rows):
        q=reg['q32'][i if i<8 else i-8];assert int(r['qid'])==q and int(r['warmup'])==int(i<8)
        assert int(r['query' if old else 'invocation'])==i
        if not old:assert int(r['query_in_batch'])==0 and int(inv[i]['invocation'])==i and int(inv[i]['warmup'])==int(i<8) and int(inv[i]['B'])==1
        z=int(r['count']);assert z>=0 and int(r['offset'])==at and at+z<=len(ids)
        if old:
            assert z==0 and abs(float(r['checksum'])-reg['read_sums'][str(n)])<=1e-4*max(1,abs(reg['read_sums'][str(n)]))
        else:
            hit,score=expected[q];actual=ids[at:at+z];f=fields[at:at+z];v=native[at:at+z]
            assert np.array_equal(hit,actual),('complete membership/order',job['label'],i,q)
            assert np.isfinite(f).all() and np.isfinite(v).all() and (f>=0).all() and (v>=0).all()
            assert np.array_equal(v,v.astype('<f4').astype('<f8')),'charged observer must be exact FP32 cast'
            error=max(float(np.max(np.abs(f.astype(float)**2-score)/np.maximum(1,score),initial=0)),
                      float(np.max(np.abs(v-score)/np.maximum(1,score),initial=0)))
            assert error<=5e-5,('ordered-FP64 fields',error);maxerror=max(maxerror,error)
        at+=z;counts.append(z)
    assert at==len(ids)
    payloads={s:sha(str(prefix)+s) for s in ('.ids.i32','.dist.f32','.native_squared.f64')}
    keeper_equal=None;native_scale_error=None
    if not old and n==1000000:
        keeper=read(ART/'exact_scan_breakdown_20261011/evidence/NATIVE_IDENTITY.json')['payloads']
        if mode=='N0':assert all(v==keeper[k]['sha256'] for k,v in payloads.items());keeper_equal=True
        else:
            native_prefix=w/'qualification/outputs/target_N0'
            assert np.array_equal(ids,vector(native_prefix,'.ids.i32','<i4'))
            score=vector(native_prefix,'.native_squared.f64','<f8');field=vector(native_prefix,'.dist.f32','<f4')
            native_scale_error=max(float(np.max(np.abs(native-score)/np.maximum(1,score),initial=0)),float(np.max(np.abs(fields.astype(float)**2-field.astype(float)**2)/np.maximum(1,score),initial=0)))
            assert native_scale_error<=5e-5;keeper_equal=all(v==sha(str(native_prefix)+k) for k,v in payloads.items())
    return dict(passed=True,mode=mode,N=n,queries=40,measured_queries=32,all_complete_members=not old,
        false_negatives=0 if not old else None,false_positives=0 if not old else None,
        max_ordered_FP64_field_error=maxerror if not old else None,max_native_scale_error=native_scale_error,
        native_payload_bits_equal=keeper_equal,min_ordered_boundary_margin=near_margin,
        counts=counts,mean_query_ms=sum(values)/32,query_ack_ms=values,pass_ms=meta['measured_pass_ms'],meta=meta,
        payload_hashes=payloads,output_hashes={p.name:sha(p) for p in prefix.parent.glob(prefix.name+'.*') if p.is_file()})

def prepared(w):
    reg=read(w/'REGISTERED.json');ready=read(w/'READY.json');b=read(w/'build/BUILD.json')
    assert ready['passed'] and ready['registration_sha256']==b['registration_sha256']==sha(w/'REGISTERED.json')
    assert reg['contract_sha256']==sha(HERE/'CONTRACT.json') and reg['source_hashes']==ready['source_hashes']==sources()
    assert ready['build_sha256']==sha(w/'build/BUILD.json') and b['binary_sha256']==sha(w/'build/candidate')
    assert reg['native_sha256']==sha(reg['native_binary']) and reg['readonly_sha256']==sha(reg['readonly_binary'])
    assert sha(reg['data'])==reg['data_sha256']
    for name,h in reg['reference_hashes'].items():assert sha(Path(reg['reference'])/name)==h
    return reg
def previous_stage(w,stage):
    p=w/stage;register=read(p/'REGISTERED.json');result=read(p/'RESULTS.json')
    assert result['complete'] and result['registration_sha256']==sha(p/'REGISTERED.json')
    assert register['jobs']==jobs(stage) and register['source_hashes']==sources()
    assert len(result['rows'])==len(jobs(stage))
    for row in result['rows']:
        assert row['status']=='passed'
        guard=p/'guards'/row['label']/'receipt.json';checked=p/(row['label']+'.checked.json')
        assert row['guard_sha256']==sha(guard) and read(guard)['runtime_valid']
        assert row['checked_sha256']==sha(checked) and read(checked)['passed']
        for name,h in row['report_hashes'].items():assert sha(p/'reports'/name)==h
        for name,h in read(checked).get('output_hashes',{}).items():assert sha(p/'outputs'/name)==h
def command(job,w,reg,prefix,report):
    diagnostic=str(job.get('diagnostic',0));mode=job['mode']
    if job.get('kind')=='fixtures':cmd=[str(w/'build/candidate'),'--fixtures']
    elif mode=='R0':cmd=[reg['readonly_binary'],reg['data'],str(w/'pool32.txt'),str(job['N']),'960',str(reg['radius']),'READ_ONLY',str(prefix),diagnostic]
    else:cmd=[reg['native_binary'] if mode=='N0' else str(w/'build/candidate'),reg['data'],str(w/'pool32.txt'),str(job['N']),'1',str(reg['radius']),str(prefix),diagnostic]
    tool=job.get('tool')
    if tool in ('memcheck','racecheck','synccheck'):cmd=['/usr/local/cuda-13.1/bin/compute-sanitizer','--tool',tool,'--error-exitcode','97',*cmd]
    if tool=='ncu':
        name={'N0':'pairwise_matrix_kernel','N1':'squared_l2_b1','R0':'coordinate_read'}[mode]
        cmd=['/usr/bin/sudo','-n','env','CUDA_VISIBLE_DEVICES='+reg['gpu'],'LD_LIBRARY_PATH='+reg['environment']['LD_LIBRARY_PATH'],
            '/usr/local/bin/ncu','--profile-from-start','off','--kernel-name-base','demangled','--kernel-name','regex:.*'+name+'.*',
            '--launch-count','1','--cache-control','none','--clock-control','none','--section','LaunchStats','--metrics',','.join(METRICS),'-o',str(report),*cmd]
    return cmd

def run(a):
    w=a.work.resolve();reg=prepared(w);assert a.gpu==reg['gpu'] and a.numa==reg['numa']
    for stage in STAGES[:STAGES.index(a.stage)]:previous_stage(w,stage)
    p=w/a.stage;p.mkdir(exist_ok=False)
    for name in ('outputs','reports','guards'):(p/name).mkdir()
    registration=dict(before_execution=True,jobs=jobs(a.stage),source_hashes=sources(),ready_sha256=sha(w/'READY.json'),gpu=a.gpu,numa=a.numa,registered_unix=time.time())
    save(p/'REGISTERED.json',registration);rows=[];env={**os.environ,**reg['environment']}
    with (w/'campaign.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        for job in registration['jobs']:
            row={**job,'status':'not_executed'};rows.append(row)
            try:
                assert sources()==registration['source_hashes']
                ledger=w/'STARTS.jsonl';count=len(ledger.read_text().splitlines()) if ledger.exists() else 0
                assert count<31,'hard GPU-start budget'
                prefix=p/'outputs'/job['label'];report=p/'reports'/job['label'];cmd=command(job,w,reg,prefix,report)
                save(p/(job['label']+'.command.json'),dict(command=cmd))
                with ledger.open('a') as f:f.write(json.dumps(dict(start=count+1,stage=a.stage,label=job['label'],command_sha256=sha(p/(job['label']+'.command.json')),registered_unix=time.time()))+'\n')
                guard=[sys.executable,str(ART/'external_closure/static_guard.py'),'--gpu',a.gpu,'--numa-node',str(a.numa),'--output',str(p/'guards'/job['label']),'--',*cmd]
                with (p/(job['label']+'.outer.log')).open('x') as log:subprocess.run(guard,env=env,stdout=log,stderr=log,check=True)
                receipt=p/'guards'/job['label']/'receipt.json';assert read(receipt)['runtime_valid']
                assert read(p/'guards'/job['label']/'before.json')['device'].split(',')[1].strip()==reg['gpu']
                if job.get('kind')=='fixtures':
                    lines=(p/'guards'/job['label']/'stdout.log').read_text().splitlines();checked=next(json.loads(s) for s in reversed(lines) if s.startswith('{'))
                    assert checked['passed'] and checked['iterations']==100 and checked['stream_slots']==2 and checked['empty_answers']>0 and checked['exact_boundary_pairs']>0
                    if job.get('tool'):
                        logs=''.join((p/'guards'/job['label']/s).read_text() for s in ('stdout.log','stderr.log'))
                        assert 'ERROR SUMMARY: 0 errors' in logs or 'RACECHECK SUMMARY: 0 hazards' in logs
                else:checked=quality(prefix,job,w,reg)
                save(p/(job['label']+'.checked.json'),checked)
                if job.get('tool')=='ncu':
                    for page,suffix,extras in [('raw','.base.csv',['--csv','--print-units','base']),('source','.sass.txt',['--print-source','sass'])]:
                        with Path(str(report)+suffix).open('x') as out:subprocess.run(['/usr/local/bin/ncu','--import',str(report)+'.ncu-rep','--page',page,*extras],env=env,stdout=out,check=True)
                    raw=list(csv.reader(Path(str(report)+'.base.csv').read_text().splitlines()));assert len(raw)==3,'one selected main-kernel launch'
                    expected={'N0':'pairwise_matrix_kernel','N1':'squared_l2_b1','R0':'coordinate_read'}[job['mode']]
                    assert expected in raw[2][raw[0].index('Kernel Name')]
                row.update(status='passed',guard_sha256=sha(receipt),checked_sha256=sha(p/(job['label']+'.checked.json')),report_hashes={x.name:sha(x) for x in (p/'reports').glob(job['label']+'.*') if x.is_file()})
                save(p/f'PROGRESS_{len(rows):03}.json',dict(rows=rows));print('PASSED',a.stage,job['label'],flush=True)
            except Exception:
                row.update(status='failed',error=traceback.format_exc());save(p/'RESULTS.json',dict(complete=False,rows=rows,registration_sha256=sha(p/'REGISTERED.json'),stop='first failure;no automatic retry'));raise
    save(p/'RESULTS.json',dict(complete=True,rows=rows,registration_sha256=sha(p/'REGISTERED.json')))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);p.add_argument('--stage',choices=STAGES,required=True)
    p.add_argument('--gpu',required=True);p.add_argument('--numa',type=int,required=True);run(p.parse_args())
