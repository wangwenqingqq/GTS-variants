#!/usr/bin/env python3
"""Serial GTSPP campaign; existing GPU allocation and sudo authority required."""
import argparse
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import time
HERE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('base',HERE.parent/'original_tree_profile/run.py');base=importlib.util.module_from_spec(s);s.loader.exec_module(base)
CASES=[(2000,32,300)]+[(65536,q,r) for q in [32,128] for r in [300,500]]
def main():
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('--gpu',required=True);p.add_argument('--stage',required=True,choices=['preflight','gates','timing','profile','stress','sustained']);a=p.parse_args();root=a.root.resolve();(root/'runs').mkdir(exist_ok=True)
    lock=open('/tmp/gtspp_gpu0.lock','a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    assert base.snapshot(a.gpu)['gpu'].split(',')[0].strip()=='0'
    fixture_pins=json.loads((HERE.parent/'tc_leaf_probe/EVIDENCE.json').read_text())['fixtures']
    for n in [2000,65536]:
        m=json.loads((root/f'fixtures/n{n}/manifest.json').read_text());assert m==fixture_pins[f'n{n}']
        for f,h in m['file_sha256'].items():assert base.sha(root/f'fixtures/n{n}'/f)==h
    def run(label,v,n,q,r,mode='check',tool=None):
        out=root/'runs'/label;out.mkdir();binary=root/'bin'/v;before=base.snapshot(a.gpu);(out/'before.json').write_text(json.dumps(before,indent=2)+'\n');assert not before['apps'].strip(),'GPU0 occupied'
        cmd=[str(binary),str(root/f'fixtures/n{n}/data.txt'),str(root/f'fixtures/n{n}/q{q}.txt'),str(r),'D',mode]
        if tool in ['memcheck','synccheck','initcheck','racecheck']:cmd=['compute-sanitizer','--tool',tool,'--error-exitcode','90']+cmd
        if tool=='nsys':cmd=['nsys','profile','--trace=cuda,nvtx','--sample=none','--cpuctxsw=none','--capture-range=cudaProfilerApi','--capture-range-end=stop','--export=sqlite','--output='+str(out/'trace')]+cmd
        if tool=='ncu':
            sections=['SpeedOfLight','MemoryWorkloadAnalysis_Tables','LaunchStats','Occupancy','SchedulerStats','WarpStateStats','SourceCounters','InstructionStats']
            prefix=['sudo','-n','/usr/bin/timeout','--signal=TERM','--kill-after=10s','600s','/usr/bin/env','CUDA_VISIBLE_DEVICES='+a.gpu,'HOME='+str(out/'home'),'/opt/nvidia/nsight-compute/2025.4.1/ncu','--profile-from-start','off','--clock-control','none','--cache-control','none','--kernel-name','mergeResRnn','--launch-count','1','--export',str(out/'trace')]
            (out/'home').mkdir()
            for section in sections:prefix+=['--section',section]
            cmd=prefix+cmd
        else:cmd=['/usr/bin/timeout','--signal=TERM','--kill-after=10s','300s']+cmd
        start=time.time()
        with (out/'stdout.log').open('w') as o,(out/'stderr.log').open('w') as er:rc=subprocess.run(cmd,cwd=out,env={**os.environ,'CUDA_VISIBLE_DEVICES':a.gpu},stdout=o,stderr=er).returncode
        after=base.snapshot(a.gpu);(out/'after.json').write_text(json.dumps(after,indent=2)+'\n');t=(out/'stdout.log').read_text()+(out/'stderr.log').read_text()
        rec={'command':cmd,'exit_code':rc,'correct':'correct,full_integer_oracle' in t and 'pass' in t.splitlines(),'post_clear':not after['apps'].strip(),'binary_sha256':base.sha(binary),'wall_s':time.time()-start,'variant':v,'n':n,'q':q,'r':r,'mode':mode,'tool':tool}
        (out/'receipt.json').write_text(json.dumps(rec,indent=2)+'\n');print(label,rc,rec['correct'],rec['wall_s'],flush=True)
        assert rc==0 and rec['correct'] and rec['post_clear'],'failed/contaminated; stop'
        if tool=='ncu':
            for page in ['raw','source','details']:
                c=['/opt/nvidia/nsight-compute/2025.4.1/ncu','--import',str(out/'trace.ncu-rep'),'--page',page]
                if page in ['raw','source']:c+=['--csv']
                if page=='raw':c+=['--print-units','base']
                if page=='source':c+=['--print-source','sass']
                if page=='details':c+=['--print-details','all']
                with (out/(page+'.txt' if page=='details' else page+'.csv')).open('w') as o:subprocess.run(c,stdout=o,stderr=subprocess.STDOUT,check=True)
    if a.stage=='preflight':
        for n,q,r in [(2000,32,300),(65536,128,500)]:
            for tool in [None,'memcheck','synccheck']:run(f'pre_{n}_{tool}_A','A',n,q,r,tool=tool)
        run('pre_timing_A','A',65536,128,500,'timing');run('pre_nsys_A','A',65536,128,500,'profile','nsys')
    elif a.stage=='gates':
        for v in 'AB':
            for n,q,r in CASES:run(f'check_{n}_{q}_{r}_{v}',v,n,q,r)
            for n,q,r in [CASES[0],CASES[-1]]:
                for tool in ['memcheck','synccheck']:run(f'{tool}_{n}_{q}_{r}_{v}',v,n,q,r,tool=tool)
        for tool in ['racecheck','initcheck']:run(tool+'_B','B',2000,32,300,tool=tool)
    else:
        for v in 'AB':
            for n,q,r in CASES:
                g=json.loads((root/'runs'/f'check_{n}_{q}_{r}_{v}'/'receipt.json').read_text());assert g['correct'] and g['exit_code']==0 and g['binary_sha256']==base.sha(root/'bin'/v)
        for v in 'AB':
            for n,q,r in [CASES[0],CASES[-1]]:
                for tool in ['memcheck','synccheck']:
                    g=json.loads((root/'runs'/f'{tool}_{n}_{q}_{r}_{v}'/'receipt.json').read_text());assert g['exit_code']==0 and g['correct'] and g['binary_sha256']==base.sha(root/'bin'/v)
        for tool in ['initcheck','racecheck']:
            g=json.loads((root/'runs'/(tool+'_B')/'receipt.json').read_text());assert g['exit_code']==0 and g['correct'] and g['binary_sha256']==base.sha(root/'bin/B')
        if a.stage!='stress':
            for v in 'AB':
                for n,q,r in [CASES[1],CASES[-1]]:
                    g=json.loads((root/'runs'/f'stress_{q}_{r}_0_{v}'/'receipt.json').read_text());assert g['exit_code']==0 and g['correct'] and g['binary_sha256']==base.sha(root/'bin'/v)
        if a.stage=='timing':
            for n,q,r in CASES[1:]:
                for pair in range(6):
                    for v in ('AB' if pair%2==0 else 'BA'):run(f'timing_{q}_{r}_{pair}_{v}',v,n,q,r,'timing')
        elif a.stage=='profile':
            for tool in ['nsys','ncu']:
                for v in 'AB':run(f'{tool}_{v}',v,65536,128,500,'profile',tool)
        else:
            for n,q,r in [CASES[1],CASES[-1]]:
                for pair in range(1 if a.stage=='stress' else 3):
                    for v in ('AB' if pair%2==0 else 'BA'):run(f'{a.stage}_{q}_{r}_{pair}_{v}',v,n,q,r,a.stage)
if __name__=='__main__':main()
