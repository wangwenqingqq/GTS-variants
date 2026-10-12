#!/usr/bin/env python3
"""24 original-region pairs, all members, independent full960 ordered projection."""
import argparse
import json
import math
from pathlib import Path
import numpy as np
from common import HERE,KS,SIZES,ETA,MARGIN,sha,save,pin,manifest,inputs,cpu_guard,freeze_check,ordered_project,original_scores

def reference_prefix(points,q):
    total=np.zeros(len(points));result=[]
    for j in range(960):
        difference=points[:,j]-float(q[j]);term=difference*difference;total=total+term
        if j+1 in KS:result.append(np.sqrt(total).copy())
    return np.array(result).T

def reference_envelope(distances):
    return (np.array([max(0.,math.nextafter(float(d)-MARGIN,-math.inf)) for d in distances]),
            np.array([math.nextafter(float(d)+MARGIN,math.inf) for d in distances]))

def main():
    p=argparse.ArgumentParser()
    for key in ['data','permutation','build','oracle','out']:p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();cpu_guard();freeze_check();a.out.mkdir(parents=True,exist_ok=False);pin(a.data,'data_f32');pin(a.permutation,'PCA_BALANCED_i32')
    im=inputs();samples=json.loads((HERE/'evidence/REPLAY_SAMPLES.json').read_text())['pairs'];assert len(samples)==24
    x=np.memmap(a.data,dtype='<f4',offset=12,mode='r',shape=(1000000,960));perm=np.fromfile(a.permutation,dtype='<i4')
    ids=set(im['queries'])
    for r in samples:
        size=SIZES[r['level']];ids.update(map(int,perm[r['region_index']*size:(r['region_index']+1)*size]))
    ids=np.array(sorted(ids),dtype=np.int32);positions={int(v):i for i,v in enumerate(ids)};vectors=x[ids].copy()
    pca=np.fromfile(a.build/'basis.f64',dtype='<f8').reshape(960,960);ref=ordered_project(vectors,pca)
    cache=np.memmap(a.build/'projected.f64',dtype='<f8',mode='r',shape=(1000000,960));difference=float(np.abs(ref-cache[ids]).max());assert difference<2*ETA
    raw=np.load(a.oracle/'capacity_raw.npz');checks=[]
    for r in samples:
        size=SIZES[r['level']];ri=r['region_index'];qi=r['query_index'];members=np.sort(perm[ri*size:(ri+1)*size]);ix=[positions[int(v)] for v in members];qix=positions[r['query_id']]
        d=reference_prefix(ref[ix],ref[qix]).min(axis=0);measured=raw[f'D_{r["level"]}'][:,qi,ri];assert np.max(np.abs(d-measured))<MARGIN/4
        truth=float(original_scores(vectors[ix],vectors[qix]).min());assert truth==raw[f'truth_sq_{r["level"]}'][qi,ri]
        lo,hi=reference_envelope(d);ml,mh=reference_envelope(measured);u=np.sqrt(raw['U_star_squared'][qi]);assert np.array_equal(lo>u,ml>u) and np.array_equal(hi>u,mh>u)
        assert np.all(lo<=np.sqrt(truth))
        checks.append(dict(**r,objects=size,prefix_cells=8,original_truth_bit_identical=True,coordinate_error_envelope_pass=True,all_prefix_classifications_equal=True,max_prefix_distance_difference=float(np.abs(d-measured).max())))
    sample=np.unique(np.concatenate([np.array(im['queries']),ids[np.linspace(0,len(ids)-1,16,dtype=int)]]));np.savez_compressed(a.out/'bridge_vectors.npz',row_ids=sample,vectors=x[sample],projection=cache[sample])
    save(a.out/'INDEPENDENT_VALIDATION.json',dict(status='PASS',original_region_pairs=24,prefix_cell_checks=192,all_region_objects_used=True,
        unique_original_vectors=len(ids),original_object_memberships=sum(r['objects'] for r in checks),max_BLAS_vs_ordered_coordinate_difference=difference,
        BLAS_vs_ordered_is_not_bit_identical=True,checks=checks,worker_sha256=sha(Path(__file__)),source_freeze_sha256=sha(HERE/'evidence/SOURCE_FREEZE.json')))
    manifest(a.out);print('Independent 24 full original-region pairs /192 prefix cells PASS',flush=True)

if __name__=='__main__':main()
