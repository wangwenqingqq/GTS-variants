#!/usr/bin/env python3
"""Native CPU/GPU Flat static entrypoints, with explicit preparation and delivery."""
import argparse,csv,ctypes,json,os,resource,sys,time
from pathlib import Path
import numpy as np
from native_cpu import NativeCPU
from qualify import cpu
now=time.perf_counter

def execute(a):
    assert os.environ.get('OMP_NUM_THREADS')=='1'
    data=cpu.validate.load(a.data);spec=json.loads((a.snapshot/'SNAPSHOT.json').read_text())
    assert cpu.sha(a.data)==spec['data_sha256'] and (spec['N'],spec['D'],spec['Q'])==(1000000,960,32)
    assert not list(a.output.parent.glob(a.output.name+'.*'))
    qids=[q['physical_qid'] for q in spec['queries']];tasks=a.order.split(',');versions={};before=cpu.rss();context_ms=0.;device_memory={}
    if a.method=='GPU_FLAT_KNN':
        import faiss
        assert faiss.__version__=='1.15.1' and 'GPU' in faiss.get_compile_options();faiss.omp_set_num_threads(1)
        binding=sys.modules[faiss.GpuIndexFlatL2.__module__]
        versions=dict(faiss=faiss.__version__,extensions={n:cpu.sha(m.__file__) for n,m in vars(binding).items() if n.startswith('_swigfaiss') and hasattr(m,'__file__')})
        assert versions['extensions']
        runtime=ctypes.CDLL('libcudart.so');start=now();assert runtime.cudaFree(ctypes.c_void_p())==0;context_ms=(now()-start)*1000
        def memory():
            free,total=ctypes.c_size_t(),ctypes.c_size_t();assert runtime.cudaMemGetInfo(ctypes.byref(free),ctypes.byref(total))==0;return total.value-free.value
        device_memory['before']=memory();start=now();res=faiss.StandardGpuResources();cfg=faiss.GpuIndexFlatConfig();cfg.device=0;cfg.useFloat16=False
        if hasattr(cfg,'use_cuvs'):cfg.use_cuvs=False
        index=faiss.GpuIndexFlatL2(res,data.shape[1],cfg);index.add(data);res.syncDefaultStreamCurrentDevice();build=(now()-start)*1000;prep=0.;tasks=['knn']
        def query(task,q):
            q=np.array(q,dtype=np.float32,order='C',copy=True).reshape(1,-1);sq,ids=index.search(q,8)
            result=(ids[0].astype(np.int32),np.sqrt(np.maximum(sq[0],np.float32(0))),sq[0].astype(np.float64));res.syncDefaultStreamCurrentDevice();return result
        def release():
            nonlocal index,res
            index=None;res.syncDefaultStreamCurrentDevice();res=None
        representation_bytes=0;index_bytes=data.nbytes;device_memory['built']=memory()
    else:
        limit=None;api=NativeCPU('CPU_FLAT' if a.method=='CPU_FLAT' else a.method,leaf=512,inclusive=True)
        if a.method=='CPU_FLAT':
            import faiss
            assert faiss.__version__=='1.15.1';faiss.omp_set_num_threads(1);versions['faiss']=faiss.__version__
            versions['native_omp_threads']=faiss.omp_get_max_threads();assert versions['native_omp_threads']==1
            start=now();api.data=np.array(data,dtype=np.float32,order='C',copy=True);prep=(now()-start)*1000
            start=now();api.index=faiss.IndexFlatL2(data.shape[1]);api.index.add(api.data);build=(now()-start)*1000;index_bytes=data.nbytes
        else:
            from threadpoolctl import threadpool_limits,threadpool_info
            limit=threadpool_limits(limits=1)
            import sklearn
            from sklearn.neighbors import KDTree,BallTree
            assert sklearn.__version__=='1.6.1';versions['sklearn']=sklearn.__version__
            start=now();api.data=np.array(data,dtype=np.float64,order='C',copy=True);prep=(now()-start)*1000
            start=now();api.index=(KDTree if a.method=='CPU_KD' else BallTree)(api.data,leaf_size=512,metric='euclidean');build=(now()-start)*1000
            index_bytes=sum(x.nbytes for x in api.index.get_arrays())-api.data.nbytes
        representation_bytes=api.data.nbytes;versions['implementation_sha256']=cpu.sha(sys.modules[api.index.__class__.__module__].__file__)
        if limit is not None:
            versions['pools']=threadpool_info();assert all(p['num_threads']==1 for p in versions['pools'])
        def query(task,q):return api.knn(q,8) if task=='knn' else api.range(q,np.float32(.705625057220459))
        def release():
            api.release()
            if limit is not None:limit.restore_original_limits()
    built=cpu.rss();payloads=[];rows=[];at=0;timing={};usage=resource.getrusage(resource.RUSAGE_SELF);warm=now()
    def call(task,qi,qid,warmup):
        nonlocal at
        t=now();answer=query(task,data[qid]);payloads.append(answer);ack=(now()-t)*1000
        rows.append(dict(task=task,query=len(rows),qid=qid,count=len(answer[0]),offset=at,ack_ms=ack,warmup=warmup,task_query=qi));at+=len(answer[0])
    for task in tasks:
        for qi,qid in enumerate(qids[:8]):call(task,qi,qid,True)
    warm=(now()-warm)*1000
    for task in tasks:
        t=now()
        for qi,qid in enumerate(qids):call(task,qi,qid,False)
        timing[task+'_pass_ms']=(now()-t)*1000
    t=now();release();release_ms=(now()-t)*1000
    if a.method=='GPU_FLAT_KNN':device_memory['final']=memory()
    end=resource.getrusage(resource.RUSAGE_SELF)
    for i,suffix,dtype in ((0,'.ids.i32','<i4'),(1,'.dist.f32','<f4'),(2,'.native_squared.f64','<f8')):np.concatenate([p[i] for p in payloads]).astype(dtype).tofile(str(a.output)+suffix)
    with Path(str(a.output)+'.queries.csv').open('x') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    cpu.save(str(a.output)+'.static.json',dict(method='CPU_FLAT_INCLUSIVE_ADAPT' if a.method=='CPU_FLAT' else a.method,preparation_ms=prep,build_ms=build,warmup_ms=warm,release_ms=release_ms,**timing,
        context_ms=context_ms,device_memory=device_memory,queries=len(rows),warmup_per_task=8,measured_per_task=32,versions=versions,native_threads=1,affinity=sorted(os.sched_getaffinity(0)),representation_bytes=representation_bytes,index_bytes=index_bytes,
        memory_before=before,memory_built=built,memory_final=cpu.rss(),cpu_user_s=end.ru_utime-usage.ru_utime,cpu_system_s=end.ru_stime-usage.ru_stime,source_sha256=cpu.sha(__file__),adapter_sha256=cpu.sha(Path(__file__).with_name('native_cpu.py')),
        scope='Host-ready complete arrays; retained native-squared observer charged; GPU build includes resource initialization/index.add H2D; serialization/client destruction excluded'))
    print('PASS native full output',a.method,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--method',choices=['CPU_KD','CPU_BALL','CPU_FLAT','GPU_FLAT_KNN'],required=True);p.add_argument('--order',choices=['knn,range','range,knn'],required=True)
    for k in ('data','snapshot','output'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();assert __debug__;execute(a)
