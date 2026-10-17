"""Registered serial campaign;preserve the first failure and all unexecuted jobs."""
if not __debug__:raise SystemExit('Mandatory checks require ordinary Python.')
import argparse,fcntl,os,subprocess,signal,sys,traceback,json
from pathlib import Path
from protocol import HERE,REPO,STAGES,VARIANTS,jobs,load,save,sha
from quality import check
from truth import RADIUS
def stamp(p):
    s=Path(p).stat();return s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns
def prepared(w):
    r=load(w/'REGISTERED.json');ready=load(w/'READY.json');assert ready['passed'] and ready['registration_sha256']==sha(w/'REGISTERED.json')
    assert r['contract_sha256']==sha(HERE/'GPU_CONTRACT.json') and load(w/'STATIC.json')['passed']
    for n,h in r['sources'].items():assert sha(REPO/n)==h,('changed source',n)
    for n,h in r['generated'].items():assert sha(w/n)==h,('changed generated source',n)
    for n,h in ready['binaries'].items():assert sha(w/'build'/n/'service')==h
    assert sha(w/'build/oracle.so')==ready['oracle_sha256'];return r,ready
def target(j,w,r,prefix):
    cmd=[str(w/'build'/str(j['trace'])/'service'),str(VARIANTS.index(j['variant']))]
    if j['kind']=='selftest':return cmd+['--selftest']
    key='micro' if j['micro'] else f'N{j["N"]}_{j["family"]}'
    return cmd+[r['data'],r['prefixes'][key],str(Path(r['derived_parent'])/'inputs'/('bounded_qids.txt' if j['N']==4096 else 'full_qids.txt')),str(RADIUS),str(prefix),'2',str(j['diagnostic']),str(j['N']),str(j['batch'])]
def command(j,w,r,prefix):
    cmd=target(j,w,r,prefix);tool=j.get('tool')
    if tool in ('memcheck','initcheck','racecheck','synccheck'):return ['/usr/local/cuda-13.1/bin/compute-sanitizer','--tool',tool,'--error-exitcode','97',*cmd]
    if tool in ('nsys','ncu'):
        report=prefix.parent.parent/'reports'/j['label'];head=['/usr/bin/sudo','-n','env','CUDA_VISIBLE_DEVICES='+r['gpu'],*[k+'='+v for k,v in r['environment'].items()]]
        if tool=='nsys':return head+['/usr/local/bin/nsys','profile','--trace=cuda,nvtx,osrt','--sample=none','--cpuctxsw=none','--cuda-event-trace=false','--capture-range=cudaProfilerApi','--capture-range-end=stop','--force-overwrite=false','--output',str(report),*cmd]
        return head+['/usr/local/bin/ncu','--target-processes','all','--profile-from-start','off','--clock-control','none','--cache-control','none','--kernel-name-base','demangled','--kernel-name','regex:.*(IndexedCopy|materialize_final).*','--launch-count','1','--metrics','dram__bytes_read.sum,dram__bytes_write.sum,lts__t_sectors_op_read.sum,lts__t_sectors_op_write.sum','--csv','--log-file',str(report)+'.csv',*cmd]
    return cmd
def run_guard(wrapper,env,output):
    # Reused parent cleanup protocol:signal only the task-owned guard itself.
    process=subprocess.Popen(wrapper,env=env,stdout=output,stderr=output,start_new_session=True)
    try:code=process.wait()
    except BaseException:
        if process.poll() is None:
            process.send_signal(signal.SIGINT)
            try:process.wait(timeout=30)
            except subprocess.TimeoutExpired as error:raise RuntimeError('Owned guard cleanup incomplete;stop,no automatic retry.') from error
        raise
    if code:raise subprocess.CalledProcessError(code,wrapper)
