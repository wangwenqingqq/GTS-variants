#!/usr/bin/env python3
"""Independent mechanisms through the inherited locked, monitored runner."""
import argparse
import fcntl
import hashlib
import json
from pathlib import Path
import sys
MODES='DEFGPQ'
ORDERS=['DEFGPQ','QPGFED','EFPGQD','DQGPFE','FPEDQG','GQDEPF']
TOOLS=['memcheck','synccheck','initcheck','racecheck']


def expected_tool(label):
    if label.startswith('nsys_'):return 'nsys-node'
    if label.startswith(('gate_','traversal_')):
        tool=label.split('_')[1];assert tool in TOOLS+['clean'];return tool
    assert label.startswith(('full_','stress_','timing_','sustained_')),label
    return 'clean'


def gate_labels():
    return (['traversal_'+t for t in TOOLS]+
            [f'gate_{t}_{m}' for t in TOOLS for m in (MODES if t in TOOLS[:2] else 'FGPQ')]+
            ['stress_'+m for m in MODES])


def main():
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('stage',choices=['smoke','gates','timing','trace']);p.add_argument('--gpu',required=True)
    a=p.parse_args();root=a.root.resolve();sys.path.insert(0,str(root))
    from run_ablation import execute,snapshot
    if a.stage!='smoke':
        full=json.loads((root/'full_verified.json').read_text())
        assert full['binary_sha256']==hashlib.sha256((root/'bin/graph_bench').read_bytes()).hexdigest()
    if a.stage in ['timing','trace']:
        for label in gate_labels():
            r=json.loads((root/'runs'/label/'receipt.json').read_text())
            assert r['exit_code']==0 and not r['runtime_errors'] and r['stop_reason'] is None and r['post_gpu_clear'] and r['validation']['pass'],label
            assert r['label']==label and r['tool']==expected_tool(label),label
            mode='V' if label.startswith('traversal_') else label[-1]
            assert r['mode']==mode and r['radius']==4
            assert r['binary_sha256']==hashlib.sha256((root/'bin'/('test_traversal' if mode=='V' else 'graph_bench')).read_bytes()).hexdigest()
            assert r['runner_sha256']==hashlib.sha256((root/'run_ablation.py').read_bytes()).hexdigest()
            assert (r['repeats'],r['warmup'])==((256,64) if label.startswith('stress_') else (1,0))
            if r['tool'] in TOOLS:
                logs=(root/'runs'/label/'stdout.log').read_text()+(root/'runs'/label/'stderr.log').read_text()
                assert ('RACECHECK SUMMARY: 0 hazards' if r['tool']=='racecheck' else 'ERROR SUMMARY: 0 errors') in logs,label
    state=snapshot(a.gpu);assert not state['apps'].strip();index=state['gpu'].split(',')[0].strip()
    with open('/tmp/gtspp_gpu'+index+'.lock','r+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        def run(label,m,r=4,repeats=1,warmup=0,tool='clean',dump=False):
            assert execute(root,a.gpu,label,m,r,repeats,warmup,tool,dump),label
        if a.stage=='smoke':
            run('traversal_clean','V')
            for r in [0,4,256]:
                for m in 'A'+MODES:run(f'full_{r}_{m}',m,r,dump=True)
            for m in MODES:run(f'full_-1_{m}',m,-1,dump=True)
        elif a.stage=='gates':
            for t in TOOLS:run('traversal_'+t,'V',tool=t)
            for t in TOOLS:
                for m in (MODES if t in TOOLS[:2] else 'FGPQ'):run(f'gate_{t}_{m}',m,tool=t)
            for m in MODES:run('stress_'+m,m,repeats=256,warmup=64)
        elif a.stage=='timing':
            for i,order in enumerate(ORDERS):
                for m in order:run(f'timing_{i}_{m}',m,repeats=64,warmup=64)
            for r in [0,4,256]:
                for i,order in enumerate([MODES,MODES[::-1]]):
                    for m in order:run(f'sustained_{r}_{i}_{m}',m,r,repeats=256,warmup=64)
        else:
            for m in 'EFP':run('nsys_'+m,m,repeats=2,warmup=64,tool='nsys-node')


if __name__=='__main__':main()
