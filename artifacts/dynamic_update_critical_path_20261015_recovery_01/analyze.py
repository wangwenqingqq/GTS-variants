"""Frozen six-process ACK estimators; diagnostic timelines never replace latency."""
if not __debug__:
    raise SystemExit('Optimized Python disables mandatory checks; run without -O/PYTHONOPTIMIZE.')
import numpy as np
from common import load, jobs


def distribution(values):
    a=np.array(values,float);assert a.shape==(6,) and np.isfinite(a).all()
    return dict(median=float(np.median(a)),p10=float(np.quantile(a,.1)),p90=float(np.quantile(a,.9)),arithmetic_mean=float(np.mean(a)),process_values=a.tolist())


def compare(a,b):
    a=np.array(a,float);b=np.array(b,float);assert a.shape==b.shape==(6,) and np.min(a)>0 and np.min(b)>0
    logs=np.log(b/a);rng=np.random.default_rng(2026101511);boot=np.exp(np.mean(logs[rng.integers(0,6,(20000,6))],axis=1))
    return dict(median_ratio=float(np.median(b)/np.median(a)),paired_geometric_ratio=float(np.exp(np.mean(logs))),
        paired_95_CI=np.quantile(boot,[.025,.975]).tolist(),paired_ratios=(b/a).tolist(),wins=int(np.count_nonzero(b<a)),
        order_strata={name:dict(geometric_ratio=float(np.exp(np.mean(logs[ids]))),wins=int(np.count_nonzero(b[ids]<a[ids]))) for name,ids in (('forward',[0,2,4]),('reverse',[1,3,5]))})


def summarize_micro(records,job):
    kind={'I':1,'D':0,'R':2}[job['op']];selected=[r for r in records if int(r['kind'])==kind]
    assert len(selected)==job['K']//job['batch'];ack=np.array([float(r['ack_ms']) for r in selected]);points=job['K']*(2 if kind==2 else 1)
    h=sum(int(r['H2D_bytes']) for r in selected);d=sum(int(r['D2D_bytes']) for r in selected);total=float(np.sum(ack))
    assert np.isfinite(ack).all() and np.min(ack)>0
    return dict(mean_ACK_ms=float(np.mean(ack)),p50_ACK_ms=float(np.quantile(ack,.5)),p95_ACK_ms=float(np.quantile(ack,.95)),
        total_ACK_ms=total,amortized_us_per_point=total*1000/points,ACKs_per_s=len(ack)*1000/total,
        point_updates_per_s=points*1000/total,requested_payload_GB_per_ACK_s=(h+d)/total/1e6,
        H2D_request_bytes=h,D2D_request_bytes=d,copy_calls=sum(int(r['copy_calls']) for r in selected),
        sync_calls=sum(int(r['sync_calls']) for r in selected),batch_ACKs=len(ack),point_updates=points,
        delete_total_ms=sum(float(r['delete_ms']) for r in selected),insert_total_ms=sum(float(r['insert_ms']) for r in selected))


def run(processes):
    assert len(processes)==84 and [r['job'] for r in processes]==jobs('primary')
    micro={};service={};copies={}
    for v in ('PLAIN','MARKED'):
        for op in ('I','D','R'):
            for b in (1,32,512):
                rows=[r for r in processes if r['job']['kind']=='micro' and r['job']['variant']==v and r['job']['op']==op and r['job']['batch']==b]
                if not rows:continue
                assert [r['job']['round'] for r in rows]==list(range(1,7))
                summaries=[summarize_micro(r['operator_samples'],r['job']) for r in rows]
                micro[f'{v}_{op}_{b}']=dict(variant=v,operator=op,batch=b,metrics={name:distribution([s[name] for s in summaries]) for name in summaries[0]})
    for mode in ('S1','S2_STALE'):
        rows=[r['parent_quality']['metadata'] for r in processes if r['job']['kind']=='service' and r['job']['mode']==mode]
        service[mode]={name:distribution([r[name] for r in rows]) for name in ('service_ms','events_ms','release_ms','query_ms','update_ms_including_statistics','other_ms','cpu_events_user_s','cpu_events_system_s')}
    for kind,name in ((0,'H2D'),(1,'D2D')):
        values=[]
        for r in processes:
            if r['job']['kind']!='copy':continue
            ack=np.array([float(s['ack_ms']) for s in r['samples'] if int(s['kind'])==kind]);assert len(ack)==16
            values.append(dict(mean_ACK_ms=float(np.mean(ack)),p95_ACK_ms=float(np.quantile(ack,.95)),payload_GB_per_ACK_s=(1<<30)/float(np.mean(ack))/1e6))
        copies[name]={metric:distribution([v[metric] for v in values]) for metric in values[0]}
    comparisons={}
    for b in (1,32,512):
        comparisons[f'D_over_I_B{b}']=compare(micro[f'PLAIN_I_{b}']['metrics']['mean_ACK_ms']['process_values'],micro[f'PLAIN_D_{b}']['metrics']['mean_ACK_ms']['process_values'])
    for b in (1,512):
        comparisons[f'MARKED_over_PLAIN_R_B{b}']=compare(micro[f'PLAIN_R_{b}']['metrics']['mean_ACK_ms']['process_values'],micro[f'MARKED_R_{b}']['metrics']['mean_ACK_ms']['process_values'])
    for op in ('I','D','R'):
        comparisons[f'B512_over_B1_amortized_{op}']=compare(micro[f'PLAIN_{op}_1']['metrics']['amortized_us_per_point']['process_values'],micro[f'PLAIN_{op}_512']['metrics']['amortized_us_per_point']['process_values'])
    comparisons['STALE_over_S1_service']=compare(service['S1']['service_ms']['process_values'],service['S2_STALE']['service_ms']['process_values'])
    return dict(scope='Unprofiled whole ACKs;6process distributions;median ratios and paired CIs separate;no SLA/production/novelty gate',
        micro=micro,whole_service=service,bulk_copy_reference=copies,comparisons=comparisons,
        seed=2026101511,bootstrap_resamples=20000,percentile_scope='within-process finite ACK quantiles,then process distribution')


def check():
    a=np.arange(1,7,dtype=float);r=compare(a,.8*a);assert r['wins']==6 and abs(r['median_ratio']-.8)<1e-14 and all(abs(v-.8)<1e-14 for v in r['paired_95_CI'])
    print('PASS:paired process estimators and finite-percentile scope')


if __name__=='__main__':check()
