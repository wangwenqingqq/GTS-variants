#!/usr/bin/env python3
"""Native boundary capability tests, not a latency benchmark or numeric repair."""
import argparse,json
from pathlib import Path
import numpy as np
from native_cpu import NativeCPU
from common import outside_repo
import qualify

def complete_knn(ids,fields,raw,sq,k=8):
    """Validate every column even for empty snapshots and K>N."""
    count=min(k,len(sq))
    if any(np.asarray(v).ndim!=1 or len(v)!=count for v in (ids,fields,raw)):return False
    if not np.issubdtype(np.asarray(ids).dtype,np.integer):return False
    if len(set(map(int,ids)))!=count or np.any(ids<0) or np.any(ids>=len(sq)):return False
    if not np.isfinite(fields).all() or not np.isfinite(raw).all() or np.any(fields<0) or np.any(raw<0):return False
    reference=sq[ids];scale=np.maximum(1.,reference)
    if np.any(abs(np.asarray(fields,dtype=np.float64)**2-reference)>5e-5*scale):return False
    if np.any(abs(raw-reference)>5e-5*scale):return False
    if np.any(np.diff(fields)<0) or np.any(np.diff(raw)<0):return False
    if count and (set(np.flatnonzero(sq<np.partition(sq,count-1)[count-1]))-set(map(int,ids))):return False
    return not count or bool(np.all(reference<=np.partition(sq,count-1)[count-1]))

def main(a):
    out=outside_repo(a.output);assert not out.exists();rows=[]
    for method in a.methods.split(','):
      for leaf in (32,128,512):
       for n in (0,1,7,513):
         x=np.zeros((n,17),np.float32)
         if n:x[:,0]=np.arange(n)%9
         api=NativeCPU(method,leaf=leaf,inclusive=a.inclusive);api.build(x);q=np.zeros(17,np.float32);sq=(x.astype(np.float64)**2).sum(axis=1)
         for repeat in range(32):
             ids,fields,raw=api.knn(q,8);k=min(8,n)
             ok=complete_knn(ids,fields,raw,sq)
             rows.append(dict(method=method,leaf=leaf,N=n,repeat=repeat,task='knn',passed=bool(ok)))
             for radius in (-1.,0.,1.,100.):
                 ids,fields,raw=api.range(q,radius)
                 if radius<0:ok=all(np.asarray(v).ndim==1 and len(v)==0 for v in (ids,fields,raw))
                 else:ok=qualify.cpu.quality(ids,fields,raw,sq,'range',radius)['passed']
                 rows.append(dict(method=method,leaf=leaf,N=n,repeat=repeat,task='range',radius=radius,passed=bool(ok)))
         api.release()
    qualify.save(out,dict(rows=rows,passed=all(r['passed'] for r in rows),adapter_sha256=qualify.cpu.sha(Path(__file__).with_name('native_cpu.py')),checker_sha256=qualify.cpu.sha(__file__),inclusive_adapter=a.inclusive))
    print({m:all(r['passed'] for r in rows if r['method']==m) for m in a.methods.split(',')})

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--inclusive',action='store_true');p.add_argument('--output',type=Path,required=True);p.add_argument('--methods',required=True);a=p.parse_args();main(a)
