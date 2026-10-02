#!/usr/bin/env python3
"""Freeze cuVS chunk size on existing development IDs, before fresh final IDs."""
import csv
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parent
BASE=Path('/home/data/wangxuran/tmp/gts_arithmetic_path_boundary_20260928')
P0=Path('/home/data/wangxuran/tmp/gts_batch_exact_highdim_20261001')
GPU='GPU-e5a0e7f5-9917-c2a1-ee8e-7282cbba2603'
MODES=('LIB64_U','LIB64_X','LIB32_U')
CHUNKS=(65536,262144,1000000)
WORK=(('GIST','half','0x3f34a3d8'),('GIST','normal','0x3fb4a3d8'),
      ('Deep','normal','0x3f8a3818'))


def main():
    results=[]
    for dataset,radius,bits in WORK:
        data=BASE/f'data/{dataset}/1000000/fixtures/data.f32bin'
        order=BASE/f'reference_v2/{dataset}_idlist.i32'
        qids=P0/'fixtures'/f'{dataset}_dev256.qid'
        for batch in (8,32):
            for chunk in CHUNKS:
                for mode in MODES:
                    label=f'screen_{dataset.lower()}_{radius}_b{batch}_{mode}_n{chunk}'
                    out=ROOT/'runs'/label
                    cmd=[sys.executable,str(ROOT/'run_p4.py'),'--gpu',GPU,'--output',str(out),
                         '--',str(ROOT/'p5_external'),str(data),str(order),str(qids),str(qids),
                         mode,bits,str(batch),'2','0',str(out/'result'),'0',str(chunk)]
                    subprocess.run(cmd,check=True,stdout=subprocess.DEVNULL,env=os.environ)
                    rows=list(csv.DictReader((out/'result.csv').open()))
                    assert len(rows)==256//batch
                    host=sum(float(row['host_ms']) for row in rows)
                    gpu=sum(float(row['gpu_ms']) for row in rows)
                    results.append((dataset,radius,batch,mode,chunk,host,gpu,
                                    sum(int(row['result_count_total']) for row in rows)))
                    print('PASS',label,round(host,3),flush=True)
    with (ROOT/'chunk_screen.csv').open('w') as f:
        w=csv.writer(f);w.writerow(('dataset','radius','B','mode','chunk_n',
                                    'host_total_ms','gpu_total_ms','hits'))
        w.writerows(results)


if __name__=='__main__':main()
