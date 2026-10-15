"""Frozen six-process estimator;reference counts never masquerade as traffic."""
if not __debug__:raise SystemExit('Mandatory checks require ordinary Python without optimization.')
import argparse
from pathlib import Path
import numpy as np
from common import BASE,load,save,module,jobs,UPDATES
stats=module('frozen_process_statistics',BASE/'analyze.py')
distribution,compare=stats.distribution,stats.compare

def micro(checked,job):
    kind={'I':1,'D':0,'R':2}[job['op']];a=np.array([float(r['ack_ms']) for r in checked['operator_samples'] if int(r['kind'])==kind]);assert len(a)==job['K']//job['batch']
    total=float(a.sum());points=job['K']*(2 if job['op']=='R' else 1)
    return dict(mean_ACK_ms=float(a.mean()),p50_ACK_ms=float(np.quantile(a,.5)),p95_ACK_ms=float(np.quantile(a,.95)),total_ACK_ms=total,
        amortized_us_per_point=total*1000/points,point_updates_per_s=points*1000/total)

def run(records):
    assert [r['job'] for r in records]==jobs('primary');cells={};services={};comparisons={}
    for op in ('I','D','R'):
        for b in (1,32,512):
            for u in UPDATES:
                rows=[r for r in records if r['job']['kind']=='micro' and r['job']['update']==u and r['job']['op']==op and r['job']['batch']==b]
                assert [r['job']['round'] for r in rows]==list(range(1,7));v=[micro(r['checked'],r['job']) for r in rows]
                cells[f'{u}_{op}_{b}']={k:distribution([r[k] for r in v]) for k in v[0]}
            for target in ('WAVES','FINAL'):
                comparisons[f'{target}_over_NATIVE_{op}_{b}']=compare(cells[f'NATIVE_{op}_{b}']['mean_ACK_ms']['process_values'],cells[f'{target}_{op}_{b}']['mean_ACK_ms']['process_values'])
            comparisons[f'FINAL_over_WAVES_{op}_{b}']=compare(cells[f'WAVES_{op}_{b}']['mean_ACK_ms']['process_values'],cells[f'FINAL_{op}_{b}']['mean_ACK_ms']['process_values'])
    for u in ('S1','CURRENT','NATIVE','WAVES','FINAL'):
        rows=[r['checked']['parent_quality']['metadata'] for r in records if r['job']['kind']=='service' and r['job']['update']==u]
        assert len(rows)==6
        services[u]={k:distribution([r[k] for r in rows]) for k in ('service_ms','events_ms','release_ms','query_ms','update_ms_including_statistics','other_ms','device_owned_peak_bytes')}
    for base,target in (('CURRENT','NATIVE'),('CURRENT','WAVES'),('CURRENT','FINAL'),('S1','FINAL'),('WAVES','FINAL')):
        for metric in ('service_ms','query_ms','update_ms_including_statistics'):
            comparisons[f'{target}_over_{base}_{metric}']=compare(services[base][metric]['process_values'],services[target][metric]['process_values'])
    return dict(scope='Unprofiled request-ready ACK;6process medians and matched log-ratio CIs;segmented events+release for service;no kernel-only promotion',
        micro=cells,whole_service=services,comparisons=comparisons,bootstrap_seed=2026101511,bootstrap_resamples=20000,new_novelty_admitted=False)

def main():
    p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    rows=[dict(job=j,checked=load(a.work/'primary'/(j['label']+'.checked.json'))) for j in jobs('primary')]
    save(a.out,run(rows));print('ANALYZED192 same-campaign targets')

if __name__=='__main__':main()
