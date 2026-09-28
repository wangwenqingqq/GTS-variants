#!/usr/bin/env python3
"""Frozen four-order complete-query timing campaign; stop on any failed run."""
import argparse
import json
from pathlib import Path
import subprocess

ROOT=Path('/home/data/wangxuran/tmp/gts_20260922_cpu_io/leaf_early_l2_20260924')
ORDERS=('QHJ','JHQ','HJQ','QJH')

def main(gpu):
    assert not (ROOT/'logs/timing_COMPLETE.json').exists()
    with (ROOT/'logs/timing.txt').open('x') as log:
        for i,order in enumerate(ORDERS):
            for dataset in (('GIST','Deep') if i%2==0 else ('Deep','GIST')):
                path=ROOT/'data'/dataset/'1000000'
                radius=json.loads((path/'fixtures/oracle.json').read_text())['radii']['normal']
                for mode in order:
                    label=f'timing_{i}_{mode}'
                    cmd=['python3',str(ROOT/'run.py'),str(path),'--gpu',gpu,
                         '--label',label,'--mode',mode,'--radius',str(radius),
                         '--warmup','8','--repeats','1']
                    print('START',i,dataset,mode,flush=True)
                    subprocess.run(cmd,cwd=ROOT,stdout=log,stderr=log,check=True)
                    print('DONE',i,dataset,mode,flush=True)
    (ROOT/'logs/timing_COMPLETE.json').write_text(
        json.dumps({'gpu':gpu,'orders':ORDERS,'runs':24})+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--gpu',required=True)
    a=p.parse_args()
    main(a.gpu)
