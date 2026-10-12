#!/usr/bin/env python3
"""Auxiliary frozen-projection per-query ceiling and additive signed gap decomposition."""
import argparse
import json
from pathlib import Path
import numpy as np
from shape_math import HERE,LEVELS,sha,save
from evaluate_shapes import csv_write


def main():
    p=argparse.ArgumentParser();p.add_argument('--build',type=Path,required=True);p.add_argument('--eval',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();meta=np.load(a.build/'metadata_and_truth.npz');raw=np.load(a.eval/'full_query_region_bounds.npz');c=json.loads((HERE/'CONTRACT.json').read_text())
    pq=[];decomposition=[]
    for l,size in LEVELS.items():
        truth=raw[f'LB_truth_{l}'];lo=raw[f'projected_oracle_lo_{l}'];hi=raw[f'projected_oracle_hi_{l}'];box=raw[f'LB_{l}'][0];sq=meta[f'truth_sq_{l}'];u=meta['U_star_squared']
        for qi,qid in enumerate(c['queries']):
            den=int(np.count_nonzero(sq[qi]>u[qi])*size)
            possible=int(np.count_nonzero((hi[qi]>np.sqrt(u[qi])) & (sq[qi]>u[qi]))*size)
            pq.append(dict(level=l,query_id=qid,hard=qi>=2,truth_prunable_objects=den,
                possible_projected_prunable_objects=possible,optimistic_ceiling_alignment=possible/den,diagnostic_only=True))
        for scope,sl in [('all8',slice(None)),('hard6',slice(2,None))]:
            total=(truth-box)[sl];loss=(truth-hi)[sl];geometry=(lo-box)[sl];envelope=(hi-lo)[sl]
            assert np.allclose(total,loss+geometry+envelope,rtol=0,atol=2e-15)
            denom=float(total.sum())
            decomposition.append(dict(level=l,scope=scope,query_region_pairs=total.size,total_dead_gap_sum=denom,
                projection_loss_sum=float(loss.sum()),projection_loss_sum_fraction=float(loss.sum()/denom),
                geometry_and_certificate_margin_sum=float(geometry.sum()),geometry_and_certificate_margin_fraction=float(geometry.sum()/denom),
                projected_interval_width_sum=float(envelope.sum()),projected_interval_width_fraction=float(envelope.sum()/denom),
                signed_no_clipping=True,denominator='sum of original_truth_distance minus safe_AABB_LB over all selected query-region pairs; not alignment or latency'))
    csv_write(a.out/'projected_oracle_per_query.csv',pq);csv_write(a.out/'gap_decomposition.csv',decomposition)
    save(a.out/'SUPPLEMENT_RECEIPT.json',dict(worker_sha256=sha(Path(__file__)),raw_bounds_sha256=sha(a.eval/'full_query_region_bounds.npz'),
        query_rows=24,decomposition_rows=6,selection='all queries/levels; diagnostic postprocessing only; no gate or certificate selection',
        decomposition='distance-gap sum, signed values, interval width separate; never a sum or ratio of medians',not_latency=True))


if __name__=='__main__':main()
