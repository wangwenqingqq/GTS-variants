"""Read-only NSYS attribution: exclusive Host spans and overlaid device activity."""
if not __debug__:
    raise SystemExit('Mandatory checks require ordinary Python without optimization.')
from bisect import bisect_right
import collections
import hashlib
from pathlib import Path
import sqlite3
import numpy as np

OPERATORS={'U_DELETE':'D','U_INSERT':'I','Q':'Q','CAL_H2D':'H2D','CAL_D2D':'D2D'}
BOOKKEEPING={'DELETE_VALIDATE','DELETE_ROWS','INSERT_OWNERS'}
PHASES=BOOKKEEPING|{'INSERT_SUBMIT'}
EXPECTED_PHASES={'D':{'DELETE_VALIDATE':1,'DELETE_ROWS':1},'I':{'INSERT_SUBMIT':1,'INSERT_OWNERS':1}}
FORMAL={'MICRO_FORMAL','COPY_FORMAL'}


def check_phases(operator,counts):
    assert dict(counts)==EXPECTED_PHASES.get(operator,{}),('Incomplete or duplicate inner NVTX phases',operator,dict(counts))


def check_update_api(operator,names):
    if operator not in ('D','I'):return
    assert set(names)<={'cudaMemcpyAsync_v3020','cudaStreamSynchronize_v3020'},('Unexpected update API',operator,dict(names))
    assert names.get('cudaStreamSynchronize_v3020')==1,('Missing or duplicate update wait',operator)


def union(intervals):
    total=0;right=None
    for a,b in sorted(intervals):
        assert b>=a
        if right is None or a>right:total+=b-a;right=b
        elif b>right:total+=b-right;right=b
    return total


def intersect(left,right):
    left=sorted(left);right=sorted(right);i=j=0;out=[]
    while i<len(left) and j<len(right):
        a,b=left[i];c,d=right[j]
        if min(b,d)>max(a,c):out.append((max(a,c),min(b,d)))
        if b<=d:i+=1
        else:j+=1
    return out


def host_partition(a,b,copy,sync,other,bookkeeping):
    # Runtime API categories take precedence; Host phases subtract their union.
    events=[]
    for category,intervals in enumerate((sync,copy,other,bookkeeping)):
        for left,right in intervals:
            assert a<=left<=right<=b
            if left<right:events.extend(((left,1,category),(right,-1,category)))
    active=[0]*4;totals=[0]*5;last=a
    for time,change,category in sorted(events):
        chosen=next((i for i,n in enumerate(active) if n),4);totals[chosen]+=time-last
        active[category]+=change;assert min(active)>=0;last=time
    chosen=next((i for i,n in enumerate(active) if n),4);totals[chosen]+=b-last
    assert not any(active) and sum(totals)==b-a
    return dict(zip(('sync_API_ns','copy_API_ns','other_API_ns','bookkeeping_Host_ns','other_Host_ns'),totals))


def records(connection,table):
    return [dict(row) for row in connection.execute('SELECT * FROM "'+table+'"')]


def quantiles(values):
    a=np.asarray(values,float);assert a.size and np.isfinite(a).all()
    return dict(count=int(a.size),mean=float(a.mean()),p50=float(np.quantile(a,.5)),p95=float(np.quantile(a,.95)),maximum=float(a.max()))


