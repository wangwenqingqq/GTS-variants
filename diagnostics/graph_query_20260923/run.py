#!/usr/bin/env python3
"""Single locked, monitored process; no GPU or permission changes."""
import argparse
import csv
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time


def snapshot(gpu):
    def query(arg):return subprocess.check_output(['nvidia-smi','-i',gpu,arg,'--format=csv,noheader'],text=True)
    return {'gpu':query('--query-gpu=index,uuid,name,memory.used,utilization.gpu'),
            'apps':query('--query-compute-apps=pid,process_name,used_memory')}


def execute(root,gpu,label,mode,radius,repeats,warmup,tool,dump):
    path=root/'runs'/label;path.mkdir();before=snapshot(gpu)
    assert not before['apps'].strip(),'GPU occupied; no foreign process touched'
    (path/'before.json').write_text(json.dumps(before))
    cmd=[str(root/'bin/graph_bench'),str(root/'fixtures/words_2000.txt'),str(root/'fixtures/queries.qid'),mode,str(radius),str(repeats),str(warmup),str(path/'result'),str(int(dump))]
    if tool.startswith('nsys'):cmd=['nsys','profile','--trace=cuda,nvtx,osrt','--sample=none','--cpuctxsw=none','--export=sqlite','--output='+str(path/'trace')]+(['--cuda-graph-trace=node'] if tool=='nsys-node' else [])+cmd
    elif tool!='clean':cmd=['compute-sanitizer','--tool',tool,'--error-exitcode','90']+(['--leak-check','no'] if tool=='memcheck' else [])+cmd
    (path/'command.json').write_text(json.dumps(cmd));limit=120 if tool=='clean' or tool.startswith('nsys') else 600
    owned=set();checks=[];reason=None;start=time.monotonic()
    with (path/'stdout.log').open('w') as out,(path/'stderr.log').open('w') as err,(path/'gpu.csv').open('w') as gs:
        mon=subprocess.Popen(['nvidia-smi','-i',gpu,'--query-gpu=timestamp,memory.used,utilization.gpu,power.draw','--format=csv,noheader,nounits','-lms','100'],stdout=gs,stderr=err)
        p=subprocess.Popen(cmd,cwd=path,env={**os.environ,'CUDA_VISIBLE_DEVICES':gpu},stdout=out,stderr=err,start_new_session=True)
        owned.add(p.pid);nextcheck=start+1
        try:
            while True:
                done,status,usage=os.wait4(p.pid,os.WNOHANG)
                if done:break
                pending=list(owned)
                while pending:
                    parent=pending.pop()
                    for f in Path(f'/proc/{parent}/task').glob('*/children'):
                        try:ids=list(map(int,f.read_text().split()))
                        except (FileNotFoundError,ProcessLookupError):continue
                        for pid in ids:
                            if pid not in owned:owned.add(pid);pending.append(pid)
                if time.monotonic()>nextcheck:
                    apps=snapshot(gpu)['apps'];foreign=[x for x in apps.splitlines() if int(x.split(',')[0]) not in owned]
                    checks.append({'elapsed_s':time.monotonic()-start,'apps':apps,'owned':sorted(owned),'foreign':foreign})
                    if foreign:reason='foreign GPU activity'
                    nextcheck=time.monotonic()+1
                if time.monotonic()-start>limit:reason='timeout'
                if reason:
                    os.killpg(p.pid,signal.SIGTERM);deadline=time.monotonic()+5
                    while True:
                        done,status,usage=os.wait4(p.pid,os.WNOHANG)
                        if done:break
                        if time.monotonic()>deadline:os.killpg(p.pid,signal.SIGKILL)
                        time.sleep(.05)
                    break
                time.sleep(.1)
            p.returncode=os.waitstatus_to_exitcode(status)
        finally:mon.terminate();mon.wait(timeout=10)
    after=snapshot(gpu);(path/'after.json').write_text(json.dumps(after));(path/'checks.json').write_text(json.dumps(checks,indent=2))
    logs=(path/'stderr.log').read_text()+(path/'stdout.log').read_text()
    errors=[x for x in logs.splitlines() if 'error:' in x.lower() or 'assertion' in x.lower()]
    gold=root/'fixtures'/f'expected_{radius:g}.json'
    validation={'pass':False,'reason':'full-output check required externally'}
    if gold.exists() and (path/'result.csv').exists():
        expected=json.loads(gold.read_text());rows=list(csv.DictReader((path/'result.csv').open()))
        ok=len(rows)==repeats*64 and all([int(r['count']),r['ordered_hash']]==expected[r['qid']] for r in rows)
        validation={'pass':ok,'scope':'count and ordered full-output hash against CPU-validated native outputs','rows':len(rows)}
    record={'label':label,'mode':mode,'radius':radius,'repeats':repeats,'warmup':warmup,'tool':tool,'dump':dump,'pid':p.pid,
        'exit_code':p.returncode,'stop_reason':reason,'wall_s':time.monotonic()-start,'user_s':usage.ru_utime,'system_s':usage.ru_stime,
        'post_gpu_clear':not after['apps'].strip(),'runtime_errors':errors,'validation':validation,
        'binary_sha256':hashlib.sha256((root/'bin/graph_bench').read_bytes()).hexdigest(),
        'runner_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (path/'receipt.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record),flush=True)
    return p.returncode==0 and not reason and not errors and record['post_gpu_clear'] and (not gold.exists() or validation['pass'])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('root',type=Path);p.add_argument('--gpu',required=True);p.add_argument('--label',required=True)
    p.add_argument('--mode',choices=['A','B','C'],required=True);p.add_argument('--radius',type=float,default=4);p.add_argument('--repeats',type=int,default=1)
    p.add_argument('--warmup',type=int,default=0);p.add_argument('--tool',choices=['clean','nsys','nsys-node','memcheck','synccheck','initcheck'],default='clean');p.add_argument('--dump',action='store_true')
    a=p.parse_args();assert a.repeats>0 and a.warmup>=0
    root=a.root.resolve();state=snapshot(a.gpu);assert not state['apps'].strip();index=state['gpu'].split(',')[0].strip()
    with open('/tmp/gtspp_gpu'+index+'.lock','a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        ok=execute(root,a.gpu,a.label,a.mode,a.radius,a.repeats,a.warmup,a.tool,a.dump)
    raise SystemExit(0 if ok else 1)
