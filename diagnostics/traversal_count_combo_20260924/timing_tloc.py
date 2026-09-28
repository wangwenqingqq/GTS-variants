#!/usr/bin/env python3
"""Run the frozen four-order Tloc screen; fail without replacing any run."""
import argparse
import json
from pathlib import Path
import subprocess

ORDERS=('EPRQ','QRPE','PREQ','QERP')
RADIUS='3.089289426803589'

def main(root,gpu):
    root=root.resolve()
    assert not (root/'logs/timing_tloc_COMPLETE.json').exists()
    with (root/'logs/timing_tloc.txt').open('x') as log:
        for i,order in enumerate(ORDERS):
            for mode in order:
                label=f'timing_{i}_{mode}'
                cmd=['python3',str(root/'run.py'),str(root/'data/Tloc/1000000'),
                     '--gpu',gpu,'--label',label,'--mode',mode,'--radius',RADIUS,
                     '--warmup','8','--repeats','1']
                print('START',label,flush=True)
                subprocess.run(cmd,cwd=root,stdout=log,stderr=log,check=True)
                print('DONE',label,flush=True)
    (root/'logs/timing_tloc_COMPLETE.json').write_text(json.dumps({'runs':16,'orders':ORDERS})+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('--gpu',required=True)
    a=p.parse_args();main(a.root,a.gpu)
