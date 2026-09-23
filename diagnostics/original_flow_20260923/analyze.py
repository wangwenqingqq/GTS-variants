#!/usr/bin/env python3
"""Read-only clean-process and NSYS utilization summaries; no NCU substitutions."""
import argparse
from collections import Counter,defaultdict
import csv
import json
from pathlib import Path
import re
import sqlite3
import statistics as st


def union(intervals):
    out=[]
    for a,b in sorted(intervals):
        if a>=b:continue
        if out and a<=out[-1][1]:out[-1]=(out[-1][0],max(out[-1][1],b))
        else:out.append((a,b))
    return out


def length(xs):return sum(b-a for a,b in union(xs))


def clipped(rows,lo,hi):return [(max(lo,r['start']),min(hi,r['end'])) for r in rows if r['start']<hi and r['end']>lo]


def quantiles(xs):
    xs=sorted(xs)
    def at(p):
        i=(len(xs)-1)*p;j=int(i)
        return xs[j]+(xs[min(j+1,len(xs)-1)]-xs[j])*(i-j)
    return {'min':xs[0],'p10':at(.1),'median':st.median(xs),'p90':at(.9),'max':xs[-1]}


def admitted(receipt):
    return (receipt['exit_code']==0 and not receipt.get('stop_reason')
            and receipt['validation']['pass'] and receipt['post_gpu_clear']
            and not receipt.get('runtime_errors'))


def clean(path):
    r=json.loads((path/'receipt.json').read_text())
    rows=list(csv.reader((path/'gpu_samples.csv').open()))
    sampled=[list(map(float,x[2:])) for x in rows]
    cpus=json.loads((path/'cpu_samples.json').read_text());windows=[]
    for a,b in zip(cpus,cpus[1:]):
        dt=b['elapsed_s']-a['elapsed_s']
        if a['elapsed_s']>=.7 and dt>0:
            windows.append(100*(b['process_cpu_s']-a['process_cpu_s'])/dt)
    cost=(path/'cost.txt').read_text()
    m=re.search(r'Search time(?: in update)?\s*:\s*([0-9.eE+-]+)',cost)
    native=float(m[1])*4096 if m and r['long'] else None
    return {'label':r['label'],'wall_s':r['wall_s'],'cpu_user_s':r['user_s'],'cpu_system_s':r['system_s'],
        'cpu_percent_one_core':100*(r['user_s']+r['system_s'])/r['wall_s'],
        'cpu_sample_after_0p7s_percent':quantiles(windows) if windows else None,
        'native_query_total_s_rounded':native,'peak_device_used_mib':max(x[0] for x in sampled),
        'device_capacity_mib':sampled[0][1],'gpu_sample_percent':quantiles([x[2] for x in sampled]),
        'gpu_samples':len(sampled),'correct':r['validation']['pass'],
        'warning':'100%=one CPU core. Device samples are windowed/coarse and can miss sub-100ms peaks. Process wall polling adds up to 100ms plus monitoring admission latency. Native timing printed to 6 decimals per query.'}


