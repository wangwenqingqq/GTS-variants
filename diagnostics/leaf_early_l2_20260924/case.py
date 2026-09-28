#!/usr/bin/env python3
"""Run the frozen monitored runner with a named boundary/query fixture."""
import argparse
import fcntl
import importlib.util
import json
from pathlib import Path

ROOT=Path('/home/data/wangxuran/tmp/gts_20260922_cpu_io/leaf_early_l2_20260924')
spec=importlib.util.spec_from_file_location('leaf_runner',ROOT/'run.py')
runner=importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

def main():
    p=argparse.ArgumentParser()
    p.add_argument('dataset',choices=['GIST','Deep'])
    p.add_argument('--gpu',required=True)
    p.add_argument('--mode',choices=['Q','H','J'],required=True)
    p.add_argument('--qfile',default='queries.qid')
    p.add_argument('--radius-kind',choices=['normal','zero','all','empty'],default='normal')
    p.add_argument('--label',required=True)
    p.add_argument('--tool',choices=['clean','memcheck','synccheck'],default='clean')
    p.add_argument('--binary',default='graph_bench')
    p.add_argument('--dump',action='store_true')
    a=p.parse_args()
    path=ROOT/'data'/a.dataset/'1000000'
    radius=json.loads((path/'fixtures/oracle.json').read_text())['radii'][a.radius_kind]
    state=runner.snapshot(a.gpu)
    assert not state['apps'].strip(), 'GPU occupied'
    index=state['gpu'].split(',')[0].strip()
    with open('/tmp/gtspp_gpu'+index+'.lock','r+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        ok=runner.execute(path,a.gpu,a.label,a.mode,radius,1,0,a.tool,a.dump,a.qfile,a.binary)
    return 0 if ok else 1

if __name__=='__main__':
    raise SystemExit(main())
