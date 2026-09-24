#!/usr/bin/env python3
"""Original-GTS update probes; adapted from original_flow_20260923/run.py."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time
import prepare


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


def run(root,gpu,label,case,mode,binary_name):
    path=root/'runs'/label;path.mkdir()
    before=snapshot(gpu);(path/'gpu_before.json').write_text(json.dumps(before,indent=2)+'\n')
    assert not before['apps'].strip(),'GPU occupied; no foreign process is touched'
    binary=root/'bin'/binary_name;data=root/'fixtures/data.txt'
    manifest=json.loads((root/'manifest.json').read_text())
    contract=manifest['cases'][case];queries=root/'fixtures'/(case+'.updates')
    assert sha(data)==manifest['data_sha256']
    assert sha(queries)==contract['updates_sha256']
    cmd=[str(binary),str(data),str(queries),'2',str(contract['radius']),str(path/'cost.txt')]
    if mode in ['memcheck','synccheck']:
        cmd=['compute-sanitizer','--tool',mode,'--error-exitcode','90']+(['--leak-check','no'] if mode=='memcheck' else [])+cmd
    env={**os.environ,'CUDA_VISIBLE_DEVICES':gpu}
    (path/'command.json').write_text(json.dumps({'command':cmd,'visible_gpu':gpu},indent=2)+'\n')
    limit=180 if mode in ['memcheck','synccheck'] else 60
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
            if child.returncode is None:
                os.killpg(child.pid,signal.SIGTERM)
                try:child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid,signal.SIGKILL);child.wait()
            monitor.terminate();monitor.wait(timeout=10)
    try:check=prepare.validate((path/'cost.txt').read_text(),contract['expected_counts'])
    except Exception as e:check={'pass':False,'reason':repr(e)}
    stderr=(path/'stderr.log').read_text(errors='replace')
    errors=[x for x in (stderr+'\n'+(path/'stdout.log').read_text(errors='replace')).splitlines() if 'error:' in x.lower() or 'cudaerror' in x.lower() or 'invalid __' in x.lower()]
    summaries=[x for x in (stderr+'\n'+(path/'stdout.log').read_text()).splitlines() if 'SUMMARY:' in x]
    sanitizer_ok=mode=='clean' or any('ERROR SUMMARY: 0 errors' in x for x in summaries)
    after=snapshot(gpu);(path/'gpu_after.json').write_text(json.dumps(after,indent=2)+'\n')
    record={'label':label,'case':case,'mode':mode,'binary_name':binary_name,'start':wall_start,'pid':child.pid,'exit_code':rc,'stop_reason':stop_reason,
            'wall_s':elapsed,'user_s':usage.ru_utime,'system_s':usage.ru_stime,
            'binary_sha256':sha(binary),'input_sha256':{p.name:sha(p) for p in [data,queries]},'validation':check,
            'runtime_errors':errors,'sanitizer_summaries':summaries,'sanitizer_ok':sanitizer_ok,'post_gpu_clear':not after['apps'].strip(),
            'cpu_scope':'wait4 direct target and reaped descendants only; clean GTS valid; profiler CPU is not GTS CPU; monitoring excluded',
            'runner_sha256':sha(Path(__file__)),'manifest_sha256':sha(root/'manifest.json'),
            'scope':'Synthetic count correctness only; process times are not performance evidence'}
    (path/'admission_checks.json').write_text(json.dumps(admission_checks,indent=2)+'\n')
    (path/'cpu_samples.json').write_text(json.dumps(samples,indent=2)+'\n')
    (path/'receipt.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(record),flush=True)
    assert record['post_gpu_clear'],'Foreign GPU workload; stop'
    return rc==0 and check['pass'] and not errors and not stop_reason and sanitizer_ok


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('root',type=Path);ap.add_argument('--gpu',required=True)
    ap.add_argument('--admitted-index',type=int,default=0,help='Requires operator authorization if not GPU0')
    ap.add_argument('--label',required=True);ap.add_argument('--case',required=True)
    ap.add_argument('--mode',choices=['clean','memcheck','synccheck'],default='clean')
    ap.add_argument('--binary',default='gts_original')
    a=ap.parse_args();root=a.root.resolve();locks=[]
    assert all(c.isalnum() or c in '_-' for c in a.label)
    assert Path(a.binary).name==a.binary
    state=snapshot(a.gpu);assert not state['apps'].strip()
    index=int(state['gpu'].split(',')[0].strip());assert index==a.admitted_index
    for p in [Path(f'/tmp/gtspp_gpu{index}.lock'),root/'run.lock']:
        try:f=p.open('r')
        except FileNotFoundError:f=p.open('x')
        fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);locks.append(f)
    ok=run(root,a.gpu,a.label,a.case,a.mode,a.binary)
    raise SystemExit(0 if ok else 1)


if __name__=='__main__':main()
