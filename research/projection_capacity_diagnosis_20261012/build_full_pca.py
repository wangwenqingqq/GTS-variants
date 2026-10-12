#!/usr/bin/env python3
"""One full-data PCA fit, one certified full basis and one private projected cache."""
import argparse
import json
import math
import resource
import struct
import time
from pathlib import Path
import numpy as np
from common import HERE,KS,sha,save,pin,manifest,cpu_guard,freeze_check,matrix_proof,arithmetic_proof

def main():
    p=argparse.ArgumentParser();p.add_argument('--data',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    cpu_guard();freeze_check();a.out.mkdir(parents=True,exist_ok=False);start=time.monotonic();pin(a.data,'data_f32')
    assert struct.unpack('<3i',a.data.open('rb').read(12))==(960,1000000,2)
    x=np.memmap(a.data,dtype='<f4',offset=12,mode='r',shape=(1000000,960));mean=np.zeros(960);domain=[np.inf,-np.inf]
    fit_start=time.monotonic();fit_cpu_start=time.process_time()
    for s in range(0,len(x),8192):
        b=x[s:s+8192].astype(np.float64);assert np.isfinite(b).all();domain=[min(domain[0],float(b.min())),max(domain[1],float(b.max()))];mean+=b.sum(axis=0,dtype=np.float64)
    assert domain[0]>=0 and domain[1]<=2;mean/=len(x);cov=np.zeros((960,960))
    for s in range(0,len(x),8192):
        b=x[s:s+8192].astype(np.float64)-mean;cov+=b.T@b
    cov/=len(x);values,vectors=np.linalg.eigh(cov);order=np.argsort(values)[::-1];values=values[order];raw=vectors[:,order].T.copy()
    assert values.min()>-1e-10 and np.isfinite(raw).all()
    for row in raw:
        if row[np.argmax(np.abs(row))]<0:row*=-1
    fit_wall=time.monotonic()-fit_start;fit_cpu=time.process_time()-fit_cpu_start
    print('Full 1M-row covariance and single 960-direction PCA fit PASS',flush=True)
    before,_,_=matrix_proof(raw)
    scale=math.nextafter(min(1.,1/math.sqrt(before['gram_infinity_upper']))*(1-2**-40),0.)
    basis=raw*scale;nonzero_min=float(np.abs(basis[basis!=0]).min());assert nonzero_min>=2**-100
    proof,lo,hi=matrix_proof(basis);assert proof['certified_contractive']
    save(a.out/'ARITHMETIC_PROOF.json',arithmetic_proof())
    basis.astype('<f8').tofile(a.out/'basis.f64');np.savez_compressed(a.out/'gram_interval.npz',low=lo,high=hi)
    save(a.out/'MATRIX_PROOF.json',dict(**proof,common_scale=scale,nonzero_abs_min=nonzero_min,before_gram_infinity_upper=before['gram_infinity_upper'],basis_sha256=sha(a.out/'basis.f64')))
    spectrum=dict(eigenvalues=values.tolist(),total_variance=float(values.sum()),explained_variance=[dict(k=k,ratio=float(values[:k].sum()/values.sum())) for k in KS],
        database_rows=1000000,centered_covariance=True,block_rows=8192,query_labels_used=False,U_star_used=False,queries_as_ordinary_database_rows=True,
        mean_sha256=__import__('hashlib').sha256(mean.astype('<f8').tobytes()).hexdigest(),covariance_sha256=__import__('hashlib').sha256(cov.astype('<f8').tobytes()).hexdigest(),domain=domain)
    save(a.out/'PCA_SPECTRUM.json',spectrum)
    old=json.loads((HERE.parent/'projection_certificate_20261011/evidence/BASIS.json').read_text());oldbasis=np.array([[float.fromhex(t) for t in r] for r in old['families']['PCA']])
    old_unit=oldbasis/np.linalg.norm(oldbasis,axis=1)[:,None];new_unit=basis[:8]/np.linalg.norm(basis[:8],axis=1)[:,None]
    save(a.out/'PCA8_CONSTRUCTION_BRIDGE.json',dict(previous_basis_sha256=sha(HERE.parent/'projection_certificate_20261011/evidence/BASIS.json'),
        same_full_database_and_covariance_block_procedure=True,previous_fit_threads=4,current_fit_threads=1,
        max_unit_direction_difference=float(np.abs(old_unit-new_unit).max()),top8_variance_ratio_difference=float(sum(old['explained_variance_ratios_top8'])-values[:8].sum()/values.sum()),
        bit_identical_anchor_required=False,comparison_boundary='same PCA procedure; full-matrix common scaling and BLAS arithmetic replace prior top8 scaling and ordered projection'))
    projection_start=time.monotonic();z=np.memmap(a.out/'projected.f64',mode='w+',dtype='<f8',shape=(1000000,960))
    for s in range(0,len(x),8192):z[s:s+8192]=x[s:s+8192].astype(np.float64)@basis.T
    z.flush();assert np.isfinite(z).all();projection_wall=time.monotonic()-projection_start
    cpu_model=next(t.split(':',1)[1].strip() for t in Path('/proc/cpuinfo').read_text().splitlines() if t.startswith('model name'))
    import sys
    save(a.out/'BUILD_RECEIPT.json',dict(status='PASS',GPU_used=False,CPU=cpu_model,affinity_count=1,library_threads=1,python=sys.version.split()[0],numpy=np.__version__,
        blas_libraries=sorted({Path(t.split()[-1]).name for t in Path('/proc/self/maps').read_text().splitlines() if 'blas' in t.lower() and '/' in t}),
        fit_wall_resource_seconds=fit_wall,fit_process_cpu_seconds=fit_cpu,projection_wall_resource_seconds=projection_wall,
        total_wall_resource_seconds=time.monotonic()-start,peak_memory_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
        covariance_logical_flops=2*1000000*960*960,projection_logical_flops=2*1000000*960*960,projected_cache_bytes=z.nbytes,
        projected_sha256=sha(a.out/'projected.f64'),basis_sha256=sha(a.out/'basis.f64'),source_freeze_sha256=sha(HERE/'evidence/SOURCE_FREEZE.json'),not_latency=True))
    manifest(a.out);print('Common full-matrix contraction proof and full960 projected cache PASS',flush=True)

if __name__=='__main__':main()
