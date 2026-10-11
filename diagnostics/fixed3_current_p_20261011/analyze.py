"""Current-P same-scope profiler and process-paired evidence, never replay latency."""
import csv,json,math,random,sqlite3,statistics
from pathlib import Path
import numpy as np

def save(p,x):Path(p).write_text(json.dumps(x,indent=2)+'\n')
def percentile(x,p):
    x=sorted(x);at=(len(x)-1)*p;i=int(at);return x[i]+(x[min(i+1,len(x)-1)]-x[i])*(at-i)
def paired(a,b,orders,left,right,seed):
    assert len(a)==len(b)==len(orders)==6 and all(math.isfinite(x) and x>0 for x in a+b)
    logs=[math.log(x/y) for x,y in zip(a,b)];rng=random.Random(seed)
    boot=[math.exp(statistics.mean(rng.choices(logs,k=6))) for _ in range(20000)]
    ci=[percentile(boot,.025),percentile(boot,.975)];wins=sum(x>y for x,y in zip(a,b))
    split={}
    for first in (left,right):
        selected=[logs[i] for i,o in enumerate(orders) if (o.index(left)<o.index(right))==(first==left)]
        split[first+'_before_other']=math.exp(statistics.mean(selected))
    return dict(paired_geometric_ratio=math.exp(statistics.mean(logs)),bootstrap_95=ci,candidate_process_wins=wins,
        raw_paired_ratios=[x/y for x,y in zip(a,b)],marginal_median_ratio=statistics.median(a)/statistics.median(b),relative_order_split=split,
        decision='confirmed_win' if ci[0]>1 and wins>=5 else 'confirmed_regression' if ci[1]<1 else 'inconclusive')
def work(path):
    with Path(path).open('rb') as f:
        head=np.fromfile(f,dtype='<u8',count=7);magic,epoch,n,nn,nl,qid,seq=map(int,head);assert magic==0x43504633574f524b
        arrays=[np.fromfile(f,dtype='<u8',count=m) for m in (nn,nn,nn,n)]
        leaves=np.fromfile(f,dtype='<i4',count=nl);sizes=np.fromfile(f,dtype='<i4',count=nl);assert f.read()==b''
    assert all(len(x)==m for x,m in zip(arrays,(nn,nn,nn,n))) and len(leaves)==len(sizes)==nl
    assert np.all((sizes>=1)&(sizes<=20))
    groups=np.pad((leaves>=0).astype(int),(0,(-nl)%3)).reshape(-1,3).sum(axis=1)
    # Counter helper excludes self; current logical requests are nonindexed scratch rows.
    nonself=int(arrays[3].sum());assert qid>=n,'self branch requires separately priced arithmetic ledger'
    return dict(seq=seq,epoch=epoch,n=n,node_count=nn,canonical_leaves=nl,qid=qid,
        node_tests=int(arrays[0].sum()),pivot_evaluations=int(arrays[1].sum()),visited_leaves=int(arrays[2].sum()),
        distance_objects=nonself,distance_dimensions=nonself*960,
        P0_ctas=nl,P1_ctas=nl,P2_ctas=(nl+2)//3,packed_active_group_histogram={str(i):int((groups==i).sum()) for i in range(4)},
        canonical_leaf_size_histogram={str(i):int((sizes==i).sum()) for i in range(1,21)})
