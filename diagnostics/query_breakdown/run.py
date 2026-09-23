#!/usr/bin/env python3
"""Fail-closed serial query attribution; retain every attempted process."""
import argparse
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import resource
import subprocess
import time
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('base',HERE.parent/'original_tree_profile/run.py');base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
CASES=[(2000,32,300)]+[(65536,q,r) for q in [32,128] for r in [300,500]]

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('root',type=Path);ap.add_argument('--gpu',required=True);ap.add_argument('--stage',choices=['check','sanitizer','timing','profile','ncu'],required=True);a=ap.parse_args();root=a.root.resolve();(root/'runs').mkdir(exist_ok=True)
    assert base.snapshot(a.gpu)['gpu'].split(',')[0].strip()=='0','physical GPU0 only'
    locks=[]
    for p in [Path('/tmp/gtspp_gpu0.lock'),root/'run.lock']:
        f=p.open('a');fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);locks.append(f)
    def invoke(label,cmd,binary,optional_counter=False):
        out=root/'runs'/label;out.mkdir();pre=base.snapshot(a.gpu);(out/'before.json').write_text(json.dumps(pre,indent=2)+'\n');assert not pre['apps'].strip(),'GPU0 occupied'
        start=time.time();cpu=resource.getrusage(resource.RUSAGE_CHILDREN)
        with (out/'stdout.log').open('w') as stdout,(out/'stderr.log').open('w') as stderr:
            try:rc=subprocess.run(list(map(str,cmd)),cwd=out,env={**os.environ,'CUDA_VISIBLE_DEVICES':a.gpu},stdout=stdout,stderr=stderr,timeout=300).returncode
            except subprocess.TimeoutExpired:rc=124
        end=resource.getrusage(resource.RUSAGE_CHILDREN);post=base.snapshot(a.gpu);text=(out/'stdout.log').read_text()+(out/'stderr.log').read_text()
        correct='correct,full_integer_oracle' in text and 'pass' in text.splitlines()
        denied=optional_counter and 'ERR_NVGPUCTRPERM' in text
        rec={'label':label,'command':list(map(str,cmd)),'gpu_uuid':a.gpu,'start':start,'wall_s':time.time()-start,'user_s':end.ru_utime-cpu.ru_utime,'system_s':end.ru_stime-cpu.ru_stime,'exit_code':rc,'binary_sha256':base.sha(binary),'correct':correct,'counter_denied':denied,'post_clear':not post['apps'].strip()}
        (out/'after.json').write_text(json.dumps(post,indent=2)+'\n');(out/'receipt.json').write_text(json.dumps(rec,indent=2)+'\n');print(label,'rc',rc,'correct',correct,'counter_denied',denied,flush=True)
        assert rec['post_clear'] and ((rc==0 and correct) or denied),'failed/contaminated; retain and stop'
    def gate(label,binary):
        r=json.loads((root/'runs'/label/'receipt.json').read_text());assert r['exit_code']==0 and r['correct'] and r['post_clear'] and r['binary_sha256']==base.sha(binary),label
    for n,q,r in CASES:
        name=f'n{n}_q{q}_r{r}';fixture=root/'fixtures'/f'n{n}';binary=root/'bin'/('bench3' if n==2000 else 'bench5')
        m=json.loads((fixture/'manifest.json').read_text());assert m==json.loads((HERE.parent/'tc_leaf_probe/EVIDENCE.json').read_text())['fixtures'][f'n{n}']
        for f,h in m['file_sha256'].items():assert base.sha(fixture/f)==h
        cmd=[binary,fixture/'data.txt',fixture/f'q{q}.txt',r]
        if a.stage=='check':
            for policy in 'DB':invoke(f'check_{name}_{policy}',cmd+[policy,'check'],binary)
            continue
        for policy in 'DB':gate(f'check_{name}_{policy}',binary)
        if a.stage=='sanitizer':
            for policy in ('DB' if n==2000 or (q,r)==(128,500) else 'D'):
                for tool in (['memcheck','synccheck','initcheck','racecheck'] if n==2000 and policy=='D' else ['memcheck','synccheck']):
                    invoke(f'{tool}_{name}_{policy}',['compute-sanitizer','--tool',tool,'--error-exitcode','90']+cmd+[policy,'check'],binary)
        elif n==65536:
            for tool in ['memcheck','synccheck']:gate(f'{tool}_{name}_D',binary)
            if a.stage=='timing':
                for pair in range(6):
                    for policy in ('DB' if pair%2==0 else 'BD'):invoke(f'timing_{name}_{pair}_{policy}',cmd+[policy,'timing'],binary)
            elif a.stage=='profile':
                for policy,um in ([('D',False),('B',False),('D',True)] if (q,r)==(128,500) else [('D',False)]):
                    label=f'profile_{name}_{policy}_um{int(um)}';out=root/'runs'/label
                    flags=['--cuda-um-cpu-page-faults=true','--cuda-um-gpu-page-faults=true'] if um else []
                    invoke(label,['nsys','profile','--trace=cuda,nvtx','--sample=none','--cpuctxsw=none','--capture-range=cudaProfilerApi','--capture-range-end=stop','--export=sqlite','--force-overwrite=false','--output='+str(out/'trace')]+flags+cmd+[policy,'profile'],binary)
            elif a.stage=='ncu' and (q,r)==(128,500):
                out=root/'runs'/'ncu_leaf'
                invoke('ncu_leaf',['ncu','--section','SpeedOfLight','--section','MemoryWorkloadAnalysis','--section','LaunchStats','--section','SchedulerStats','--kernel-name','regex:dataProcessRnn','--launch-skip','4','--launch-count','1','--export',out/'trace']+cmd+['D','check'],binary,True)

if __name__=='__main__':main()
