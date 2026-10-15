"""Exact bounded job ledger; serialize admission and stop on the first failure."""
if not __debug__:
    raise SystemExit('Optimized Python disables mandatory checks; run without -O/PYTHONOPTIMIZE.')
import argparse
import fcntl
import json
import os
import signal
from pathlib import Path
import subprocess
import sys
import traceback
from common import HERE, REPO, PARENT, load, save, sha, jobs
from prepare import input_prefix
from quality import check

STAGES=('qualification','primary','timeline')


def run_guard(wrapper,env,output):
    process=subprocess.Popen(wrapper,env=env,stdout=output,stderr=output,start_new_session=True)
    try:code=process.wait()
    except BaseException:
        if process.poll() is None:
            process.send_signal(signal.SIGINT)
            try:process.wait(timeout=30)
            except subprocess.TimeoutExpired as error:
                raise RuntimeError('Owned guard cleanup did not finish;stop and audit identities,never auto-retry.') from error
        raise
    if code:raise subprocess.CalledProcessError(code,wrapper)


def prepared(w):
    r=load(w/'REGISTERED.json');ready=load(w/'READY.json');assert ready['passed'] and sha(w/'REGISTERED.json')==ready['registration_sha256']
    assert sha(HERE/'CONTRACT.json')==r['contract_sha256']
    for n,h in r['sources'].items():assert sha(REPO/n)==h
    for n,h in r['generated'].items():assert sha(w/n)==h
    for v,h in ready['binaries'].items():assert sha(w/'build'/v/'service')==h
    assert sha(w/'build/replay.so')==ready['replay_sha256']
    parent=Path(r['parent']);old=load(parent/'READY.json')
    assert sha(parent/'REGISTERED.json')==r['parent_registration_sha256'] and sha(parent/'READY.json')==r['parent_ready_sha256']
    for mode,h in ready['parent_binaries'].items():assert sha(parent/'build'/mode/'service')==h==old['binaries'][mode]
    return r,ready


def command(job,w,reg,prefix):
    parent=Path(reg['parent']);old=load(parent/'REGISTERED.json')
    binary=parent/'build'/job['mode']/'service' if job['variant']=='PARENT' else w/'build'/job['variant']/'service'
    cmd=[str(binary)]
    if job['kind']=='selftest':cmd+=['--selftest']
    elif job['kind']=='copy':cmd+=['--copy',str(prefix),str(int(job.get('round',1)%2==0))]
    elif job['kind']=='service':
        if job['variant']!='PARENT':cmd+=['--legacy']
        cmd += [old['data'],str(input_prefix(parent,1000000,2)),str(parent/'inputs/full_qids.txt'),str(load(HERE/'CONTRACT.json')['radius']),str(prefix),'2',str(job['diagnostic']),'1000000']
    else:
        cmd+=['--micro',old['data'],str(input_prefix(parent,job['N'],2)),str(parent/'inputs'/('bounded_qids.txt' if job['N']==4096 else 'full_qids.txt')),
              str(load(HERE/'CONTRACT.json')['radius']),str(prefix),str(('I','D','R').index(job['op'])),str(job['batch']),str(job['N']),str(job['K']),str(job['diagnostic']),'v1']
    if job.get('tool') in ('memcheck','racecheck','synccheck'):
        cmd=['/usr/local/cuda-13.1/bin/compute-sanitizer','--tool',job['tool'],'--error-exitcode','97',*cmd]
    if job.get('tool')=='nsys':
        report=prefix.parent.parent/'reports'/job['label']
        cmd=['/usr/bin/sudo','-n','env','CUDA_VISIBLE_DEVICES='+reg['gpu'],*[k+'='+v for k,v in reg['environment'].items()],
             '/usr/local/bin/nsys','profile','--trace=cuda,nvtx,osrt','--sample=none','--cpuctxsw=none','--cuda-event-trace=false',
             '--gpu-metrics-devices='+reg['gpu'],'--gpu-metrics-set=gb20x','--gpu-metrics-frequency=10000',
             '--capture-range=cudaProfilerApi','--capture-range-end=stop','--force-overwrite=false','--output',str(report),*cmd]
    return cmd


def stamp(path):
    s=Path(path).stat();return (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)


