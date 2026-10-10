#!/usr/bin/env python3
"""Analyze all12 new logical P/E jobs; never substitute old component timings."""
if not __debug__:raise RuntimeError('Python assertions must remain enabled')
import argparse,json,math
from pathlib import Path
from common import outside_repo
import numpy as np
from qualify import cpu
from pe_check import check,csvrows
from pe_campaign import CONTRACT,jobs
from pe_binding import bind
read=lambda p:json.loads(Path(p).read_text())

def paired(e,p):
    x=np.asarray(e);y=np.asarray(p);assert x.shape==y.shape==(6,) and np.isfinite(x).all() and np.isfinite(y).all() and (x>0).all() and (y>0).all()
    ratios=x/y;logs=np.log(ratios);rng=np.random.default_rng(2026101010);boot=np.exp(logs[rng.integers(0,6,(20000,6))].mean(1));ci=np.quantile(boot,[.025,.975]).tolist()
    strata={order:float(np.exp(logs[np.array(CONTRACT['orders'])==order].mean())) for order in ('PE','EP')}
    return dict(paired_geometric_E_over_P=float(np.exp(logs.mean())),CI95=ci,P_wins=int((ratios>1).sum()),raw_ratios=ratios.tolist(),order_strata=strata,marginal_median_E_over_P=float(np.median(x)/np.median(y)),arithmetic_mean_E_over_P=float(x.mean()/y.mean()),meaningful_P_gain=ci[0]>1.05 and (ratios>1).sum()>=5 and min(strata.values())>1)

def result(a):
    proof=bind(a)
    w=a.work;reg=read(w/'RECOVERY.json');q=read(w/'recovery/RESULTS.json');formal=read(w/'primary/RESULTS.json')
    assert all(cpu.sha(a.reference.parent/n)==v for n,v in reg['reference'].items()),'reference binding drift'
    assert q['complete'] and formal['complete'] and len(q['rows'])==10 and len(formal['rows'])==12
    assert all(r['status']=='passed' for r in q['rows']+formal['rows']) and all(v['passed'] for v in reg['first_sample_offline_recheck'].values())
    assert [(r['label'],r['method'],r['case'],r['order']) for r in formal['rows']]==[(r['label'],r['method'],r['case'],r['order']) for r in jobs('primary')]
    rows=[];case=w/'cases/target'
    for j in formal['rows']:
        p=w/'primary/outputs'/j['label'];receipt=w/'primary/guards'/j['label']/'receipt.json';assert cpu.sha(receipt)==j['receipt_sha256'] and read(receipt)['runtime_valid']
        assert cpu.sha(str(p)+'.quality.json')==j['quality_sha256']
        quality=check(a.data,case/'events.txt',case/'trace',p,j['method'],a.reference)
        saved=read(str(p)+'.quality.json');assert quality==saved['measured']
        assert check(a.data,case/'warmup.events',str(case/'trace')+'.warmup',str(p)+'.warmup',j['method'],str(a.reference)+'.warmup')==saved['warmup']
        scope=read(str(p)+'.scope.json');meta=read(str(p)+'.pe.json');ops=csvrows(str(p)+'.ops.csv')
        if j['method']=='P':
            summary=read(str(p)+'.summary.json');region=read(str(p)+'.region.json');trace=summary['trace_ms'];setup=region['setup_ms'];release=summary['final_drain_ms']
            memory={k:summary[k] for k in ('sampled_device_peak_bytes','host_output_capacity_bytes')}
        else:summary=meta;trace=meta['trace_ms'];setup=meta['setup_ms'];release=meta['release_ms'];memory={k:meta[k] for k in ('device_used_built_bytes','device_used_final_bytes','vector_storage_bytes','norm_storage_bytes','client_payload_bytes')}
        ack={name:dict(sum_ms=sum(float(r['ack_ms']) for r in ops if int(r['flag'])==flag),p50_p95_p99_ms=np.quantile([float(r['ack_ms']) for r in ops if int(r['flag'])==flag],[.5,.95,.99]).tolist()) for flag,name in enumerate(('insert','delete','range','knn'))}
        residual=trace-release-sum(v['sum_ms'] for v in ack.values());assert residual>=-1e-6
        rows.append(dict(label=j['label'],round=j['round'],method=j['method'],order=j['order'],trace_ms=trace,setup_ms=setup,setup_plus_trace_ms=setup+trace,release_ms=release,trace_residual_ms=residual,
            parse_ms=scope['parse_ms'],context_ms=scope['context_ms'],warmup_total_ms=scope['warmup_total_ms'],ack=ack,rebuild_inclusive_ms=sum(float(r['rebuild_ms']) for r in ops),
            memory=memory,cpu_user_s=summary['cpu_user_s'],cpu_system_s=summary['cpu_system_s'],output_items=quality['output_items'],quality_sha256=j['quality_sha256'],receipt_sha256=j['receipt_sha256'],payload_hashes=quality['payload_hashes']))
    comparisons={s:paired([next(r[s] for r in rows if r['round']==i and r['method']=='E') for i in range(1,7)],[next(r[s] for r in rows if r['round']==i and r['method']=='P') for i in range(1,7)]) for s in ('trace_ms','setup_plus_trace_ms')}
    return dict(status='MEASURED_PE_LOGICAL_SHORT',shape=CONTRACT['shape'],events=CONTRACT['events'],rows=rows,comparisons=comparisons,branch='sustained_candidate_requires_separate_registration' if comparisons['trace_ms']['meaningful_P_gain'] else 'one_cost_intervention_no_10K',
        registration_sha256=cpu.sha(w/'REGISTERED.json'),recovery_sha256=cpu.sha(w/'RECOVERY.json'),formal_results_sha256=cpu.sha(w/'primary/RESULTS.json'),binaries=reg['binaries'],source_hashes=reg['source_hashes'],binding=proof,
        actual_qualification_GPU_processes=11,failed_checker_records_retained=1,formal_GPU_processes=12,limits=CONTRACT['limits']+['E native squared observer charged','final occurrence manifest retained inside service release; client destruction/disk outside','adapter results are not native Faiss dynamic indexing'])

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('work','data','reference','output','first-source','executed-source','p-build','e-build'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();a.output=outside_repo(a.output);assert not a.output.exists();cpu.save(a.output,result(a))
