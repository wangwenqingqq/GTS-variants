#!/usr/bin/env python3
"""Full exact-safe masks, dead gaps, and diagnostic projected-point ceiling."""
import argparse
import csv
import json
import os
import time
from pathlib import Path
import numpy as np
from shape_math import HERE, NAMES, BYTES, LEVELS, all_bounds, sha, save, decision, up, down, positive_down, norm_upper, norm_lower, ETA, QUERY_ERROR, RHO, check_freeze


def csv_write(path,rows):
    with Path(path).open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def main():
    p=argparse.ArgumentParser()
    for key in ['build','projected','permutation','scores','out']:p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();check_freeze();a.out.mkdir(parents=True,exist_ok=False);start=time.monotonic()
    assert os.environ.get('CUDA_VISIBLE_DEVICES')=='' and len(os.sched_getaffinity(0))==1
    c=json.loads((HERE/'CONTRACT.json').read_text());im=json.loads((HERE/'evidence/INPUT_IDENTITY.json').read_text())
    for path,key in [(a.projected,'projected_f64'),(a.permutation,'PCA_BALANCED_i32'),(a.scores,'scores_f64')]:assert sha(path)==im[key]['sha256']
    meta=np.load(a.build/'metadata_and_truth.npz');bm=json.loads((a.build/'OUTPUT_MANIFEST.json').read_text())
    assert sha(a.build/'metadata_and_truth.npz')==bm['metadata_and_truth.npz']['sha256']
    z=np.memmap(a.projected,dtype='<f8',mode='r',shape=(1000000,16))[:,8:16]
    scores=np.memmap(a.scores,dtype='<f8',offset=16,mode='r',shape=(8,1000000))
    ids=np.fromfile(a.permutation,dtype='<i4');qz=meta['query_projection'];u_sq=meta['U_star_squared'];u=np.sqrt(u_sq)
    assert np.array_equal(u_sq,np.array([float.fromhex(v) for v in c['U_star_squared_hex']]))
    oldbridge=json.loads((HERE.parent/'multi_view_certificate_20261012/evidence/PCA8_PER_QUERY_BRIDGE.json').read_text())
    summary=[];perquery=[];dead=[];orows=[];arrays={};fullviolations=0;falseprunes=0;keeperchecks=0
    for level,size in LEVELS.items():
        m={k:meta[f'{k}_{level}'] for k in ['low','high','center','radius','minimax','minimax_radius','scale','factor']}
        truth_sq=meta[f'truth_sq_{level}'];truth=np.sqrt(truth_sq)
        assert np.array_equal(truth_sq,np.array([scores[qi,ids].reshape(-1,size).min(1) for qi in range(8)]))
        lb=np.array([all_bounds(m,q) for q in qz]).transpose(1,0,2)
        fullviolations+=int(np.count_nonzero(lb>truth[None]));assert fullviolations==0
        masks=lb>u[None,:,None];falseprunes+=int(np.count_nonzero(masks & (truth_sq<=u_sq[:,None])[None]));assert falseprunes==0
        arrays[f'LB_{level}']=lb;arrays[f'LB_truth_{level}']=truth
        # Upper and lower enclosure of exact projected point-set nearest distance.
        oracle_lo=np.empty_like(truth);oracle_hi=np.empty_like(truth)
        for qi,q in enumerate(qz):
            dlo=positive_down(np.abs(z-q));dhi=up(np.abs(z-q))
            oracle_lo[qi]=positive_down(norm_lower(dlo).reshape(-1)[ids].reshape(-1,size).min(1)-up(2*QUERY_ERROR))
            oracle_hi[qi]=up(norm_upper(dhi).reshape(-1)[ids].reshape(-1,size).min(1)+up(2*QUERY_ERROR))
        assert np.all(oracle_lo<=oracle_hi)
        arrays[f'projected_oracle_lo_{level}']=oracle_lo;arrays[f'projected_oracle_hi_{level}']=oracle_hi
        ceiling_safe=oracle_lo>up(u[:,None]+RHO);ceiling_possible=oracle_hi>u[:,None]
        # If a covering shape prunes, the true nearest projected point must cross U* too.
        assert not np.any(masks & ~ceiling_possible[None])
        truth_mask=truth_sq>u_sq[:,None];truthcounts=truth_mask.sum(1)*size
        for si,(shape,b) in enumerate(zip(NAMES,BYTES)):
            counts=masks[si].sum(1)*size;hard=counts[2:].sum();hd=truthcounts[2:].sum()
            worst=min(float(n/d) for n,d in zip(counts[2:],truthcounts[2:]));basecounts=masks[0].sum(1)*size
            row=dict(shape=shape,level=level,objects_per_region=size,aligned_bytes=b,matched_budget=b<=64,metadata_heavy=b>64,
                pruned_objects=int(counts.sum()),truth_prunable_objects=int(truthcounts.sum()),alignment=float(counts.sum()/truthcounts.sum()),
                hard_pruned_objects=int(hard),hard_truth_prunable_objects=int(hd),hard_alignment=float(hard/hd),
                worst_hard_alignment=worst,canary_alignment=float(counts[2]/truthcounts[2]),
                hard_gain_over_AABB=float((hard-basecounts[2:].sum())/hd),
                worst_gain_over_AABB=float(worst-min(basecounts[2:]/truthcounts[2:])),
                alignment_per_aligned_byte=float(hard/hd/b),hard_query_pruned=counts[2:].tolist(),hard_query_truth_prunable=truthcounts[2:].tolist())
            summary.append(row)
            for qi,qid in enumerate(c['queries']):
                perquery.append(dict(shape=shape,level=level,query_id=qid,hard=qi>=2,pruned_objects=int(counts[qi]),
                    truth_prunable_objects=int(truthcounts[qi]),alignment=float(counts[qi]/truthcounts[qi]),
                    gain_over_AABB=float((counts[qi]-basecounts[qi])/truthcounts[qi])))
                if si==0:
                    prior=next(v for v in oldbridge['checks'] if v['query_id']==qid and v['level']==level)
                    assert prior['pruned_objects']==int(counts[qi]) and prior['truth_prunable_objects']==int(truthcounts[qi]);keeperchecks+=1
            for scope,sl in [('all8',slice(None)),('hard6',slice(2,None))]:
                gap=(truth-lb[si])[sl];universe=gap.size
                new=masks[si,sl] & ~masks[0,sl];lost=masks[0,sl] & ~masks[si,sl]
                dead.append(dict(shape=shape,level=level,scope=scope,query_region_pairs=universe,
                    median=float(np.quantile(gap,.5)),p90=float(np.quantile(gap,.9)),p99=float(np.quantile(gap,.99)),
                    LB_gt_AABB_pairs=int(np.count_nonzero(lb[si,sl]>lb[0,sl])),LB_gt_AABB_fraction=float(np.mean(lb[si,sl]>lb[0,sl])),
                    new_cross_U_pairs=int(new.sum()),new_cross_U_full_pair_fraction=float(new.mean()),new_cross_U_objects=int(new.sum()*size),
                    lost_cross_U_pairs=int(lost.sum()),lost_cross_U_full_pair_fraction=float(lost.mean()),lost_cross_U_objects=int(lost.sum()*size)))
        for scope,sl in [('all8',slice(None)),('hard6',slice(2,None))]:
            den=int(truthcounts[sl].sum());qcount=8 if scope=='all8' else 6
            guaranteed=int(np.count_nonzero(ceiling_safe[sl] & truth_mask[sl])*size)
            possible=int(np.count_nonzero(ceiling_possible[sl] & truth_mask[sl])*size)
            orows.append(dict(level=level,scope=scope,truth_prunable_objects=den,guaranteed_projected_prunable_objects=guaranteed,
                possible_projected_prunable_objects=possible,guaranteed_alignment=guaranteed/den,ceiling_alignment=possible/den,
                diagnostic_only=True,projection_loss_gap_median=float(np.median((truth-oracle_hi)[sl])),
                AABB_geometry_gap_median=float(np.median((oracle_lo-lb[0])[sl]))))
        print(f'L{level}: all four shapes, full truth/masks/keeper and projected diagnostic PASS',flush=True)
    np.savez_compressed(a.out/'full_query_region_bounds.npz',**arrays)
    result=dict(partition='PCA_BALANCED',projection='PCA8',shapes=NAMES,levels=list(LEVELS),rows=summary,**decision(summary),
        scope='8 frozen queries (6 hard), GIST1M D960 K8 B1; offline geometry only; not a universal linear-summary limit',
        projected_oracle=orows)
    save(a.out/'aggregate_summary.json',result)
    csv_write(a.out/'per_level_summary.csv',[{k:v for k,v in r.items() if not isinstance(v,list)} for r in summary])
    csv_write(a.out/'per_query_summary.csv',perquery);csv_write(a.out/'dead_space_summary.csv',dead);csv_write(a.out/'projected_oracle_summary.csv',orows)
    save(a.out/'EVAL_RECEIPT.json',dict(status='PASS',full_shape_truth_checks=4*8*111000,bound_above_truth=fullviolations,
        false_topK_prunes=falseprunes,exact_AABB_query_level_bridges=keeperchecks,original_score_cache_region_minima_checked=8*111000,
        projected_oracle_query_region_pairs=8*111000,GPU_used=False,timing_is_not_latency=True,
        elapsed_resource_seconds=time.monotonic()-start,worker_sha256=sha(Path(__file__)),math_sha256=sha(HERE/'shape_math.py')))
    save(a.out/'OUTPUT_MANIFEST.json',{p.name:dict(sha256=sha(p),bytes=p.stat().st_size) for p in sorted(a.out.iterdir()) if p.is_file()})


if __name__=='__main__':main()
