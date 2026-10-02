#!/usr/bin/env python3
"""Check all four P5 causal modes against independent CPU boundary outputs."""
import csv
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parent
P0=Path('/home/data/wangxuran/tmp/gts_batch_exact_highdim_20261001/fixtures/small')
P4=Path('/home/data/wangxuran/tmp/gts_p4_tree_batch_20261002')
GPU='GPU-e5a0e7f5-9917-c2a1-ee8e-7282cbba2603'
CASES=((31,4096,3),(33,4103,32),(960,4103,33))
MODES=('SCAN_E','MASK_ALL_E','TREE_ALL_E','TREE_REAL_E')


def main():
    summary=[]
    for d,n,b in CASES:
        name=f'd{d}_n{n}_b{b}'
        old=P0/f'd{d}_n{n}';new=P4/'fixtures/small'/f'd{d}_n{n}'
        source=new if b==33 else old
        oracle=P4/'runs/small_matrix_v3/results'/name/'cpu.bin'
        for mode in MODES:
            label=f'causal_boundary_{name}_{mode}'
            folder=ROOT/'runs'/label
            cmd=[sys.executable,str(ROOT/'run_p4.py'),'--gpu',GPU,'--output',str(folder),
                 '--',str(ROOT/'p5_causal'),str(old/'data.f32bin'),str(old/'idlist.i32'),
                 str(source/f'q{b}.qid'),str(source/f'q{b}.qid'),mode,
                 '@'+str(source/f'r{b}.f32'),str(b),'2','0',str(folder/'result'),'1',
                 str(new/'tree_c4.bin'),'4']
            subprocess.run(cmd,check=True,stdout=subprocess.DEVNULL,env=os.environ)
            result=subprocess.check_output([sys.executable,str(ROOT/'compare_outputs.py'),
                                            str(oracle),str(folder/'result.bin')],text=True)
            qualification=json.loads(result)['qualification']
            assert qualification=='BITWISE_MATCH_ON_TESTED',(label,result)
            (folder/'qualification.json').write_text(result)
            (folder/'result.bin').unlink()
            summary.append((d,n,b,mode,qualification))
            print('PASS',label,flush=True)
    with (ROOT/'causal_boundary.csv').open('w') as f:
        w=csv.writer(f);w.writerow(('d','n','B','mode','qualification'))
        w.writerows(summary)


if __name__=='__main__':main()
