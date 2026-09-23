#!/usr/bin/env python3
"""Serial unmodified-GTS runs with native output checks and external sampling."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import time


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot(gpu):
    def query(fields):
        return subprocess.check_output(['nvidia-smi','-i',gpu,*fields,'--format=csv,noheader'],text=True)
    return {'time':time.time(),'gpu':query(['--query-gpu=index,uuid,name,memory.used,memory.total,utilization.gpu,pstate']),
            'apps':query(['--query-compute-apps=pid,process_name,used_memory'])}


def proc(pid):
    def ticks(path):
        f=path.read_text().rsplit(')',1)[1].split()
        return (int(f[11])+int(f[12]))/os.sysconf('SC_CLK_TCK'),int(f[17]),int(f[21])*os.sysconf('SC_PAGE_SIZE')
    total,threads,rss=ticks(Path(f'/proc/{pid}/stat'))
    main=ticks(Path(f'/proc/{pid}/task/{pid}/stat'))[0]
    return {'process_cpu_s':total,'main_cpu_s':main,'threads':threads,'rss_bytes':rss}


def validate(cost,expected,kind,repeats):
    text=cost.read_text()
    m=re.search(r'Result (?:num|radius):\s*([^\n]+)',text)
    if not m:return {'pass':False,'reason':'missing results'}
    actual=list(map(float,m[1].split()))
    target=expected['knn_kth' if kind=='knn' else 'range_counts']*repeats
    return {'pass':len(actual)==len(target) and all(abs(a-b)<1e-5 for a,b in zip(actual,target)),
            'actual_count':len(actual),'expected_count':len(target),'scope':'counts/kth distances, not full IDs'}


def run(root,gpu,label,kind,mode,long=False,kernel='getQresultCount'):
    path=root/'runs'/label;path.mkdir()
    before=snapshot(gpu);(path/'gpu_before.json').write_text(json.dumps(before,indent=2)+'\n')
    assert not before['apps'].strip(),'GPU occupied; no foreign process is touched'
    binary=root/'bin/gts_original';data=root/'fixtures/words_2000.txt'
    suffix='_long' if long else ''
    queries=root/'fixtures'/('words_2000'+suffix+('.updates' if kind=='update' else '.qid'))
    cmd=[str(binary),str(data),str(queries),str({'range':1,'knn':0,'update':2}[kind]),'4',str(path/'cost.txt')]
    if mode in ['nsys','nsys-light']:
        cmd=['nsys','profile','--trace=cuda,nvtx,osrt','--sample=none','--cpuctxsw=none','--cuda-memory-usage='+str(mode=='nsys').lower(),'--cuda-um-cpu-page-faults='+str(mode=='nsys').lower(),'--cuda-um-gpu-page-faults='+str(mode=='nsys').lower(),'--export=sqlite','--force-overwrite=false','--output='+str(path/'trace')]+cmd
    elif mode in ['ncu','ncu-launch']:
        cmd=['ncu','--clock-control','none','--cache-control','none','--kernel-name-base','function','--kernel-name',kernel,'--launch-count','1',*(['--section','LaunchStats'] if mode=='ncu-launch' else ['--section','SpeedOfLight','--section','LaunchStats','--section','Occupancy','--section','SchedulerStats','--section','WarpStateStats']),'--export',str(path/'kernel')]+cmd
    elif mode in ['memcheck','synccheck']:
        cmd=['compute-sanitizer','--tool',mode,'--error-exitcode','90']+(['--leak-check','no'] if mode=='memcheck' else [])+cmd
    env={**os.environ,'CUDA_VISIBLE_DEVICES':gpu}
    (path/'command.json').write_text(json.dumps({'command':cmd,'visible_gpu':gpu},indent=2)+'\n')
    limit=300 if mode in ['memcheck','synccheck'] else 180 if mode in ['nsys','nsys-light','ncu','ncu-launch'] else 120
    samples=[];admission_checks=[];start=time.monotonic();wall_start=time.time();usage=None
    with (path/'stdout.log').open('w') as out,(path/'stderr.log').open('w') as err,(path/'gpu_samples.csv').open('w') as gs,(path/'monitor_errors.log').open('w') as ge:
        monitor=subprocess.Popen(['nvidia-smi','-i',gpu,'--query-gpu=timestamp,index,memory.used,memory.total,utilization.gpu,utilization.memory,power.draw,clocks.current.graphics','--format=csv,noheader,nounits','-lms','100'],stdout=gs,stderr=ge)
        child=subprocess.Popen(cmd,stdout=out,stderr=err,cwd=path,env=env,start_new_session=True)
        (path/'pid.txt').write_text(str(child.pid)+'\n');stop_reason=None;next_check=start+1;owned={child.pid}
        try:
            while True:
                done,status,usage_now=os.wait4(child.pid,os.WNOHANG)
                if done:
                    child.returncode=os.waitstatus_to_exitcode(status);usage=usage_now;break
                pending=list(owned)
                while pending:
                    parent=pending.pop()
                    for children_file in Path(f'/proc/{parent}/task').glob('*/children'):
                        try:children=map(int,children_file.read_text().split())
                        except (FileNotFoundError,ProcessLookupError):continue
                        for pid in children:
                            if pid not in owned:owned.add(pid);pending.append(pid)
                try:samples.append({'elapsed_s':time.monotonic()-start,**proc(child.pid)})
                except (FileNotFoundError,ProcessLookupError):pass
                if time.monotonic()-start>limit:stop_reason='timeout'
                if time.monotonic()>next_check:
                    apps=snapshot(gpu)['apps'];next_check=time.monotonic()+1
                    foreign=[x for x in apps.splitlines() if int(x.split(',')[0]) not in owned]
                    admission_checks.append({'elapsed_s':time.monotonic()-start,'apps':apps,'owned_pids':sorted(owned),'foreign':foreign})
                    if foreign:stop_reason='foreign GPU activity'
                if stop_reason:
                    os.killpg(child.pid,signal.SIGTERM)
                    deadline=time.monotonic()+5
                    while True:
                        done,status,usage=os.wait4(child.pid,os.WNOHANG)
                        if done:break
                        if time.monotonic()>deadline:os.killpg(child.pid,signal.SIGKILL)
                        time.sleep(.05)
                    child.returncode=os.waitstatus_to_exitcode(status)
                    break
                time.sleep(.1)
            rc=child.returncode;elapsed=time.monotonic()-start
        finally:
            monitor.terminate();monitor.wait(timeout=10)
    expected=json.loads((root/'fixtures/manifest.json').read_text())['cases']['words_2000']
    try:check=validate(path/'cost.txt',expected,kind,128 if long else 1)
    except Exception as e:check={'pass':False,'reason':repr(e)}
    stderr=(path/'stderr.log').read_text(errors='replace')
    errors=[x for x in (stderr+'\n'+(path/'stdout.log').read_text(errors='replace')).splitlines() if 'error:' in x.lower() or 'ERR_NVGPUCTRPERM' in x]
    after=snapshot(gpu);(path/'gpu_after.json').write_text(json.dumps(after,indent=2)+'\n')
    record={'label':label,'kind':kind,'mode':mode,'long':long,'start':wall_start,'pid':child.pid,'exit_code':rc,'stop_reason':stop_reason,
            'wall_s':elapsed,'user_s':usage.ru_utime,'system_s':usage.ru_stime,
            'binary_sha256':sha(binary),'input_sha256':{p.name:sha(p) for p in [data,queries]},'validation':check,
            'runtime_errors':errors,'post_gpu_clear':not after['apps'].strip(),
            'cpu_scope':'wait4 direct target and reaped descendants only; clean GTS valid; profiler CPU is not GTS CPU; monitoring excluded',
            'runner_sha256':sha(Path(__file__))}
    (path/'admission_checks.json').write_text(json.dumps(admission_checks,indent=2)+'\n')
    (path/'cpu_samples.json').write_text(json.dumps(samples,indent=2)+'\n')
    (path/'receipt.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(record),flush=True)
    assert record['post_gpu_clear'],'Foreign GPU workload; stop'
    return rc==0 and check['pass'] and not errors and not stop_reason


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('root',type=Path);ap.add_argument('--gpu',required=True)
    ap.add_argument('--label',required=True);ap.add_argument('--kind',choices=['range','knn','update'],required=True)
    ap.add_argument('--mode',choices=['clean','nsys','nsys-light','ncu','ncu-launch','memcheck','synccheck'],required=True)
    ap.add_argument('--long',action='store_true');ap.add_argument('--kernel',default='getQresultCount')
    a=ap.parse_args();root=a.root.resolve();locks=[]
    state=snapshot(a.gpu);assert not state['apps'].strip()
    index=state['gpu'].split(',')[0].strip()
    for p in [Path(f'/tmp/gtspp_gpu{index}.lock'),root/'run.lock']:
        f=p.open('r+' if p.exists() else 'a');fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);locks.append(f)
    ok=run(root,a.gpu,a.label,a.kind,a.mode,a.long,a.kernel)
    raise SystemExit(0 if ok else 1)


if __name__=='__main__':main()
