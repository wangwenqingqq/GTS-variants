#!/usr/bin/env python3
"""All 384 frozen pairs independently rebuilt from original FP32 vectors, CPU only."""
import argparse
import json
import os
import struct
import time
from pathlib import Path
import numpy as np
from shape_math import HERE,sha,save,all_bounds,check_freeze
from independent import project,original_score,reference_shapes,ball_lb,ellipsoid_lb,box_lb


def main():
    p=argparse.ArgumentParser()
    for key in ['data','projected','permutation','build','out']:p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();check_freeze();a.out.mkdir(parents=True,exist_ok=False);start=time.monotonic()
    assert os.environ.get('CUDA_VISIBLE_DEVICES')=='' and len(os.sched_getaffinity(0))==1
    im=json.loads((HERE/'evidence/INPUT_IDENTITY.json').read_text())
    for path,key in [(a.data,'data_f32'),(a.projected,'projected_f64'),(a.permutation,'PCA_BALANCED_i32')]:assert sha(path)==im[key]['sha256']
    assert struct.unpack('<3i',a.data.open('rb').read(12))==(960,1000000,2)
    samples=json.loads((HERE/'evidence/G5_SAMPLES.json').read_text());pairs=samples['pairs'];assert len(pairs)==384
    assert sha(HERE/'evidence/G5_SAMPLES.json')==im['samples_sha256']
    x=np.memmap(a.data,dtype='<f4',offset=12,mode='r',shape=(1000000,960))
    z=np.memmap(a.projected,dtype='<f8',mode='r',shape=(1000000,16))[:,8:16]
    perm=np.fromfile(a.permutation,dtype='<i4');meta=np.load(a.build/'metadata_and_truth.npz')
    selected=set(im['queries'])
    for pair in pairs:
        size=10**(6-pair['level']);ri=pair['region_index'];selected.update(map(int,perm[ri*size:(ri+1)*size]))
    selected=np.array(sorted(selected),dtype=np.int32)
    source=json.loads((HERE.parent/'projection_certificate_20261011/evidence/BASIS.json').read_text())
    basis=np.array([[float.fromhex(t) for t in row] for row in source['families']['PCA']])
    rows=x[selected].copy();reproject=project(rows,basis);assert np.array_equal(reproject,z[selected])
    positions={int(rowid):i for i,rowid in enumerate(selected)};checks=[];unique_regions={};max_difference=0.
    for index,pair in enumerate(pairs):
        level=pair['level'];ri=pair['region_index'];qi=pair['query_index'];size=10**(6-level)
        ids=np.sort(perm[ri*size:(ri+1)*size]);ix=[positions[int(i)] for i in ids];points=reproject[ix]
        key=(level,ri)
        if key not in unique_regions:unique_regions[key]=reference_shapes(points)
        ref=unique_regions[key]
        for name,value in ref.items():assert np.array_equal(value,meta[f'{name}_{level}'][ri]),(level,ri,name)
        q=reproject[positions[pair['query_id']]]
        lo=meta[f'low_{level}'][ri];hi=meta[f'high_{level}'][ri]
        assert np.all(lo.astype(float)<=np.nextafter(points-1e-8,-np.inf))
        assert np.all(hi.astype(float)>=np.nextafter(points+1e-8,np.inf))
        bounds=[box_lb(lo,hi,q),ball_lb(ref['center'],ref['radius'],q),ball_lb(ref['minimax'],ref['minimax_radius'],q),
                ellipsoid_lb(ref['center'],ref['scale'],ref['factor'],q)]
        actual=all_bounds({name:meta[f'{name}_{level}'][ri:ri+1] for name in ['low','high','center','radius','minimax','minimax_radius','scale','factor']},q)[:,0]
        assert np.array_equal(actual,bounds)
        truth=float(original_score(rows[ix],rows[positions[pair['query_id']]]).min())
        assert truth==float(meta[f'truth_sq_{level}'][qi,ri])
        assert np.all(actual<=np.sqrt(truth))
        checks.append(dict(**pair,objects=size,projection_equal=True,metadata_equal=True,bounds_equal=True,truth_equal=True))
        if (index+1)%128==0:print(f'Independent original-vector G5 {index+1}/384 PASS',flush=True)
    # A tiny restricted fixture permits cross-runtime original-coordinate checking locally.
    sample=np.unique(np.concatenate([np.array(im['queries']),selected[np.linspace(0,len(selected)-1,24,dtype=int)]]))
    np.savez_compressed(a.out/'bridge_vectors.npz',row_ids=sample,vectors=x[sample],projection=z[sample])
    save(a.out/'G5_VALIDATION.json',dict(status='PASS',pairs_total=384,pairs_per_level={str(l):sum(p['level']==l for p in pairs) for l in (3,4,5)},
        original_vectors_reprojected=len(selected),original_coordinate_products=len(selected)*960*8,
        independent_regions=len(unique_regions),metadata_mismatch=0,bound_mismatch=0,truth_mismatch=0,
        original_region_objects_recomputed=sum(p['objects'] for p in checks),all_pair_objects_used=True,
        checks=checks,samples_sha256=im['samples_sha256'],worker_sha256=sha(Path(__file__)),reference_sha256=sha(HERE/'independent.py'),
        elapsed_resource_seconds=time.monotonic()-start,timing_is_not_latency=True,GPU_used=False))
    save(a.out/'OUTPUT_MANIFEST.json',{p.name:dict(sha256=sha(p),bytes=p.stat().st_size) for p in sorted(a.out.iterdir()) if p.is_file()})


if __name__=='__main__':main()
