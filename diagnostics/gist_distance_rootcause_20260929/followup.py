#!/usr/bin/env python3
"""Collect work counts and query-only traces after the clean timing campaign."""
import csv
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path('/home/data/wangxuran/tmp/gts_gist_rootcause_20260929/data/GIST/1000000')
TOP = ROOT.parent.parent.parent
GPU = 'GPU-e5a0e7f5-9917-c2a1-ee8e-7282cbba2603'
RADII = {'normal':1.411250114440918,
         'half':0.705625057220459,
         'all':25.43084716796875}


def rows(path):
    with path.open() as f:
        return list(csv.DictReader(f))


def checked(label, kind, mode):
    path = ROOT / 'runs' / label
    receipt = json.loads((path / 'receipt.json').read_text())
    assert receipt['exit_code'] == 0 and receipt['post_gpu_clear']
    assert not receipt['stop_reason'] and not receipt['runtime_errors']
    observed = rows(path / 'result.csv')
    expected = rows(ROOT / 'runs' / f'audit_{kind}_{mode}' / 'result.csv')
    assert len(observed)==len(expected)==64
    assert [(r['qid'],r['count'],r['ordered_hash']) for r in observed] == [
        (r['qid'],r['count'],r['ordered_hash']) for r in expected]


def run(label,kind,mode,tool,binary,runner):
    path=ROOT / 'runs' / label
    if path.exists():
        checked(label,kind,mode)
        return
    env=os.environ.copy()
    if binary=='graph_bench_count':
        env['GTS_DIMS_OUTPUT']=str(path/'dims.csv')
    args=[sys.executable,str(TOP/runner),str(ROOT),'--gpu',GPU,
          '--label',label,'--mode',mode,'--radius',str(RADII[kind]),
          '--repeats','1','--warmup', '0' if binary=='graph_bench_count' else '8',
          '--qfile','final_v3.qid','--binary',binary,'--tool',tool]
    subprocess.run(args,check=True,env=env)
    checked(label,kind,mode)


def main():
    for kind in RADII:
        for mode in ('B','L','E64','L_E64'):
            label=f'count_{kind}_{mode}'
            run(label,kind,mode,'clean','graph_bench_count','run.py')
            assert len(rows(ROOT/'runs'/label/'dims.csv'))==64
            print('COUNTED',kind,mode,flush=True)
    for kind in RADII:
        for mode in ('B','L','E64','L_E64'):
            label=f'profile_{kind}_{mode}'
            run(label,kind,mode,'nsys-range','graph_bench_profile','run_profile.py')
            assert (ROOT/'runs'/label/'trace.sqlite').exists()
            print('PROFILED',kind,mode,flush=True)
    subprocess.run([sys.executable,str(TOP/'analyze_profile.py')],check=True)
    print('FOLLOWUP PASS',flush=True)


if __name__=='__main__':
    main()
