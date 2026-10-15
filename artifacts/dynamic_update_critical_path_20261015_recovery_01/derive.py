"""Descriptive tables from complete raw or public scalar ledgers;no new selection."""
if not __debug__:
    raise SystemExit('Mandatory checks require ordinary Python without optimization.')
import argparse
import json
from pathlib import Path
import numpy as np
from common import load, save, sha
from quality import table
from analyze import distribution


def service_records(w):
    out=[]
    for row in load(w/'primary/RESULTS.json')['rows']:
        if row['kind']!='service':continue
        label=row['label'];checked=load(w/'primary'/(label+'.checked.json'));assert sha(w/'primary'/(label+'.checked.json'))==row['checked_sha256']
        path=w/'primary/outputs'/(label+'.ops.csv');assert sha(path)==checked['raw_outputs'][path.name]['sha256']
        meta=checked['parent_quality']['metadata'];ops=table(path)
        packed=[[int(r['kind']),int(r['rows']),float(r['ack_ms'])] for r in ops]
        for kind in (0,1):assert sum(n for k,n,t in packed if k==kind)==500000
        assert sum(k==2 for k,n,t in packed)==160
        counts={key:meta[key] for key in ('N','D','B','formal_queries','warmup_queries','replacements','update_batches','point_updates','insert_H2D_request_bytes','swap_D2D_request_bytes')}
        out.append(dict(label=label,mode=row['mode'],round=row['round'],order=row['order'],counts=counts,operations=packed))
    assert len(out)==12;return out


