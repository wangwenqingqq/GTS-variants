#!/usr/bin/env python3
"""Audit and time GIST half/all radii with the frozen P1 binary."""
import argparse
import csv
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from campaign import ROOT, OLD, GPU, DATA, IDLIST, verify


MODES = ('GRID_L', 'TILE_L', 'GRID_E', 'TILE_E')
BATCHES = (1, 32, 128)
RADII = {'half':('0x3f34a3d8','batch_final1024_FR_half_20261001'),
         'all':('0x41cb7260','batch_final1024_FR_all_20261001')}


def reference(kind):
    label = RADII[kind][1]
    path = OLD/'data/GIST/1000000/runs'/label
    with (path/'result.csv').open() as f:
        expected = [(int(r['qid']),int(r['count']),int(r['ordered_hash']))
                    for r in csv.DictReader(f)]
    assert len(expected)==1024
    if kind=='all':
        assert all(count==1000000 for _,count,_ in expected)
        binary = path/'result.bin.gz'
    else:
        binary = path/'result.bin'
    return expected,binary


def run(kind, label, mode, batch, reverse=False, dump=False):
    out = ROOT/'runs'/label
    cmd = [sys.executable,str(ROOT/'run_batch.py'),
           str(ROOT/'bin/batch_bench_v2'),str(DATA),str(IDLIST),
           str(ROOT/'fixtures/GIST_final1024.qid'),
           str(ROOT/'fixtures/GIST_dev256.qid'),mode,RADII[kind][0],
           str(batch),'2',str(out),'--gpu',GPU]
    if reverse:cmd.append('--reverse')
    if dump:cmd.append('--dump')
    subprocess.run(cmd,check=True)
    receipt=json.loads((out/'receipt.json').read_text())
    assert receipt['runtime_valid'] and receipt['batch']==batch and receipt['mode']==mode
    return out


def compare(binary, result, compressed):
    digest=hashlib.sha256()
    opener=gzip.open if compressed else open
    with opener(binary,'rb') as old,result.open('rb') as new:
        while True:
            a=old.read(4*1024*1024)
            b=new.read(len(a) if a else 1)
            assert a==b,(binary,result)
            if not a:break
            digest.update(b)
    return digest.hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('phase',choices=('audit','formal'))
    p.add_argument('radius',choices=tuple(RADII))
    a=p.parse_args()
    expected,binary=reference(a.radius)
    if a.phase=='audit':
        assert binary.exists()
        for batch in BATCHES:
            modes=('GRID_L','GRID_E') if batch==1 else MODES
            for mode in modes:
                label=f'audit_gist_{a.radius}_b{batch}_{mode}'
                out=run(a.radius,label,mode,batch,dump=True)
                verify(out,batch,expected)
                digest=compare(binary,out/'result.bin',a.radius=='all')
                (out/'output.sha256').write_text(digest+'\n')
                (out/'result.bin').unlink()
                print('AUDIT PASS',a.radius,batch,mode,flush=True)
        return
    for round_no in range(1,7):
        sizes=BATCHES[(round_no-1)%3:]+BATCHES[:(round_no-1)%3]
        for batch in sizes:
            base=('GRID_L','GRID_E') if batch==1 else MODES
            modes=base[(round_no-1)%len(base):]+base[:(round_no-1)%len(base)]
            for mode in modes:
                label=f'formal_gist_{a.radius}_r{round_no}_b{batch}_{mode}'
                out=run(a.radius,label,mode,batch,reverse=round_no%2==0)
                total=verify(out,batch,expected)
                print('FORMAL PASS',a.radius,round_no,batch,mode,round(total,3),flush=True)


if __name__=='__main__':main()
