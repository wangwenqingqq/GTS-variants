#!/usr/bin/env python3
"""Audit a completed traversal screen and produce paired latency evidence."""
import argparse
import csv
import itertools
import json
import math
from pathlib import Path
import sqlite3
import statistics as st

import numpy as np

from suite import DATASETS, ORDERS, stage_rows
from verify import check, clean, qids, read, sha

HERE=Path(__file__).resolve().parent
PAIRS=(('E','S'),('S','P'),('E','P'))

def percentile(xs,p):
    xs=sorted(xs);return xs[min(len(xs)-1,math.ceil(len(xs)*p)-1)]

def paired(a,b):
    logs=[math.log(x/y) for x,y in zip(a,b)]
    boot=sorted(math.exp(st.mean(xs)) for xs in itertools.product(logs,repeat=4))
    return {'ratio_of_medians':st.median(a)/st.median(b),
            'paired_geomean':math.exp(st.mean(logs)),
            'bootstrap_95':[percentile(boot,.025),percentile(boot,.975)],
            'wins':sum(x>y for x,y in zip(a,b)),
            'round_ratios':[x/y for x,y in zip(a,b)]}

def profile(path):
    with sqlite3.connect(path) as db:
        kernels=db.execute('''SELECT s.value,k.gridX,k.blockX,k.registersPerThread,
                                    k.end-k.start FROM CUPTI_ACTIVITY_KIND_KERNEL k
                                    JOIN StringIds s ON s.id=k.demangledName ORDER BY k.start''').fetchall()
    start=next(i for i,x in enumerate(kernels) if x[0].startswith('initQnode('))
    kernels=kernels[start:]
    assert len(kernels)%5==0
    per=len(kernels)//5
    signature=[list(x[:-1]) for x in kernels[:per]]
    assert all([list(x[:-1]) for x in kernels[i:i+per]]==signature for i in range(0,len(kernels),per))
    sums={}
    for name,grid,block,reg,ns in kernels:
        key=name.split('(')[0].split('<')[0]
        sums[key]=sums.get(key,0)+ns/5000
    return {'kernel_count':per,'signature':signature,'kernel_us':sums,
            'sqlite_sha256':sha(path)}

def audit(root,output):
    reg=read(root/'PREREGISTRATION.json')
    assert reg==read(HERE/'PREREGISTRATION.json')
    for key,name in [('binary_sha256','bin/graph_bench'),('driver_sha256','graph_bench.cu'),
                     ('header_sha256','l2_traversal.cuh'),('runner_sha256','run.py'),
                     ('suite_sha256','suite.py'),('verify_sha256','verify.py')]:
        assert sha(root/name)==reg[key],name
    complete=read(root/'logs/COMPLETE.json')
    assert complete['runs']==sum(reg['stage_counts'].values())==63
    admission=read(root/'logs/admission.json')
    assert not admission['state']['apps'].strip()
    gpu=admission['gpu_uuid']
    result={'experiment':reg['experiment'],'gpu':admission,'runs':63,'data':{},
            'binary_sha256':reg['binary_sha256']}
    for stage in ('full','gates','timing','trace'):
        rows=list(stage_rows(stage,root))
        assert len(rows)==reg['stage_counts'][stage]
        log=[json.loads(x) for x in (root/'logs'/f'{stage}.txt').read_text().splitlines()
             if x.startswith('{')]
        assert len(log)==len(rows)
        for row,record in zip(rows,log):
            path,label,mode,radius,reps,warm,tool,dump,qfile=row
            run=path/'runs'/label
            receipt=read(run/'receipt.json');clean(receipt)
            assert receipt==record
            assert receipt['validation']['pass'] and receipt['binary_sha256']==reg['binary_sha256']
            assert receipt['runner_sha256']==reg['runner_sha256']
            assert (receipt['label'],receipt['mode'],receipt['radius'],receipt['repeats'],
                    receipt['warmup'],receipt['tool'],receipt['dump'],receipt['qfile'])==(label,mode,radius,reps,warm,tool,dump,qfile)
            assert all(not read(run/f'{phase}.json')['apps'].strip() for phase in ('before','after'))
            assert all(not x['foreign'] for x in read(run/'checks.json'))
            rows_csv=list(csv.DictReader((run/'result.csv').open()))
            assert [int(x['qid']) for x in rows_csv]==qids(path/'fixtures'/qfile)*reps
            gold=read(path/'fixtures'/f'expected_{radius:g}.json')
            assert all([int(x['count']),x['ordered_hash']]==gold[x['qid']] for x in rows_csv)
            if tool in ('memcheck','synccheck'):
                logs=(run/'stdout.log').read_text()+(run/'stderr.log').read_text()
                assert 'ERROR SUMMARY: 0 errors' in logs
    for d in DATASETS:
        p=root/'data'/d/'1000000'
        meta=read(p/'fixtures/oracle.json')
        assert sha(p/'fixtures/oracle.json')==reg['oracle_sha256'][d]
        matrix=np.load(p/'fixtures/oracle.npy',mmap_mode='r')
        gold=read(p/'fixtures'/f"expected_{meta['radii']['normal']:g}.json")
        for m in 'SP':
            got,_=check(p,f'full_normal_{m}',m,'normal',meta,matrix)
            assert all(gold[str(q)]==[count,fnv] for q,count,_,fnv in got)
        timing={m:[] for m in 'ESP'}
        for i in range(4):
            for m in 'ESP':
                x=read(p/'runs'/f'timing_{i}_{m}/result.json')
                timing[m].append(1e3*x['sum_query_s']/x['queries'])
        ratios={a+'/'+b:paired(timing[a],timing[b]) for a,b in PAIRS}
        traces={m:profile(p/'runs'/f'trace_{m}/trace.sqlite') for m in 'ESP'}
        assert traces['E']['kernel_count']==traces['S']['kernel_count']==traces['P']['kernel_count']
        # Query work after traversal must remain byte-identical in launch signature.
        sigs={m:traces[m]['signature'] for m in 'ESP'}
        for m in 'SP':
            assert sigs[m][0]==sigs['E'][0]
            assert sigs[m][11:]==sigs['E'][11:]
        result['data'][d]={'n':1000000,'dimension':meta['dimension'],'timing_ms':timing,
                           'median_ms':{m:st.median(timing[m]) for m in 'ESP'},
                           'ratios':ratios,'trace':traces}
    output.write_text(json.dumps(result,indent=2)+'\n')
    for d,x in result['data'].items():
        print(d,{m:round(x['median_ms'][m],3) for m in 'ESP'},
              {name:round(v['ratio_of_medians'],3) for name,v in x['ratios'].items()})

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('root',type=Path)
    parser.add_argument('output',type=Path);a=parser.parse_args();audit(a.root.resolve(),a.output)
