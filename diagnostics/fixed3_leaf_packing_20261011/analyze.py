#!/usr/bin/env python3
"""Same-scope trace summaries and preregistered three-way process statistics."""
import csv,json,math,random,sqlite3,statistics
from pathlib import Path

def trace(path):
    db=sqlite3.connect(path);db.row_factory=sqlite3.Row
    ranges=[dict(x) for x in db.execute("SELECT n.start,n.end,coalesce(n.text,s.value) AS name FROM NVTX_EVENTS n LEFT JOIN StringIds s ON n.textId=s.id")]
    passes=[x for x in ranges if x['name']=='formal.query_pass'];assert len(passes)==1
    lo,hi=passes[0]['start'],passes[0]['end'];assert hi and hi>lo
    queries=[x for x in ranges if x['name']=='query.gts.host_ready' and x['start']>=lo and x['end'] and x['end']<=hi]
    assert len(queries)==32
    kernels=[dict(x) for x in db.execute('SELECT k.*,s.value AS name FROM CUPTI_ACTIVITY_KIND_KERNEL k JOIN StringIds s ON k.demangledName=s.id WHERE k.start>=? AND k.end<=? ORDER BY k.start',(lo,hi))]
    leaf=[x for x in kernels if x['name'].startswith('dataProcessKnn(')];assert len(leaf)==32
    runtime=[dict(x) for x in db.execute('SELECT r.*,s.value AS name FROM CUPTI_ACTIVITY_KIND_RUNTIME r JOIN StringIds s ON r.nameId=s.id WHERE r.start>=? AND r.end<=?',(lo,hi))]
    assert all(x['returnValue']==0 for x in runtime),'CUDA API errors'
    families={}
    for x in kernels:
        name=x['name'].split('(')[0];v=families.setdefault(name,{'count':0,'inclusive_ms':0.})
        v['count']+=1;v['inclusive_ms']+=(x['end']-x['start'])/1e6
    rows=[]
    for q,x in zip(sorted(queries,key=lambda v:v['start']),leaf):
        assert q['start']<=x['start']<x['end']<=q['end']
        rows.append({'duration_ms':(x['end']-x['start'])/1e6,'ctas':x['gridX']*x['gridY']*x['gridZ'],
            'threads':x['blockX']*x['blockY']*x['blockZ'],'registers':x['registersPerThread'],
            'static_shared_bytes':x['staticSharedMemory'],'dynamic_shared_bytes':x['dynamicSharedMemory'],
            'local_bytes_per_thread':x['localMemoryPerThread']})
    return {'scope':'NSYS inclusive kernel duration, not unprofiled latency or SM occupancy',
        'formal_nvtx_ms':(hi-lo)/1e6,'leaf_inclusive_ms':sum(x['duration_ms'] for x in rows),
        'leaf_launches':len(rows),'leaf_ctas':sum(x['ctas'] for x in rows),
        'configured_warp_slots':sum(x['ctas']*(x['threads']//32) for x in rows),
        'kernel_count':len(kernels),'kernel_inclusive_ms':sum((x['end']-x['start'])/1e6 for x in kernels),
        'cuda_api_count':len(runtime),'cuda_api_inclusive_ms':sum((x['end']-x['start'])/1e6 for x in runtime),
        'rows':rows,'kernel_families':families}

def percentile(xs,p):
    xs=sorted(xs);pos=(len(xs)-1)*p;i=int(pos)
    return xs[i]+(xs[min(i+1,len(xs)-1)]-xs[i])*(pos-i)
def paired(a,b,orders,left,right,seed):
    assert len(a)==len(b)==len(orders)==6 and all(math.isfinite(x) and x>0 for x in a+b)
    logs=[math.log(x/y) for x,y in zip(a,b)];rng=random.Random(seed)
    boot=[math.exp(statistics.mean(rng.choices(logs,k=6))) for _ in range(20000)]
    ci=[percentile(boot,.025),percentile(boot,.975)];wins=sum(x>y for x,y in zip(a,b))
    split={}
    for first in (left,right):
        selected=[logs[i] for i,o in enumerate(orders) if (o.index(left)<o.index(right))==(first==left)]
        split[first+'_before_other']=math.exp(statistics.mean(selected))
    return {'paired_geometric_ratio':math.exp(statistics.mean(logs)),'bootstrap_95':ci,
        'candidate_process_wins':wins,'raw_paired_ratios':[x/y for x,y in zip(a,b)],
        'marginal_median_ratio':statistics.median(a)/statistics.median(b),'relative_order_split':split,
        'all_order_strata':[{'order':o,'ratio':a[i]/b[i]} for i,o in enumerate(orders)],
        'decision':'confirmed_win' if ci[0]>1 and wins>=5 else 'confirmed_regression' if ci[1]<1 else 'inconclusive'}
def formal(root,contract):
    orders=contract['formal_process_orders'];values={m:[] for m in ('G0','G1','G2')};rows=[]
    for number,order in enumerate(orders,1):
        for position,mode in enumerate(order):
            label=f'r{number}_{mode}';samples=list(csv.DictReader((root/(label+'.csv')).open()))
            assert len(samples)==1 and samples[0]['sample']=='0'
            ms=float(samples[0]['total_ms']);values[mode].append(ms)
            rows.append({'round':number,'position':position,'mode':mode,'Q':256,'total_ms':ms})
    distributions={m:{'raw_ms':x,'p10_ms':percentile(x,.1),'median_ms':statistics.median(x),'p90_ms':percentile(x,.9),
        'arithmetic_mean_ms':statistics.mean(x),'geometric_mean_ms':math.exp(statistics.mean(map(math.log,x)))} for m,x in values.items()}
    return {'scope':contract['formal_scope'],'distributions':distributions,'rows':rows,
        'ratios':{a+'_over_'+b:paired(values[a],values[b],orders,a,b,contract['statistics']['bootstrap_seed']) for a,b in [('G0','G1'),('G1','G2'),('G0','G2')]}}
