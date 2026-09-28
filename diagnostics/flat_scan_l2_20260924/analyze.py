#!/usr/bin/env python3
"""Audit the exact-flat-scan campaign and emit compact evidence."""
import csv,hashlib,itertools,json,math,statistics
from pathlib import Path

ROOT=Path('/home/data/wangxuran/tmp/gts_20260922_cpu_io/flat_scan_l2_20260924')
ORDERS=('QJF','FJQ','JFQ','QFJ')
BOUNDARIES=(('zero','zero.qid'),('all','all.qid'),('empty','negative.qid'))

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for part in iter(lambda:f.read(8*1024*1024),b''):h.update(part)
    return h.hexdigest()

def load(path):return json.loads(path.read_text())

def quantile(a,p):
    v=sorted(a);x=(len(v)-1)*p;i=int(x);j=min(i+1,len(v)-1)
    return v[i]+(v[j]-v[i])*(x-i)

def paired(a,b):
    ratios=[x/y for x,y in zip(a,b)]
    logs=[math.log(x) for x in ratios]
    boot=[math.exp(statistics.mean(x)) for x in itertools.product(logs,repeat=4)]
    return {'ratio_of_medians':statistics.median(a)/statistics.median(b),
            'paired_geomean':math.exp(statistics.mean(logs)),
            'bootstrap_95':[quantile(boot,.025),quantile(boot,.975)],
            'wins':sum(x>1 for x in ratios),'round_ratios':ratios}

def main():
    assert (ROOT/'logs/full_gate_COMPLETE').exists()
    assert (ROOT/'logs/gates_COMPLETE').exists()
    timing=load(ROOT/'logs/timing_COMPLETE.json')
    assert timing['orders']==list(ORDERS) and timing['runs']==24
    manifest=load(ROOT/'PREREGISTRATION.json')
    for name,value in manifest['sha256'].items():assert sha(ROOT/name)==value,name
    gpu=timing['gpu'];uuid=None;receipts={}

    def audit(ds,label,mode,radius,qfile,warmup,tool):
        nonlocal uuid
        base=ROOT/'data'/ds/'1000000'
        path=base/'runs'/label
        r=load(path/'receipt.json')
        assert (r['mode'],r['label'],r['radius'],r['qfile'],r['repeats'],
                r['warmup'],r['tool'])==(mode,label,radius,qfile,1,warmup,tool)
        assert r['exit_code']==0 and r['stop_reason'] is None and not r['runtime_errors']
        assert r['validation']['pass'] and r['post_gpu_clear']
        assert r['binary_sha256']==manifest['sha256']['bin/graph_bench']
        assert r['runner_sha256']==manifest['sha256']['run.py']
        before=load(path/'before.json');after=load(path/'after.json')
        assert not before['apps'].strip() and not after['apps'].strip()
        assert not any(x['foreign'] for x in load(path/'checks.json'))
        index,identity,*_=map(str.strip,before['gpu'].split(','))
        assert index==gpu
        if uuid is None:uuid=identity
        else:assert uuid==identity
        rows=list(csv.DictReader((path/'result.csv').open()))
        nq=int((base/'fixtures'/qfile).read_text().split()[0])
        assert len(rows)==nq
        gold=load(base/'fixtures'/f'expected_{radius:g}.json')
        assert all([int(x['count']),x['ordered_hash']]==gold[x['qid']] for x in rows)
        ms=statistics.mean(float(x['query_us']) for x in rows)/1000
        receipts[f'{ds}/{label}']=sha(path/'receipt.json')
        return ms,rows,path

    full={};gates={};boundary={};samples={}
    for ds in ('GIST','Deep'):
        base=ROOT/'data'/ds/'1000000'
        radii=load(base/'fixtures/oracle.json')['radii']
        full[ds]={};hashes=[]
        for mode in 'QJF':
            ms,rows,path=audit(ds,f'full_normal_{mode}',mode,radii['normal'],
                               'queries.qid',0,'clean')
            value=sha(path/'result.results');hashes.append(value)
            full[ds][mode]={'mean_ms':ms,'output_sha256':value,
                            'query_ms':[float(x['query_us'])/1000 for x in rows],
                            'hit_counts':[int(x['count']) for x in rows]}
        assert len(set(hashes))==1
        gates[ds]={}
        for tool in ('memcheck','synccheck'):
            _,_,path=audit(ds,f'gate_{tool}_F','F',radii['normal'],
                           'check.qid',0,tool)
            logs=(path/'stdout.log').read_text()+(path/'stderr.log').read_text()
            assert 'ERROR SUMMARY: 0 errors' in logs
            gates[ds][tool]='pass'
        boundary[ds]={}
        for kind,qfile in BOUNDARIES:
            _,rows,_=audit(ds,f'boundary_{kind}_F','F',radii[kind],qfile,0,'clean')
            boundary[ds][kind]=[int(x['count']) for x in rows]
        samples[ds]={m:[] for m in 'QJF'}
        for i,order in enumerate(ORDERS):
            for mode in order:
                ms,_,_=audit(ds,f'timing_{i}_{mode}',mode,radii['normal'],
                             'queries.qid',8,'clean')
                samples[ds][mode].append(ms)
    ratios={ds:{'Q/J':paired(x['Q'],x['J']),
                'J/F':paired(x['J'],x['F']),
                'Q/F':paired(x['Q'],x['F'])} for ds,x in samples.items()}
    evidence={'experiment':'flat_scan_l2_20260924','gpu_index':gpu,
              'gpu_uuid':uuid,'binary_sha256':manifest['sha256']['bin/graph_bench'],
              'runner_sha256':manifest['sha256']['run.py'],'orders':ORDERS,
              'full':full,'gates':gates,'boundary':boundary,'timing_ms':samples,
              'ratios':ratios,'receipts':receipts}
    (ROOT/'EVIDENCE.json').write_text(json.dumps(evidence,indent=2)+'\n')
    print(json.dumps({'timing_ms':samples,'ratios':ratios},indent=2))

if __name__=='__main__':main()
