#!/usr/bin/env python3
"""Offline, address-free UM overlap diagnostic for the frozen Nsight trace."""
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

def union_ns(intervals):
    total=0;end=None
    for a,b in sorted(intervals):
        total+=max(0,b-max(a,end if end is not None else a))
        end=max(b,end if end is not None else b)
    return total

def analyze(path):
    c=sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True)
    faults=c.execute('SELECT start,end,numberOfPageFaults,globalPid,deviceId FROM CUDA_UM_GPU_PAGE_FAULT_EVENTS').fetchall()
    query='SELECT k.start,k.end,s.value,k.gridX,k.gridY,k.gridZ,k.globalPid,k.deviceId FROM CUPTI_ACTIVITY_KIND_KERNEL k JOIN StringIds s ON k.shortName=s.id ORDER BY k.start'
    rows=[]
    for a,b,name,x,y,z,pid,device in c.execute(query):
        if name not in ['simt','tensor','dataProcessRnn']:continue
        mode={'simt':'S','dataProcessRnn':'O'}.get(name)
        if name=='tensor':
            assert x in [4096,10000] and y==8 and z==1,'unexpected frozen launch'
            mode='D' if x==4096 else 'T'
        overlap=[(max(a,u),min(b,v),n) for u,v,n,p,d in faults if p==pid and d==device and u<b and v>a]
        rows.append({'variant':mode,'kernel':name,'grid':[x,y,z],
                     'duration_ms':(b-a)/1e6,'overlapping_fault_events':len(overlap),
                     'fault_count_in_overlapping_events':sum(n for _,_,n in overlap),
                     'fault_interval_union_ms':union_ns([(u,v) for u,v,_ in overlap])/1e6})
    c.close()
    assert all(sum(r['variant']==v for r in rows)==5 for v in 'OSTD')
    return {'scope':'One diagnostic trace, Q128/r500; five calls per variant, not timing campaign. Rows retain chronological launch order. Fault counts include entire overlapping events; interval union is clipped to the kernel. Temporal overlap is not causal stalled time.',
            'trace_sqlite_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'leaf_kernel_calls':rows}

if __name__=='__main__':
    assert union_ns([])==0 and union_ns([(1,3),(2,5),(8,9),(1,2)])==5
    assert union_ns([(2,3),(0,5),(5,7)])==7
    print(json.dumps(analyze(Path(sys.argv[1])),indent=2))
