#!/usr/bin/env python3
"""Native GPU pointers and timed final-K Host-ready delivery; no refinement."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import time
import cupy as cp
import numpy as np
from qualification import native_ivf,check_output

ROOT=Path(__file__).resolve().parent

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(8<<20),b''):h.update(b)
    return h.hexdigest()

class Backend:
    def __init__(self,source,method,nlist=1024):
        self.method=method;self.source=source;self.nlist=nlist;self.setup={}
        begin=time.perf_counter();self.data=cp.asarray(source);cp.cuda.Stream.null.synchronize()
        self.setup['data_layout_ms']=(time.perf_counter()-begin)*1000
        begin=time.perf_counter()
        if method=='CAGRA':
            import cuvs
            from cuvs.neighbors import cagra
            self.library=cagra;path=ROOT/f'cagra_n{len(source)}_d{source.shape[1]}.index'
            if path.exists():
                self.index=cagra.Index();self.loaded_dataset=cagra.Dataset()
                cagra.load(self.index,str(path),out_dataset=self.loaded_dataset)
                self.setup['index_action']='load frozen graph and dataset'
            else:
                self.index=cagra.build(cagra.IndexParams(metric='sqeuclidean',graph_degree=64,intermediate_graph_degree=128),self.data)
                cagra.save(str(path),self.index)
                self.setup['index_action']='build ivf_pq default graph and freeze full index'
            self.setup.update(version=cuvs.__version__,index_sha256=sha(path),
                graph_degree=64,intermediate_graph_degree=128,build_algo='ivf_pq')
        else:
            import faiss
            assert faiss.__version__=='1.15.1' and 'GPU' in faiss.get_compile_options()
            faiss.omp_set_num_threads(16);self.library=faiss
            self.resources=faiss.StandardGpuResources();self.resources.setDefaultNullStreamAllDevices()
            if method=='FAISS_FLAT':
                cfg=faiss.GpuIndexFlatConfig();cfg.device=0;cfg.useFloat16=False
                cfg.use_cuvs=False
                self.index=faiss.GpuIndexFlatL2(self.resources,source.shape[1],cfg)
            else:
                path=ROOT/f'ivf_rows{len(source)}_d{source.shape[1]}_n{nlist}_trained.index'
                if path.exists():
                    cpu=faiss.read_index(str(path));opts=faiss.GpuClonerOptions();opts.useFloat16=False;opts.use_cuvs=False
                    self.index=faiss.index_cpu_to_gpu(self.resources,0,cpu,opts)
                else:
                    cfg=faiss.GpuIndexIVFFlatConfig();cfg.device=0;cfg.use_cuvs=False
                    self.index=faiss.GpuIndexIVFFlat(self.resources,source.shape[1],nlist,faiss.METRIC_L2,cfg)
                    sample=np.random.default_rng(2026100307).choice(len(source),min(200000,len(source)),replace=False)
                    train_begin=time.perf_counter();self.index.train(np.asarray(source[sample],dtype=np.float32,order='C'))
                    self.setup['train_ms']=(time.perf_counter()-train_begin)*1000
                    faiss.write_index(faiss.index_gpu_to_cpu(self.index),str(path))
                self.setup['trained_index_sha256']=sha(path)
            self.index.add_c(len(source),faiss.cast_integer_to_float_ptr(self.data.data.ptr))
            cp.cuda.Stream.null.synchronize();assert self.index.ntotal==len(source)
            cpu=faiss.index_gpu_to_cpu(self.index)
            serialized=faiss.serialize_index(cpu)
            self.setup['index_sha256']=hashlib.sha256(memoryview(serialized)).hexdigest()
            if method!='FAISS_FLAT':
                lists=cpu.invlists
                seen=[]
                for i in range(cpu.nlist):
                    count=lists.list_size(i);ptr=lists.get_ids(i)
                    seen.append(faiss.rev_swig_ptr(ptr,count).copy());lists.release_ids(i,ptr)
                seen=np.concatenate(seen);assert np.array_equal(np.sort(seen),np.arange(len(source)))
                self.setup['exactly_once_id_coverage']=True
            del cpu,serialized
            self.setup.update(version=faiss.__version__,use_cuvs=False,fp16_storage=False,
                default_stream='CuPy null stream',train_seed=2026100307,training_rows=min(200000,len(source)))
        self.setup['index_setup_ms']=(time.perf_counter()-begin)*1000

    def measure(self,qids,warm,k,b,config,out,reference=None):
        if self.method=='CAGRA':
            params=self.library.SearchParams(algo='auto',itopk_size=config['itopk_size'],search_width=config['search_width'])
            actual={'algo':'auto','itopk_size':params.itopk_size,'search_width':params.search_width,
                    'max_iterations':params.max_iterations,'min_iterations':params.min_iterations,
                    'num_random_samplings':params.num_random_samplings,'rand_xor_mask':params.rand_xor_mask}
        elif self.method!='FAISS_FLAT':
            self.index.nprobe=config['nprobe'];assert self.index.nprobe==config['nprobe']<=min(self.nlist,2048)
            actual={'nlist':self.nlist,'nprobe':self.index.nprobe}
        else:actual={}
        native_ids=cp.empty((b,k),dtype=cp.uint32 if self.method=='CAGRA' else cp.int64);native_ds=cp.empty((b,k),dtype=cp.float32)
        host_ids=np.empty((len(qids),k),dtype=np.int32);host_ds=np.empty((len(qids),k),dtype=np.float32)
        def batch(qs,offset):
            count=len(qs);dev_qids=cp.asarray(qs);query=self.data[dev_qids]
            ni,nd=native_ids[:count],native_ds[:count]
            if self.method=='CAGRA':
                # Default cuVS resources synchronize internally; complete the
                # caller's gather before handing input to the library stream.
                cp.cuda.Stream.null.synchronize()
                self.library.search(params,self.index,query,k,neighbors=ni,distances=nd)
            else:
                faiss=self.library
                self.index.search_c(count,faiss.cast_integer_to_float_ptr(query.data.ptr),k,
                    faiss.cast_integer_to_float_ptr(nd.data.ptr),faiss.cast_integer_to_idx_t_ptr(ni.data.ptr))
            converted_ids=ni.astype(cp.int32);fields=cp.sqrt(cp.maximum(nd,np.float32(0)))
            converted_ids.get(out=host_ids[offset:offset+count]);fields.get(out=host_ds[offset:offset+count])
            cp.cuda.Stream.null.synchronize()
            del dev_qids,query,converted_ids,fields,ni,nd
        for w in range(2):batch(warm[w*b:(w+1)*b],0)
        times=[];cp.cuda.nvtx.RangePush('formal.query_pass');begin=time.perf_counter()
        for first in range(0,len(qids),b):
            start=time.perf_counter();batch(qids[first:first+b],first);times.append((time.perf_counter()-start)*1000)
        cp.cuda.Stream.null.synchronize();total=(time.perf_counter()-begin)*1000;cp.cuda.nvtx.RangePop()
        out=Path(out)
        with Path(str(out)+'.bin').open('wb') as f:
            f.write(struct.pack('<iiii',len(self.source),self.source.shape[1],len(qids),k));host_ids.tofile(f);host_ds.tofile(f)
        meta={'mode':self.method,'K':k,'B':b,'Q':len(qids),'pass_ms':total,
              'batch_p50_ms':float(np.median(times)),'batch_p95_ms':float(np.quantile(times,.95)),
              'configuration':actual,'setup':self.setup,'input_bridge':'timed host IDs H2D and device database gather',
              'output_bridge':'device squared-to-Euclidean FP32 and native ID-to-int32; final K D2H; actual stream synchronization',
              'python_query_control_timed':True,'native':True}
        if reference is not None:meta['quality']=check_output(str(out)+'.bin',self.source,reference,k)
        Path(str(out)+'.json').write_text(json.dumps(meta,indent=2)+'\n')
        Path(str(out)+'.csv').write_text('batch_index,host_ms\n'+''.join(f'{i},{v:.12f}\n' for i,v in enumerate(times)))
        return meta

def main():
    p=argparse.ArgumentParser();p.add_argument('--data',required=True);p.add_argument('--method',required=True)
    p.add_argument('--qids',required=True);p.add_argument('--warm',required=True);p.add_argument('--reference')
    p.add_argument('--k',type=int,required=True);p.add_argument('--b',type=int,required=True);p.add_argument('--out',required=True)
    p.add_argument('--nlist',type=int,default=1024);p.add_argument('--nprobe',type=int,default=1024)
    p.add_argument('--itopk',type=int,default=1024);p.add_argument('--width',type=int,default=4)
    a=p.parse_args();source=native_ivf.load_data(a.data);backend=Backend(source,a.method,a.nlist)
    reference=json.loads(Path(a.reference).read_text()) if a.reference else None
    row=backend.measure(native_ivf.read_qids(a.qids),native_ivf.read_qids(a.warm),a.k,a.b,
                        {'nprobe':a.nprobe,'itopk_size':a.itopk,'search_width':a.width},a.out,reference)
    print(json.dumps(row),flush=True)

if __name__=='__main__':main()
