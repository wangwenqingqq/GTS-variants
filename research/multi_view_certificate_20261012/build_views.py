#!/usr/bin/env python3
"""Query-independent PCA32/random construction, full ordered projection, no curves."""
import argparse, hashlib, json, os, resource, struct, subprocess, sys, time
from pathlib import Path
import numpy as np
from views import HERE, sha, save, certify, exact_gram_bound, configurations, ETA, projection_error_bound
sys.path.insert(0,str(HERE.parent/'projection_certificate_20261011'))
from build_projection import ordered

def main():
    p=argparse.ArgumentParser()
    for key in ['data','out']:p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args(); a.out.mkdir(parents=True,exist_ok=False); start=time.monotonic()
    im=json.loads((HERE/'evidence/INPUT_IDENTITY.json').read_text())
    assert sha(HERE/'CONTRACT.json')==im['contract_sha256'] and sha(a.data)==im['data_sha256']
    assert os.environ.get('CUDA_VISIBLE_DEVICES')=='' and len(os.sched_getaffinity(0))==4
    assert all(os.environ.get(k)=='4' for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'])
    assert os.getpriority(os.PRIO_PROCESS,0)>=10
    assert a.data.stat().st_size==3840000012 and struct.unpack('<3i',a.data.open('rb').read(12))==(960,1000000,2)
    oldpath=HERE.parent/'projection_certificate_20261011/evidence/BASIS.json'
    assert sha(oldpath)==im['old_basis_sha256']; old=json.loads(oldpath.read_text())
    oldp=np.array([[float.fromhex(t) for t in row] for row in old['families']['PCA']])
    x=np.memmap(a.data,dtype='<f4',offset=12,mode='r',shape=(1000000,960))
    mean=np.zeros(960); minimum=np.inf; maximum=-np.inf
    for s in range(0,len(x),8192):
        b=x[s:s+8192].astype('f8'); assert np.isfinite(b).all()
        minimum=min(minimum,float(b.min()));maximum=max(maximum,float(b.max()));mean+=b.sum(0,dtype='f8')
    assert 0<=minimum<=maximum<=2;mean/=len(x)
    cov=np.zeros((960,960))
    for s in range(0,len(x),8192):
        b=x[s:s+8192].astype('f8')-mean;cov+=b.T@b
    cov/=len(x)
    hashes={'mean_sha256':hashlib.sha256(mean.astype('<f8').tobytes()).hexdigest(),'covariance_sha256':hashlib.sha256(cov.astype('<f8').tobytes()).hexdigest()}
    assert all(hashes[k]==old[k] for k in hashes),'old PCA fitting arithmetic did not reproduce'
    ev,v=np.linalg.eigh(cov);order=np.argsort(ev)[::-1]; raw=v[:,order[:32]].T.copy()
    keeper,_=certify(raw[:8]);assert keeper.tobytes()==oldp.tobytes(),'PCA8 basis bridge'
    for row in raw:
        if row[np.argmax(np.abs(row))]<0:row*=-1
    pcs=[1,5,9,13,17,21,25,29];spread,spreadproof=certify(raw[np.array(pcs)-1])
    rng=np.random.default_rng(20261012); random=[]; construction=[]
    for v,k in [(2,4),(4,2),(8,1)]:
        for i in range(v):
            q=np.linalg.qr(rng.standard_normal((960,k)),mode='reduced')[0].T
            cp,proof=certify(q);random.extend(cp)
            construction.append(dict(layout=f'{v}x{k}',view=i,proof=proof))
    new=np.concatenate([spread,np.array(random)]);assert new.shape==(32,960)
    new.astype('<f8').tofile(a.out/'basis.f64')
    allp=np.concatenate([oldp,new]);cfg,aliases=configurations();proofs=[];diversity=[]
    for c in cfg:
        bases=[allp[g] for g in c['groups']]
        for i,b in enumerate(bases):
            upper,ss=exact_gram_bound(b);assert upper<=1
            assert np.abs(b[b!=0]).min()>=2.**-100
            proofs.append(dict(config=c['config'],view=i,exact_gram_infinity_bound=str(upper),exact_gram_row_sums=[str(t) for t in ss],certified_contractive=True))
        for i in range(len(bases)):
            for j in range(i+1,len(bases)):
                # Normalized numerical principal-angle diagnostics are not norm proofs.
                ai=np.linalg.qr(bases[i].T,mode='reduced')[0];aj=np.linalg.qr(bases[j].T,mode='reduced')[0]
                s=np.linalg.svd(ai.T@aj,compute_uv=False)
                diversity.append(dict(config=c['config'],view_a=i,view_b=j,normalized_basis_overlap_frobenius_sq=float(np.sum(s*s)),largest_principal_angle_cosine=float(s[0]),principal_cosines=s.tolist()))
    manifest=dict(physical_configs=cfg,aliases=aliases,logical_configs=16,physical_cells=36,metadata_bytes_per_region=64,PCA32_component_numbers=pcs,
        PCA32_raw_hex=[[float(t).hex() for t in row] for row in raw],projected_direction_hex=[[float(t).hex() for t in row] for row in new],
        coordinate_cache_mapping='physical coordinate ids 0..7 inherited PCA8; 8..39 new cache columns 0..31',proofs=proofs,random_construction=construction,
        spread_joint_proof=spreadproof,basis_f64_sha256=sha(a.out/'basis.f64'),PCA_rows_used=1000000,construction_block_size=8192,
        PCA8_basis_bridge=True,eigenvalues_top32=ev[order[:32]].tolist(),data_domain=[minimum,maximum],**hashes,
        queries_used_in_construction=False,pruning_curves_evaluated=False,basis_diversity=diversity)
    save(a.out/'VIEW_MANIFEST.json',manifest)
    print('Basis frozen: original covariance/PCA8 reproduced; all per-view exact contraction PASS',flush=True)
    flags=['-O3','-std=c++17','-fno-fast-math','-ffp-contract=off']
    subprocess.run(['g++',*flags,str(HERE/'project_views.cpp'),'-o',str(a.out/'project_views')],check=True,capture_output=True,timeout=60)
    cpu=min(os.sched_getaffinity(0))
    run=subprocess.run(['numactl',f'--physcpubind={cpu}','timeout','400s',str(a.out/'project_views'),str(a.data),str(a.out/'basis.f64'),str(a.out/'projected.f64')],check=True,capture_output=True,text=True,timeout=410)
    (a.out/'projection.log').write_text(run.stdout+run.stderr)
    assert (a.out/'projected.f64').stat().st_size==256000000
    z=np.memmap(a.out/'projected.f64',dtype='<f8',mode='r',shape=(1000000,32))
    # This independent original-vector check does not evaluate any prune outcomes.
    ids=np.unique(np.concatenate([np.array(im['queries']),np.random.default_rng(20261013).choice(1000000,256,replace=False)]))
    assert np.array_equal(ordered(x[ids],new),z[ids]),'independent ordered projection bridge'
    np.savez_compressed(a.out/'bridge_vectors.npz',row_ids=ids,vectors=x[ids],projection=z[ids])
    save(a.out/'BUILD_RECEIPT.json',dict(GPU_used=False,CPU=next(l.split(':',1)[1].strip() for l in Path('/proc/cpuinfo').read_text().splitlines() if l.startswith('model name')),
        python=sys.version.split()[0],numpy=np.__version__,PCA_cpu_cores=4,projection_cpu_cores=1,compiler=subprocess.check_output(['g++','--version'],text=True).splitlines()[0],build_flags=flags,
        blas_libraries=sorted({Path(l.split()[-1]).name for l in Path('/proc/self/maps').read_text().splitlines() if 'blas' in l.lower() and '/' in l}),
        binary_sha256=sha(a.out/'project_views'),source_sha256=sha(HERE/'project_views.cpp'),projected_sha256=sha(a.out/'projected.f64'),
        independent_projection_rows=len(ids),independent_projection_equal=True,bridge_vectors_sha256=sha(a.out/'bridge_vectors.npz'),elapsed_resource_seconds=time.monotonic()-start,
        process_peak_RSS_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,no_latency_measured=True))
    print('Full ordered projection + original-vector independent bridge PASS; no pruning outcomes yet',flush=True)

if __name__=='__main__':main()
