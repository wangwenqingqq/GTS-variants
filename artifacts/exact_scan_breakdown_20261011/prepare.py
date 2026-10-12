#!/usr/bin/env python3
"""Freeze inputs, build diagnostic-only controls, calibrate without measured queries."""
import argparse,ctypes,json,os,subprocess,sys,time
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
EXT=HERE.parent/'external_closure';sys.path.insert(0,str(EXT))
from pruning_value.build import sha,save,outside_repo
read=lambda p:json.loads(Path(p).read_text())
if not __debug__:raise RuntimeError('Assertions required')


def sources():
    paths=list(HERE.glob('*'))+[EXT/k for k in ('range_service.cu','static_range.cu','pe_e.cu','pe_common.hpp','static_guard.py','static_check.py','pe_check.py','pe_trace.py')]
    return {str(p.relative_to(HERE.parent)):sha(p) for p in paths if p.is_file()}


def scores_library(path):
    f=ctypes.CDLL(str(path)).ordered_scores;f.argtypes=[ctypes.c_void_p]*4+[ctypes.c_size_t,ctypes.c_int,ctypes.c_int];f.restype=ctypes.c_int
    def score(x,q):
        ids=np.arange(len(x),dtype=np.int64);q=np.ascontiguousarray(q,dtype=np.float32);v=np.empty(len(x),np.float64)
        assert x.dtype==np.float32 and x.flags.c_contiguous and f(x.ctypes.data,ids.ctypes.data,q.ctypes.data,v.ctypes.data,len(x),x.shape[1],4)==0
        return v
    return score


