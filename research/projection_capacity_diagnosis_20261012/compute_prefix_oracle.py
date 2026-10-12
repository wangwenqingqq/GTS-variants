#!/usr/bin/env python3
"""Single full-dimension accumulation per query/object; all nested region minima."""
import argparse
import json
import resource
import struct
import time
from pathlib import Path
import numpy as np
from common import HERE,KS,SIZES,MARGIN,sha,save,pin,manifest,cpu_guard,freeze_check,inputs,prefix_distances,envelope

def main():
    p=argparse.ArgumentParser()
    for name in ['build','scores','permutation','old','out']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();cpu_guard();freeze_check();a.out.mkdir(parents=True,exist_ok=False);start=time.monotonic()
    for path,key in [(a.scores,'scores_f64'),(a.permutation,'PCA_BALANCED_i32'),(a.old,'PCA_BALANCED_npz')]:pin(path,key)
    receipt=json.loads((a.build/'BUILD_RECEIPT.json').read_text());assert sha(a.build/'projected.f64')==receipt['projected_sha256']
    assert json.loads((a.build/'MATRIX_PROOF.json').read_text())['certified_contractive']
    assert struct.unpack('<4i',a.scores.open('rb').read(16))==(1000000,960,8,8)
    perm=np.fromfile(a.permutation,dtype='<i4');assert np.array_equal(np.sort(perm),np.arange(1000000))
    z=np.memmap(a.build/'projected.f64',mode='r',dtype='<f8',shape=(1000000,960));scores=np.memmap(a.scores,mode='r',dtype='<f8',offset=16,shape=(8,1000000))
    im=inputs();qz=z[im['queries']].copy();old=np.load(a.old);u=np.array([float.fromhex(v) for v in im['U_star_squared_hex']]);assert np.array_equal(u,old['U_star_squared'])
    arrays={'U_star_squared':u};truth={}
    for l,size in SIZES.items():
        truth[l]=scores[:,perm].reshape(8,10**l,size).min(axis=2);assert np.array_equal(truth[l],old[f'truth_sq_{l}'])
        arrays[f'truth_sq_{l}']=truth[l];arrays[f'D_{l}']=np.empty((8,8,10**l))
    for s in range(0,1000000,10000):
        block=z[perm[s:s+10000]]
        for qi,q in enumerate(qz):
            distances=prefix_distances(block,q);assert np.all(np.diff(distances,axis=1)>=0)
            for l,size in SIZES.items():arrays[f'D_{l}'][:,qi,s//size:(s+len(block))//size]=distances.reshape(-1,size,8).min(axis=1).T
        if (s+10000)%250000==0:print(f'Full nested accumulation/reduction {s+10000}/1000000 objects PASS',flush=True)
    checks=[]
    for l,size in SIZES.items():
        d=arrays[f'D_{l}'];low,high=envelope(d);t=np.sqrt(truth[l]);safe=low>np.sqrt(u)[None,:,None];possible=high>np.sqrt(u)[None,:,None]
        assert np.isfinite(d).all() and np.all(np.diff(d,axis=0)>=0) and np.all(np.diff(low,axis=0)>=0) and np.all(np.diff(high,axis=0)>=0)
        assert np.all(~safe[:-1]|safe[1:]) and np.all(~possible[:-1]|possible[1:]);assert np.all(low<=t[None])
        assert not np.any(safe & (truth[l]<=u[:,None])[None]);assert np.all(safe<=possible)
        raw960=d[-1]>np.sqrt(u)[:,None];true_mask=truth[l]>u[:,None]
        checks.append(dict(level=l,query_region_pairs=8*10**l,dimension_query_region_checks=d.size,
            distance_monotonicity_violations=0,safe_set_nested_violations=0,possible_set_nested_violations=0,bound_above_truth=0,false_prunes=0,
            full960_central_classification_differences=int(np.count_nonzero(raw960!=true_mask)),
            full960_guaranteed_missing_true_regions=int(np.count_nonzero(true_mask & ~safe[-1])),
            full960_max_absolute_distance_difference=float(np.max(np.abs(d[-1]-t)))))
    np.savez_compressed(a.out/'capacity_raw.npz',**arrays)
    save(a.out/'MONOTONICITY_VALIDATION.json',dict(status='PASS_FULL_DISTANCE_AND_MASK_NESTING',levels=checks,total_dimension_query_region_checks=sum(v['dimension_query_region_checks'] for v in checks),
        original_truth_bridge_exact=True,full960_is_not_bit_identical_score_contract=True,common_margin=MARGIN))
    save(a.out/'ORACLE_RECEIPT.json',dict(status='PASS',GPU_used=False,query_level_dimension_cells=192,elapsed_resource_seconds=time.monotonic()-start,
        peak_memory_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,prefix_squared_terms=8*1000000*960,
        logical_prefix_operations=dict(subtractions=8*1000000*960,multiplications=8*1000000*960,ordered_additions=8*1000000*960),
        logical_region_min_comparisons=8*8*sum(1000000-10**l for l in SIZES),raw_sha256=sha(a.out/'capacity_raw.npz'),source_freeze_sha256=sha(HERE/'evidence/SOURCE_FREEZE.json'),not_latency=True))
    manifest(a.out)

if __name__=='__main__':main()
