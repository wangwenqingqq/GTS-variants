#!/usr/bin/env python3
"""Run the preregistered stages through the existing monitored process harness."""
import argparse
import fcntl
import hashlib
import json
from pathlib import Path
import sys

ORDERS=['BCDE','EDCB','CEBD','DBEC','DEBC','CBED']

def main():
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('stage',choices=['smoke','gates','timing','trace']);p.add_argument('--gpu',required=True)
    a=p.parse_args();root=a.root.resolve();sys.path.insert(0,str(root))
    from run_fusion import execute,snapshot
    if a.stage!='smoke':
        gold=json.loads((root/'full_verified.json').read_text())
        assert gold['binary_sha256']==hashlib.sha256((root/'bin/graph_bench').read_bytes()).hexdigest()
        assert all((root/'fixtures'/f'expected_{r}.json').exists() for r in [-1,0,4,256])
    if a.stage in ['timing','trace']:
        for label in ['selector_'+t for t in ['memcheck','synccheck','initcheck','racecheck']]+['gate_'+t+'_'+m for t in ['memcheck','synccheck'] for m in 'BCDE']+['gate_'+t+'_'+m for t in ['initcheck','racecheck'] for m in 'DE']+['stress_'+m for m in 'BCDE']:
            rec=json.loads((root/'runs'/label/'receipt.json').read_text())
            assert rec['exit_code']==0 and rec['stop_reason'] is None and not rec['runtime_errors'] and rec['post_gpu_clear'] and rec['validation']['pass'],label
    state=snapshot(a.gpu);assert not state['apps'].strip();index=state['gpu'].split(',')[0].strip()
    with open('/tmp/gtspp_gpu'+index+'.lock','r+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        def run(label,m,r=4,repeats=1,warmup=0,tool='clean',dump=False):
            assert execute(root,a.gpu,label,m,r,repeats,warmup,tool,dump),label
        if a.stage=='smoke':
            run('selector_clean','T')
            for r in [0,4,256]:
                for m in 'ABCDE':run(f'full_{r}_{m}',m,r,dump=True)
            for m in 'BCDE':run(f'full_-1_{m}',m,-1,dump=True)
        elif a.stage=='gates':
            for tool in ['memcheck','synccheck','initcheck','racecheck']:run('selector_'+tool,'T',tool=tool)
            for tool in ['memcheck','synccheck']:
                for m in 'BCDE':run(f'gate_{tool}_{m}',m,tool=tool)
            for tool in ['initcheck','racecheck']:
                for m in 'DE':run(f'gate_{tool}_{m}',m,tool=tool)
            for m in 'BCDE':run('stress_'+m,m,repeats=256,warmup=64)
        elif a.stage=='timing':
            for i,order in enumerate(ORDERS):
                for m in order:run(f'timing_{i}_{m}',m,repeats=64,warmup=64)
            for r in [0,4,256]:
                for i,order in enumerate(['BCDE','EDCB']):
                    for m in order:run(f'sustained_{r}_{i}_{m}',m,r,repeats=256,warmup=64)
        else:
            for m in 'CE':run('nsys_'+m,m,repeats=2,warmup=64,tool='nsys-node')

if __name__=='__main__':main()
