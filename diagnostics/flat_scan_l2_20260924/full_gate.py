#!/usr/bin/env python3
"""Run Q/J/F complete-output pilots on the preregistered idle GPU."""
import json
from pathlib import Path
import subprocess

ROOT=Path('/home/data/wangxuran/tmp/gts_20260922_cpu_io/flat_scan_l2_20260924')
GPU='4'

def main():
    with (ROOT/'logs/full_gate.txt').open('x') as log:
        for ds in ('GIST','Deep'):
            path=ROOT/'data'/ds/'1000000'
            radius=json.loads((path/'fixtures/oracle.json').read_text())['radii']['normal']
            for mode in 'QJF':
                label=f'full_normal_{mode}'
                cmd=['python3',str(ROOT/'run.py'),str(path),'--gpu',GPU,
                     '--label',label,'--mode',mode,'--radius',str(radius),
                     '--repeats','1','--warmup','0','--dump']
                print('START',ds,mode,flush=True)
                subprocess.run(cmd,stdout=log,stderr=log,check=True)
                print('DONE',ds,mode,flush=True)
    (ROOT/'logs/full_gate_COMPLETE').write_text('6 pass\n')

if __name__=='__main__':main()