def sampled_metrics(db,tables,start,end):
    assert {'GPU_METRICS','TARGET_INFO_GPU_METRICS','GENERIC_EVENT_TYPE_FIELDS'}<=tables
    info=records(db,'TARGET_INFO_GPU_METRICS');fields={(r['typeId'],r['fieldIdx']):r for r in records(db,'GENERIC_EVENT_TYPE_FIELDS')}
    assert len({r['typeId'] for r in info})==1
    selected={}
    for r in info:
        if not r['metricName'].endswith('[Throughput %]'):continue
        f=fields[(r['typeId'],r['metricId'])];assert f['type']==1 and f['size']==1,'Only verified unsigned-byte percent fields are normalized'
        selected[(r['typeId'],r['metricId'])]=r['metricName']
    values=collections.defaultdict(list);times=collections.defaultdict(list)
    for row in records(db,'GPU_METRICS'):
        key=(row['typeId'],row['metricId'])
        if key not in selected or not start<=row['timestamp']<=end:continue
        value=int(row['value'])&255;assert 0<=value<=100
        values[selected[key]].append(value);times[selected[key]].append(row['timestamp'])
    assert values and set(values)==set(selected.values())
    first=next(iter(times.values()));spacing=np.diff(sorted(set(first)));assert spacing.size
    return dict(scope='Unweighted device-wide samples from first operator start through last operator end on the isolated target GPU;not the full formal anchor,not per-ACK or ACK-weighted activity,not traffic bytes',
        requested_Hz=10000,export_resolution='Unsigned8-bit integer percentages;zero is a quantized observation,not proof ofzero activity.',
        time_spacing_ns=quantiles(spacing),fields={name:quantiles(v) for name,v in sorted(values.items())},
        exact_DRAM_bytes=None,exact_L2_bytes=None,clock_or_scaled_warp_counts_decoded=False,
        note='Only verified percent fields used;raw signed clock exports and scaled warp-average fields are not guessed or converted.')


def diagnostics(db,tables):
    assert 'DIAGNOSTIC_EVENT' in tables
    categories=collections.Counter();unknown=[]
    recognized={
        'Scheduling information is absent.':'Scheduling unavailable as predeclared',
        'Not all NVTX events might have been collected.':'NVTX completeness warning',
        'No NVTX events collected.':'NVTX no-events warning',
        'Not all CUDA events might have been collected.':'CUDA completeness warning',
        'Not all OS runtime libraries events might have been collected.':'OSRT completeness warning'}
    for row in records(db,'DIAGNOSTIC_EVENT'):
        assert row['severity']!=3, 'NSYS reported an Error;retain raw diagnosis and stop attribution admission'
        if row['severity']!=2:continue
        category=next((name for prefix,name in recognized.items() if row['text'].startswith(prefix)),None)
        if category is None:unknown.append(hashlib.sha256(row['text'].encode()).hexdigest())
        else:categories[category]+=1
    assert not unknown,('Unreviewed NSYS warning hashes',unknown)
    return dict(warnings=dict(categories),unreviewed_warning_hashes=unknown,
        limitation='Completeness warnings remain disclosed.Independent expected NVTX/API/payload counts are checked per cell;that does not establish complete OSRT/scheduler or internal-driver visibility.')


