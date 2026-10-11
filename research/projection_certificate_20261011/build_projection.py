#!/usr/bin/env python3
"""Full-database CPU PCA and independent Stage A; never performs pruning curves."""
import argparse,json,os,struct,subprocess,sys,time
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'certified_navigation_20261010'))
from audit import sha,save,load_index
from projection_math import certify,endpoints,prefix_bounds,ETA,RHO,projection_error_bound,error_bound

def ordered(x,p):
    out=np.zeros((len(x),len(p)),dtype=np.float64)
    for j in range(len(p)):
        for d in range(960):
            term=np.multiply(x[:,d].astype(np.float64),p[j,d])
            np.add(out[:,j],term,out=out[:,j])
    return out

def main():
    parser=argparse.ArgumentParser()
    for key in ['data','index','ancestors','freeze','out']:parser.add_argument('--'+key,type=Path,required=True)
    a=parser.parse_args();a.out.mkdir(parents=True,exist_ok=False);started=time.monotonic()
    im=json.loads((a.freeze/'INPUT_MANIFEST.json').read_text())
    assert sha(a.data)==im['data_sha256'] and sha(a.index)==im['tree_sha256']
    assert sha(a.ancestors)==im['ancestors_sha256'] and sha(HERE/'CONTRACT.json')==im['contract_sha256']
    assert sha(a.freeze/'BRIDGE_PAIRS.json')==im['pairs_sha256']
    assert os.environ.get('CUDA_VISIBLE_DEVICES')=='','CPU-only contract requires no visible GPU'
    allowed_cpus=os.sched_getaffinity(0);assert len(allowed_cpus)==4,'bind four admitted CPU cores'
    projection_cpu=min(allowed_cpus)
    thread_config={k:os.environ.get(k) for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS']}
    assert all(v=='4' for v in thread_config.values()),'freeze four-thread construction'
    cpu_model=next(line.split(':',1)[1].strip() for line in Path('/proc/cpuinfo').read_text().splitlines() if line.startswith('model name'))
    assert struct.unpack('<3i',a.data.open('rb').read(12))==(960,1000000,2)
    assert a.data.stat().st_size==12+1000000*960*4
    x=np.memmap(a.data,dtype='<f4',offset=12,mode='r',shape=(1000000,960))
    mean=np.zeros(960,dtype=np.float64);minimum=np.inf;maximum=-np.inf
    for start in range(0,len(x),8192):
        block=x[start:start+8192].astype(np.float64);assert np.isfinite(block).all()
        minimum=min(minimum,float(block.min()));maximum=max(maximum,float(block.max()))
        mean+=block.sum(axis=0,dtype=np.float64)
    assert minimum>=0 and maximum<=2;mean/=len(x)
    cov=np.zeros((960,960),dtype=np.float64)
    for start in range(0,len(x),8192):
        block=x[start:start+8192].astype(np.float64)-mean
        cov += block.T@block
    cov/=len(x);ev,v=np.linalg.eigh(cov);order=np.argsort(ev)[::-1]
    rawp=v[:,order[:8]].T.copy()
    random=np.linalg.qr(np.random.default_rng(20261011).standard_normal((960,8)),mode='reduced')[0].T
    families={};certs={}
    for name,p in [('RANDOM_ORTHO',random),('PCA',rawp)]:families[name],certs[name]=certify(p)
    p=np.concatenate(list(families.values()));p.astype('<f8').tofile(a.out/'basis.f64')
    save(a.out/'BASIS.json',dict(families={k:[[float(t).hex() for t in row] for row in v] for k,v in families.items()},
        certificates=certs,PCA_rows_used=1000000,construction_block_size=8192,random_seed=20261011,
        eigenvalues_top8=ev[order[:8]].tolist(),explained_variance_ratios_top8=(ev[order[:8]]/ev.sum()).tolist(),
        covariance_trace=float(ev.sum()),mean_sha256=__import__('hashlib').sha256(mean.astype('<f8').tobytes()).hexdigest(),
        covariance_sha256=__import__('hashlib').sha256(cov.astype('<f8').tobytes()).hexdigest(),
        data_domain=[minimum,maximum],queries_used_in_construction=False,basis_f64_sha256=sha(a.out/'basis.f64')))
    print('Full PCA + exact stored contraction PASS',flush=True)
    build=['g++','-O3','-std=c++17','-fno-fast-math','-ffp-contract=off',str(HERE/'project_rows.cpp'),'-o',str(a.out/'project_rows')]
    subprocess.run(build,check=True,capture_output=True,text=True,timeout=60)
    command=['numactl',f'--physcpubind={projection_cpu}','timeout','240s',str(a.out/'project_rows'),str(a.data),str(a.out/'basis.f64'),str(a.out/'projected.f64')]
    run=subprocess.run(command,check=True,capture_output=True,text=True,timeout=250)
    (a.out/'projection.log').write_text(run.stdout+run.stderr)
    assert (a.out/'projected.f64').stat().st_size==1000000*16*8
    z=np.memmap(a.out/'projected.f64',dtype='<f8',mode='r',shape=(1000000,16))
    n,d,h,ids,nodes,flags=load_index(a.index);perm=np.array(ids)
    arrays={};bounds={};qz=z[im['queries']].copy();arrays['query_projection']=qz
    for level,size in [(3,1000),(4,100),(5,10)]:
        rz=z[perm].reshape(10**level,size,16)
        low,high=endpoints(rz.min(axis=1),rz.max(axis=1))
        arrays[f'low_{level}']=low;arrays[f'high_{level}']=high
    np.savez_compressed(a.out/'intervals.npz',**arrays)
    pairs=json.loads((a.freeze/'BRIDGE_PAIRS.json').read_text())['pairs']
    selected=sorted({int(i) for pair in pairs for i in pair['object_ids']}|set(im['queries']))
    independent=ordered(x[selected],p)
    assert np.array_equal(independent,z[selected]),'independent all-object ordered projection mismatch'
    positions={v:i for i,v in enumerate(selected)};ancestor=np.load(a.ancestors)
    checks=[]
    for pair in pairs:
        level=pair['level'];ri=pair['region_index'];qi=pair['query_index'];rowix=[positions[i] for i in pair['object_ids']]
        low=arrays[f'low_{level}'][ri].astype(np.float64);high=arrays[f'high_{level}'][ri].astype(np.float64)
        assert np.all(low<=np.nextafter(independent[rowix]-ETA,-np.inf))
        assert np.all(high>=np.nextafter(independent[rowix]+ETA,np.inf))
        truth=float(np.sqrt(ancestor[f'truth_sq_{level}'][qi,ri]));u=float(np.sqrt(ancestor['U_star_squared'][qi]))
        for fi,name in enumerate(families):
            sl=slice(fi*8,(fi+1)*8)
            bs=prefix_bounds(low[None,sl].astype(np.float32),high[None,sl].astype(np.float32),qz[qi,sl])
            prior=0.
            for k,values in bs.items():
                lb=float(values[0]);assert prior<=lb<=truth
                assert not (lb>u and ancestor[f'truth_sq_{level}'][qi,ri]<=ancestor['U_star_squared'][qi])
                prior=lb
        checks.append(dict(query_id=pair['query_id'],level=level,region_id=pair['region_id'],objects_checked=len(rowix)))
    # Export a tiny independent scalar-replay fixture, not the entire dataset.
    sample=sorted(set(im['queries'])|{pair['object_ids'][0] for pair in pairs}|{pair['object_ids'][-1] for pair in pairs})
    np.savez_compressed(a.out/'bridge_vectors.npz',row_ids=np.array(sample,dtype='<i4'),vectors=x[sample],projection=z[sample])
    save(a.out/'STAGE_A.json',dict(status='PASS',pairs=128,family_prefix_bounds=128*2*4,
        independently_recomputed_objects=len(selected),coordinate_values_checked=len(selected)*16,
        all_selected_region_objects_covered=True,query_coordinates_identical=True,
        false_topK_prunes=0,bound_above_truth=0,nested_bounds=True,checks=checks,
        ETA=ETA,projection_error_bound=projection_error_bound(),RHO=RHO,original_error_bound=error_bound(),
        inputs=im,intervals_sha256=sha(a.out/'intervals.npz'),basis_sha256=sha(a.out/'BASIS.json'),
        bridge_vectors_sha256=sha(a.out/'bridge_vectors.npz')))
    save(a.out/'BUILD_RECEIPT.json',dict(GPU_used=False,exit_code=run.returncode,
        CPU=cpu_model,thread_config=thread_config,PCA_cpu_cores=len(allowed_cpus),projection_cpu_cores=1,
        python=sys.version.split()[0],numpy=np.__version__,
        blas_libraries=sorted({Path(line.split()[-1]).name for line in Path('/proc/self/maps').read_text().splitlines() if 'blas' in line.lower() and '/' in line}),compiler=subprocess.check_output(['g++','--version'],text=True).splitlines()[0],
        build_flags=build[1:5],source_sha256=sha(HERE/'project_rows.cpp'),worker_sha256=sha(Path(__file__)),
        math_sha256=sha(HERE/'projection_math.py'),binary_sha256=sha(a.out/'project_rows'),
        projected_sha256=sha(a.out/'projected.f64'),elapsed_resource_seconds=time.monotonic()-started))
    save(a.out/'OUTPUT_MANIFEST.json',{name:dict(sha256=sha(a.out/name),bytes=(a.out/name).stat().st_size) for name in
        ['BASIS.json','STAGE_A.json','BUILD_RECEIPT.json','intervals.npz','bridge_vectors.npz','projection.log']})
    print('Stage A PASS: all objects in frozen regions independently recomputed; Stage B not run',flush=True)
if __name__=='__main__':main()
