#!/usr/bin/env python3
"""Use the independently compiled ordered-FP64 CPU loop for bounded large-state checks."""
import argparse
import ctypes
import json
from pathlib import Path
import sys
import numpy as np
if not __debug__:raise RuntimeError('Python assertions are required')
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
import validate


def install(path,threads=8):
    lib=ctypes.CDLL(str(Path(path).resolve()));fn=lib.ordered_scores
    fn.argtypes=[ctypes.c_void_p]*4+[ctypes.c_size_t,ctypes.c_int,ctypes.c_int];fn.restype=ctypes.c_int
    def scores(data,physical,query,chunk=4096):
        assert data.dtype==np.float32 and data.flags.c_contiguous
        physical=np.ascontiguousarray(physical,dtype=np.int64);query=np.ascontiguousarray(query,dtype=np.float32)
        assert 0<threads<=16 and query.shape==(data.shape[1],)
        assert len(physical)==0 or (physical.min()>=0 and physical.max()<len(data))
        out=np.empty(len(physical),dtype=np.float64)
        assert fn(data.ctypes.data,physical.ctypes.data,query.ctypes.data,out.ctypes.data,len(physical),data.shape[1],threads)==0
        return out
    return scores


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--library',type=Path,required=True)
    p.add_argument('--data',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    fast=install(a.library);data=validate.load(a.data);rows=[]
    for n in (255,4096,65536):
        for qid in (0,1,31):
            old=validate.scores(data,np.arange(n),data[qid]);new=fast(data,np.arange(n),data[qid])
            assert old.tobytes()==new.tobytes(),(n,qid)
            rows.append(dict(n=n,qid=qid,bitwise_ordered_numpy_match=True))
    for d in (128,960):
        x=np.zeros((32,d),np.float32);x[:,0]=np.arange(32)%5
        x[1,0]=np.finfo(np.float32).max;x[2,0]=-np.finfo(np.float32).max
        x[3,0]=np.nextafter(np.float32(0.705625057220459),np.float32(np.inf))
        x[4,0]=np.nextafter(np.float32(0),np.float32(1))
        assert fast(x,np.arange(len(x)),x[0]).tobytes()==validate.scores(x,np.arange(len(x)),x[0]).tobytes()
    a.output.write_text(json.dumps(dict(rows=rows,extreme_nextafter_subnormal_D128_D960=True,cuda_used=False,
        scope='CPU reference backend qualification, not a performance comparison'),indent=2)+'\n')
    print('PASS independent C++/OpenMP ordered scores match dimension-wise NumPy bits')
