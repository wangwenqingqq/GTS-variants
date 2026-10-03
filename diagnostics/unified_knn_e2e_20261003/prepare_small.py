#!/usr/bin/env python3
"""CPU enumeration of every small-table distance, including exact ties."""
import hashlib
import json
from pathlib import Path
import struct
import numpy as np

ROOT = Path(__file__).resolve().parent

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def cpu_reference(data, queries):
    records=[]
    for q in queries:
        squared=np.zeros(len(data),dtype=np.float64)
        for j in range(data.shape[1]):
            delta=data[:,j].astype(np.float64)-float(data[q,j])
            squared+=delta*delta
        ids=np.lexsort((np.arange(len(data)),squared))[:32]
        ties={str(k):{'strictly_closer_ids':np.flatnonzero(squared<squared[ids[k-1]]).tolist(),
                     'boundary_ids':np.flatnonzero(squared==squared[ids[k-1]]).tolist(),
                     'boundary_squared':float(squared[ids[k-1]])} for k in (8,32)}
        records.append({'qid':int(q),'ids':ids.tolist(),'squared':squared[ids].tolist(),'ties':ties})
    return {'N':len(data),'D':data.shape[1],'Q':len(queries),'records':records,
            'cpu_spotcheck':'ALL objects, separate subtract/multiply/add in original dimension order'}

def main():
    fixtures=ROOT/'fixtures';fixtures.mkdir(exist_ok=True)
    manifest={'seed':2026100308,'files':{}}
    for n in (4097,1000000):
        seeds=np.random.default_rng(2026100308).choice(n,min(4096,n),replace=False).astype('<i4')
        path=fixtures/f'seeds_{n}.i32';seeds.tofile(path)
        manifest['files'][path.name]={'N':n,'M':len(seeds),'sha256':digest(path)}
    queries=np.array([0,1,63,*range(64,80),*range(128,138),4096,4000,3999,3998],dtype=np.int32)
    assert len(queries)==33
    qpath=fixtures/'small33.qid';qpath.write_text('33\n'+'\n'.join(map(str,queries))+'\n')
    for d in (96,960):
        n=4097;rng=np.random.default_rng(2026100300+d)
        data=(rng.standard_normal((n,d))*.125).astype('<f4')
        data[:64]=0;data[64:128]=0;data[64:128,0]=1
        data[128:138]=np.float32(1e-40)
        data[3998]=np.float32(1e15);data[3999]=np.nextafter(np.float32(1e15),np.float32(np.inf))
        data[4000]=np.float32(-1e15)
        p=fixtures/f'small{d}.f32bin'
        with p.open('wb') as f:f.write(struct.pack('<iii',d,n,2));data.tofile(f)
        order=rng.permutation(n).astype('<i4')
        count=11111;dtype=np.dtype([('pid','<i4'),('min_dis','<f4'),('size','<i4'),('lid','<i4'),('is_leaf','<i4')])
        nodes=np.zeros(count,dtype=dtype);empty=np.ones(count,dtype='<i4')
        def split(nid,start,size,level,pivot):
            empty[nid]=0;nodes[nid]=(pivot,0,size,start,int(level==4 or size<=20))
            if nodes[nid]['is_leaf']:return
            boundaries=np.linspace(start,start+size,11,dtype=int)
            # Siblings use an actually identical pivot ID.
            child_pivot=int(order[start+size//2])
            for c in range(10):
                s,e=map(int,boundaries[c:c+2])
                if e>s:split(nid*10+1+c,s,e-s,level+1,child_pivot)
        split(0,0,n,0,int(order[0]))
        idx=fixtures/f'small{d}.index'
        with idx.open('wb') as f:f.write(struct.pack('<iiii',n,d,5,count));order.tofile(f);nodes.tofile(f);empty.tofile(f)
        oracle=fixtures/f'cpu_small{d}.json';oracle.write_text(json.dumps(cpu_reference(data,queries),indent=2)+'\n')
        for path in (p,idx,oracle):manifest['files'][path.name]={'sha256':digest(path)}
    manifest['files'][qpath.name]={'sha256':digest(qpath)}
    (ROOT/'SMALL_FIXTURES.json').write_text(json.dumps(manifest,indent=2)+'\n')

if __name__=='__main__':main()