def main():
    p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);p.add_argument('--stage',choices=STAGES,required=True);a=p.parse_args()
    w=a.work.resolve();reg,ready=prepared(w);c=load(HERE/'CONTRACT.json');assert load(w/'STATIC.json')['passed']
    for s in STAGES[:STAGES.index(a.stage)]:assert load(w/s/'RESULTS.json')['complete']
    if a.stage=='primary':save(w/'ANALYSIS_FREEZE.json',dict(before_primary=True,analyzer_sha256=sha(HERE/'analyze.py'),contract_sha256=sha(HERE/'CONTRACT.json')))
    stage=w/a.stage;stage.mkdir();[(stage/n).mkdir() for n in ('guards','outputs','reports')];expected=jobs(a.stage);rows=[{**j,'status':'not_executed'} for j in expected]
    save(stage/'REGISTERED.json',dict(before_starts=True,jobs=expected,contract_sha256=sha(HERE/'CONTRACT.json'),executor_sha256=sha(HERE/'campaign.py')))
    for n,h in reg['inputs'].items():assert sha(n)==h
    stamps={n:stamp(n) for n in reg['inputs']};env={**os.environ,**reg['environment'],'CUDA_VISIBLE_DEVICES':reg['gpu'],'PYTHONDONTWRITEBYTECODE':'1'}
    with (w/'campaign.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        for job,row in zip(expected,rows):
            try:
                prepared(w);assert all(stamp(n)==v for n,v in stamps.items())
                label=job['label'];prefix=stage/'outputs'/label;cmd=command(job,w,reg,prefix)
                save(stage/(label+'.command.json'),dict(command=cmd));ledger=w/'STARTS.jsonl';count=len(ledger.read_text().splitlines()) if ledger.exists() else 0
                assert count<c['max_GPU_starts']
                with ledger.open('a') as f:f.write(json.dumps(dict(start=count+1,stage=a.stage,label=label,command_sha256=sha(stage/(label+'.command.json'))))+'\n')
                guard=stage/'guards'/label;wrapper=[sys.executable,str(REPO/'artifacts/external_closure/static_guard.py'),'--gpu',reg['gpu'],'--numa-node',str(reg['numa']),'--output',str(guard),'--',*cmd]
                with (stage/(label+'.outer.log')).open('x') as f:run_guard(wrapper,env,f)
                receipt=load(guard/'receipt.json');assert receipt['runtime_valid'] and receipt['exit_code']==0 and receipt['stop_reason'] is None
                assert receipt['observer']=='two-sided-starttime-v1' and receipt['gpu']==reg['gpu']
                assert receipt['command']==load(guard/'command.json')==['numactl',f"--cpunodebind={reg['numa']}",f"--membind={reg['numa']}",*cmd]
                assert not load(guard/'before.json')['apps'] and not load(guard/'after.json')['apps'] and all(not x['foreign'] for x in load(guard/'checks.json'))
                if job['kind']=='selftest':
                    checked=next(json.loads(line) for line in reversed((guard/'stdout.log').read_text().splitlines()) if line.startswith('{'))
                    assert checked['passed'] and checked['iterations']==100 and checked['stream_slots']==2 and checked['query_checks']==400
                else:checked=check(prefix,job,w,reg)
                if job.get('tool') in ('memcheck','racecheck','synccheck'):
                    log=(guard/'stdout.log').read_text()+(guard/'stderr.log').read_text();assert 'ERROR SUMMARY: 0 errors' in log or 'RACECHECK SUMMARY: 0 hazards' in log;checked['sanitizer_summary_zero']=True
                if job.get('tool')=='nsys':
                    report=stage/'reports'/label
                    subprocess.run(['/usr/local/bin/nsys','export','--type=sqlite','--force-overwrite=false','--output',str(report)+'.sqlite',str(report)+'.nsys-rep'],env=env,check=True)
                save(stage/(label+'.checked.json'),checked)
                row.update(status='passed',checked_sha256=sha(stage/(label+'.checked.json')),guard_sha256=sha(guard/'receipt.json'),
                    guard_files={p.name:sha(p) for p in guard.iterdir() if p.is_file()},reports={p.name:dict(sha256=sha(p),bytes=p.stat().st_size) for p in (stage/'reports').glob(label+'.*') if p.is_file()})
                print('PASSED',a.stage,label,'start',count+1,flush=True)
            except BaseException:
                row.update(status='failed',error=traceback.format_exc());save(stage/'RESULTS.json',dict(complete=False,rows=rows,stop='first failure,no retry'));raise
        save(stage/'RESULTS.json',dict(complete=True,rows=rows))


if __name__=='__main__':main()
