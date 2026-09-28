#!/usr/bin/env python3
"""Paired latency validation of compact-frontier fixed-depth choices."""
import csv
import json
from pathlib import Path
import subprocess

ROOT=Path('/home/ls/tmp/gts_compact_cutoff_20260927')
ORDERS={
    'GIST':(('F','C1'),('C1','F'),('F','C1')),
    'Deep':(('C1','F'),('F','C1'),('C1','F')),
    'Tloc':(('F','C2','C3','C4','J'),('J','C4','C3','C2','F'),
            ('C3','F','J','C2','C4'),('C4','C2','J','F','C3'),
            ('C2','C3','F','C4','J')),
}

def run_one(dataset,round_index,mode):
    path=ROOT/'data'/dataset/'1000000'
    radius=json.loads((path/'fixtures/oracle.json').read_text())['radii']['normal']
    base=f'paired_{round_index}_{dataset.lower()}_{mode.lower()}'
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
                 '--warmup','8','--repeats','1']
        result=subprocess.run(command,cwd=ROOT,text=True,capture_output=True)
        if result.returncode:
            print(result.stdout,result.stderr,flush=True)
            raise RuntimeError(label)
    run=path/'runs'/label
    with (run/'result.csv').open() as file:
        samples=list(csv.DictReader(file))
    ms=sum(float(row['query_us']) for row in samples)/len(samples)/1000
    print(f'{round_index} {dataset} {mode} {ms:.6f} ms',flush=True)

def main():
    for round_index in range(5):
        if round_index<3:
            order=('GIST','Deep','Tloc') if round_index%2==0 else ('Tloc','Deep','GIST')
        else:order=('Tloc',)
        for dataset in order:
            for mode in ORDERS[dataset][round_index]:
                run_one(dataset,round_index,mode)

if __name__=='__main__':main()
