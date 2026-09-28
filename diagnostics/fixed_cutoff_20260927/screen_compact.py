#!/usr/bin/env python3
"""Exact screen for compact-frontier fallback and same-binary baselines."""
import argparse
import csv
import json
from pathlib import Path
import subprocess

ROOT=Path('/home/ls/tmp/gts_compact_cutoff_20260927')
DATASETS=('GIST','Deep','Tloc')
MODES=('F','C1','C2','C3','C4','C5','J')

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--datasets',nargs='+',choices=DATASETS,default=DATASETS)
    args=parser.parse_args()
    for dataset in args.datasets:
        path=ROOT/'data'/dataset/'1000000'
        radius=json.loads((path/'fixtures/oracle.json').read_text())['radii']['normal']
        for mode in MODES:
            base=f'screen_{dataset.lower()}_{mode.lower()}'
            label=base
            attempt=0
            while (path/'runs'/label).exists():
                old=path/'runs'/label/'receipt.json'
                if old.exists():
                    receipt=json.loads(old.read_text())
                    if receipt['exit_code']==0 and receipt['validation']['pass']:
                        break
                attempt+=1
                label=f'{base}_retry{attempt}'
            else:
                command=['python3',str(ROOT/'run.py'),str(path),'--gpu','0',
                         '--label',label,'--mode',mode,'--radius',str(radius),
                         '--warmup','4','--repeats','1']
                result=subprocess.run(command,cwd=ROOT,text=True,capture_output=True)
                if result.returncode:
                    print(result.stdout,result.stderr,flush=True)
                    raise RuntimeError(label)
            run=path/'runs'/label
            with (run/'result.csv').open() as file:
                samples=list(csv.DictReader(file))
            ms=sum(float(row['query_us']) for row in samples)/len(samples)/1000
            print(f'{dataset} {mode} {ms:.6f} ms',flush=True)

if __name__=='__main__':main()
