#!/usr/bin/env python3
"""Paired complete-query timing on one idle GPU and one binary."""
import json
import subprocess
from pathlib import Path

ROOT=Path('/home/ls/tmp/gts_pca_end_to_end_20260925')
ORDERS=(('F','P32','P64'),('P64','F','P32'),('P32','P64','F'),('F','P64','P32'))
RADIUS={'GIST':1.411250114440918,'Deep':1.0798368453979492}

def main():
    for ds in ('GIST','Deep'):
        for mode in ('F','P32','P64'):
            p=ROOT/'data'/ds/'1000000'/'runs'/f'{ds.lower()}_{mode}_gate'/'receipt.json'
            assert json.loads(p.read_text())['validation']['pass'],p
    records=[]
    for round_id,order in enumerate(ORDERS):
        datasets=('GIST','Deep') if round_id%2==0 else ('Deep','GIST')
        for ds in datasets:
            root=ROOT/'data'/ds/'1000000'
            for mode in order:
                label=f'timing_{round_id}_{mode}'
                cmd=['python3',str(ROOT/'run.py'),str(root),'--gpu','0','--label',label,
                     '--mode',mode,'--radius',str(RADIUS[ds]),'--warmup','8','--repeats','1']
                print('START',round_id,ds,mode,flush=True)
                with (ROOT/'logs/timing_runner.log').open('a') as log:
                    subprocess.run(cmd,cwd=ROOT,check=True,stdout=log)
                receipt=json.loads((root/'runs'/label/'receipt.json').read_text())
                assert receipt['validation']['pass'] and receipt['stop_reason'] is None
                records.append({'round':round_id,'dataset':ds,'mode':mode,'label':label,
                                'receipt':str(root/'runs'/label/'receipt.json')})
                print('DONE',round_id,ds,mode,flush=True)
                (ROOT/'logs/timing_progress.json').write_text(json.dumps(records,indent=2)+'\n')
    (ROOT/'logs/timing_COMPLETE.json').write_text(json.dumps({'orders':ORDERS,'runs':records},indent=2)+'\n')

if __name__=='__main__':main()
