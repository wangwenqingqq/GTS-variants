#!/usr/bin/env python3
"""Check compact fallback on empty, zero, all-hit, and sanitizer cases."""
import fcntl
import importlib.util
import json
from pathlib import Path

ROOT=Path('/home/ls/tmp/gts_compact_cutoff_20260927')
spec=importlib.util.spec_from_file_location('cutoff_runner',ROOT/'run.py')
runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)

def main():
    cases=(
        ('Tloc','zero','zero.qid','clean'),
        ('Tloc','all','all.qid','clean'),
        ('Tloc','empty','negative.qid','clean'),
        ('GIST','zero','zero.qid','clean'),
        ('GIST','empty','negative.qid','clean'),
        ('Tloc','normal','queries.qid','memcheck'),
        ('Tloc','normal','queries.qid','synccheck'),
    )
    for dataset,kind,qfile,tool in cases:
        path=ROOT/'data'/dataset/'1000000'
        radius=json.loads((path/'fixtures/oracle.json').read_text())['radii'][kind]
        label=f'boundary_{dataset.lower()}_{kind}_{tool}'
        existing=path/'runs'/label
        if (existing/'receipt.json').exists():
            receipt=json.loads((existing/'receipt.json').read_text())
            if receipt['exit_code']==0 and receipt['validation']['pass']:
                print('PASS',dataset,kind,tool,'(existing)',flush=True)
                continue
        if existing.exists():label+='_retry1'
        state=runner.snapshot('0')
        assert not state['apps'].strip(),'GPU occupied'
        index=state['gpu'].split(',')[0].strip()
        with open('/tmp/gtspp_gpu'+index+'.lock','r+') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            ok=runner.execute(path,'0',label,'C3',radius,1,0,tool,False,qfile)
        if not ok:raise RuntimeError(label)
        print('PASS',dataset,kind,tool,flush=True)

if __name__=='__main__':main()
