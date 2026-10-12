#!/usr/bin/env python3
"""Build the complete query-independent frozen matrix; all inputs are hash pinned."""
import argparse
import gzip
import csv
import json
import os
import sys
import time
from pathlib import Path
import numpy as np
from shape_math import HERE, NAMES, BYTES, LEVELS, construct, pack, unpack, sha, save, check_freeze
from projection_math import exact_gram_bound,projection_error_bound,error_bound,ETA,RHO


def main():
    p=argparse.ArgumentParser()
    for name in ['data','projected','scores','permutation','old','out']:
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();check_freeze();a.out.mkdir(parents=True,exist_ok=False); start=time.monotonic()
    assert os.environ.get('CUDA_VISIBLE_DEVICES') == '' and len(os.sched_getaffinity(0)) == 1
    assert all(os.environ.get(k)=='1' for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'])
    im=json.loads((HERE/'evidence/INPUT_IDENTITY.json').read_text())
    assert sha(HERE/'CONTRACT.json')==im['contract_sha256']
    assert sha(HERE/'evidence/G5_SAMPLES.json')==im['samples_sha256']
    for path,key in [(a.data,'data_f32'),(a.projected,'projected_f64'),(a.scores,'scores_f64'),
                     (a.permutation,'PCA_BALANCED_i32'),(a.old,'PCA_BALANCED_npz')]:
        assert path.stat().st_size==im[key]['bytes'] and sha(path)==im[key]['sha256'],key
    basis=HERE.parent/'projection_certificate_20261011/evidence/BASIS.json'
    assert sha(basis)==im['basis_sha256']
    b=json.loads(basis.read_text());pca=np.array([[float.fromhex(v) for v in r] for r in b['families']['PCA']])
    gram,_=exact_gram_bound(pca);assert gram<=1 and projection_error_bound()<ETA and error_bound()<RHO
    z=np.memmap(a.projected,dtype='<f8',mode='r',shape=(1000000,16))[:,8:16]
    ids=np.fromfile(a.permutation,dtype='<i4');assert np.array_equal(np.sort(ids),np.arange(1000000))
    old=np.load(a.old);contract=json.loads((HERE/'CONTRACT.json').read_text())
    qz=z[contract['queries']].copy();assert np.array_equal(qz,old['query_projection'])
    arrays={'query_projection':qz,'U_star_squared':old['U_star_squared']}; manifest=[];stats_count=0
    with gzip.open(a.out/'region_shape_stats.csv.gz','wt',newline='') as f:
        writer=None
        for level,size in LEVELS.items():
            region_ids=ids.reshape(-1,size); collected={}; batches=[]
            for begin in range(0,len(region_ids),max(1,20000//size)):
                selected=np.sort(region_ids[begin:begin+max(1,20000//size)],axis=1)
                meta,stats=construct(z[selected])
                if writer is None:
                    writer=csv.DictWriter(f,fieldnames=['level','region_index','objects']+list(stats));writer.writeheader()
                for i in range(len(selected)):
                    writer.writerow(dict(level=level,region_index=begin+i,objects=size,**{k:float(v[i]) for k,v in stats.items()}));stats_count+=1
                for k,v in meta.items():collected.setdefault(k,[]).append(v)
            meta={k:np.concatenate(v) for k,v in collected.items()}
            assert np.array_equal(meta['low'],old[f'low_{level}']) and np.array_equal(meta['high'],old[f'high_{level}'])
            for k,v in meta.items():arrays[f'{k}_{level}']=v
            arrays[f'truth_sq_{level}']=old[f'truth_sq_{level}']
            for shape,b in zip(NAMES,BYTES):
                blob=pack(meta,shape);name=f'{shape}_L{level}.metadata.f32'
                (a.out/name).write_bytes(blob);assert len(blob)==10**level*b
                restored=unpack(blob,shape)
                assert all(np.array_equal(v,meta[k]) for k,v in restored.items())
                manifest.append(dict(shape=shape,level=level,regions=10**level,aligned_bytes=b,
                    logical_bytes={'AABB':64,'CENTROID_BALL':36,'MINIMAX_BALL':36,'DIAGONAL_ELLIPSOID':68}[shape],
                    matched_budget_admitted=b<=64,metadata_heavy=b>64,
                    metadata_sha256=sha(a.out/name),metadata_bytes=len(blob)))
            print(f'L{level}: full shape coverage and AABB endpoints/packing PASS',flush=True)
    np.savez_compressed(a.out/'metadata_and_truth.npz',**arrays)
    save(a.out/'SHAPE_MANIFEST.json',dict(cells=manifest,region_stats_rows=stats_count,query_used_in_construction=False,
        stored_parameter_roundtrip_cells=12,full_shape_coverage_objects_per_shape=3000000,
        exact_stored_Gram_bound=str(gram),projection_error_bound=projection_error_bound(),original_score_error_bound=error_bound(),
        arithmetic='ordered RN-FP64 construction; operation-wise upper envelopes; stored FP32 parameters'))
    cpu=next(line.split(':',1)[1].strip() for line in Path('/proc/cpuinfo').read_text().splitlines() if line.startswith('model name'))
    save(a.out/'BUILD_RECEIPT.json',dict(status='PASS',GPU_used=False,CPU=cpu,
        affinity_count=len(os.sched_getaffinity(0)),python=sys.version.split()[0],numpy=np.__version__,threads=1,nice=os.getpriority(os.PRIO_PROCESS,0),
        elapsed_resource_seconds=time.monotonic()-start,timing_is_not_latency=True,inputs=im,
        worker_sha256=sha(Path(__file__)),math_sha256=sha(HERE/'shape_math.py'),stats_rows=stats_count,
        source_freeze_sha256=sha(HERE/'evidence/SOURCE_FREEZE.json')))
    save(a.out/'OUTPUT_MANIFEST.json',{p.name:dict(sha256=sha(p),bytes=p.stat().st_size) for p in sorted(a.out.iterdir()) if p.is_file()})


if __name__=='__main__':main()
