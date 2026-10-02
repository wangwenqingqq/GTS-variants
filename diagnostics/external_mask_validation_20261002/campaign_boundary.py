#!/usr/bin/env python3
"""Small independent-CPU qualification for the four cuVS arithmetic paths."""
import csv
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
P0 = Path('/home/data/wangxuran/tmp/gts_batch_exact_highdim_20261001/fixtures/small')
P4 = Path('/home/data/wangxuran/tmp/gts_p4_tree_batch_20261002')
GPU = 'GPU-e5a0e7f5-9917-c2a1-ee8e-7282cbba2603'
CASES = ((2,4096,1),(31,4096,3),(32,4096,32),(33,4096,8),
         (33,4103,32),(96,4103,3),(960,4103,33))
MODES = ('LIB64_U','LIB64_X','LIB32_U','LIB32_X')


def main():
    summary=[]
    for d,n,b in CASES:
        name=f'd{d}_n{n}_b{b}'
        old=P0/f'd{d}_n{n}'
        new=P4/'fixtures/small'/f'd{d}_n{n}'
        source=new if b==33 else old
        oracle=P4/'runs/small_matrix_v3/results'/name/'cpu.bin'
        assert oracle.exists(), oracle
        for mode in MODES:
            label=f'boundary_v2_{name}_{mode}'
            folder=ROOT/'runs'/label
            command=[sys.executable,str(ROOT/'run_p4.py'),'--gpu',GPU,
                     '--output',str(folder),'--',str(ROOT/'p5_external'),
                     str(old/'data.f32bin'),str(old/'idlist.i32'),
                     str(source/f'q{b}.qid'),str(source/f'q{b}.qid'),
                     mode,'@'+str(source/f'r{b}.f32'),str(b),'2','0',
                     str(folder/'result'),'1']
            if not folder.exists():
                subprocess.run(command,check=True,stdout=subprocess.DEVNULL,env=os.environ)
                result=subprocess.check_output([sys.executable,str(ROOT/'compare_outputs.py'),
                                                str(oracle),str(folder/'result.bin')],text=True)
                (folder/'qualification.json').write_text(result)
                (folder/'result.bin').unlink()
            q=json.loads((folder/'qualification.json').read_text())
            summary.append((d,n,b,mode,q['qualification'],q['false_negatives'],
                            q['false_positives'],q['bitwise_field_mismatches'],
                            q['tolerance_field_mismatches'],q.get('max_abs_error',0.0)))
            print('PASS',label,q['qualification'],q['false_negatives'],
                  q['false_positives'],flush=True)
    with (ROOT/'boundary_qualification.csv').open('w') as f:
        w=csv.writer(f);w.writerow(('d','n','B','mode','qualification','false_negatives',
                                    'false_positives','bitwise_field_mismatches',
                                    'tolerance_field_mismatches','max_abs_error'))
        w.writerows(summary)


if __name__=='__main__':main()
