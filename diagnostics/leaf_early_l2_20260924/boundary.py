#!/usr/bin/env python3
"""Check the early-reject arm at zero, all-hit, and empty radii."""
import argparse
from pathlib import Path
import subprocess

ROOT=Path('/home/data/wangxuran/tmp/gts_20260922_cpu_io/leaf_early_l2_20260924')
CASES=(('zero','zero.qid'),('all','all.qid'),('empty','negative.qid'))

def main(gpu):
    with (ROOT/'logs/boundary.txt').open('x') as log:
        for dataset in ('GIST','Deep'):
            for kind,qfile in CASES:
                label=f'boundary_{kind}_J'
                print('START',dataset,kind,flush=True)
                cmd=['python3',str(ROOT/'case.py'),dataset,'--gpu',gpu,'--mode','J',
                     '--qfile',qfile,'--radius-kind',kind,'--label',label]
                subprocess.run(cmd,stdout=log,stderr=log,check=True)
                print('DONE',dataset,kind,flush=True)
    (ROOT/'logs/boundary_COMPLETE').write_text('6 pass\n')

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--gpu',required=True)
    a=p.parse_args()
    main(a.gpu)
