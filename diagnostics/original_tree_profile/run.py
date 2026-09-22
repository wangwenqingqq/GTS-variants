#!/usr/bin/env python3
"""Bounded serial diagnostic runner. GPU admission is an external prerequisite."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import subprocess
import time


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot(uuid):
    gpu=subprocess.check_output(['nvidia-smi','-i',uuid,'--query-gpu=index,uuid,name,driver_version,memory.used,utilization.gpu,pstate,power.draw,clocks.current.graphics,clocks.current.memory','--format=csv,noheader'],text=True)
    apps=subprocess.check_output(['nvidia-smi','-i',uuid,'--query-compute-apps=pid,process_name,used_memory','--format=csv,noheader'],text=True)
    return {'time':time.time(),'gpu':gpu,'apps':apps}


def parse(stderr):
    phases={}
    for line in stderr.splitlines():
        parts=line.split(',')
        if len(parts)==5 and parts[0]=='GTS_DIAG' and parts[2].isdigit():
            phases[parts[1]]={'calls':int(parts[2]),'wall_s':float(parts[3]),'main_thread_cpu_s':float(parts[4])}
    return phases


def validate(variant,kind,stdout,cost,expected):
    if variant=='gputree':
        rows=[x.split(',') for x in stdout.splitlines() if x.startswith('GTS_AUDIT_RESULT,')]
        assert [int(x[2]) for x in rows]==list(range(32)), 'Missing/unordered output'
        actual=[float(x[3]) for x in rows]
    else:
        match=re.search(r'Result (?:num|radius):\s*([^\n]+)',cost.read_text())
        assert match,'Missing native results'
        actual=list(map(float,match[1].split()))
    target=expected['knn_kth' if kind=='knn' else 'range_counts']
    return {'pass':len(actual)==len(target) and all(abs(a-b)<1e-5 for a,b in zip(actual,target)),
            'actual':actual,'expected':target,'scope':'native counts or kth distances, not full IDs'}


def invoke(root,uuid,label,variant,kind,size,blocking,mode,expected,tool=None):
    path=root/'runs'/label;path.mkdir()
    before=snapshot(uuid);(path/'gpu_before.json').write_text(json.dumps(before,indent=2)+'\n')
    assert not before['apps'].strip(),'GPU occupied; no foreign work is touched'
    binary=root/'bin'/f'{variant}_profiled_v2';data=root/'fixtures'/f'words_{size}'
    op=0 if kind=='knn' else 2 if kind=='update' else 1
    cmd=[str(binary),str(data.with_suffix('.txt')),str(data.with_suffix('.updates' if op==2 else '.qid')),str(op),'4',str(path/'cost.txt')]
    if mode=='profile':
        cmd=['nsys','profile','--trace=cuda,nvtx,osrt','--sample=none','--cpuctxsw=none','--export=sqlite','--cuda-um-cpu-page-faults=true','--cuda-um-gpu-page-faults=true','--force-overwrite=false','--output='+str(path/'trace')]+cmd
    elif tool:
        cmd=['compute-sanitizer','--tool',tool,'--error-exitcode','90','--leak-check','no']+cmd if tool=='memcheck' else ['compute-sanitizer','--tool',tool,'--error-exitcode','90']+cmd
    env={**os.environ,'CUDA_VISIBLE_DEVICES':uuid,'GTS_DIAG_BLOCKING':str(int(blocking))}
    start=time.time();cpu0=resource.getrusage(resource.RUSAGE_CHILDREN)
    with (path/'stdout.log').open('w') as out,(path/'stderr.log').open('w') as err:
        try:
            p=subprocess.run(cmd,stdout=out,stderr=err,cwd=path,env=env,timeout=300 if tool else 120)
            rc=p.returncode
        except subprocess.TimeoutExpired: rc=124
    cpu1=resource.getrusage(resource.RUSAGE_CHILDREN)
    record={'label':label,'command':cmd,'gpu_uuid':uuid,'blocking':blocking,'mode':mode,'tool':tool,
            'start':start,'process_wall_s':time.time()-start,'process_user_s':cpu1.ru_utime-cpu0.ru_utime,
            'process_system_s':cpu1.ru_stime-cpu0.ru_stime,'exit_code':rc,'binary_sha256':sha(binary)}
    stderr=(path/'stderr.log').read_text(errors='replace');stdout=(path/'stdout.log').read_text(errors='replace')
    record['phases']=parse(stderr)
    try: record['validation']=validate(variant,kind,stdout,path/'cost.txt',expected)
    except Exception as e: record['validation']={'pass':False,'error':repr(e)}
    after=snapshot(uuid);(path/'gpu_after.json').write_text(json.dumps(after,indent=2)+'\n')
    record['post_gpu_clear']=not after['apps'].strip()
    record['runtime_errors']=[s for s in stderr.splitlines() if 'error:' in s.lower()]
    (path/'receipt.json').write_text(json.dumps(record,indent=2)+'\n')
    print(label,'rc',rc,'correct',record['validation']['pass'],'wall',record['process_wall_s'],flush=True)
    assert record['post_gpu_clear'],'GPU acquired by another workload; stop campaign'
    return rc==0 and record['validation']['pass'] and not record['runtime_errors']


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('root',type=Path);ap.add_argument('--gpu',required=True,help='Explicitly admitted GPU UUID')
    ap.add_argument('--stage',choices=['smoke','paired','profile','sanitizer'],required=True)
    a=ap.parse_args();root=a.root.resolve();(root/'runs').mkdir(exist_ok=True)
    locks=[]
    index=snapshot(a.gpu)['gpu'].split(',')[0].strip()
    for p in [Path(f'/tmp/gtspp_gpu{index}.lock'),root/'run.lock']:
        f=p.open('a');fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);locks.append(f)
    manifest=json.loads((root/'fixtures/manifest.json').read_text())
    for name,digest in manifest['file_sha256'].items(): assert sha(root/'fixtures'/name)==digest
    paths=[('gts','range'),('gts','knn'),('gts','update'),('gputree','range'),('gputree','knn')]
    for variant,kind in paths:
        if a.stage=='smoke':
            for size in [1000,2000]:
                invoke(root,a.gpu,f'smoke_{variant}_{kind}_{size}',variant,kind,size,False,'smoke',manifest['cases'][f'words_{size}'])
            continue
        for size in [1000,2000]:
            r=json.loads((root/'runs'/f'smoke_{variant}_{kind}_{size}'/'receipt.json').read_text())
            assert r['exit_code']==0 and r['validation']['pass'],f'{variant}/{kind}: failed smoke, do not promote'
        if a.stage=='sanitizer':
            for tool in ['memcheck','synccheck']:
                invoke(root,a.gpu,f'{tool}_{variant}_{kind}',variant,kind,1000,False,'sanitizer',manifest['cases']['words_1000'],tool)
        elif a.stage=='profile':
            assert invoke(root,a.gpu,f'profile_{variant}_{kind}',variant,kind,2000,False,'profile',manifest['cases']['words_2000'])
        else:
            gates=[json.loads((root/'runs'/f'{tool}_{variant}_{kind}'/'receipt.json').read_text()) for tool in ['memcheck','synccheck']]
            if not all(r['exit_code']==0 and r['validation']['pass'] for r in gates):
                print('SKIP paired:',variant,kind,'failed sanitizer gate',flush=True)
                continue
            for pair in range(6):
                for blocking in ([False,True] if pair%2==0 else [True,False]):
                    assert invoke(root,a.gpu,f'pair{pair}_{variant}_{kind}_b{int(blocking)}',variant,kind,2000,blocking,'paired',manifest['cases']['words_2000'])


if __name__=='__main__': main()
