#!/usr/bin/env python3
"""Summarize independent developer traces; keep API/GPU overlap explicit."""
import csv
import json
from pathlib import Path
import sqlite3
from campaign10k import ROOT,save,sha

def union(intervals):
    total=0;last=-1
    for start,end in sorted(intervals):
        total+=max(0,end-max(start,last));last=max(last,end)
    return total

def nsys(path):
    c=sqlite3.connect(path);c.row_factory=sqlite3.Row
    names=dict(c.execute('select id,value from StringIds'))
    ranges=[r for r in c.execute('select * from NVTX_EVENTS') if (r['text'] or names.get(r['textId']))=='formal.query_pass' and r['end']]
    assert len(ranges)==1;begin,end=ranges[0]['start'],ranges[0]['end']
    kernels=list(c.execute('select * from CUPTI_ACTIVITY_KIND_KERNEL where start>=? and end<=?',(begin,end)))
    api=list(c.execute('select * from CUPTI_ACTIVITY_KIND_RUNTIME where start>=? and end<=?',(begin,end)))
    grouped={};apis={}
    for row in kernels:
        name=names[row['shortName']];item=grouped.setdefault(name,{'launches':0,'gpu_ms':0.,'registers':row['registersPerThread'],'local_memory_per_thread':row['localMemoryPerThread']})
        item['launches']+=1;item['gpu_ms']+=(row['end']-row['start'])/1e6
    for row in api:
        name=names[row['nameId']];item=apis.setdefault(name,{'calls':0,'inclusive_ms':0.})
        item['calls']+=1;item['inclusive_ms']+=(row['end']-row['start'])/1e6
    tables={r[0] for r in c.execute("select name from sqlite_master where type='table'")}
    counts={}
    for name in ('CUDA_UM_CPU_PAGE_FAULT_EVENTS','CUDA_UM_GPU_PAGE_FAULT_EVENTS','COMPOSITE_EVENTS','SCHED_EVENTS'):
        counts[name]=c.execute(f'select count(*) from {name} where start>=? and start<=?',(begin,end)).fetchone()[0] if name in tables else 'no table exported; zero/unavailable not distinguished'
    samples={}
    if 'COMPOSITE_EVENTS' in tables and 'SAMPLING_CALLCHAINS' in tables:
        # Each leaf IP sample counted once; inclusive parent frames are not CPU time.
        for r in c.execute('select s.symbol,s.module,count(*) n from COMPOSITE_EVENTS e join SAMPLING_CALLCHAINS s on s.id=e.id where s.stackDepth=0 and e.start>=? and e.start<=? group by s.symbol,s.module',(begin,end)):
            symbol=names.get(r[0],'unresolved');module=Path(names.get(r[1],'unknown')).name
            if symbol.startswith('0x'):symbol='unresolved_IP'
            name=f'{module}:{symbol}';samples[name]=samples.get(name,0)+r[2]
    memcpy=[]
    if 'CUPTI_ACTIVITY_KIND_MEMCPY' in tables:
        cols={r[1] for r in c.execute('pragma table_info(CUPTI_ACTIVITY_KIND_MEMCPY)')}
        for r in c.execute('select * from CUPTI_ACTIVITY_KIND_MEMCPY where start>=? and end<=?',(begin,end)):
            memcpy.append({'bytes':r['bytes'],'copy_kind':r['copyKind'],'ms':(r['end']-r['start'])/1e6})
    return {'trace_sha256':sha(path),'scope':'GIST1M/K8/developer32 post-warmup Host-ready query range; instrumentation overhead; not formal timing',
            'range_ms':(end-begin)/1e6,'gpu_kernel_union_ms':union([(r['start'],r['end']) for r in kernels])/1e6,
            'kernel_sum_ms':sum(x['gpu_ms'] for x in grouped.values()),'kernels':grouped,'cuda_api':apis,
            'cpu_and_fault_events':counts,'CPU_leaf_IP_samples':dict(sorted(samples.items(),key=lambda x:-x[1])[:30]),
            'copies':memcpy,'interpretation':'API inclusive waiting overlaps GPU kernels; do not add API duration to GPU time. IP samples are samples, not CPU-time deltas. UVM faults are not themselves migrated-byte totals.'}

def counters(path):
    with path.open() as f:
        rows=list(csv.reader(f))
    at=next(i for i,r in enumerate(rows) if r and r[0]=='ID')
    header,units=rows[at:at+2];records=[]
    for row in rows[at+2:]:
        if len(row)!=len(header):continue
        record=dict(zip(header,row));kept={}
        for name,value,unit in zip(header,row,units):
            if any(t in name for t in ('dram__bytes','l1tex__t_requests','l1tex__t_sectors','lts__t_requests','lts__t_sectors',
               'sass_thread_inst_executed_op_d','pipe_fp64','sass_inst_executed_op_global','sass_inst_executed_op_local','register','local_mem',
               'occupancy','warps_active','warps_eligible','warp_issue_stalled','gpu__time_duration','shared_mem')):
                kept[name]={'value':value,'unit':unit}
        records.append({'kernel':record['Kernel Name'],'grid':record['Grid Size'],'block':record['Block Size'],'metrics':kept})
    return {'csv_sha256':sha(path),'records':records,'scope':'one selected developer launch, kernel replay, cache-control none, clock-control none; normalize by actual batch32 only when launch covers those32 queries; no pure-coalescing claim'}

def main():
    traces={p.stem:nsys(p) for p in (ROOT/'profiles').glob('nsys_*.sqlite')}
    save(ROOT/'ATTRIBUTION.json',traces)
    physical={p.stem:counters(p) for p in (ROOT/'profiles').glob('*.metrics.csv')}
    save(ROOT/'PHYSICAL_COUNTERS.json',physical)
    print('ATTRIBUTION summaries:',len(traces),'NSYS,',len(physical),'NCU')

if __name__=='__main__':main()
