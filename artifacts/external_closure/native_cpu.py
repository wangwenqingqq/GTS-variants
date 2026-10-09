"""Native CPU API adapter, including empty/small snapshots without dummy neighbors."""
import numpy as np

class NativeCPU:
    capabilities={'knn':True,'range':True,'native_updates_qualified':False}
    def __init__(self,method,leaf=128,inclusive=False):
        assert method in ('CPU_KD','CPU_BALL','CPU_FLAT') and leaf in (32,128,512)
        self.method,self.leaf,self.index,self.data,self.limit=method,leaf,None,None,None
        self.inclusive=inclusive
    def build(self,data):
        assert self.data is None and data.ndim==2 and data.shape[1]>0 and np.isfinite(data).all()
        if self.method=='CPU_FLAT':
            import faiss
            assert faiss.__version__=='1.15.1';faiss.omp_set_num_threads(1)
            self.data=np.array(data,dtype=np.float32,order='C',copy=True)
            self.index=faiss.IndexFlatL2(data.shape[1]);self.index.add(self.data)
        else:
            import sklearn
            from sklearn.neighbors import KDTree,BallTree
            from threadpoolctl import threadpool_limits
            assert sklearn.__version__=='1.6.1';self.limit=threadpool_limits(limits=1)
            self.data=np.array(data,dtype=np.float64,order='C',copy=True)
            if len(data):self.index=(KDTree if self.method=='CPU_KD' else BallTree)(self.data,leaf_size=self.leaf,metric='euclidean')
    def _query(self,q,task,k=8,r=0.):
        assert self.data is not None and k>0 and np.isfinite(r)
        q=np.array(q,dtype=self.data.dtype,order='C',copy=True).reshape(1,-1)
        assert q.shape[1]==self.data.shape[1] and np.isfinite(q).all()
        if not len(self.data) or task=='range' and r<0:return np.empty(0,np.int32),np.empty(0,np.float32),np.empty(0,np.float64)
        k=min(k,len(self.data))
        if self.method=='CPU_FLAT':
            if task=='knn':sq,ids=self.index.search(q,k);sq,ids=sq[0],ids[0]
            else:
                cutoff=np.float64(np.float32(r))**2
                bound=np.float32(cutoff)
                if self.inclusive and float(bound)<=cutoff:
                    bound=np.nextafter(bound,np.float32(np.inf))
                # Strict native search below the first representable score ABOVE
                # cutoff is exactly inclusive for native FP32 scores. No field
                # tolerance is used to excuse FP64 membership disagreement.
                _,sq,ids=self.index.range_search(q,float(bound))
            return ids.astype(np.int32),np.sqrt(np.maximum(sq,np.float32(0))),sq.astype(np.float64)
        if task=='knn':
            dis,ids=self.index.query(q,k=k,return_distance=True,dualtree=False,breadth_first=False,sort_results=True)
        else:ids,dis=self.index.query_radius(q,float(np.float32(r)),return_distance=True,sort_results=False)
        return ids[0].astype(np.int32),dis[0].astype(np.float32),dis[0].astype(np.float64)**2
    def knn(self,q,k):return self._query(q,'knn',k=k)
    def range(self,q,r):return self._query(q,'range',r=r)
    def release(self):
        self.index=None;self.data=None
        if self.limit is not None:self.limit.restore_original_limits();self.limit=None
