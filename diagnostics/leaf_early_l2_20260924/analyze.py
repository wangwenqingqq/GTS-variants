#!/usr/bin/env python3
"""Audit the frozen large L2 leaf campaign and emit compact evidence."""
import csv
import hashlib
import itertools
import json
import math
from pathlib import Path
import statistics

ROOT=Path('/home/data/wangxuran/tmp/gts_20260922_cpu_io/leaf_early_l2_20260924')
ORDERS=('QHJ','JHQ','HJQ','QJH')
CASES=(('zero','zero.qid'),('all','all.qid'),('empty','negative.qid'))

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(8*1024*1024),b''):
            h.update(chunk)
    return h.hexdigest()

def load(path):return json.loads(path.read_text())

def mean_ms(path):
    rows=list(csv.DictReader(path.open()))
    assert rows
    return statistics.mean(float(x['query_us']) for x in rows)/1000,rows

def quantile(a,p):
    v=sorted(a);i=(len(v)-1)*p;lo=int(i);hi=min(lo+1,len(v)-1)
    return v[lo]+(v[hi]-v[lo])*(i-lo)

def paired(a,b):
    ratios=[x/y for x,y in zip(a,b)]
    logs=[math.log(x) for x in ratios]
    exact=[math.exp(statistics.mean(x)) for x in itertools.product(logs,repeat=len(logs))]
    return {'ratio_of_medians':statistics.median(a)/statistics.median(b),
            'paired_geomean':math.exp(statistics.mean(logs)),
            'bootstrap_95':[quantile(exact,.025),quantile(exact,.975)],
            'wins':sum(x>1 for x in ratios),'round_ratios':ratios}

def main():
    assert (ROOT/'logs/full_gate_complete.json').exists()
    assert (ROOT/'logs/boundary_COMPLETE').exists()
    timing=load(ROOT/'logs/timing_COMPLETE.json')
    assert timing['orders']==list(ORDERS) and timing['runs']==24
    manifest=load(ROOT/'PREREGISTRATION.json')
    for name,value in manifest['sha256'].items():assert sha(ROOT/name)==value,name
    gpu=timing['gpu'];gpu_uuid=None;receipts={}

    def audit(ds,label,mode,radius,qfile,repeats,warmup,tool):
        nonlocal gpu_uuid
        base=ROOT/'data'/ds/'1000000'
        path=base/'runs'/label
        receipt=load(path/'receipt.json')
        assert (receipt['mode'],receipt['label'],receipt['radius'],receipt['qfile'],
                receipt['repeats'],receipt['warmup'],receipt['tool'])==(
                    mode,label,radius,qfile,repeats,warmup,tool)
        assert receipt['exit_code']==0 and receipt['stop_reason'] is None
        assert not receipt['runtime_errors'] and receipt['validation']['pass']
        assert receipt['post_gpu_clear'] and receipt['binary_sha256']==manifest['sha256']['bin/graph_bench']
        assert receipt['runner_sha256']==manifest['sha256']['run.py']
        before=load(path/'before.json');after=load(path/'after.json')
        assert not before['apps'].strip() and not after['apps'].strip()
        assert not any(x['foreign'] for x in load(path/'checks.json'))
        index,uuid,*_=map(str.strip,before['gpu'].split(','))
        assert index==gpu
        if gpu_uuid is None:gpu_uuid=uuid
        else:assert uuid==gpu_uuid
        duration,rows=mean_ms(path/'result.csv')
        assert len(rows)==repeats*int((base/'fixtures'/qfile).read_text().split()[0])
        gold=load(base/'fixtures'/f'expected_{radius:g}.json')
        assert all([int(x['count']),x['ordered_hash']]==gold[x['qid']] for x in rows)
        receipts[f'{ds}/{label}']=sha(path/'receipt.json')
        return duration,rows,path

    full={};gates={};boundary={};samples={}
    for ds in ('GIST','Deep'):
        base=ROOT/'data'/ds/'1000000'
        radii=load(base/'fixtures/oracle.json')['radii']
        full[ds]={};fullhash=[]
        for mode in 'QHJ':
            ms,rows,path=audit(ds,f'full_normal_{mode}',mode,radii['normal'],
                               'queries.qid',1,0,'clean')
            value=sha(path/'result.results');fullhash.append(value)
            full[ds][mode]={'mean_ms':ms,'output_sha256':value,
                            'query_ms':[float(x['query_us'])/1000 for x in rows],
                            'hit_counts':[int(x['count']) for x in rows]}
        assert len(set(fullhash))==1
        gates[ds]={}
        for tool in ('memcheck','synccheck'):
            _,_,path=audit(ds,f'{tool}_normal_J','J',radii['normal'],
                           'check.qid',1,0,tool)
            assert 'ERROR SUMMARY: 0 errors' in (
                (path/'stderr.log').read_text()+(path/'stdout.log').read_text())
            gates[ds][tool]='pass'
        boundary[ds]={}
        for kind,qfile in CASES:
            _,rows,_=audit(ds,f'boundary_{kind}_J','J',radii[kind],qfile,1,0,'clean')
            boundary[ds][kind]=[int(x['count']) for x in rows]
        samples[ds]={m:[] for m in 'QHJ'}
        for i,order in enumerate(ORDERS):
            for mode in order:
                ms,_,_=audit(ds,f'timing_{i}_{mode}',mode,radii['normal'],
                             'queries.qid',1,8,'clean')
                samples[ds][mode].append(ms)
    ratios={ds:{'Q/H':paired(x['Q'],x['H']),
                'H/J':paired(x['H'],x['J']),
                'Q/J':paired(x['Q'],x['J'])} for ds,x in samples.items()}
    report={'experiment':'leaf_early_l2_20260924','gpu_index':gpu,
            'gpu_uuid':gpu_uuid,'binary_sha256':manifest['sha256']['bin/graph_bench'],
            'runner_sha256':manifest['sha256']['run.py'],'orders':ORDERS,
            'full':full,'gates':gates,'boundary':boundary,
            'timing_ms':samples,'ratios':ratios,'receipts':receipts}
    (ROOT/'EVIDENCE.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'gpu':gpu,'timing_ms':samples,'ratios':ratios},indent=2))

if __name__=='__main__':main()
