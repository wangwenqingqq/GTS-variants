#!/usr/bin/env python3
"""Build reproducible 64-D PCA projection companions for the million-point fixtures."""
import hashlib
import json
import time
import argparse
from pathlib import Path
import numpy as np

DATA_ROOT=Path('/home/data/wangxuran/tmp/gts_20260922_cpu_io/leaf_early_l2_20260924/data')
OUT=Path('/home/data/wangxuran/tmp/gts_20260922_cpu_io/pca_end_to_end_20260925/projection')
SEED=250925
TRAIN_N=8192
WIDTH=64
CHUNK=16384

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for part in iter(lambda:f.read(8*1024*1024),b''):h.update(part)
    return h.hexdigest()

def main(data_root=DATA_ROOT,out_dir=OUT,dataset='all'):
    out_dir.mkdir(parents=True,exist_ok=True)
    report={'seed':SEED,'train_points':TRAIN_N,'projection_dimensions':WIDTH,'datasets':{}}
    for offset,name in enumerate(('GIST','Deep')):
        if dataset!='all' and name!=dataset:continue
        t0=time.monotonic()
        rng=np.random.default_rng(SEED+offset)
        source=data_root/name/'1000000/fixtures/data.f32bin'
        with source.open('rb') as f: dim,n,metric=np.fromfile(f,dtype='<i4',count=3)
        dim,n=int(dim),int(n)
        assert n==1000000 and metric==2 and dim>=WIDTH
        data=np.memmap(source,mode='r',dtype='<f4',offset=12,shape=(n,dim))
        train_ids=rng.choice(n,size=TRAIN_N,replace=False)
        train=np.asarray(data[train_ids],dtype=np.float64)
        centered=train-train.mean(axis=0)
        omega=rng.standard_normal((dim,WIDTH+16))
        y=centered@omega
        q,_=np.linalg.qr(y,mode='reduced')
        b=q.T@centered
        _,_,vt=np.linalg.svd(b,full_matrices=False)
        basis=vt[:WIDTH].T.copy()
        orth_error=float(np.max(np.abs(basis.T@basis-np.eye(WIDTH))))
        assert orth_error<1e-10
        target=out_dir/(name+'.f32bin.pca64')
        with target.open('wb') as f:f.write(np.asarray([n,dim,WIDTH],dtype='<i4').tobytes())
        projected=np.memmap(target,mode='r+',dtype='<f4',offset=12,shape=(n,WIDTH))
        for start in range(0,n,CHUNK):
            stop=min(n,start+CHUNK)
            projected[start:stop]=np.asarray(data[start:stop],dtype=np.float64)@basis
        projected.flush()
        report['datasets'][name]={'n':n,'dimensions':dim,'input_sha256':sha(source),
            'projection_sha256':sha(target),'basis_sha256':hashlib.sha256(basis.tobytes()).hexdigest(),
            'training_ids_sha256':hashlib.sha256(train_ids.tobytes()).hexdigest(),
            'orthogonality_max_error':orth_error,'build_seconds':time.monotonic()-t0,
            'projection_bytes':target.stat().st_size}
        print(name,report['datasets'][name],flush=True)
        (out_dir/('BUILD_'+name+'.json')).write_text(json.dumps(report,indent=2)+'\n')
    (out_dir/'BUILD.json').write_text(json.dumps(report,indent=2)+'\n')

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--data-root',type=Path,default=DATA_ROOT)
    parser.add_argument('--out',type=Path,default=OUT)
    parser.add_argument('--dataset',choices=['all','GIST','Deep'],default='all')
    args=parser.parse_args()
    main(args.data_root,args.out,args.dataset)
