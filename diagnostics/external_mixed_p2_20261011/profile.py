#!/usr/bin/env python3
"""NSYS-only attribution: explicit client D2H copies, never primary latency."""
import argparse,csv,sqlite3
from pathlib import Path
from prepare import read,save,sha

def duration(xs):return sum(x['end']-x['start'] for x in xs)/1e6

def collect(r,m):
    path=r/'diagnostic'/(m+'.sqlite');db=sqlite3.connect(path);db.row_factory=sqlite3.Row
    copies=[dict(x) for x in db.execute('select * from CUPTI_ACTIVITY_KIND_MEMCPY order by start')]
    kernels=[dict(x) for x in db.execute('select k.*,s.value as name from CUPTI_ACTIVITY_KIND_KERNEL k join StringIds s on k.demangledName=s.id order by k.start')]
    apis=[dict(x) for x in db.execute('select r.*,s.value as name from CUPTI_ACTIVITY_KIND_RUNTIME r join StringIds s on r.nameId=s.id order by r.start')]
    runtime={x['correlationId']:x for x in apis};prefix=r/'diagnostic/outputs'/m
    ops=list(csv.DictReader(Path(str(prefix)+'.ops.csv').open()));qs=list(csv.DictReader(Path(str(prefix)+'.queries.csv').open()));windows=[]
    if m=='P2':
        ranges=[dict(x) for x in db.execute('select n.start,n.end,coalesce(n.text,s.value) as name from NVTX_EVENTS n left join StringIds s on n.textId=s.id')]
        traces=sorted((x for x in ranges if x['name']=='native.trace'),key=lambda x:x['start']);assert len(traces)==2
        lo,hi=traces[-1]['start'],traces[-1]['end']
        windows=sorted((x for x in ranges if x['name']=='native.query' and lo<=x['start'] and x['end']<=hi),key=lambda x:x['start']);assert len(windows)==256
        boundary='second native.trace, query NVTX ranges; includes final release in aggregate kernel/API ledger'
    else:
        s=read(str(prefix)+'.pe.json');uploads=[x for x in copies if x['copyKind']==1 and x['bytes']==s['vector_storage_bytes']];assert len(uploads)==2
        inputs=[x for x in copies if x['copyKind']==1 and x['bytes']==960*4 and x['start']>uploads[-1]['end']]
        flags=[int(x['flag']) for x in ops if int(x['flag'])!=1];assert len(inputs)==len(flags)==296
        assert all(x['correlationId'] in runtime for x in inputs)
        lo=runtime[inputs[0]['correlationId']]['start'];last_input=inputs[-1]['end']
        release=next(x for x in apis if x['name'].startswith('cudaFree') and x['start']>last_input);hi=release['start']
        for i,(x,f) in enumerate(zip(inputs,flags)):
            end=runtime[inputs[i+1]['correlationId']]['start'] if i+1<len(inputs) else hi
            if f>=2:windows.append(dict(start=runtime[x['correlationId']]['start'],end=end,name='input-bound query slot'))
        assert len(windows)==256
        boundary='after second capacity-sized database upload; 296 per-event H2D vectors map to all nondelete operations; first service submission to first final cudaFree (no exact Host-end marker)'
    ledger=[]
    for w,q,op in zip(windows,qs,[x for x in ops if int(x['flag'])>=2]):
        count=int(q['count']);f=int(op['flag']);dc=[x for x in copies if x['copyKind']==2 and w['start']<=x['start'] and x['end']<=w['end']]
        selected=dc[-2:] if m=='P2' else dc[-(3 if f==2 else 2):]
        wanted=[count*4,count*4]+([count*8] if m=='E' and f==2 else [])
        if count:assert [x['bytes'] for x in selected]==wanted,(m,q['step'],'client copy binding',[x['bytes'] for x in selected],wanted)
        else:selected=[]
        calls=[runtime[x['correlationId']] for x in selected];assert all(x['returnValue']==0 for x in calls)
        overlap=sum(max(0,min(a['end'],k['end'])-max(a['start'],k['start'])) for a in calls for k in kernels)/1e6
        ledger.append(dict(output_API_overlap_kernel_inclusive_ms=overlap,step=int(q['step']),flag=f,count=count,client_D2H_bytes=sum(x['bytes'] for x in selected),client_D2H_device_ms=duration(selected),client_D2H_API_inclusive_ms=duration(calls)))
    ks=[x for x in kernels if lo<=x['start'] and x['end']<=hi];rt=[x for x in apis if lo<=x['start'] and x['end']<=hi];cs=[x for x in copies if lo<=x['start'] and x['end']<=hi]
    families={};api_families={}
    for x in ks:
        name=x['name'].split('(')[0];row=families.setdefault(name,dict(calls=0,inclusive_ms=0));row['calls']+=1;row['inclusive_ms']+=(x['end']-x['start'])/1e6
    for x in rt:
        row=api_families.setdefault(x['name'],dict(calls=0,inclusive_ms=0));row['calls']+=1;row['inclusive_ms']+=(x['end']-x['start'])/1e6
    return dict(method=m,sqlite_sha256=sha(path),boundary=boundary,diagnostic_window_ms=(hi-lo)/1e6,kernel_calls=len(ks),kernel_inclusive_ms=duration(ks),kernel_families=families,api_families=api_families,copy_ledger={str(k):dict(bytes=sum(x['bytes'] for x in cs if x['copyKind']==k),device_ms=duration([x for x in cs if x['copyKind']==k])) for k in sorted({x['copyKind'] for x in cs})},client_D2H=dict(bytes=sum(x['client_D2H_bytes'] for x in ledger),device_ms=sum(x['client_D2H_device_ms'] for x in ledger),API_inclusive_ms=sum(x['client_D2H_API_inclusive_ms'] for x in ledger),API_overlap_kernel_inclusive_ms=sum(x['output_API_overlap_kernel_inclusive_ms'] for x in ledger),per_query=ledger),scope='Partial explicit full ID/field D2H output attribution. P2 last two copies in NVTX query; E last 3 range /2 K copies in input-bound slot. Host map, retention, sqrt and synchronization not separately isolated. Native-squared E range copy is included. Do not sum API wait plus same GPU duration or compare these to primary unprofiled latency.')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();assert read(a.root/'diagnostic/GATE.json')['passed']
    j={m:collect(a.root,m) for m in ('P2','E')};save(a.out,j);print({m:{k:v for k,v in x['client_D2H'].items() if k!='per_query'} for m,x in j.items()})
