#!/usr/bin/env python3
"""Separate Nsight Systems trace of the last measured dev32 batch."""
import csv
import hashlib
from pathlib import Path
import sqlite3
import subprocess
import sys

ROOT=Path(__file__).resolve().parent
BASE=Path('/home/data/wangxuran/tmp/gts_arithmetic_path_boundary_20260928')
P0=Path('/home/data/wangxuran/tmp/gts_batch_exact_highdim_20261001')
GPU='GPU-e5a0e7f5-9917-c2a1-ee8e-7282cbba2603'
MODES=('SCAN_E','MASK_ALL_E','TREE_ALL_E','TREE_REAL_E')


def main():
    summary=[]
    for mode in MODES:
        label=f'profile_causal_half_b32_{mode}'
        folder=ROOT/'runs'/label
        command=[sys.executable,str(ROOT/'run_p4.py'),'--gpu',GPU,'--output',str(folder),
                 '--','/usr/local/bin/nsys','profile','--trace=cuda,nvtx','--sample=none',
                 '--cpuctxsw=none','--cuda-graph-trace=node','--force-overwrite=true',
                 '-o',str(folder/'trace'),str(ROOT/'p5_causal'),
                 str(BASE/'data/GIST/1000000/fixtures/data.f32bin'),
                 str(BASE/'reference_v2/GIST_idlist.i32'),
                 str(P0/'fixtures/GIST_dev32_profile.qid'),
                 str(P0/'fixtures/GIST_dev256.qid'),mode,'0x3f34a3d8','32','2','0',
                 str(folder/'result'),'0',str(BASE/'replay/GIST_index.bin'),'4']
        subprocess.run(command,check=True,stdout=subprocess.DEVNULL)
        report=folder/'trace.nsys-rep'
        database=folder/'trace.sqlite'
        subprocess.run(['/usr/local/bin/nsys','export','--type=sqlite',
                        '--output',str(database),str(report)],check=True,
                       stdout=subprocess.DEVNULL)
        with sqlite3.connect(database) as conn:
            names=dict(conn.execute('SELECT id,value FROM StringIds'))
            kernels=[(start,end,names[name]) for start,end,name in conn.execute(
                'SELECT start,end,shortName FROM CUPTI_ACTIVITY_KIND_KERNEL ORDER BY start')]
        target='batchDistance' if mode=='SCAN_E' else 'masked_distance'
        distance=[(end-start)/1e6 for start,end,name in kernels if name==target]
        assert len(distance)==9,(mode,len(distance))
        measured=distance[-1]
        rows=list(csv.DictReader((folder/'result.csv').open()))
        assert len(rows)==1
        summary.append((mode,measured,float(rows[0]['host_ms']),float(rows[0]['gpu_ms']),
                        len(kernels),hashlib.sha256(report.read_bytes()).hexdigest()))
        print('PROFILE',mode,round(measured,3),flush=True)
    with (ROOT/'profile_summary.csv').open('w') as f:
        w=csv.writer(f);w.writerow(('mode','measured_distance_kernel_ms',
                                    'profiled_host_ready_ms','profiled_gpu_ready_ms',
                                    'all_trace_kernel_count','trace_sha256'))
        w.writerows(summary)


if __name__=='__main__':main()