def trace(path):
    db=sqlite3.connect(path);db.row_factory=sqlite3.Row
    ranges=[dict(x) for x in db.execute('SELECT n.start,n.end,coalesce(n.text,s.value) AS name FROM NVTX_EVENTS n LEFT JOIN StringIds s ON n.textId=s.id')]
    passes=sorted((x for x in ranges if x['name']=='native.trace'),key=lambda x:x['start']);assert len(passes)==2
    lo,hi=passes[-1]['start'],passes[-1]['end'];assert hi>lo
    kernels=[dict(x) for x in db.execute('SELECT k.*,s.value AS name FROM CUPTI_ACTIVITY_KIND_KERNEL k JOIN StringIds s ON k.demangledName=s.id WHERE k.start>=? AND k.end<=? ORDER BY k.start',(lo,hi))]
    leaf=[x for x in kernels if x['name'].startswith('rex::verify_materialized(')];assert len(leaf)==128
    runtime=[dict(x) for x in db.execute('SELECT r.*,s.value AS name FROM CUPTI_ACTIVITY_KIND_RUNTIME r JOIN StringIds s ON r.nameId=s.id WHERE r.start>=? AND r.end<=?',(lo,hi))]
    assert all(x['returnValue']==0 for x in runtime)
    families={}
    for x in kernels:
        name=x['name'].split('(')[0];v=families.setdefault(name,dict(count=0,inclusive_ms=0.));v['count']+=1;v['inclusive_ms']+=(x['end']-x['start'])/1e6
    rows=[dict(duration_ms=(x['end']-x['start'])/1e6,ctas=x['gridX']*x['gridY']*x['gridZ'],threads=x['blockX']*x['blockY']*x['blockZ'],registers=x['registersPerThread'],static_shared=x['staticSharedMemory'],local_bytes=x['localMemoryPerThread']) for x in leaf]
    return dict(scope='NSYS kernel-inclusive diagnostic; second native.trace only; not unprofiled latency/occupancy',leaf_inclusive_ms=sum(x['duration_ms'] for x in rows),leaf_launches=len(rows),leaf_ctas=sum(x['ctas'] for x in rows),configured_warp_slots=sum(x['ctas']*(x['threads']//32) for x in rows),kernel_count=len(kernels),kernel_inclusive_ms=sum((x['end']-x['start'])/1e6 for x in kernels),cuda_api_count=len(runtime),cuda_api_inclusive_ms=sum((x['end']-x['start'])/1e6 for x in runtime),rows=rows,kernel_families=families)
def formal(root,c):
    values={m:[] for m in ('P0','P1','P2')};rows=[];ops={m:{str(f):[] for f in range(4)} for m in values};operation_totals={m:{str(f):[] for f in range(4)} for m in values}
    for number,order in enumerate(c['formal_orders'],1):
        for pos,mode in enumerate(order):
            label=f'r{number}_{mode}';p=root/'outputs'/label;s=json.loads(Path(str(p)+'.summary.json').read_text());ms=s['trace_ms'];values[mode].append(ms)
            rr=list(csv.DictReader(Path(str(p)+'.ops.csv').open()));assert len(rr)==336
            row=dict(round=number,position=pos,mode=mode,total_ms=ms,cpu_user_s=s['cpu_user_s'],cpu_system_s=s['cpu_system_s'],device_peak_bytes=s['sampled_device_peak_bytes'])
            for f in range(4):
                samples=[float(x['ack_ms']) for x in rr if int(x['flag'])==f];ops[mode][str(f)].extend(samples);operation_totals[mode][str(f)].append(sum(samples));row['flag'+str(f)+'_ack_sum_ms']=sum(samples)
            rows.append(row)
    def dist(x):return dict(raw_ms=x,p10_ms=percentile(x,.1),median_ms=statistics.median(x),p90_ms=percentile(x,.9),arithmetic_mean_ms=statistics.mean(x),geometric_mean_ms=math.exp(statistics.mean(map(math.log,x))))
    return dict(scope=c['primary'],rows=rows,distributions={m:dist(x) for m,x in values.items()},
        ratios={a+'_over_'+b:paired(values[a],values[b],c['formal_orders'],a,b,c['primary']['seed']) for a,b in [('P0','P1'),('P1','P2'),('P0','P2')]},
        operation_ACKs={m:{f:dist(x) for f,x in v.items()} for m,v in ops.items()},operation_process_totals={m:{f:dist(x) for f,x in v.items()} for m,v in operation_totals.items()})