def main():
    p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);p.add_argument('--stage',choices=STAGES,required=True);a=p.parse_args();w=a.work.resolve();r,ready=prepared(w)
    for s in STAGES[:STAGES.index(a.stage)]:assert load(w/s/'RESULTS.json')['complete']
    assert jobs(a.stage)==r['schedule'][a.stage];expected=jobs(a.stage);stage=w/a.stage;stage.mkdir();[(stage/n).mkdir() for n in ('guards','outputs','reports')]
    for n,h in r['inputs'].items():assert sha(n)==h,('input digest',n)
    stamps={n:stamp(n) for n in r['inputs']}
    save(stage/'REGISTERED.json',dict(before_starts=True,jobs=expected,registration_sha256=sha(w/'REGISTERED.json'),campaign_sha256=sha(HERE/'campaign.py')))
    rows=[{**j,'status':'not_executed'} for j in expected];env={**os.environ,**r['environment'],'CUDA_VISIBLE_DEVICES':r['gpu'],'PYTHONDONTWRITEBYTECODE':'1'}
    with (w/'campaign.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        for j,row in zip(expected,rows):
            try:
                prepared(w);assert all(stamp(n)==s for n,s in stamps.items()),'input changed during campaign'
                label=j['label'];prefix=stage/'outputs'/label;cmd=command(j,w,r,prefix);save(stage/(label+'.command.json'),dict(command=cmd))
                ledger=w/'STARTS.jsonl';count=len(ledger.read_text().splitlines()) if ledger.exists() else 0;assert count<r['max_GPU_starts']
                with ledger.open('a') as f:f.write(json.dumps(dict(start=count+1,stage=a.stage,label=label,command_sha256=sha(stage/(label+'.command.json'))))+'\n')
                guard=stage/'guards'/label;wrapper=[sys.executable,str(REPO/'artifacts/external_closure/static_guard.py'),'--gpu',r['gpu'],'--numa-node',str(r['numa']),'--output',str(guard),'--',*cmd]
                with (stage/(label+'.outer.log')).open('x') as f:run_guard(wrapper,env,f)
                receipt=load(guard/'receipt.json');assert receipt['runtime_valid'] and receipt['exit_code']==0 and receipt['stop_reason'] is None and receipt['observer']=='two-sided-starttime-v1'
                assert not load(guard/'before.json')['apps'] and not load(guard/'after.json')['apps'] and all(not c['foreign'] for c in load(guard/'checks.json'))
                text=(guard/'stdout.log').read_text()+(guard/'stderr.log').read_text()
                if j['kind']=='selftest':
                    checked=next(json.loads(line) for line in text.splitlines() if line.startswith('{'));assert checked['passed'] and checked['query_checks']==400 and 'BITCHECK capacity_cases=36 invalid_rejections=6' in text
                    checked.update(capacity_bit_cases=36,invalid_rejections=6)
                else:checked=check(prefix,j,w,r)
                if j.get('tool') in ('memcheck','initcheck','racecheck','synccheck'):
                    assert 'ERROR SUMMARY: 0 errors' in text or 'RACECHECK SUMMARY: 0 hazards' in text;checked['sanitizer_zero']=True
                if j.get('tool')=='nsys':
                    report=stage/'reports'/label;subprocess.run(['/usr/local/bin/nsys','export','--type=sqlite','--force-overwrite=false','--output',str(report)+'.sqlite',str(report)+'.nsys-rep'],check=True,env=env)
                if j.get('tool')=='ncu':
                    report=stage/'reports'/(label+'.csv');profile_text=report.read_text();assert 'dram__bytes_read.sum' in profile_text and 'lts__t_sectors_op_write.sum' in profile_text,'missing NCU capture'
                assert all(stamp(n)==s for n,s in stamps.items()),'input changed during target'
                save(stage/(label+'.checked.json'),checked);row.update(status='passed',checked_sha256=sha(stage/(label+'.checked.json')),guard_sha256=sha(guard/'receipt.json'))
                print('PASSED',a.stage,label,'start',count+1,flush=True)
            except BaseException:
                row.update(status='failed',error=traceback.format_exc());save(stage/'RESULTS.json',dict(complete=False,rows=rows,stop='first failure,no retry'));raise
        save(stage/'RESULTS.json',dict(complete=True,rows=rows))
if __name__=='__main__':main()
