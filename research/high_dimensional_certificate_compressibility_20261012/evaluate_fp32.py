#!/usr/bin/env python3
"""Exhaustive frozen point-set bridge, bound dominance, counts and exact gates."""
import argparse
import csv
from pathlib import Path
import numpy as np
from aabb_math import *

def compute(aabb,point):
    query=[];levels=[];out={};checks=0;expected={(int(r['k']),int(r['level']),int(r['query_id'])):int(r['safe_objects']) for r in csv.DictReader((HERE.parent/'projection_capacity_diagnosis_20261012/evidence/per_query_capacity.csv').open())}
    assert np.array_equal(aabb['U_star_squared'],point['U_star_squared'])
    for level,size in SIZES.items():
        truth=aabb[f'truth_sq_{level}'];assert np.array_equal(truth,point[f'truth_sq_{level}'])
        allbounds=np.array([bounds(aabb[f'lo_{level}'],aabb[f'hi_{level}'],q) for q in aabb['q']]).transpose(1,0,2)
        assert np.all(allbounds[1:]>=allbounds[:-1]);out[f'LB_{level}']=allbounds
        for ki,k in enumerate(KS):
            lower=prior.envelope(point[f'D_{level}'][prior.KS.index(k)])[0];lb=allbounds[ki];u=np.sqrt(point['U_star_squared'])[:,None]
            assert np.all(lb<=lower) and np.all(lower<=np.sqrt(truth))
            pm=lower>u;cm=lb>u;tm=truth>point['U_star_squared'][:,None]
            assert not np.any(cm & ~pm) and not np.any(cm & ~tm)
            checks+=lb.size
            cells=[]
            for qi,qid in enumerate(identity()['queries']):
                t,p,c=[int(m[qi].sum())*size for m in (tm,pm,cm)];assert p==expected[k,level,qid],(k,level,qid,p,expected[k,level,qid])
                r=dict(k=k,level=level,query_id=qid,hard=qi>=2,truth_objects=t,point_objects=p,aabb_objects=c,
                    point_alignment=ratio(p,t),aabb_alignment=ratio(c,t),pointset_retention=ratio(c,p),compression_loss=ratio(p-c,p),
                    projection_loss_objects=t-p,summary_loss_objects=p-c,quantization_loss_objects=None)
                query.append(r);cells.append(r)
            hard=cells[2:];t,p,c=[sum(r[key] for r in hard) for key in ('truth_objects','point_objects','aabb_objects')];can=cells[2]
            levels.append(dict(k=k,level=level,regions=1000000//size,hard_truth_objects=t,hard_point_objects=p,hard_aabb_objects=c,
                hard_point_alignment=ratio(p,t),hard_alignment=ratio(c,t),hard_retention=ratio(c,p),hard_compression_loss=ratio(p-c,p),
                worst_hard_retention=min(r['pointset_retention'] for r in hard if r['pointset_retention'] is not None),
                worst_hard_alignment=min(r['aabb_alignment'] for r in hard),canary_truth_objects=can['truth_objects'],canary_point_objects=can['point_objects'],
                canary_aabb_objects=can['aabb_objects'],canary_alignment=can['aabb_alignment'],canary_retention=can['pointset_retention'],
                projection_loss_objects=t-p,summary_loss_objects=p-c,quantization_loss_objects=None,aligned_bytes_per_region=8*k))
    return query,levels,out,checks

def main():
    p=argparse.ArgumentParser()
    for key in ['build','pointset','out']:p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();prior.cpu_guard();freeze_check();pin(a.pointset,'capacity_raw_npz');a.out.mkdir(parents=True,exist_ok=False)
    build_check(a.build)
    with np.load(a.build/'aabb_raw.npz') as ab,np.load(a.pointset) as pt:query,levels,raw,checks=compute(ab,pt)
    csv_write(a.out/'per_query_summary.csv',query);csv_write(a.out/'per_level_summary.csv',levels)
    csv_write(a.out/'retention_summary.csv',[{key:r[key] for key in ('k','level','hard_retention','hard_compression_loss','worst_hard_retention','canary_retention')} for r in levels])
    budgets=[];costs=[]
    for r in levels:
        k=r['k'];regions=r['regions'];budgets.append(dict(k=k,level=r['level'],format='FP32_AABB',endpoint_bytes_per_region=8*k,
            scale_bytes_per_region=0,offset_bytes_per_region=0,header_bytes_per_region=0,padding_bytes_per_region=0,alignment=16,
            logical_bytes_per_region=8*k,aligned_bytes_per_region=8*k,total_region_bytes=8*k*regions,shared_scale_offset_bytes=0,
            inherited_full_basis_bytes=960*960*8,active_prefix_basis_logical_bytes=k*960*8,query_cache_physical_bytes=8*128*8,
            query_cache_active_B1_logical_bytes=k*8,query_cache_eight_queries_prefix_logical_bytes=8*k*8))
        for q in [v for v in query if v['k']==k and v['level']==r['level']]:
            costs.append(dict(k=k,level=r['level'],query_id=q['query_id'],query_projection_coordinate_updates=960*k,
                standalone_fullscan_metadata_bytes=regions*8*k,bound_coordinate_iterations=regions*k,
                query_interval_scalar_primitives=4*k,directed_bound_scalar_primitives=regions*(13*k+6),remaining_original_distance_coordinate_updates=(1000000-q['aabb_objects'])*960,
                scope='logical standalone level/prefix scan; no hardware traffic or latency'))
    csv_write(a.out/'metadata_budget.csv',budgets);csv_write(a.out/'cost_proxy.csv',costs)
    np.savez_compressed(a.out/'bounds_raw.npz',**raw)
    decision=stage_a(levels)
    save(a.out/'aggregate_summary.json',dict(base_commit=identity()['base_commit'],partition='PCA_BALANCED',dimensions=list(KS),primary_dimension=64,primary_level=4,
        formats=['POINT_SET','FP32_AABB'],stage_B_formats=[],query_cells=72,level_cells=9,**decision,level_results=levels))
    save(a.out/'FP32_VALIDATION.json',dict(status='PASS',G1='see BUILD_VALIDATION',G2='PASS: AABB lower<=point-set safe lower<=RN sqrt original truth',
        G3='PASS: strict original squared no false prunes',bound_cell_checks=checks,false_prunes=0,prefix_monotonicity='PASS',
        worker_sha256=sha(Path(__file__)),source_freeze_sha256=sha(HERE/'evidence/SOURCE_FREEZE.json')))
    save(a.out/'POINTSET_BRIDGE.json',dict(status='PASS',query_cells=72,exact_counts_equal=True,all_original_truth_and_U_squared_equal=True,keeper_commit=identity()['base_commit']))
    # No precision experiment may run until this receipt authorizes it.
    save(a.out/'QUANTIZATION_VALIDATION.json',dict(status='ADMITTED_PENDING' if decision['stage_B_admitted'] else 'NOT_ADMITTED',tested_formats=[],
        G5='NOT_TESTED' if decision['stage_B_admitted'] else 'NOT_APPLICABLE: only FP32 measured',stage_A_decision=decision['decision']))
    manifest(a.out);print(json.dumps(decision),flush=True)

if __name__=='__main__':main()