def derive(timing,primary,traces,services):
    cells={}
    for op in ('I','D','R'):
        for b in (1,32,512):
            name=f'PLAIN_{op}_{b}';metric=timing['micro'][name]['metrics'];trace=traces[f'trace_{op}_{b}'];profile=trace['profiled_ACK']
            total={key:sum(r['totals'][key] for r in trace['operators'].values()) for key in next(iter(trace['operators'].values()))['totals']}
            ack=profile['total_ACK_ns'];gap=ack-total['scope_ns'];assert gap>=0,('Profile ACK/function timing mismatch',name)
            prof_parts=dict(copy_API_ns=total['copy_API_ns'],sync_API_ns=total['sync_API_ns'],bookkeeping_Host_ns=total['bookkeeping_Host_ns'],
                other_Host_API_wrapper_ns=total['other_API_ns']+total['other_Host_ns']+gap)
            assert abs(sum(prof_parts.values())-ack)<=1e-7*max(1.,ack)
            processes=[r for r in primary if r['job']['kind']=='micro' and r['job']['variant']=='PLAIN' and r['job']['op']==op and r['job']['batch']==b]
            cpu=distribution([(r['metadata']['CPU_events_user_s']+r['metadata']['CPU_events_system_s'])*1000/r['metadata']['events_ms'] for r in processes])
            cells[f'{op}_{b}']=dict(operator=op,batch=b,points_per_ACK=b*(2 if op=='R' else 1),native_metrics=metric,
                native_process_CPU_core_equivalents=cpu,profile_ACKs=profile['ACKs'],profile_total_ACK_ns=ack,profile_mean_ACK_ms=profile['mean_ACK_ms'],
                profile_host_parts_ns=prof_parts,profile_host_fractions={key:value/ack for key,value in prof_parts.items()},
                profile_device_totals=total,profile_DMA_over_ACK=total['DMA_union_ns']/ack,profile_kernel_over_ACK=total['kernel_union_ns']/ack,
                profile_over_native_mean_ratio=profile['mean_ACK_ms']/metric['mean_ACK_ms']['median'],
                profile_sampling=trace['sampled_GPU_metrics'],profile_diagnostics=trace['diagnostics'])
    whole={}
    lookup={r['job']['label']:r for r in primary if r['job']['kind']=='service'}
    for mode in ('S1','S2_STALE'):
        rows=sorted((r for r in services if r['mode']==mode),key=lambda r:r['round']);assert [r['round'] for r in rows]==list(range(1,7))
        native={}
        for kind,label in ((0,'D'),(1,'I'),(2,'Q')):
            stats=[]
            for process in rows:
                values=[t for k,n,t in process['operations'] if k==kind];a=np.array(values,float)
                assert len(values)==160 if kind==2 else 2*len(values)==process['counts']['update_batches']
                stats.append(dict(ACKs=len(values),total_ACK_ms=float(a.sum()),mean_ACK_ms=float(a.mean()),p50_ACK_ms=float(np.quantile(a,.5)),p95_ACK_ms=float(np.quantile(a,.95))))
            native[label]={field:distribution([s[field] for s in stats]) for field in stats[0]}
        shares=[];cpu=[]
        for i,row in enumerate(rows):
            meta=lookup[row['label']]['parent_quality']['metadata'];d=native['D']['total_ACK_ms']['process_values'][i];ins=native['I']['total_ACK_ms']['process_values'][i]
            assert abs(d+ins-meta['update_ms_including_statistics'])<1e-6 and abs(native['Q']['total_ACK_ms']['process_values'][i]-meta['query_ms'])<1e-6
            shares.append((d+ins)/meta['service_ms']);cpu.append((meta['cpu_events_user_s']+meta['cpu_events_system_s'])*1000/meta['events_ms'])
        whole[mode]=dict(native_operators=native,update_share_of_service=distribution(shares),CPU_event_core_equivalents=distribution(cpu),counts=rows[0]['counts'])
    summary=dict(scope='Descriptive derived tables;original inferential comparisons remain unchanged in TIMING.json',micro=cells,whole_service=whole,
        query_median_gain_percent=100*(1-timing['whole_service']['S2_STALE']['query_ms']['median']/timing['whole_service']['S1']['query_ms']['median']),
        service_median_gain_percent=100*(1-timing['comparisons']['STALE_over_S1_service']['median_ratio']),
        service_paired_interval_crosses_one=timing['comparisons']['STALE_over_S1_service']['paired_95_CI'][0]<=1<=timing['comparisons']['STALE_over_S1_service']['paired_95_CI'][1],
        D512_payload_rate_GB_s=timing['micro']['PLAIN_D_512']['metrics']['requested_payload_GB_per_ACK_s']['median'],
        bulk_D2D_payload_rate_GB_s=timing['bulk_copy_reference']['D2D']['payload_GB_per_ACK_s']['median'],
        I512_payload_rate_GB_s=timing['micro']['PLAIN_I_512']['metrics']['requested_payload_GB_per_ACK_s']['median'],
        bulk_pageable_H2D_payload_rate_GB_s=timing['bulk_copy_reference']['H2D']['payload_GB_per_ACK_s']['median'],
        new_update_optimization_implemented=False,new_same_contract_service_speedup_claim=False)
    assert traces['trace_service']['operators']['Q']['totals']['kernels']>0,'Positive-control query kernels must be visible'
    return summary


def main():
    p=argparse.ArgumentParser();p.add_argument('--curated',type=Path,required=True);p.add_argument('--work',type=Path);p.add_argument('--services',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    assert (a.work is None)!=(a.services is None);records=service_records(a.work) if a.work else load(a.services)
    summary=derive(load(a.curated/'results/TIMING.json'),load(a.curated/'evidence/PRIMARY_SCALARS.json'),load(a.curated/'results/TIMELINES.json'),records)
    a.out.mkdir(parents=True,exist_ok=False)
    with (a.out/'SERVICE_OPERATORS.json').open('x') as f:json.dump(records,f,separators=(',',':'));f.write('\n')
    save(a.out/'DERIVED.json',summary);print('DERIVED:all9microcells,12 native service ledgers,CPU accounting and profiler perturbation;no new GPU starts')


if __name__=='__main__':main()