def trace(path,kind):
    db=sqlite3.connect(path);db.row_factory=sqlite3.Row
    tables={r[0] for r in db.execute("select name from sqlite_master where type='table'")}
    names=dict(db.execute('select id,value from StringIds'))
    def rows(table):return list(db.execute('select * from '+table)) if table in tables else []
    kernels=rows('CUPTI_ACTIVITY_KIND_KERNEL');api=rows('CUPTI_ACTIVITY_KIND_RUNTIME')
    copies=rows('CUPTI_ACTIVITY_KIND_MEMCPY');sets=rows('CUPTI_ACTIVITY_KIND_MEMSET')
    first,last=('initQnode','mergeTotalResult') if kind=='update' else ('initPListKnn','mergeResKnn')
    lo=min(r['start'] for r in kernels if names[r['shortName']]==first)
    hi=max(r['end'] for r in kernels if names[r['shortName']]==last)
    scope=(hi-lo)/1e6;ku=union(clipped(kernels,lo,hi));busy=union(clipped(kernels+copies+sets,lo,hi))
    gaps=[(b,c) for (_,b),(c,_) in zip(busy,busy[1:]) if c>b]
    totals=defaultdict(lambda:{'calls':0,'ms':0,'grids':Counter(),'blocks':Counter(),'registers':set()})
    for r in kernels:
        if not lo<=r['start']<hi:continue
        d=totals[names[r['shortName']]];d['calls']+=1;d['ms']+=(r['end']-r['start'])/1e6
        d['grids'][str(r['gridX']*r['gridY']*r['gridZ'])]+=1
        d['blocks'][str(r['blockX']*r['blockY']*r['blockZ'])]+=1
        d['registers'].add(r['registersPerThread'])
    for d in totals.values():d['registers']=sorted(d['registers'])
    apis=defaultdict(lambda:{'calls':0,'inclusive_ms':0})
    for r in api:
        if lo<=r['start']<hi:
            d=apis[names[r['nameId']]];d['calls']+=1;d['inclusive_ms']+=(r['end']-r['start'])/1e6
    memory=defaultdict(lambda:{'calls':0,'bytes':0,'ms':0})
    copy_names={r[0]:r[2] for r in db.execute('select * from ENUM_CUDA_MEMCPY_OPER')}
    for r in copies:
        if lo<=r['start']<hi:
            d=memory[copy_names[r['copyKind']]];d['calls']+=1;d['bytes']+=r['bytes'];d['ms']+=(r['end']-r['start'])/1e6
    alloc=rows('CUDA_GPU_MEMORY_USAGE_EVENTS');live={};peak=0;max_alloc=0
    for r in sorted(alloc,key=lambda r:r['start']):
        if r['memKind'] not in (2,4):continue
        key=(r['globalPid'],r['address'])
        if r['memoryOperationType']==0:live[key]=r['bytes'];max_alloc=max(max_alloc,r['bytes'])
        elif r['memoryOperationType']==1:live.pop(key,None)
        peak=max(peak,sum(live.values()))
    cf=rows('CUDA_UM_CPU_PAGE_FAULT_EVENTS');gf=rows('CUDA_UM_GPU_PAGE_FAULT_EVENTS')
    sms=db.execute('select smCount from TARGET_INFO_GPU where id=?',(kernels[0]['deviceId'],)).fetchone()[0]
    one_block=[r for r in kernels if lo<=r['start']<hi and r['gridX']*r['gridY']*r['gridZ']==1]
    return {'scope':'first query kernel start through last query kernel end; excludes initial query setup/final cleanup; diagnostic only',
        'query_span_ms':scope,'kernel_union_ms':length(ku)/1e6,'gpu_work_union_ms':length(busy)/1e6,
        'gpu_work_fraction':length(busy)/(hi-lo),'no_recorded_gpu_work_ms':scope-length(busy)/1e6,
        'gap_us':quantiles([(b-a)/1000 for a,b in gaps]) if gaps else None,
        'gaps_at_least_100us':sum(b-a>=100000 for a,b in gaps),'sm_count':sms,
        'single_block_kernel_calls':len(one_block),'all_query_kernel_calls':sum(x['calls'] for x in totals.values()),
        'single_block_kernel_ms':sum(r['end']-r['start'] for r in one_block)/1e6,
        'kernels':dict(sorted(totals.items(),key=lambda x:-x[1]['ms'])),'cuda_api':dict(apis),'copy_activity':dict(memory),
        'tracked_explicit_peak_live_bytes':peak if alloc else None,'largest_explicit_allocation_bytes':max_alloc if alloc else None,
        'cpu_um_fault_events':sum(lo<=r['start']<hi for r in cf) if cf else None,
        'gpu_um_fault_count':sum(r['numberOfPageFaults'] for r in gf if lo<=r['start']<hi) if gf else None,
        'warning':'Traced GPU work fraction is temporal coverage, not SM utilization. API durations overlap kernels. Trace gaps include instrumentation/driver/host/UVM effects. Explicit allocation tracking excludes device context/local-stack backing; missing counters are unknown.'}


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('root',type=Path);a=ap.parse_args()
    runs=a.root/'runs' if (a.root/'runs').is_dir() else a.root
    result={'clean':[clean(p.parent) for p in sorted(runs.glob('clean_*/receipt.json'))
                     if admitted(json.loads(p.read_text()))], 'traces':{}}
    for p in sorted(runs.glob('nsys*/trace.sqlite')):
        receipt=json.loads((p.parent/'receipt.json').read_text())
        if not admitted(receipt):continue
        result['traces'][p.parent.name]=trace(p,receipt['kind'])
    (a.root/'analysis.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'clean':result['clean'],'traces':{k:{x:y for x,y in v.items() if x not in ['kernels','cuda_api']} for k,v in result['traces'].items()}},indent=2))


if __name__=='__main__':main()
