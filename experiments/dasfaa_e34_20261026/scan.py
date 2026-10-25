"""Native FAISS GPU FP32 FlatL2 with complete host result delivery."""
import csv,json,os,sys,time
from pathlib import Path
import numpy as np
import faiss

def main(base,query,n,q,reps,warm,out):
    n,q,reps,warm=map(int,(n,q,reps,warm));out=Path(out);Path(str(out)+'.pid').write_text(str(os.getpid()))
    h=np.fromfile(base,dtype='<i4',count=2);d=int(h[1]);x=np.memmap(base,dtype='<f4',mode='r',offset=8,shape=(int(h[0]),d))[:n]
    h=np.fromfile(query,dtype='<i4',count=2);queries=np.fromfile(query,dtype='<f4',offset=8).reshape(int(h[0]),d)
    resource=faiss.StandardGpuResources();resource.setTempMemory(512<<20)
    config=faiss.GpuIndexFlatConfig();config.device=0;config.useFloat16=False
    if hasattr(config,'use_cuvs'):config.use_cuvs=False
    t=time.perf_counter();index=faiss.GpuIndexFlatL2(resource,d,config)
    for s in range(0,n,1000000):index.add(np.ascontiguousarray(x[s:s+1000000]))
    build_ms=(time.perf_counter()-t)*1000
    def call(start,b):
        # Contiguous host input creation, H2D, native search, sync and full D2H.
        z=np.ascontiguousarray(queries[np.arange(start,start+b)%1000]);D,I=index.search(z,64)
        # Native candidate generation; explicit FP64 reranking is inside host-ready time.
        exact=((np.asarray(x[I],dtype=np.float64)-z[:,None,:].astype(np.float64))**2).sum(2)
        order=np.argsort(exact,axis=1,kind='stable')[:,:8]
        return np.take_along_axis(exact,order,1),np.take_along_axis(I,order,1)
    for _ in range(warm):call(0,q)
    with open(str(out)+'.csv','x') as f:
        w=csv.writer(f);w.writerow(['iteration','start','batch','batch_ms'])
        for it in range(-1,reps):
            ids=[]
            for start in range(0,1000,q):
                b=1024 if q==1024 else min(q,1000-start);t=time.perf_counter();D,I=call(start,b);dt=(time.perf_counter()-t)*1000
                assert I.shape==(b,8);w.writerow([it,start,b,dt]);f.flush()
                if it==-1:ids.append(I.astype('<i4'))
            if it==-1:np.concatenate(ids).tofile(str(out)+'.ids')
    Path(str(out)+'.json').write_text(json.dumps({'implementation':'native FAISS GpuIndexFlatL2','faiss':faiss.__version__,'N':n,'D':d,'Q':q,'build_ms':build_ms,'useFloat16':False,'candidate_k':64,'refinement':'CPU FP64 explicit differences over native candidates','logical_scan_bytes_per_batch':q*n*d*4})+'\n')
if __name__=='__main__':main(*sys.argv[1:])
