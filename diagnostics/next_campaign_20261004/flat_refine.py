#!/usr/bin/env python3
"""Explicit optional native Flat overfetch64 + timed RN-FP64 refinement."""
import argparse
import json
from pathlib import Path
import struct
import time
import cupy as cp
import numpy as np
from native_knn import Backend
from qualification import native_ivf,check_output
from query_trace import QueryTrace

RN=r'''
extern "C" __global__ void refine(const float* x,const float* q,const long long* ids,double* out,int b,int d,int fetch) {
    int i=blockIdx.x*blockDim.x+threadIdx.x;if(i>=b*fetch)return;
    int row=i/fetch;long long id=ids[i];double s=0;
    for(int j=0;j<d;++j){double delta=__dsub_rn(double(x[id*d+j]),double(q[(long long)row*d+j]));s=__dadd_rn(s,__dmul_rn(delta,delta));}
    out[i]=s;
}
'''
SELECT=r'''
extern "C" __global__ void select_refined(const long long* ids,const double* ds,int* out,float* fields,int b,int k) {
    int q=blockIdx.x*blockDim.x+threadIdx.x;if(q>=b)return;bool used[64]={false};
    for(int rank=0;rank<k;++rank){int at=-1;
        for(int j=0;j<64;++j)if(!used[j]&&(at<0||ds[q*64+j]<ds[q*64+at]||(ds[q*64+j]==ds[q*64+at]&&ids[q*64+j]<ids[q*64+at])))at=j;
        used[at]=true;out[q*k+rank]=int(ids[q*64+at]);fields[q*k+rank]=__double2float_rn(__dsqrt_rn(ds[q*64+at]));
    }
}
'''

def main():
    p=argparse.ArgumentParser();p.add_argument('--data',required=True);p.add_argument('--qids',required=True)
    p.add_argument('--warm',required=True);p.add_argument('--k',type=int,required=True);p.add_argument('--b',type=int,required=True)
    p.add_argument('--out',required=True);p.add_argument('--reference');a=p.parse_args()
    begin=time.perf_counter();source=native_ivf.load_data(a.data);qs=native_ivf.read_qids(a.qids)
    warm=np.array(list(map(int,Path(a.warm).read_text().split()))[1:],dtype=np.int32)
    assert a.k in (8,32) and a.b>0 and len(warm)>=8*a.b
    backend=Backend(source,'FAISS_FLAT');faiss=backend.library;fetch=64
    ni=cp.empty((a.b,fetch),dtype=cp.int64);nd=cp.empty((a.b,fetch),dtype=cp.float32)
    exact=cp.empty((a.b,fetch),dtype=cp.float64);ids=np.empty((len(qs),a.k),dtype=np.int32);fields=np.empty_like(ids,dtype=np.float32)
    kernel=cp.RawKernel(RN,'refine',options=('--std=c++17','--fmad=false'))
    selector=cp.RawKernel(SELECT,'select_refined',options=('--std=c++17','--fmad=false'))
    selected=cp.empty((a.b,a.k),dtype=cp.int32);delivered=cp.empty((a.b,a.k),dtype=cp.float32)
    def batch(part,offset):
        count=len(part);dq=cp.asarray(part);query=backend.data[dq];neighbors=ni[:count];dist=nd[:count];score=exact[:count]
        backend.index.search_c(count,faiss.cast_integer_to_float_ptr(query.data.ptr),fetch,
            faiss.cast_integer_to_float_ptr(dist.data.ptr),faiss.cast_integer_to_idx_t_ptr(neighbors.data.ptr))
        kernel(((count*fetch+255)//256,),(256,),(backend.data,query,neighbors,score,np.int32(count),np.int32(source.shape[1]),np.int32(fetch)))
        selector(((count+127)//128,),(128,),(neighbors,score,selected,delivered,np.int32(count),np.int32(a.k)))
        selected[:count].get(out=ids[offset:offset+count]);delivered[:count].get(out=fields[offset:offset+count]);cp.cuda.Stream.null.synchronize()
    for shape in ({a.b,len(qs)%a.b}-{0}):
        for w in range(8):batch(warm[w*shape:(w+1)*shape],0)
    trace=QueryTrace(a.out);trace.begin();times=[];cp.cuda.nvtx.RangePush('formal.query_pass');start=time.perf_counter()
    for first in range(0,len(qs),a.b):
        t=time.perf_counter();batch(qs[first:first+a.b],first);times.append((time.perf_counter()-t)*1000)
        trace.sample(min(first+a.b,len(qs)),len(qs))
    cp.cuda.Stream.null.synchronize();total_ms=(time.perf_counter()-start)*1000;cp.cuda.nvtx.RangePop();trace.finish(total_ms)
    cold_ms=(time.perf_counter()-begin)*1000
    out=Path(a.out)
    with Path(str(out)+'.bin').open('wb') as f:
        f.write(struct.pack('<iiii',len(source),source.shape[1],len(qs),a.k));ids.tofile(f);fields.tofile(f)
    meta={'mode':'FAISS_FLAT_REF64','Q':len(qs),'K':a.k,'B':a.b,'pass_ms':total_ms,'cold_api_entry_total_ms':cold_ms,
          'batch_p50_ms':float(np.median(times)),'batch_p95_ms':float(np.quantile(times,.95)),'setup':backend.setup,
          'fetch':fetch,'timed_work':'native full Flat search64, gathered candidate FP64 explicit RN distances, deterministic topK, Euclidean fields, complete final-K D2H and stream completion',
          'quality_role':'empirical full-output only after independent gate; finite overfetch is not a general completeness proof',
          'raw_native_flat':'retained separately; this adapter does not repair or rename its rejected outputs'}
    if a.reference:meta['quality']=check_output(str(out)+'.bin',source,json.loads(Path(a.reference).read_text()),a.k)
    Path(str(out)+'.json').write_text(json.dumps(meta,indent=2)+'\n')
    Path(str(out)+'.csv').write_text('batch_index,host_ms\n'+''.join(f'{i},{v:.12f}\n' for i,v in enumerate(times)))
    print(json.dumps({k:v for k,v in meta.items() if k!='quality'},indent=2),flush=True)

if __name__=='__main__':main()
