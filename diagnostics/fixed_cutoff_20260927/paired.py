#!/usr/bin/env python3
"""Three paired repetitions of the screen finalists with exact output checks."""
import csv
import json
from pathlib import Path
import subprocess

ROOT=Path('/home/ls/tmp/gts_fixed_cutoff_20260927')
PAIRS={
    'GIST':(('F','D1'),('D1','F'),('F','D1')),
    'Deep':(('D1','F'),('F','D1'),('D1','F')),
    'Tloc':(('F','D3','J'),('J','D3','F'),('D3','F','J')),
}

def main():
    for round_index in range(3):
        for dataset in (('GIST','Deep','Tloc') if round_index%2==0 else ('Tloc','Deep','GIST')):
            path=ROOT/'data'/dataset/'1000000'
            radius=json.loads((path/'fixtures/oracle.json').read_text())['radii']['normal']
            for mode in PAIRS[dataset][round_index]:
                label=f'paired_{round_index}_{dataset.lower()}_{mode.lower()}'
                run=path/'runs'/label
                if not (run/'receipt.json').exists():
                    command=['python3',str(ROOT/'run.py'),str(path),'--gpu','0',
                             '--label',label,'--mode',mode,'--radius',str(radius),
                             '--warmup','8','--repeats','1']
                    result=subprocess.run(command,cwd=ROOT,text=True,capture_output=True)
                    if result.returncode:
                        print(result.stdout,result.stderr,flush=True)
                        raise RuntimeError(label)
                receipt=json.loads((run/'receipt.json').read_text())
                assert receipt['exit_code']==0 and receipt['validation']['pass']
                with (run/'result.csv').open() as file:
                    samples=list(csv.DictReader(file))
                ms=sum(float(row['query_us']) for row in samples)/len(samples)/1000
                print(f'{round_index} {dataset} {mode} {ms:.6f} ms',flush=True)

if __name__=='__main__':main()
