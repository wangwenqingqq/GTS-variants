#!/usr/bin/env python3
"""Finite correctness, paired wait-policy, and NSYS plans; stop on any failed gate."""
import argparse
import json
from pathlib import Path
import subprocess
import sys


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('root', type=Path); p.add_argument('--stage', choices=['check','timing','trace'], required=True)
    p.add_argument('--gpu', required=True); p.add_argument('--index', type=int, required=True)
    a = p.parse_args(); root = a.root.resolve(); plan = []
    def add(label, case, binary='gts_profile', mode='clean', blocking=0):
        plan.append((label, case, binary, mode, blocking))
    if a.stage == 'check':
        for case in ['query128','mixed16']:
            for mode in ['clean','memcheck','synccheck']:
                add('gate_reset_'+case+'_'+mode, case, 'gts_rnum_reset', mode)
            for blocking in [0,1]:
                add('gate_profile_'+case+'_'+str(blocking), case, blocking=blocking)
        for mode in ['memcheck','synccheck']:
            for blocking in [0,1]:
                add('gate_profile_mixed16_'+mode+'_'+str(blocking), 'mixed16', mode=mode, blocking=blocking)
    elif a.stage == 'timing':
        for case in ['query128','mixed16']:
            for pair, order in enumerate(['RDB','BDR','DRB']):
                for policy in order:
                    add(f'timing_{case}_{pair}_{policy}', case,
                        'gts_rnum_reset' if policy=='R' else 'gts_profile', blocking=int(policy=='B'))
    else:
        for case in ['query128','mixed16']:
            for blocking in [0,1]:
                add('trace_'+case+'_'+str(blocking), case, mode='nsys', blocking=blocking)
    plan_path = root/'logs'/('plan_'+a.stage+'.json')
    with plan_path.open('x') as f:
        json.dump({'stage':a.stage,'gpu':a.gpu,'index':a.index,'plan':plan},f,indent=2)
    runner = Path(__file__).resolve().with_name('run_profile.py')
    for label, case, binary, mode, blocking in plan:
        cmd = [sys.executable,str(runner),str(root),'--gpu',a.gpu,'--admitted-index',str(a.index),
               '--label',label,'--case',case,'--binary',binary,'--mode',mode,'--blocking',str(blocking)]
        r = subprocess.run(cmd,stdout=subprocess.PIPE,text=True)
        if r.returncode:
            print(r.stdout,flush=True)
            raise SystemExit('Gate/admission failure: '+label)
        receipt = json.loads((root/'runs'/label/'receipt.json').read_text())
        print(label, 'PASS', len(receipt['validation']['actual']), 'queries', flush=True)


if __name__ == '__main__':main()
