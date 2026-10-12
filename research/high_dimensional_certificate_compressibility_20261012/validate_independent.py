#!/usr/bin/env python3
"""All members of24 preregistered regions; independent ordered projection."""
import argparse
from pathlib import Path
import numpy as np
from aabb_math import *

def main():
    p=argparse.ArgumentParser()
    for key in ['data','permutation','cache','build','out']:p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();prior.cpu_guard();freeze_check();a.out.mkdir(parents=True,exist_ok=False)
    for path,key in [(a.data,'data_f32'),(a.permutation,'PCA_BALANCED_i32'),(a.cache,'projected_f64')]:pin(path,key)
    assert np.array_equal(np.fromfile(a.data,dtype='<i4',count=3),[960,1000000,2])
    basis=HERE.parent/'projection_capacity_diagnosis_20261012/evidence/basis.f64';pin(basis,'basis_f64')
    pca=np.fromfile(basis,dtype='<f8').reshape(960,960)[:128]
    x=np.memmap(a.data,dtype='<f4',offset=12,mode='r',shape=(1000000,960));perm=np.fromfile(a.permutation,dtype='<i4')
    samples=json.loads((HERE/'evidence/REPLAY_SAMPLES.json').read_text())['pairs'];assert len(samples)==24
    ids=set(identity()['queries'])
    for r in samples:ids.update(map(int,perm[r['region_index']*SIZES[r['level']]:(r['region_index']+1)*SIZES[r['level']]]))
    ids=np.array(sorted(ids),dtype=np.int32);position={int(v):i for i,v in enumerate(ids)};vectors=x[ids].copy();ref=prior.ordered_project(vectors,pca)
    cache=np.memmap(a.cache,dtype='<f8',mode='r',shape=(1000000,960));cached=np.array(cache[ids,:128]);difference=float(np.abs(ref-cached).max());assert difference<2*ETA
    build_check(a.build)
    ab=np.load(a.build/'aabb_raw.npz');checks=[]
    for r in samples:
        level=r['level'];size=SIZES[level];ri=r['region_index'];qi=r['query_index'];members=perm[ri*size:(ri+1)*size]
        ix=np.array([position[int(v)] for v in members]);qix=position[r['query_id']]
        # Independent Python min/max reduction over every cached member.
        lo=np.array([min(float(v) for v in cached[ix,j]) for j in range(128)])
        hi=np.array([max(float(v) for v in cached[ix,j]) for j in range(128)])
        lo=outward32(np.nextafter(lo-ETA,-np.inf),-1);hi=outward32(np.nextafter(hi+ETA,np.inf),1)
        assert np.array_equal(lo,ab[f'lo_{level}'][ri]) and np.array_equal(hi,ab[f'hi_{level}'][ri])
        assert np.all(ref[ix]>=lo) and np.all(ref[ix]<=hi)
        truth=float(prior.original_scores(vectors[ix],vectors[qix]).min());assert truth==ab[f'truth_sq_{level}'][qi,ri]
        scalar=scalar_bounds(lo,hi,cached[qix]);vector=bounds(lo[None,:],hi[None,:],cached[qix])[:,0];assert np.array_equal(scalar,vector)
        assert np.all(scalar<=np.sqrt(truth))
        checks.append(dict(**r,objects=size,original_truth_bit_identical=True,endpoint_bit_identical=True,scalar_bound_bit_identical=True,all_ordered_coordinates_enclosed=True))
    np.savez_compressed(a.out/'replay_vectors.npz',ids=ids,vectors=vectors,cached=cached,ordered=ref)
    save(a.out/'INDEPENDENT_VALIDATION.json',dict(status='PASS',original_region_pairs=24,prefix_cell_checks=72,all_region_members_used=True,
        unique_original_vectors=len(ids),original_object_memberships=sum(r['objects'] for r in checks),max_cached_vs_ordered_coordinate_difference=difference,
        coordinate_difference_envelope=2*ETA,checks=checks,worker_sha256=sha(Path(__file__)),source_freeze_sha256=sha(HERE/'evidence/SOURCE_FREEZE.json')))
    manifest(a.out);print('Independent all-member24 regions /72 prefixes PASS',flush=True)

if __name__=='__main__':main()