def main(a):
    w=outside_repo(a.work);w.mkdir(exist_ok=False);(w/'build').mkdir();(w/'reference').mkdir()
    records=read(a.inputs)['records'];r=records['initial'];data=Path(r['data']);qids=r['qids'];ref=a.references/'initial'
    c=read(HERE/'CONTRACT.json');assert len(qids)==32 and not set(qids)&set(c['calibration_qids'])
    assert sha(data)==r['data_sha256']== 'f371099f42fea105bed573c67bbfd5b522743220873cf68aa900eb6c44b388e7'
    assert sha(ref/'REFERENCE.json')==r['reference_sha256'];prior=read(ref/'REFERENCE.json')
    assert all(sha(ref/(q+'.f64'))==h for q,h in prior['files'].items())
    assert sha(a.cpu_library)==prior['library_binding']['library_sha256']
    e=read(a.e_build/'REGISTERED.json');old=read(a.range_build/'BUILD_REGISTERED.json')
    assert sha(a.e_build/'scan')==read(a.e_build/'BUILD.json')['binary_sha256']=='3625babbafc9bd428ebd61e339c9651f663c7e651fdeedc8d965ba40979c6594'
    assert sha(a.range_build/'bin/range_static')==read(a.range_build/'BUILD.json')['binaries']['range_static']=='14f6d53ce1471c0f5f093d4266787ddf0a600fbd07e7d0434b77de568d599071'
    env={**os.environ,**e['environment'],'OMP_NUM_THREADS':'4','OPENBLAS_NUM_THREADS':'4','MKL_NUM_THREADS':'4'}
    src=(HERE.parent/'unified_target_workflow/phase_b/cpu_oracle.cpp').read_text();assert src.count('(d!=128&&d!=960)')==1
    cpu_source=w/'build/cpu_oracle.cpp';cpu_source.write_text(src.replace('(d!=128&&d!=960)','(d!=128&&d!=256&&d!=512&&d!=960)'))
    cpu_cmd=['g++','-std=c++17','-O3','-fPIC','-shared','-fopenmp','-ffp-contract=off','-fno-fast-math','-fno-associative-math','-frounding-math',str(cpu_source),'-o',str(w/'build/cpu_oracle.so')]
    cmd=[str(HERE/'probe.cu') if v.endswith('/static_range.cu') else str(w/'build/probe') if v.endswith('/bin/range_static') else v for v in old['commands']['range_static']]+['--ptxas-options=-v']
    dynamic=(EXT/'pe_e.cu').read_text();dynamic='#include <cuda_profiler_api.h>\n#include <nvtx3/nvToolsExt.h>\n'+dynamic
    dynamic=dynamic.replace('#include "range_service.cu"','#include "'+str(EXT/'range_service.cu')+'"').replace('#include "pe_common.hpp"','#include "'+str(EXT/'pe_common.hpp')+'"')
    replacements=[('        norm(n,1);','        nvtxRangePushA("insert.norm");norm(n,1);nvtxRangePop();'),('        ck(cudaMemcpyAsync(database+size_t(n)*d,v,size_t(d)*4,cudaMemcpyHostToDevice,stream));','        nvtxRangePushA("insert.vector_H2D");ck(cudaMemcpyAsync(database+size_t(n)*d,v,size_t(d)*4,cudaMemcpyHostToDevice,stream));nvtxRangePop();'),('        if(row!=last){','        nvtxRangePushA("delete.swap_last");\n        if(row!=last){'),('        occurrence.pop_back();','        nvtxRangePop();nvtxRangePushA("delete.bookkeeping");occurrence.pop_back();'),('position[id]=-1;--n;ck(cudaStreamSynchronize(stream));','position[id]=-1;--n;nvtxRangePop();ck(cudaStreamSynchronize(stream));'),('    for(size_t i=0;i<trace.flags.size();i++){','    static int calls=0;bool profile=(++calls==2);if(profile)ck(cudaProfilerStart());\n    for(size_t i=0;i<trace.flags.size();i++){'),('        auto begin=Clock::now();int n=scan.n,flag=trace.flags[i];','        auto begin=Clock::now();int n=scan.n,flag=trace.flags[i];if(profile)nvtxRangePushA(("op_"+std::to_string(i)+"_flag_"+std::to_string(flag)).c_str());'),('        ck(cudaDeviceSynchronize());ops.push_back','        ck(cudaDeviceSynchronize());if(profile)nvtxRangePop();ops.push_back'),('    tick=Clock::now();auto final=scan.occurrence;','    if(profile)ck(cudaProfilerStop());\n    tick=Clock::now();auto final=scan.occurrence;')]
    for before,after in replacements:assert dynamic.count(before)==1,before;dynamic=dynamic.replace(before,after)
    dyn=w/'build/dynamic.cu';dyn.write_text(dynamic)
    dyn_cmd=[str(dyn) if v.endswith('/pe_e.cu') else str(w/'build/dynamic') if v.endswith('/E_build/scan') else v for v in e['command']]
    (w/'qids.txt').write_text('\n'.join(map(str,qids))+'\n')
    reg=dict(contract_sha256=sha(HERE/'CONTRACT.json'),source_hashes=sources(),data=str(data),data_sha256=sha(data),qids=qids,prior_reference=prior,prior_reference_folder=str(ref),cpu_parent_sha256=sha(a.cpu_library),commands=dict(cpu=cpu_cmd,probe=cmd,dynamic=dyn_cmd),generated_sources=dict(cpu=sha(cpu_source),dynamic=sha(dyn)),environment={k:env[k] for k in ('LD_LIBRARY_PATH','OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS')},keeper_binary=str(a.range_build/'bin/range_static'),keeper_sha256=sha(a.range_build/'bin/range_static'),dynamic_keeper_binary=str(a.e_build/'scan'),dynamic_keeper_sha256=sha(a.e_build/'scan'),registered_unix=time.time())
    save(w/'REGISTERED.json',reg)
    for name,command in reg['commands'].items():
        with (w/'build'/f'{name}.compile.log').open('x') as log:subprocess.run(command,env=env,stdout=log,stderr=log,check=True)
    binary={name:sha(w/'build'/file) for name,file in [('probe','probe'),('dynamic','dynamic'),('cpu','cpu_oracle.so')]}
    ldd=subprocess.check_output(['ldd',str(w/'build/probe')],env=env,text=True);assert 'not found' not in ldd;(w/'build/ldd.txt').write_text(ldd)
    deps={};
    for line in ldd.splitlines():
        v=line.strip().split()
        if '=>' in v and len(v)>2 and v[2].startswith('/'):deps[v[0]]=dict(sha256=sha(v[2]))
    save(w/'build/BUILD.json',dict(binaries=binary,registration_sha256=sha(w/'REGISTERED.json'),libraries=deps))
    score=scores_library(w/'build/cpu_oracle.so');rng=np.random.default_rng(2026101111)
    for d in c['dimensions']:
        x=rng.random((513,d),dtype=np.float32);q=x[1];expected=np.zeros(len(x))
        for j in range(d):delta=x[:,j].astype(float)-float(q[j]);expected+=delta*delta
        assert expected.tobytes()==score(x,q).tobytes()
    x=np.memmap(data,dtype='<f4',offset=12,shape=(1000000,960));radius=float(np.array([0x3f34a3d8],np.uint32).view(np.float32)[0])
    target=float(np.mean([np.count_nonzero(np.fromfile(ref/f'{q}.f64','<f8')<=radius*radius) for q in qids]));calibration={};bindings={}
    for d in (960,128,256,512):
        xx=np.ascontiguousarray(x[:,:d]);folder=w/'reference'/str(d);folder.mkdir();cal=np.concatenate([score(xx,xx[q]) for q in c['calibration_qids']]);targets={'low':10,'high':target*10} if d==960 else {'mid':target}
        radius_by={}
        for name,t in targets.items():
            k=int(np.floor(8*t))-1;z=np.partition(cal,k)[k];r32=np.float32(np.sqrt(z));radius_by[name]=dict(radius=float(r32),radius_bits=hex(int(r32.view(np.uint32))),target_hits=t,calibration_mean_hits=float(np.count_nonzero(cal<=float(r32)**2)/8))
        if d==960:radius_by['mid']=dict(radius=radius,radius_bits='0x3f34a3d8',target_hits=target)
        calibration[str(d)]=radius_by
        for q in qids:
            v=np.fromfile(ref/f'{q}.f64','<f8') if d==960 else score(xx,xx[q]);v.tofile(folder/f'{q}.f64')
        bindings[str(d)]={p.name:sha(p) for p in folder.iterdir()}
        print('PREPARED D',d,'calibration',radius_by,flush=True)
    save(w/'PREPARED.json',dict(passed=True,registration_sha256=sha(w/'REGISTERED.json'),cpu_extended_dimensions_bitwise_conformance=True,reference_hashes=bindings,calibration=calibration,calibration_queries_disjoint=True,data_sha256=sha(data),qids_sha256=sha(w/'qids.txt'),source_hashes=sources(),build_sha256=sha(w/'build/BUILD.json')))

    # Fresh active-contract preparation is distinct from a retained R0-to-R1 repair.
    save(w/'READY.json',dict(passed=True,prepared_sha256=sha(w/'PREPARED.json'),contract_sha256=sha(HERE/'CONTRACT.json'),calibration=calibration,calibration_qids=c['calibration_qids'],low_mid_high_radius_order=calibration['960']['low']['radius']<radius<calibration['960']['high']['radius'],scope='fresh active-contract preparation; not historical R0-to-R1 repair'))

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('work','inputs','references','cpu-library','e-build','range-build'):p.add_argument('--'+k,type=Path,required=True)
    main(p.parse_args())
