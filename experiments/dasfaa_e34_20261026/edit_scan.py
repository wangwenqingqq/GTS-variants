"""Rolling-row GPU edit scan and batched platform top-k; no proxy library names."""
import csv,json,os,sys,time
from pathlib import Path
import numpy as np
from audit_word import load

CUDA=r'''
// The rolling-row recurrence is reused from the frozen range-scan baseline.
extern "C" __global__ void scan(int n,int b,int stride,const char*x,const int*xl,const char*q,const int*ql,int*out){
 int k=blockIdx.x*blockDim.x+threadIdx.x;if(k>=n*b)return;int qi=k/n,id=k%n;
 const char*a=x+(size_t)id*stride;const char*c=q+(size_t)qi*stride;int an=xl[id],cn=ql[qi];
 if(cn>an){const char*t=a;a=c;c=t;int z=an;an=cn;cn=z;}
 unsigned short row0[109],row1[109];unsigned short*p=row0,*r=row1;
 for(int j=0;j<=cn;j++)p[j]=j;
 for(int i=1;i<=an;i++){r[0]=i;for(int j=1;j<=cn;j++)r[j]=min(min(p[j]+1,r[j-1]+1),p[j-1]+(a[i-1]!=c[j-1]));unsigned short*t=p;p=r;r=t;}
 out[k]=p[cn];
}
'''
def main(base,query,n,q,reps,warm,out,k='8'):
    import cupy as cp
    n,q,reps,warm,k=map(int,(n,q,reps,warm,k))
    if not (8 <= n <= 10000000 and q > 0 and reps >= 0 and warm >= 0 and 0 < k <= n):
        raise ValueError('invalid edit scan workload')
    if 32*n > np.iinfo(np.int32).max:
        raise ValueError('scan tile exceeds int32 addressing')
    Path(out+'.pid').write_text(str(os.getpid()))
    xl,x=load(base,n);ql,z=load(query);nq=len(ql)
    t=time.perf_counter();dx=cp.asarray(x);dl=cp.asarray(xl);kernel=cp.RawKernel(CUDA,'scan',options=('--std=c++17',));kernel.compile();cp.cuda.runtime.deviceSynchronize();build=(time.perf_counter()-t)*1000
    def call(start,b):
        got=[]
        for s in range(start,start+b,32):
            bb=min(32,start+b-s);sel=np.arange(s,s+bb)%nq;qq=cp.asarray(z[sel]);ll=cp.asarray(ql[sel]);dist=cp.empty((bb,n),dtype=cp.int32)
            kernel(((bb*n+127)//128,),(128,),(np.int32(n),np.int32(bb),np.int32(x.shape[1]),dx,dl,qq,ll,dist))
            ii=cp.argpartition(dist,k-1,axis=1)[:,:k];dd=cp.take_along_axis(dist,ii,axis=1);order=cp.argsort(dd,axis=1);got.append(cp.asnumpy(cp.take_along_axis(ii,order,axis=1)).astype('<i4'))
        return np.concatenate(got)
    with open(out+'.csv','x') as f:
        w=csv.writer(f);w.writerow(['iteration','start','batch','batch_ms'])
        for it in range(-1,reps):
            ids=[]
            for s in range(0,nq,q):
                b=1024 if q==1024 and nq==1000 else min(q,nq-s);t=time.perf_counter();r=call(s,b);dt=(time.perf_counter()-t)*1000;w.writerow([it,s,b,dt]);f.flush()
                if it==-1:ids.append(r)
            if it==-1:
                np.concatenate(ids).tofile(out+'.ids')
                for _ in range(warm):call(0,q)
    Path(out+'.json').write_text(json.dumps({'implementation':'rolling-row edit scan + CuPy argpartition top-k','N':n,'Q':q,'k':k,'build_ms':build,'internal_query_tile':32,'cupy':cp.__version__,'stride':int(x.shape[1]),'max_indexed_length':int(max(xl)),'timing_scope':'host-ready query materialization, H2D, GPU edit+topk, complete IDs D2H','logical_scan_bytes_per_batch':q*n*int(x.shape[1]),'index_queries':False})+'\n')
if __name__=='__main__':main(*sys.argv[1:])
