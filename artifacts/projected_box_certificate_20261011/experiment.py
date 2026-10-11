#!/usr/bin/env python3
"""Train one initial-only PCA4; evaluate the fixed projected-box diagnostic."""
import argparse
import ctypes
import json
import os
import platform
import resource
import subprocess
import sys
import time
from pathlib import Path
import numpy as np
from box import HERE,sha,save,outside_repo,raw,stats,library,project,projection_interval,select_directions,keep,sources,bind,summarize,decision


def cpu():
    r=resource.getrusage(resource.RUSAGE_SELF);return r.ru_utime+r.ru_stime


def pca(x):
    n,d=x.shape;chunk=8192;mean=np.zeros(d);wall=time.perf_counter();start=cpu();rss0=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    for first in range(0,n,chunk):
        a=np.array(x[first:first+chunk],dtype=np.float64);assert np.isfinite(a).all();mean+=a.sum(axis=0);del a
    mean/=n;cov=np.zeros((d,d));peak=0
    for first in range(0,n,chunk):
        a=np.array(x[first:first+chunk],dtype=np.float64);a-=mean;product=a.T@a
        peak=max(peak,a.nbytes+product.nbytes+cov.nbytes+mean.nbytes);cov+=product;del a,product
    cov=(cov+cov.T)/(2*n);values,u,proof=select_directions(cov)
    v2,u2,p2=select_directions(cov);assert np.array_equal(u.view(np.uint64),u2.view(np.uint64)) and np.array_equal(values.view(np.uint64),v2.view(np.uint64)) and proof==p2
    return mean,cov,values,u,dict(**proof,PCA_wall_seconds=time.perf_counter()-wall,PCA_process_CPU_seconds=cpu()-start,
        process_peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,pre_PCA_peak_RSS_bytes=rss0*1024,
        explicit_chunk_live_array_bytes_peak=peak,direction_matrix_bytes=u.nbytes,accounting='PCA time includes two full input passes, covariance, two eigh/sign/Gram qualifications. Peak RSS includes mapped input/runtime; explicit chunk arrays exclude BLAS/LAPACK internals. No query timing collected.')


def backend():
    # Pin the actually loaded OpenBLAS object; private path is used only to hash it.
    loaded={line.split()[-1] for line in Path('/proc/self/maps').read_text().splitlines() if any(s in line for s in ('/libopenblas','/libblas','/liblapack'))}
    paths={p for p in loaded if '/libopenblas' in p}
    assert len(paths)==1,'Expected one loaded OpenBLAS backend'
    path=Path(next(iter(paths)));lib=ctypes.CDLL(str(path))
    lib.openblas_get_config.restype=ctypes.c_char_p
    threads=lib.openblas_get_num_threads();assert threads==4
    import numpy.linalg._umath_linalg as lapack_binding
    loaded.add(lapack_binding.__file__)
    return dict(name=path.name,sha256=sha(path),config=lib.openblas_get_config().decode(),threads_actual=threads,architecture=platform.machine(),
        native_objects=[dict(name=Path(p).name,sha256=sha(p)) for p in sorted(loaded)],scope='Actual loaded BLAS/LAPACK objects plus NumPy eigh binding; private paths omitted')