def parse(path):
    db=sqlite3.connect('file:'+str(Path(path).resolve())+'?mode=ro&immutable=1',uri=True);db.row_factory=sqlite3.Row
    tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {'StringIds','NVTX_EVENTS','CUPTI_ACTIVITY_KIND_RUNTIME'}<=tables
    strings={r['id']:r['value'] for r in records(db,'StringIds')}
    nvtx=[]
    for row in records(db,'NVTX_EVENTS'):
        name=strings.get(row.get('textId')) or row.get('text')
        if name not in set(OPERATORS)|PHASES|FORMAL:continue
        assert row['eventType'] in (59,70) and row['end'] is not None and row['start']<=row['end']
        assert row.get('endGlobalTid') is None
        nvtx.append(dict(start=row['start'],end=row['end'],tid=row['globalTid'],name=name))
    anchors=[r for r in nvtx if r['name'] in FORMAL];assert len(anchors)<=1
    discarded=0
    if anchors:
        a,b=anchors[0]['start'],anchors[0]['end'];discarded=sum(not (a<=r['start']<=r['end']<=b) for r in nvtx)
        nvtx=[r for r in nvtx if a<=r['start']<=r['end']<=b]
    ranges=sorted((r for r in nvtx if r['name'] in OPERATORS),key=lambda r:r['start']);assert ranges
    t0=ranges[0]['start'];end=ranges[-1]['end'];by_tid=collections.defaultdict(list)
    for i,r in enumerate(ranges):
        r.update(index=i,operator=OPERATORS[r['name']],copy=[],sync=[],other=[],bookkeeping=[],phase_names=collections.Counter(),copies=[],kernels=[],api_names=collections.Counter(),launch_API_calls=0)
        by_tid[r['tid']].append(i)
    starts={tid:[ranges[i]['start'] for i in indexes] for tid,indexes in by_tid.items()}
    for tid,indexes in by_tid.items():
        assert all(ranges[a]['end']<=ranges[b]['start'] for a,b in zip(indexes,indexes[1:]))
    def locate(tid,a,b):
        if tid not in starts:return None
        index=bisect_right(starts[tid],a)-1
        if index<0:return None
        r=ranges[by_tid[tid][index]]
        if a>=r['end']:return None
        assert r['start']<=a<=b<=r['end'],('Activity crosses operator boundary',a,b,r['operator'])
        return r
    for phase in nvtx:
        if phase['name'] in PHASES:
            r=locate(phase['tid'],phase['start'],phase['end']);assert r is not None
            r['phase_names'][phase['name']]+=1
            if phase['name'] in BOOKKEEPING:r['bookkeeping'].append((phase['start'],phase['end']))
    for r in ranges:check_phases(r['operator'],r['phase_names'])
    correlations={};outside_apis=collections.Counter()
    for api in records(db,'CUPTI_ACTIVITY_KIND_RUNTIME'):
        a,b=api['start'],api['end'];assert a<=b
        name=strings[api['nameId']];r=locate(api['globalTid'],a,b)
        if r is None:outside_apis[name]+=1;continue
        if api.get('returnValue') is not None:assert api['returnValue']==0,('CUDA runtime returned error',name)
        category='copy' if name.startswith('cudaMemcpy') else 'sync' if name.startswith('cudaStreamSynchronize') else 'other'
        r[category].append((a,b));r['api_names'][name]+=1
        r['launch_API_calls']+=int(name.startswith(('cudaLaunch','cudaGraphLaunch')))
        correlation=api['correlationId'];assert correlation not in correlations,('Repeated runtime correlation',correlation)
        correlations[correlation]=r
    memcpy=records(db,'CUPTI_ACTIVITY_KIND_MEMCPY') if 'CUPTI_ACTIVITY_KIND_MEMCPY' in tables else []
    kinds={r['id']:r['label'] for r in records(db,'ENUM_CUDA_MEMCPY_OPER')} if memcpy else {}
    unmatched=collections.Counter();devices=set();streams=set()
    for activity in memcpy:
        r=correlations.get(activity['correlationId'])
        if r is None:
            if activity['start']>=t0 and activity['end']<=end:unmatched['memcpy']+=1
            continue
        assert activity['start']<=activity['end'] and activity['bytes']>=0
        devices.add(activity['deviceId']);streams.add(activity['streamId'])
        label=kinds[activity['copyKind']];simple=''.join(c.lower() for c in label if c.isalnum())
        kind='H2D' if simple in ('htod','hosttodevice','h2d') else 'D2D' if simple in ('dtod','devicetodevice','d2d') else 'D2H' if simple in ('dtoh','devicetohost','d2h') else label
        r['copies'].append(dict(start=activity['start'],end=activity['end'],bytes=activity['bytes'],kind=kind))
    kernel_tables=[name for name in ('CUPTI_ACTIVITY_KIND_KERNEL','CUPTI_ACTIVITY_KIND_CONCURRENT_KERNEL') if name in tables]
    kernel_rows=[(name,records(db,name)) for name in kernel_tables];assert sum(bool(rows) for _,rows in kernel_rows)<=1
    for _,activities in kernel_rows:
        for activity in activities:
            r=correlations.get(activity['correlationId'])
            if r is None:
                if activity['start']>=t0 and activity['end']<=end:unmatched['kernel']+=1
                continue
            devices.add(activity['deviceId']);streams.add(activity['streamId'])
            r['kernels'].append(dict(start=activity['start'],end=activity['end'],name=strings.get(activity.get('demangledName'),strings.get(activity.get('shortName'),'unknown'))))
    assert len(devices)<=1 and not unmatched,('Unmatched device work in formal operator span',dict(unmatched))
    normalized=[];api_hist=collections.defaultdict(collections.Counter)
    for r in ranges:
        check_update_api(r['operator'],r['api_names'])
        part=host_partition(r['start'],r['end'],r['copy'],r['sync'],r['other'],r['bookkeeping'])
        copies=r['copies'];kernels=r['kernels'];dma=[(c['start'],c['end']) for c in copies];compute=[(k['start'],k['end']) for k in kernels]
        for left,right in dma+compute:assert r['start']<=left<=right<=r['end'],('Device work outside ready ACK',r['operator'])
        n=dict(index=r['index'],operator=r['operator'],begin_ns=r['start']-t0,scope_ns=r['end']-r['start'],**part,
            DMA_union_ns=union(dma),DMA_sum_ns=sum(b-a for a,b in dma),kernel_union_ns=union(compute),kernel_sum_ns=sum(b-a for a,b in compute),
            H2D_activity_bytes=sum(c['bytes'] for c in copies if c['kind']=='H2D'),D2D_activity_bytes=sum(c['bytes'] for c in copies if c['kind']=='D2D'),
            other_copy_activity_bytes=sum(c['bytes'] for c in copies if c['kind'] not in ('H2D','D2D')),memcpy_activities=len(copies),kernels=len(kernels),
            copy_API_calls=len(r['copy']),sync_API_calls=len(r['sync']),other_API_calls=len(r['other']),launch_API_calls=r['launch_API_calls'],
            **{name+'_ranges':r['phase_names'][name] for name in sorted(PHASES)})
        normalized.append(n);api_hist[r['operator']].update(r['api_names'])
    operators={}
    for kind in sorted({r['operator'] for r in normalized}):
        selected=[r for r in normalized if r['operator']==kind];total={field:sum(r[field] for r in selected) for field in selected[0] if field not in ('index','operator','begin_ns')}
        operators[kind]=dict(ranges=len(selected),totals=total,scope_ns_quantiles=quantiles([r['scope_ns'] for r in selected]),runtime_API_calls=dict(api_hist[kind]))
    result=dict(scope='Profiled NVTX function scopes;exclusive Host partition;device time overlaid,not additive;not unprofiled latency',
        formal_span_ns=end-t0,operators=operators,ranges=normalized,outside_operator_runtime_calls=dict(outside_apis),
        formal_anchor=anchors[0]['name'] if anchors else None,prepost_NVTX_ranges_discarded=discarded,
        unmatched_formal_device_activities=dict(unmatched),target_device_count=len(devices),stream_count=len(streams),
        sampled_GPU_metrics=sampled_metrics(db,tables,t0,end),diagnostics=diagnostics(db,tables),
        table_columns={name:[r['name'] for r in db.execute('PRAGMA table_info("'+name+'")')] for name in sorted(tables) if name.startswith(('CUPTI_ACTIVITY','NVTX','GPU_METRICS','TARGET_INFO_GPU_METRICS','DIAGNOSTIC'))})
    db.close();return result


def test():
    assert union([(0,8),(4,12),(15,17)])==14
    assert intersect([(0,8),(10,20)],[(4,12)])==[(4,8),(10,12)]
    p=host_partition(0,20,[(4,12)],[(10,16)],[],[(0,8)])
    assert p==dict(sync_API_ns=6,copy_API_ns=6,other_API_ns=0,bookkeeping_Host_ns=4,other_Host_ns=4)
    assert sum(p.values())==20 and union([(5,15)])==10 # DMA is overlay,not a30ns additive wall.
    try:host_partition(0,20,[(-1,3)],[],[],[])
    except AssertionError:pass
    else:raise AssertionError('Cross-boundary activity admitted')
    print('PASS:interval unions,overlap-safe Host partition and boundary rejection;0 GPU starts')


if __name__=='__main__':test()
