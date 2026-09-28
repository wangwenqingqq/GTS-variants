#!/usr/bin/env python3
"""Audit Tloc 1M E/P/R/Q paired hot-query screen."""
import argparse
import csv
import itertools
import json
import math
from pathlib import Path
import statistics as st
import sys

import numpy as np

HERE=Path(__file__).resolve().parent
PRIOR=HERE.parent/'large_end_to_end_20260924/local/raw'
sys.path.insert(0,str(PRIOR))
from verify import check,clean,qids,read,sha

ORDERS=('EPRQ','QRPE','PREQ','QERP')
PAIRS=(('E','R'),('P','Q'),('E','P'),('R','Q'),('E','Q'))

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

def audit(root,out):
    root=root.resolve();data=root/'data/Tloc/1000000'
    assert sha(root/'TIMING_PLAN.md')==sha(HERE/'TIMING_PLAN.md')
    assert sha(root/'graph_bench.cu')==sha(HERE/'local/build/graph_bench.cu')
    assert sha(root/'l2_traversal.cuh')==sha(HERE/'local/build/l2_traversal.cuh')
    assert sha(root/'run.py')==sha(HERE/'local/build/run.py')
    binary=sha(root/'bin/graph_bench');runner=sha(root/'run.py')
    done=read(root/'logs/timing_tloc_COMPLETE.json')
    assert done['runs']==16 and tuple(done['orders'])==ORDERS
    meta=read(data/'fixtures/oracle.json')
    matrix=np.load(data/'fixtures/oracle.npy',mmap_mode='r')
    radius=meta['radii']['normal']
    gold=read(data/'fixtures'/f'expected_{radius:g}.json')
    output={'experiment':'tloc_1m_traversal_grid_x_dead_count_20260924',
            'gpu_index':6,'gpu_uuid':'GPU-865ae1f0-780e-d04c-5ec3-4deccea65f82',
            'binary_sha256':binary,'runner_sha256':runner,'orders':ORDERS,
            'full':{},'gates':{},'timing_ms':{m:[] for m in 'EPRQ'},'ratios':{},'receipts':{}}
    for mode in 'RQ':
        label=f'full_normal_{mode}'
        got,band=check(data,label,mode,'normal',meta,matrix)
        assert all(gold[str(q)]==[count,fnv] for q,count,_,fnv in got)
        run=data/'runs'/label
        output['full'][mode]={'output_sha256':sha(run/'result.results'),'boundary_count':band}
        output['receipts'][label]=sha(run/'receipt.json')
        for tool in ('memcheck','synccheck'):
            label=f'gate_{tool}_{mode}';run=data/'runs'/label
            receipt=read(run/'receipt.json');clean(receipt)
            assert receipt['validation']['pass'] and receipt['binary_sha256']==binary
            assert receipt['runner_sha256']==runner and receipt['tool']==tool
            assert 'ERROR SUMMARY: 0 errors' in (run/'stdout.log').read_text()+(run/'stderr.log').read_text()
            assert not read(run/'before.json')['apps'].strip() and not read(run/'after.json')['apps'].strip()
            assert all(not check['foreign'] for check in read(run/'checks.json'))
            output['gates'][f'{mode}/{tool}']='pass'
            output['receipts'][label]=sha(run/'receipt.json')
    assert output['full']['R']['output_sha256']==output['full']['Q']['output_sha256']
    log=(root/'logs/timing_tloc.txt').read_text().splitlines()
    receipts=[json.loads(line) for line in log if line.startswith('{')]
    assert len(receipts)==16
    k=0
    for i,order in enumerate(ORDERS):
        for mode in order:
            label=f'timing_{i}_{mode}';run=data/'runs'/label
            receipt=read(run/'receipt.json');clean(receipt)
            assert receipt==receipts[k];k+=1
            assert receipt['validation']['pass'] and receipt['binary_sha256']==binary
            assert receipt['runner_sha256']==runner
            assert (receipt['mode'],receipt['label'],receipt['repeats'],receipt['warmup'],receipt['radius'],receipt['tool'])==(mode,label,1,8,radius,'clean')
            for phase in ('before','after'):
                state=read(run/f'{phase}.json')
                assert not state['apps'].strip() and output['gpu_uuid'] in state['gpu']
            assert all(not item['foreign'] for item in read(run/'checks.json'))
            rows=list(csv.DictReader((run/'result.csv').open()))
            assert [int(x['qid']) for x in rows]==qids(data/'fixtures/queries.qid')
            assert all([int(x['count']),x['ordered_hash']]==gold[x['qid']] for x in rows)
            summary=read(run/'result.json')
            assert summary['queries']==len(rows)==8
            mean_ms=summary['sum_query_s']*1000/8
            assert math.isclose(mean_ms,st.mean(float(x['query_us']) for x in rows)/1000,abs_tol=2e-6)
            output['timing_ms'][mode].append(mean_ms)
            output['receipts'][label]=sha(run/'receipt.json')
    assert len(output['receipts'])==22
    output['median_ms']={m:st.median(xs) for m,xs in output['timing_ms'].items()}
    output['ratios']={a+'/'+b:paired(output['timing_ms'][a],output['timing_ms'][b]) for a,b in PAIRS}
    out.write_text(json.dumps(output,indent=2)+'\n')
    print('median_ms',output['median_ms'])
    print('ratios',{k:v['ratio_of_medians'] for k,v in output['ratios'].items()})

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();audit(a.root,a.output)
