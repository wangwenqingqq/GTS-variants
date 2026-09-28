#!/usr/bin/env python3
"""Frozen paired Q/J/F complete-query timing campaign."""
import argparse,json
from pathlib import Path
import subprocess

ROOT=Path('/home/data/wangxuran/tmp/gts_20260922_cpu_io/flat_scan_l2_20260924')
ORDERS=('QJF','FJQ','JFQ','QFJ')

def main(gpu):
    assert (ROOT/'logs/full_gate_COMPLETE').exists()
    assert (ROOT/'logs/gates_COMPLETE').exists()
    with (ROOT/'logs/timing.txt').open('x') as log:
        for i,order in enumerate(ORDERS):
            for ds in (('GIST','Deep') if i%2==0 else ('Deep','GIST')):
                path=ROOT/'data'/ds/'1000000'
                radius=json.loads((path/'fixtures/oracle.json').read_text())['radii']['normal']
                for mode in order:
                    label=f'timing_{i}_{mode}'
                    cmd=['python3',str(ROOT/'run.py'),str(path),'--gpu',gpu,
                         '--label',label,'--mode',mode,'--radius',str(radius),
                         '--warmup','8','--repeats','1']
                    print('START',i,ds,mode,flush=True)
                    subprocess.run(cmd,cwd=ROOT,stdout=log,stderr=log,check=True)
                    print('DONE',i,ds,mode,flush=True)
    (ROOT/'logs/timing_COMPLETE.json').write_text(json.dumps(
        {'gpu':gpu,'orders':ORDERS,'runs':24})+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--gpu',default='4');a=p.parse_args()
    main(a.gpu)
