"""One immutable campaign,owned guard,first failure stops;no automatic retry."""
if not __debug__:raise SystemExit('Mandatory checks require ordinary Python without optimization.')
import argparse,fcntl,json,os,subprocess,sys,traceback
from pathlib import Path
import numpy as np
from common import HERE,REPO,BASE,STAGES,UPDATES,jobs,load,save,sha,module
from prepare import input_prefix
from quality import check
run_guard=module('inherited_owned_guard_controller',BASE/'campaign.py').run_guard
METRICS=('dram__bytes_read.sum','dram__bytes_write.sum','lts__t_sectors_op_read.sum','lts__t_sectors_op_write.sum')

def prepared(w):
    r=load(w/'REGISTERED.json');ready=load(w/'READY.json');assert ready['passed'] and sha(w/'REGISTERED.json')==ready['registration_sha256']
    assert r['contract_sha256']==sha(HERE/'CONTRACT.json')
    for n,h in r['sources'].items():assert sha(REPO/n)==h
    for n,h in r['generated'].items():assert sha(w/n)==h
    for name,h in ready['binaries'].items():assert sha(w/'build'/name/'service')==h
    parent=Path(r['parent']);assert sha(parent/'REGISTERED.json')==r['parent_registration_sha256'] and sha(parent/'READY.json')==r['parent_ready_sha256']
    for name,h in ready['parent_binaries'].items():assert sha(parent/'build'/name/'service')==h
    return r,ready

def target(job,w,reg,prefix):
    parent=Path(reg['parent']);old=load(parent/'REGISTERED.json');u=job['update']
    binary=parent/'build'/('S1' if u=='S1' else 'S2_STALE')/'service' if u in ('S1','CURRENT') else w/'build'/(u+'_'+job['variant'])/'service'
    cmd=[str(binary)]
    if job['kind']=='selftest':cmd+=['--selftest']
    elif job['kind']=='shape':cmd+=['--shape',job['shape'],str(prefix)]
    elif job['kind']=='service':
        if u not in ('S1','CURRENT'):cmd+=['--legacy']
        n=job['N'];cmd+=[old['data'],str(input_prefix(parent,n,2)),str(parent/'inputs'/('bounded_qids.txt' if n==4096 else 'full_qids.txt')),str(load(HERE/'CONTRACT.json')['radius']),str(prefix),'2',str(job['diagnostic']),str(n)]
    else:cmd+=['--micro',old['data'],str(input_prefix(parent,job['N'],2)),str(parent/'inputs/full_qids.txt'),str(load(HERE/'CONTRACT.json')['radius']),str(prefix),str(('I','D','R').index(job['op'])),str(job['batch']),str(job['N']),str(job['K']),str(job['diagnostic']),'v1']
    return cmd

def command(job,w,reg,prefix):
    cmd=target(job,w,reg,prefix);tool=job.get('tool');report=prefix.parent.parent/'reports'/job['label']
    if tool in ('memcheck','racecheck','synccheck'):return ['/usr/local/cuda-13.1/bin/compute-sanitizer','--tool',tool,'--error-exitcode','97',*cmd]
    if tool in ('nsys','ncu'):
        head=['/usr/bin/sudo','-n','env','CUDA_VISIBLE_DEVICES='+reg['gpu'],*[k+'='+v for k,v in reg['environment'].items()]]
        if tool=='nsys':return head+['/usr/local/bin/nsys','profile','--trace=cuda,nvtx,osrt','--sample=none','--cpuctxsw=none','--cuda-event-trace=false','--gpu-metrics-devices='+reg['gpu'],'--gpu-metrics-set=gb20x','--gpu-metrics-frequency=10000','--capture-range=cudaProfilerApi','--capture-range-end=stop','--force-overwrite=false','--output',str(report),*cmd]
        kernel='regex:.*progressive_.*' if job['kind']=='service' else 'regex:.*materialize_final.*'
        return head+['/usr/local/bin/ncu','--target-processes','all','--profile-from-start','off','--clock-control','none','--cache-control','none','--kernel-name',kernel,'--metrics',','.join(METRICS),'--csv','--log-file',str(report)+'.csv',*cmd]
    return cmd

def screen(w):
    from analyze import micro
    ratios={u:[] for u in ('WAVES','FINAL')}
    for r in (1,2):
        values={}
        for u in UPDATES:
            job=next(j for j in jobs('screen') if j['round']==r and j['update']==u)
            values[u]=micro(load(w/'screen'/(job['label']+'.checked.json')),job)['mean_ACK_ms']
        for u in ratios:ratios[u].append(values[u]/values['NATIVE'])
    passed=any(all(v<=.75 for v in values) for values in ratios.values())
    record=dict(operator_screen_supports_expansion=passed,ratios=ratios,scope='Two-process cheap screen,not inferential final result or novelty admission',next='primary' if passed else 'pause for research review;no mechanism rejection')
    save(w/'SCREEN_DECISION.json',record);assert passed,'Screen did not support automatic expensive expansion;retain evidence'

