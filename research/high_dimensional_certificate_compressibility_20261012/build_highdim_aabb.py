#!/usr/bin/env python3
"""Build nine physical FP32 records; prove coverage of all memberships."""
import argparse
import json
from pathlib import Path
import numpy as np
from aabb_math import *

def main():
    p=argparse.ArgumentParser()
    for key in ['cache','scores','permutation','out']:p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();prior.cpu_guard();freeze_check();a.out.mkdir(parents=True,exist_ok=False)
    for path,key in [(a.cache,'projected_f64'),(a.scores,'scores_f64'),(a.permutation,'PCA_BALANCED_i32')]:pin(path,key)
    assert np.array_equal(np.fromfile(a.scores,dtype='<i4',count=4),[1000000,960,8,8])
    z=np.memmap(a.cache,dtype='<f8',mode='r',shape=(1000000,960))
    scores=np.memmap(a.scores,dtype='<f8',offset=16,mode='r',shape=(8,1000000))
    perm=np.fromfile(a.permutation,dtype='<i4');assert np.array_equal(np.sort(perm),np.arange(1000000))
    raw={'q':np.array(z[identity()['queries'],:128]),'U_star_squared':np.array([float.fromhex(v) for v in identity()['U_star_squared_hex']])}
    for level,size in SIZES.items():
        lo=np.empty((1000000//size,128),dtype='<f4');hi=lo.copy();truth=np.empty((8,len(lo)))
        for start in range(0,1000000,10000):
            rows=perm[start:start+10000];block=np.array(z[rows,:128]);assert np.isfinite(block).all()
            groups=block.reshape(-1,size,128);l,h=endpoints(groups);ix=slice(start//size,(start+10000)//size)
            lo[ix]=l;hi[ix]=h
            assert np.all(l[:,None,:].astype(np.float64)<=np.nextafter(groups-ETA,-np.inf))
            assert np.all(h[:,None,:].astype(np.float64)>=np.nextafter(groups+ETA,np.inf))
            truth[:,ix]=np.array(scores[:,rows]).reshape(8,-1,size).min(axis=2)
        raw[f'lo_{level}']=lo;raw[f'hi_{level}']=hi;raw[f'truth_sq_{level}']=truth
        for k in KS:
            packed=np.stack((lo[:,:k],hi[:,:k]),axis=2).astype('<f4');file=a.out/f'PCA{k}_L{level}_FP32.bin';packed.tofile(file)
            replay=np.fromfile(file,dtype='<f4').reshape(len(lo),k,2);assert np.array_equal(replay,packed)
        print(f'L{level}: full coverage + three packed roundtrips PASS',flush=True)
    np.savez_compressed(a.out/'aabb_raw.npz',**raw)
    save(a.out/'BUILD_VALIDATION.json',dict(status='PASS',full128_memberships=3000000,covered_prefix_memberships=9000000,
        explicit_endpoint_coordinate_comparisons=768000000,prefix_proof='32/64 endpoint files are exact slices of the fully checked128D enclosures',
        physical_record_files=9,physical_record_bytes=sum((a.out/f'PCA{k}_L{l}_FP32.bin').stat().st_size for k in KS for l in SIZES),
        worker_sha256=sha(Path(__file__)),source_freeze_sha256=sha(HERE/'evidence/SOURCE_FREEZE.json')))
    manifest(a.out)

if __name__=='__main__':main()
