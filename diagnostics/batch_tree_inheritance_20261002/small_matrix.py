#!/usr/bin/env python3
"""Compare all P4 paths with independent CPU full enumeration on boundary fixtures."""
import argparse
import csv
import filecmp
import hashlib
from pathlib import Path
import subprocess

CASES=((2,4096,1),(2,4103,33),(31,4096,3),(31,4103,8),
       (32,4096,32),(32,4103,33),(33,4096,8),(33,4103,32),
       (96,4096,33),(96,4103,3),(960,4096,1),(960,4103,33))
MODES=('SCAN_L','SCAN_E','C_ID_L','C_ID_E','C_MASK_L','C_MASK_E','C_TASK_L','C_TASK_E')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('old_fixtures','new_fixtures','bench','oracle','output'):
        p.add_argument(name,type=Path)
    a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=True)
    records=[]
    for d,n,b in CASES:
        name=f'd{d}_n{n}_b{b}'
        out=a.output/name;out.mkdir(exist_ok=False)
        old=a.old_fixtures/f'd{d}_n{n}'
        new=a.new_fixtures/f'd{d}_n{n}'
        q=(new if b==33 else old)/f'q{b}.qid'
        radii=(new if b==33 else old)/f'r{b}.f32'
        reference=out/'cpu.bin'
        subprocess.run([str(a.oracle),str(old/'data.f32bin'),str(old/'idlist.i32'),
                        str(q),str(radii),str(reference)],check=True,stdout=subprocess.DEVNULL)
        digest=hashlib.sha256(reference.read_bytes()).hexdigest()
        for mode in MODES:
            prefix=out/mode
            subprocess.run([str(a.bench),str(old/'data.f32bin'),str(old/'idlist.i32'),
                            str(q),str(q),mode,'@'+str(radii),str(b),'2','0',
                            str(prefix),'1',str(new/'tree_c4.bin'),'4'],
                           check=True,stdout=subprocess.DEVNULL)
            assert filecmp.cmp(reference,Path(str(prefix)+'.bin'),shallow=False),(name,mode)
            records.append((d,n,b,mode,digest))
            print('PASS',name,mode,flush=True)
    with (a.output/'small_correctness.csv').open('w') as f:
        w=csv.writer(f);w.writerow(('d','n','B','mode','cpu_output_sha256'));w.writerows(records)
    print('PASS all',len(records),'full CPU oracle cases',flush=True)


if __name__=='__main__':main()
