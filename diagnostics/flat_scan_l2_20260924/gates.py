#!/usr/bin/env python3
"""F sanitizer and boundary gates; stop on any error."""
from pathlib import Path
import subprocess

ROOT=Path('/home/data/wangxuran/tmp/gts_20260922_cpu_io/flat_scan_l2_20260924')

def main():
    with (ROOT/'logs/gates.txt').open('x') as log:
        for ds in ('GIST','Deep'):
            for tool in ('memcheck','synccheck'):
                label=f'gate_{tool}_F'
                cmd=['python3',str(ROOT/'case.py'),ds,'--mode','F',
                     '--qfile','check.qid','--tool',tool,'--label',label]
                print('START',ds,tool,flush=True)
                subprocess.run(cmd,stdout=log,stderr=log,check=True)
                print('DONE',ds,tool,flush=True)
            for kind,qfile in (('zero','zero.qid'),('all','all.qid'),('empty','negative.qid')):
                label=f'boundary_{kind}_F'
                cmd=['python3',str(ROOT/'case.py'),ds,'--mode','F',
                     '--qfile',qfile,'--radius-kind',kind,'--label',label]
                print('START',ds,kind,flush=True)
                subprocess.run(cmd,stdout=log,stderr=log,check=True)
                print('DONE',ds,kind,flush=True)
    (ROOT/'logs/gates_COMPLETE').write_text('10 pass\n')

if __name__=='__main__':main()