def main(a):
    out=outside_repo(a.output);out.mkdir(exist_ok=False);source=sources()
    flags=['-std=c++17','-O3','-fno-fast-math','-ffp-contract=off','-fopenmp','-shared','-fPIC']
    save(out/'REGISTERED.json',dict(source_hashes=source,contract_sha256=sha(HERE/'CONTRACT.json'),compiler_flags=flags,
        Python=platform.python_version(),NumPy=np.__version__,thread_policy={k:os.environ.get(k) for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS')},GPU_processes=0,nice_actual=os.getpriority(os.PRIO_PROCESS,0),BLAS_backend=backend()))
    assert all(os.environ.get(k)=='4' for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'))
    subprocess.run(['g++',*flags,str(HERE/'project.cpp'),'-o',str(out/'projection.so')],check=True)
    subprocess.run([sys.executable,str(HERE/'test_box.py'),'--library',str(out/'projection.so'),'-v'],check=True)
    save(out/'BUILD.json',dict(compiler_flags=flags,compiler=subprocess.check_output(['g++','--version'],text=True).splitlines()[0],library_sha256=sha(out/'projection.so'),numerical_tests_passed=17))
    c,prior,inputs,files=bind(a);lib=library(out/'projection.so')
    n,d=1000000,960
    for name in c['snapshots']:
        path=Path(inputs[name]['data']);assert tuple(np.fromfile(path,'<i4',count=3))==(d,n,2) and path.stat().st_size==12+n*d*4
    initial=np.memmap(inputs['initial']['data'],dtype='<f4',mode='r',offset=12,shape=(n,d))
    mean,cov,values,u,p=pca(initial);np.savez(out/'PCA_CONSTRUCTION.npz',mean=mean,covariance=cov,eigenvalues=values,directions=u)
    save(out/'PCA_DIRECTIONS.json',dict(training_snapshot='initial',training_data_sha256=c['inputs']['initial']['data_sha256'],rows=n,dimensions=d,K=4,dtype='FP64',directions=u.tolist(),eigenvalues=values.tolist(),mean=mean.tolist(),sign_coordinates=p['sign_coordinates'],uncentered_projection=True))
    save(out/'DIRECTION_PROOF.json',dict(passed=True,**p,construction_sha256=sha(out/'PCA_CONSTRUCTION.npz'),direction_json_sha256=sha(out/'PCA_DIRECTIONS.json'),source_hashes=source,training_has_no_query_radius_oracle_input=True,initial_only=True,eigh_repeated_bitwise=True))
    print('PCA4 frozen',p['PCA_wall_seconds'],'s wall, CPU',p['PCA_process_CPU_seconds'],flush=True)
    radius=float(np.array([0x3f34a3d8],dtype=np.uint32).view(np.float32)[0]);result=[];br=[];bindings={}
    ballrows=json.loads((a.ball/'SUMMARY_COMPARISON.json').read_text())['rows']
    for name in c['snapshots']:
        x=np.memmap(inputs[name]['data'],dtype='<f4',mode='r',offset=12,shape=(n,d))
        with np.load(a.partition/(name+'_S1_P2.npz')) as f:perm=f['permutation'];starts=f['starts']
        sizes=np.diff(np.r_[starts,n]);assert len(starts)==4096 and set(sizes)=={244,245}
        z,m=project(lib,x,u);lo,hi=projection_interval(z,m,u)
        blo=np.minimum.reduceat(lo[perm],starts);bhi=np.maximum.reduceat(hi[perm],starts)
        np.savez(out/(name+'_projections.npz'),z=z,maxabs=m,lo=lo,hi=hi,box_lo=blo,box_hi=bhi)
        save(out/(name+'_BOX_READY.json'),dict(passed=True,projection_sha256=sha(out/(name+'_projections.npz')),direction_json_sha256=sha(out/'PCA_DIRECTIONS.json'),construction_has_no_query_radius_oracle_input=True))
        for b,size in enumerate(sizes):br.append(dict(snapshot=name,block=b,size=int(size),lo=blo[b].tolist(),hi=bhi[b].tolist(),width=(bhi[b]-blo[b]).tolist()))
        qids=c['inputs'][name]['qids'];q=np.ascontiguousarray(x[qids]);qz,qm=project(lib,q,u)
        assert np.array_equal(qz.view(np.uint64),z[qids].view(np.uint64)) and np.array_equal(qm,m[qids])
        qlo,qhi=projection_interval(qz,qm,u)
        refs=np.stack([raw(a.references/name/(str(q)+'.f64'),'<f8',(n,)) for q in qids])
        rr=[r for r in ballrows if r['snapshot']==name];assert len(rr)==32 and [r['qid'] for r in rr]==qids
        for qi,qid in enumerate(qids):
            hits=refs[qi]<=radius*radius;required=np.maximum.reduceat(hits[perm],starts)
            k=keep(qlo[qi],qhi[qi],blo,bhi,radius,d,p['operator_norm_squared_upper']);assert not np.any(required&~k),('false prune',name,qi)
            nk,nr=int(k.sum()),int(required.sum());no=int(sizes[k].sum());r=rr[qi]
            assert r['oracle_required_blocks']==nr and r['true_hit_count']==int(hits.sum())
            result.append(dict(snapshot=name,query=qi,qid=qid,total_blocks=4096,global4_surviving_blocks=r['global4_surviving_blocks'],local_ball_surviving_blocks=r['local_ball_surviving_blocks'],projected_box_surviving_blocks=nk,oracle_required_blocks=nr,
                global4_survival_fraction=r['global4_survival_fraction'],local_ball_survival_fraction=r['local_ball_survival_fraction'],projected_box_survival_fraction=nk/4096,oracle_fraction=nr/4096,
                projected_box_false_prune=0,projected_box_oracle_gap=nk-nr,true_hits=int(hits.sum()),surviving_objects=no,global4_surviving_objects=r['global4_surviving_objects'],local_ball_surviving_objects=r['surviving_objects'],
                query_projection_ops=4,numeric_maxabs_reductions=1,summary_endpoint_reads=32768,summary_metadata_bytes=262144,direction_coordinate_bytes=30720,
                modeled_total_fullD_equivalent_work=5+no,modeled_dot_only_plus_verification=4+no,modeled_total_coordinate_bytes=30720+3840+no*3840))
        bindings[name]=dict(data_sha256=c['inputs'][name]['data_sha256'],partition_sha256=c['partition_sha256'][name],queries=qids,directions_json_sha256=sha(out/'PCA_DIRECTIONS.json'))
        print(name,'projected mean',np.mean([r['projected_box_survival_fraction'] for r in result if r['snapshot']==name]),flush=True)
    assert len(result)==64 and len(br)==8192
    save(out/'PROJECTED_BOX_STATS.json',dict(rows=br,summary=[dict(snapshot=name,blocks=4096,width_by_direction=[stats([r['width'][j] for r in br if r['snapshot']==name]) for j in range(4)]) for name in c['snapshots']]))
    s=summarize(result);save(out/'SUMMARY_COMPARISON.json',dict(rows=result,summary=s));save(out/'DECISION.json',decision(s))
    assert sources()==source
    for path,h in files.items():assert sha(path)==h,('input mutation',path.name)
    save(out/'PROOF.json',dict(passed=True,source_hashes=source,bindings=bindings,direction_proof_sha256=sha(out/'DIRECTION_PROOF.json'),
        raw_files={p.name:sha(p) for p in out.iterdir() if p.is_file()},object_projections=2000000,query_projections=64,query_rows=64,block_rows=8192,false_prune=0,GPU_processes=0))
    print(json.dumps(decision(s)),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('partition','partition-verify','prior','prior-verify','inputs','maintenance','references','ball','output'):p.add_argument('--'+k,type=Path,required=True)
    main(p.parse_args())
