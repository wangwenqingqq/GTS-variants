#!/usr/bin/env python3
"""One-pass exact fixed-depth screen; every mode uses the same binary and GPU."""
import argparse
import csv
import json
from pathlib import Path
import subprocess

ROOT=Path('/home/ls/tmp/gts_fixed_cutoff_20260927')
DATASETS=('GIST','Deep','Tloc')
MODES=('F','D1','D2','D3','D4','D5','J')

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--datasets',nargs='+',choices=DATASETS,default=DATASETS)
    args=parser.parse_args()
    for dataset in args.datasets:
        path=ROOT/'data'/dataset/'1000000'
        radius=json.loads((path/'fixtures/oracle.json').read_text())['radii']['normal']
        for mode in MODES:
            base='screen_'+dataset.lower()+'_'+mode.lower()
            label=base
            attempt=0
            while (path/'runs'/label).exists():
                old=path/'runs'/label/'receipt.json'
                if old.exists():
                    record=json.loads(old.read_text())
                    if record['exit_code']==0 and record['validation']['pass']:
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
            receipt=json.loads((run/'receipt.json').read_text())
            assert receipt['validation']['pass']
            with (run/'result.csv').open() as file:
                samples=list(csv.DictReader(file))
            ms=sum(float(row['query_us']) for row in samples)/len(samples)/1000
            print(f'{dataset} {mode} {ms:.6f} ms, exact={receipt["validation"]["pass"]}',flush=True)

if __name__=='__main__':main()
