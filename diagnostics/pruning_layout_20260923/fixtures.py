#!/usr/bin/env python3
"""Read-only pinned sources -> bounded float32 fixtures and independent CPU oracle."""
import argparse, hashlib, json, random
from pathlib import Path
import numpy as np
SOURCES={
 'GIST':('gist1m/gist_base.fvecs',960,'73418110328f5aa522d9f6b0cd9115a6c515dc44e3c48420e506ddeddbdbdbc0'),
 'Deep':('deep1m/deep1M_base.fvecs',96,'4f418cbd3d87183ad2965fbf85b921c16b3702e973ad585edc4c791380abde90'),
 'Tloc':('T-loc/1_million_location_gts.txt',2,'a9c71ead1bdab0f254abfcdc8b947db56e3af50c571b3b5ad9fbe607fddb8677')}

def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(8<<20),b''):h.update(b)
 return h.hexdigest()

def main(data,out):
 out.mkdir();ids=sorted(random.Random(2026092301).sample(range(1000000),2000))
 qids=random.Random(2026092317).sample(range(2000),64)
 for name,(relative,dim,pin) in SOURCES.items():
  source=data/relative;assert sha(source)==pin, name
  if source.suffix=='.fvecs':
   a=np.memmap(source,dtype='<f4',mode='r').reshape(1000000,dim+1)
   assert np.all(a[:,0].view('<i4')==dim)
   x=np.array(a[ids,1:],dtype=np.float32)
  else:
   chosen=set(ids);rows=[]
   with source.open() as f:
    assert list(map(int,next(f).split()))==[dim,1000000,2]
    for i,line in enumerate(f):
     if i in chosen:rows.append(np.fromstring(line,sep=' ',dtype=np.float32))
    assert i==999999
   x=np.array(rows,dtype=np.float32)
  assert x.shape==(2000,dim) and np.isfinite(x).all()
  root=out/name;root.mkdir();f=root/'fixtures';f.mkdir();(root/'runs').mkdir()
  np.savetxt(f/'data.txt',x,fmt='%.9g',header=f'{dim} 2000 2',comments='')
  assert np.array_equal(x,np.loadtxt(f/'data.txt',skiprows=1,dtype=np.float32))
  (f/'queries.qid').write_text('64\n'+'\n'.join(map(str,qids))+'\n')
  (f/'source_indices.json').write_text(json.dumps(ids)+'\n')
  y=x.astype(np.float64);dist=np.array([np.sqrt(np.sum((y-y[q])**2,axis=1)) for q in qids])
  nonself=dist.copy()
  for j,q in enumerate(qids):nonself[j,q]=np.inf
  normal=float(np.float32(np.median(np.partition(nonself,49,axis=1)[:,49])))
  radii={'empty':-1.,'zero':0.,'normal':normal,'all':float(np.float32(dist.max()+1))}
  record={'dataset':name,'dimension':dim,'source_sha256':pin,'source_relative':relative,
          'data_sha256':sha(f/'data.txt'),'qids_sha256':sha(f/'queries.qid'),
          'source_indices_sha256':sha(f/'source_indices.json'),'radii':radii,
          'queries':qids,'distances':dist.tolist(),
          'normal_min_boundary_margin':float(np.min(np.abs(dist-normal))),
          'normal_count_min_median_max':[int(v) for v in [np.sum(dist<=normal,axis=1).min(),np.median(np.sum(dist<=normal,axis=1)),np.sum(dist<=normal,axis=1).max()]]}
  (f/'oracle.json').write_text(json.dumps(record)+'\n')
  print(json.dumps({k:v for k,v in record.items() if k not in ['queries','distances']}),flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('data_root',type=Path);p.add_argument('output',type=Path)
 a=p.parse_args();main(a.data_root,a.output)
