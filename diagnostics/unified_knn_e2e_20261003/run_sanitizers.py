#!/usr/bin/env python3
"""Separate admissions prevent short-lived test-child ownership ambiguity."""
import argparse
import json
from pathlib import Path
from types import SimpleNamespace
from campaign import run
from qualification import native_ivf,check_output

ROOT=Path(__file__).resolve().parent

def main():
    p=argparse.ArgumentParser();p.add_argument('--gpu',required=True);a=p.parse_args()
    (ROOT/'runs').mkdir(exist_ok=True);outdir=ROOT/'small_runs';rows=[]
    for d in (96,960):
        data=native_ivf.load_data(ROOT/f'fixtures/small{d}.f32bin')
        reference=json.loads((ROOT/f'fixtures/cpu_small{d}.json').read_text())
        for mode in ('O_FULL','O_BOUND','O_MASK'):
            for tool in ('memcheck','synccheck'):
                label=f'sanitize_v3_{tool}_d{d}_{mode}';out=outdir/label
                cmd=['/usr/local/cuda/bin/compute-sanitizer','--tool',tool,'--error-exitcode',91,ROOT/'opt_knn_bench',
                     ROOT/f'fixtures/small{d}.f32bin',ROOT/'fixtures/small33.qid',ROOT/f'fixtures/small{d}.index',
                     ROOT/'fixtures/seeds_4097.i32',mode,32,32,out,ROOT/'fixtures/small33.qid',0]
                receipt=run(a,label,cmd);text=(ROOT/'runs'/label/'stdout.log').read_text()+(ROOT/'runs'/label/'stderr.log').read_text()
                assert 'ERROR SUMMARY: 0 errors' in text
                q=check_output(str(out)+'.bin',data,reference,32,True)
                rows.append({'label':label,'tool':tool,'D':d,'mode':mode,'quality':q,'runtime_valid':receipt['runtime_valid'],'zero_errors':True})
                print('PASS '+label,flush=True)
    (ROOT/'SANITIZER.json').write_text(json.dumps(rows,indent=2)+'\n')

if __name__=='__main__':main()
