#!/usr/bin/env python3
"""Read all six fresh pairs; registered trace-minus-release service and nested ledgers."""
import argparse,csv,hashlib,importlib.util,math,statistics
import numpy as np
from pathlib import Path
from prepare import read,save,sha
from test_recipe import service_timer
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('prior_stats',HERE.parent/'fixed3_current_p_20261011/analyze.py')
prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)
pct=prior.percentile

def dist(x):
    assert x and all(math.isfinite(v) and v>=0 for v in x)
    return dict(raw_ms=x,arithmetic_mean_ms=statistics.mean(x),geometric_mean_ms=math.exp(statistics.mean(map(math.log,x))) if min(x)>0 else None,median_ms=statistics.median(x),p10_ms=pct(x,.1),p90_ms=pct(x,.9),p95_ms=pct(x,.95),p99_ms=pct(x,.99))
def ratio(a,b,c):
    x=prior.paired(a,b,c['primary']['orders'],'P2','E',c['primary']['seed'])
    x['P2_process_wins']=sum(v<w for v,w in zip(a,b));x.pop('candidate_process_wins')
    x['orientation']='P2/E; >1 means P2 slower'
    x['decision']='P2_slower' if x['bootstrap_95'][0]>1 else 'P2_faster' if x['bootstrap_95'][1]<1 else 'inconclusive'
    return x

def collect(r,c):
    assert read(r/'CLOSURE.json')['passed'];g=read(r/'primary/GATE.json');assert g['passed'] and len(g['rows'])==12
    rows=[];v={m:[] for m in ('P2','E')};legacy={m:[] for m in v};totals={m:{f:[] for f in range(4)} for m in v};tails={m:{f:[] for f in range(4)} for m in v};payloads={m:[] for m in v}
    for n,order in enumerate(c['primary']['orders'],1):
        for pos,m in enumerate(order):
            p=r/'primary/outputs'/f'r{n}_{m}';s=read(str(p)+('.summary.json' if m=='P2' else '.pe.json'));t=service_timer(s,m);v[m].append(t);legacy[m].append(s['trace_ms'])
            scope=read(str(p)+'.scope.json');rr_scope={k:scope[k] for k in ('parse_ms','context_ms','warmup_total_ms')}
            rr_scope['restored_setup_ms']=read(str(p)+'.region.json')['setup_ms'] if m=='P2' else s['setup_ms']
            ops=list(csv.DictReader(Path(str(p)+'.ops.csv').open()));assert len(ops)==336
            rr=dict(round=n,position=pos,method=m,service_ms=t,trace_plus_release_ms=s['trace_ms'],final_state_release_ms=s['trace_ms']-t,cpu_user_trace_plus_release_s=s['cpu_user_s'],cpu_system_trace_plus_release_s=s['cpu_system_s'])
            rr['lifecycle_side_accounts']=rr_scope
            rr['device_snapshot_bytes']=s['sampled_device_peak_bytes'] if m=='P2' else s['device_used_built_bytes']
            for f,count in enumerate((40,40,128,128)):
                samples=[float(x['ack_ms']) for x in ops if int(x['flag'])==f];assert len(samples)==count
                totals[m][f].append(sum(samples));tails[m][f].extend(samples);rr['flag'+str(f)+'_ack_ms']=sum(samples)
            rr['ACK_sum_ms']=sum(rr['flag'+str(f)+'_ack_ms'] for f in range(4));rr['between_ACK_residual_ms']=t-rr['ACK_sum_ms'];assert rr['between_ACK_residual_ms']>=0
            rr['rebuild_inclusive_ms']=sum(float(x['rebuild_ms']) for x in ops);rr['rebuild_calls']=sum(float(x['rebuild_ms'])>0 for x in ops)
            if m=='P2':
                numeric=read(str(p)+'.numeric.json');live=read(str(p)+'.unified.json');region=read(str(p)+'.region.json')
                rr['inclusive_stages']=s['stages'];rr['numeric_refresh_update_ms']=sum(numeric['refresh_ms'][1:]);rr['knn_pack_refresh_update_ms']=sum(live['refresh_ms'][1:]);rr['region']=region;rr['PAR_plan_refresh_update_ms']=sum(x['ms'] for x in region['refresh_rows'][1:])
            qs=list(csv.DictReader(Path(str(p)+'.queries.csv').open()));counts=[int(x['count']) for x in qs];assert len(counts)==256
            payload=dict(items=sum(counts),ID_FP32_bytes=sum(counts)*8,extra_native_squared_bytes=sum(counts)*8 if m=='E' else 0,range_items=sum(z for z,op in zip(counts,[x for x in ops if int(x['flag'])>=2]) if int(op['flag'])==2),final_sha256=sha(str(p)+'.final.i32'))
            final=np.fromfile(str(p)+'.final.i32',dtype='<i4');payload['logical_final_set_sha256']=hashlib.sha256(np.sort(final).astype('<i4').tobytes()).hexdigest()
            payloads[m].append(payload);rr['payload']=payload;rr['summary_sha256']=sha(str(p)+('.summary.json' if m=='P2' else '.pe.json'));rows.append(rr)
    return dict(primary_measurement_note='Registered trace minus measured final drain/release; unisolated post-drain fence/clock tail remains; not exact last-ACK isolation',lifecycle_side_accounts={m:{k:dist([x['lifecycle_side_accounts'][k] for x in rows if x['method']==m]) for k in ('parse_ms','context_ms','warmup_total_ms','restored_setup_ms')} for m in ('P2','E')},experiment=c['experiment'],primary_scope=c['primary'],rows=rows,service_distributions={m:dist(x) for m,x in v.items()},primary_ratio=ratio(v['P2'],v['E'],c),legacy_trace_plus_release_distributions={m:dist(x) for m,x in legacy.items()},legacy_ratio=ratio(legacy['P2'],legacy['E'],c),operation_process_totals={m:{str(f):dist(x) for f,x in per.items()} for m,per in totals.items()},pooled_request_tail={m:{str(f):dist(x) for f,x in per.items()} for m,per in tails.items()},payloads=payloads,limits=['CI covers process variation of this fixed trace only','nested inclusive stages cannot be added to ACKs or CUDA waits','no full independent Host-output component in frozen binaries','device built snapshot and sampled peak are different estimators'])
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();j=collect(a.root,read(HERE/'CONTRACT.json'));save(a.out,j)
    print(j['primary_ratio']);print({m:x['geometric_mean_ms'] for m,x in j['service_distributions'].items()})
