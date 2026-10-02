#!/usr/bin/env python3
"""Frozen Deep development selection, full-output audit, and P3 timing."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import sys

from campaign import ROOT, OLD, GPU
from campaign_p2 import compare

DATA = OLD/'data/Deep/1000000/fixtures/data.f32bin'
IDLIST = OLD/'reference_v2/Deep_idlist.i32'
BITS = {'normal':'0x3f8a3818', 'half':'0x3f0a3818'}
MODES = ('GRID_L','TILE_L','GRID_E','TILE_E')


def oracle(kind, split):
    label = f'batch_{split}_FR_{kind}_20261001'
    path = OLD/'data/Deep/1000000/runs'/label
    with (path/'result.csv').open() as f:
        expected = [(int(r['qid']),int(r['count']),int(r['ordered_hash']))
                    for r in csv.DictReader(f)]
    return expected,path/'result.bin'


def execute(label, mode, batch, qt, split, kind='normal', reverse=False, dump=False):
    out = ROOT/'runs'/label
    cmd = [sys.executable,str(ROOT/'run_batch.py'),str(ROOT/'bin/batch_bench_v2'),
           str(DATA),str(IDLIST),str(ROOT/f'fixtures/Deep_{split}.qid'),
           str(ROOT/'fixtures/Deep_dev256.qid'),mode,BITS[kind],str(batch),str(qt),
           str(out),'--gpu',GPU]
    if reverse: cmd.append('--reverse')
    if dump: cmd.append('--dump')
    subprocess.run(cmd,check=True)
    receipt=json.loads((out/'receipt.json').read_text())
    assert receipt['runtime_valid'] and receipt['mode']==mode
    assert receipt['batch']==batch and receipt['tile']==qt
    return out


def verify(out, batch, expected):
    with (out/'result_queries.csv').open() as f:
        found=list(csv.DictReader(f))
    found.sort(key=lambda r:int(r['query_index']))
    assert [(int(r['qid']),int(r['count']),int(r['ordered_hash']))
            for r in found]==expected,out
    with (out/'result.csv').open() as f:
        rows=list(csv.DictReader(f))
    assert len(rows)==len(expected)//batch
    for row in rows:
        i=int(row['batch_id'])
        count=sum(e[1] for e in expected[i*batch:(i+1)*batch])
        assert int(row['result_count_total'])==count
        assert int(row['d2h_bytes'])==8*(batch+1)+8*count
        assert float(row['host_ms'])>0 and float(row['gpu_ms'])>0
    return sum(float(r['host_ms']) for r in rows)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase',choices=('sweep','audit','formal'))
    parser.add_argument('--qt',type=int,default=2)
    args=parser.parse_args()
    if args.phase=='sweep':
        results=[]
        for kind in ('normal','half'):
            expected,binary=oracle(kind,'dev256')
            assert len(expected)==256 and binary.exists()
            for qt in (1,2,4,8):
                for mode in ('TILE_L','TILE_E'):
                    label=f'sweep_deep_{kind}_qt{qt}_{mode}'
                    out=execute(label,mode,32,qt,'dev256',kind,dump=True)
                    ms=verify(out,32,expected)
                    digest=compare(binary,out/'result.bin',False)
                    (out/'output.sha256').write_text(digest+'\n')
                    (out/'result.bin').unlink()
                    results.append((kind,qt,mode,ms))
                    print('SWEEP PASS',*results[-1],flush=True)
        with (ROOT/'qt_sweep_deep.csv').open('w') as f:
            w=csv.writer(f);w.writerow(('radius','Q_T','mode','host_ms'))
            w.writerows(results)
        for qt in (1,2,4,8):
            score=sum(ms for _,tile,_,ms in results if tile==qt)
            print('SCORE',qt,score,flush=True)
        return
    expected,binary=oracle('normal','final1024')
    assert len(expected)==1024
    if args.phase=='audit':
        for batch in (1,32,128):
            modes=('GRID_L','GRID_E') if batch==1 else MODES
            for mode in modes:
                label=f'audit_deep_normal_b{batch}_{mode}'
                out=execute(label,mode,batch,args.qt,'final1024',dump=True)
                verify(out,batch,expected)
                digest=compare(binary,out/'result.bin',False)
                (out/'output.sha256').write_text(digest+'\n')
                (out/'result.bin').unlink()
                print('AUDIT PASS',batch,mode,flush=True)
        return
    for round_no in range(1,7):
        batches=(1,32,128)
        sizes=batches[(round_no-1)%3:]+batches[:(round_no-1)%3]
        for batch in sizes:
            base=('GRID_L','GRID_E') if batch==1 else MODES
            modes=base[(round_no-1)%len(base):]+base[:(round_no-1)%len(base)]
            for mode in modes:
                label=f'formal_deep_normal_r{round_no}_b{batch}_{mode}'
                out=execute(label,mode,batch,args.qt,'final1024',reverse=round_no%2==0)
                ms=verify(out,batch,expected)
                print('FORMAL PASS',round_no,batch,mode,round(ms,3),flush=True)


if __name__=='__main__': main()