def main():
    p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);p.add_argument('--stage',choices=STAGES,required=True);a=p.parse_args();w=a.work.resolve();reg,ready=prepared(w);c=load(HERE/'CONTRACT.json')
    for stage in STAGES[:STAGES.index(a.stage)]:assert load(w/stage/'RESULTS.json')['complete']
    if a.stage=='primary':
        assert load(w/'SCREEN_DECISION.json')['operator_screen_supports_expansion']
        save(w/'ANALYSIS_FREEZE.json',dict(before_primary=True,analyzer_sha256=sha(HERE/'analyze.py'),contract_sha256=sha(HERE/'CONTRACT.json'),screen_decision_sha256=sha(w/'SCREEN_DECISION.json')))
    for n,h in reg['inputs'].items():assert sha(n)==h
    stage=w/a.stage;stage.mkdir();[(stage/n).mkdir() for n in ('guards','outputs','reports')];expected=jobs(a.stage);rows=[{**j,'status':'not_executed'} for j in expected]
    save(stage/'REGISTERED.json',dict(before_starts=True,jobs=expected,contract_sha256=sha(HERE/'CONTRACT.json'),executor_sha256=sha(HERE/'campaign.py')))
    env={**os.environ,**reg['environment'],'CUDA_VISIBLE_DEVICES':reg['gpu'],'PYTHONDONTWRITEBYTECODE':'1'}
    with (w/'campaign.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        for job,row in zip(expected,rows):
            try:
                prepared(w);label=job['label'];prefix=stage/'outputs'/label;cmd=command(job,w,reg,prefix)
                save(stage/(label+'.command.json'),dict(command=cmd));ledger=w/'STARTS.jsonl';count=len(ledger.read_text().splitlines()) if ledger.exists() else 0;assert count<c['max_GPU_starts']
                with ledger.open('a') as f:f.write(json.dumps(dict(start=count+1,stage=a.stage,label=label,command_sha256=sha(stage/(label+'.command.json'))))+'\n')
                guard=stage/'guards'/label;wrapper=[sys.executable,str(REPO/'artifacts/external_closure/static_guard.py'),'--gpu',reg['gpu'],'--numa-node',str(reg['numa']),'--output',str(guard),'--',*cmd]
                with (stage/(label+'.outer.log')).open('x') as f:run_guard(wrapper,env,f)
                receipt=load(guard/'receipt.json');assert receipt['runtime_valid'] and receipt['exit_code']==0 and receipt['stop_reason'] is None and receipt['observer']=='two-sided-starttime-v1'
                assert not load(guard/'before.json')['apps'] and not load(guard/'after.json')['apps'] and all(not x['foreign'] for x in load(guard/'checks.json'))
                if job['kind']=='selftest':
                    text=(guard/'stdout.log').read_text();checked=next(json.loads(line) for line in reversed(text.splitlines()) if line.startswith('{'))
                    assert checked['passed'] and checked['query_checks']==400 and 'OWNERSHIP_SELFTEST full_capacity_cases=180 invalid_rejections=6 streams=2' in text
                    checked.update(full_capacity_bit_cases=180,invalid_atomic_rejections=6,synthetic_D=[1,31,128,960,1024])
                else:checked=check(prefix,job,w,reg)
                if job.get('tool') in ('memcheck','racecheck','synccheck'):
                    text=(guard/'stdout.log').read_text()+(guard/'stderr.log').read_text();assert 'ERROR SUMMARY: 0 errors' in text or 'RACECHECK SUMMARY: 0 hazards' in text;checked['sanitizer_summary_zero']=True
                if job.get('tool')=='nsys':
                    report=stage/'reports'/label;subprocess.run(['/usr/local/bin/nsys','export','--type=sqlite','--force-overwrite=false','--output',str(report)+'.sqlite',str(report)+'.nsys-rep'],env=env,check=True)
                save(stage/(label+'.checked.json'),checked)
                row.update(status='passed',checked_sha256=sha(stage/(label+'.checked.json')),guard_sha256=sha(guard/'receipt.json'),guard_files={p.name:sha(p) for p in guard.iterdir() if p.is_file()},reports={p.name:dict(sha256=sha(p),bytes=p.stat().st_size) for p in (stage/'reports').glob(label+'.*') if p.is_file()})
                print('PASSED',a.stage,label,'start',count+1,flush=True)
            except BaseException:
                row.update(status='failed',error=traceback.format_exc());save(stage/'RESULTS.json',dict(complete=False,rows=rows,stop='first failure,no retry'));raise
        save(stage/'RESULTS.json',dict(complete=True,rows=rows))
    if a.stage=='screen':screen(w)

if __name__=='__main__':main()
