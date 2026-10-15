"""Read-only adaptation of the frozen NSYS parser for safe batching/materialization."""
if not __debug__:raise SystemExit('Mandatory checks require ordinary Python without optimization.')
from common import BASE,module
from bisect import bisect_right
import collections

def parse(path,update):
    legacy=module('ownership_trace_base',BASE/'timeline.py')
    original_records=legacy.records;captured={}
    special={'cuLibraryGetKernel':'kernel_lookup_API_calls','cuKernelGetName':'kernel_name_API_calls','cudaGetLastError':'get_last_error_API_calls'}
    def records(db,table):
        rows=original_records(db,table)
        if table in ('StringIds','NVTX_EVENTS'):captured[table]=rows
        if table=='CUPTI_ACTIVITY_KIND_RUNTIME':
            strings={r['id']:r['value'] for r in captured['StringIds']}
            captured['special']=[{**r,'extra':next(field for name,field in special.items() if strings[r['nameId']].startswith(name))} for r in rows if any(strings[r['nameId']].startswith(name) for name in special)]
        return rows
    legacy.records=records
    legacy.PHASES=legacy.PHASES|{'DELETE_EXECUTE'}
    legacy.EXPECTED_PHASES['D']={'DELETE_VALIDATE':1,'DELETE_ROWS':1,**({'DELETE_EXECUTE':1} if update!='NATIVE' else {})}
    def check_api(operator,names):
        if operator not in ('D','I'):return
        assert names.get('cudaStreamSynchronize_v3020')==1,('Missing/duplicate ACK wait',operator)
        allowed=('cudaMemcpyAsync_','cudaMemcpyBatchAsync_','cudaStreamSynchronize_','cudaLaunchKernel_','cudaLaunchKernelExC_','cudaGetLastError_','cuLibraryGetKernel','cuKernelGetName')
        assert all(n.startswith(allowed) for n in names),('Unreviewed update API',dict(names))
        if operator=='I':assert set(names)<={'cudaMemcpyAsync_v3020','cudaStreamSynchronize_v3020'}
    legacy.check_update_api=check_api
    result=legacy.parse(path)
    strings={r['id']:r['value'] for r in captured['StringIds']};nvtx=[dict(r,name=strings.get(r.get('textId')) or r.get('text')) for r in captured['NVTX_EVENTS']]
    anchors=[r for r in nvtx if r['name'] in legacy.FORMAL];assert len(anchors)<=1
    ranges=[r for r in nvtx if r['name'] in legacy.OPERATORS and (not anchors or anchors[0]['start']<=r['start']<=r['end']<=anchors[0]['end'])]
    ranges.sort(key=lambda r:r['start']);assert len(ranges)==len(result['ranges']);by_tid=collections.defaultdict(list)
    for i,(raw,normalized) in enumerate(zip(ranges,result['ranges'])):
        assert normalized['begin_ns']==raw['start']-ranges[0]['start'] and normalized['scope_ns']==raw['end']-raw['start']
        normalized.update({field:0 for field in special.values()});by_tid[raw['globalTid']].append(i)
    starts={tid:[ranges[i]['start'] for i in ids] for tid,ids in by_tid.items()}
    for api in captured['special']:
        tid=api['globalTid']
        if tid not in starts:continue
        index=bisect_right(starts[tid],api['start'])-1
        if index<0:continue
        i=by_tid[tid][index];r=ranges[i]
        if api['start']>=r['end']:continue
        assert r['start']<=api['start']<=api['end']<=r['end'];result['ranges'][i][api['extra']]+=1
    for op,value in result['operators'].items():
        for field in special.values():value['totals'][field]=sum(r[field] for r in result['ranges'] if r['operator']==op)
    result['scope']='Profiled function scopes;exclusive Host spans and overlaid device activity. API spans are not pure CPU computation;not native ACK latency.'
    result['update']=update
    return result

def bind(trace,physical,operators):
    assert len(trace['ranges'])==len(operators)
    at=0
    for actual,op in zip(trace['ranges'],operators):
        assert actual['operator']==op
        if op=='Q':continue
        wanted={k:int(v) for k,v in physical[at].items()};at+=1
        assert wanted['kind']==int(op=='I')
        for name,key in (('copy_API_calls','copy_APIs'),('sync_API_calls','syncs'),('launch_API_calls','launches'),('kernels','launches')):
            assert actual[name]==wanted[key],('Per-ACK count mismatch',actual['index'],name,actual[name],wanted[key])
        assert actual['H2D_activity_bytes']==wanted['H2D_plan_bytes']+wanted['H2D_vector_bytes']
        assert actual['D2D_activity_bytes']==wanted['D2D_bytes'] and actual['other_copy_activity_bytes']==0
        # CUDA13/NSYS exposes driver metadata lookups;GetLastError may have no trace callback.
        metadata=sum(actual[field] for field in ('kernel_lookup_API_calls','kernel_name_API_calls','get_last_error_API_calls'))
        assert all(0<=actual[field]<=wanted['launches'] for field in ('kernel_lookup_API_calls','kernel_name_API_calls','get_last_error_API_calls'))
        assert actual['other_API_calls']==wanted['launches']+metadata
    assert at==len(physical)
    trace['physical_binding']=dict(passed=True,ACKs=at,query_scopes=len(operators)-at,
        scope='Exact chronological API/launch/transfer accounting against the validated physical ledger;kernel payload is not a memcpy activity or DRAM count.')

def test():
    trace={'ranges':[dict(index=0,operator='D',copy_API_calls=1,sync_API_calls=1,launch_API_calls=1,kernels=1,H2D_activity_bytes=4096,D2D_activity_bytes=0,other_copy_activity_bytes=0,other_API_calls=2,kernel_lookup_API_calls=0,kernel_name_API_calls=0,get_last_error_API_calls=1)]}
    row=dict(kind=0,copy_APIs=1,syncs=1,launches=1,H2D_plan_bytes=4096,H2D_vector_bytes=0,D2D_bytes=0)
    bind(trace,[row],['D']);trace['ranges'][0]['H2D_activity_bytes']+=1
    try:bind(trace,[row],['D'])
    except AssertionError:pass
    else:raise AssertionError('Traffic corruption admitted')
    module('ownership_interval_tests',BASE/'timeline.py').test()
    print('PASS:batch/materialization ledger binding and corrupt-traffic rejection;0 GPU starts')

if __name__=='__main__':test()
