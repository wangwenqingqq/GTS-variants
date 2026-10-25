"""Freeze real-data prefixes, disjoint query pools, and a fitted synthetic mixture."""
import hashlib,json,os,sys
from pathlib import Path
import numpy as np

def sha(p):
    with open(p,'rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def fbin(p,x):
    with open(p,'wb') as f:np.array(x.shape,dtype='<i4').tofile(f);np.asarray(x,dtype='<f4').tofile(f)
def readbin(p):
    n,d=np.fromfile(p,dtype='<i4',count=2);return np.memmap(p,dtype='<f4',offset=8,mode='r',shape=(int(n),int(d)))
def main(root,ds):
    root=Path(root);ds=Path(ds);out=root/'data';out.mkdir(exist_ok=True)
    manifest={'seed':20261026,'inputs':{},'cases':[]}
    for rel in ['T-loc/tloc_10m.txt','T-loc/tloc_1m.npy','deep100m/base.100M.fbin','deep100m/query.public.10K.fbin','word/word.txt']:
        p=ds/rel;manifest['inputs'][rel]={'bytes':p.stat().st_size,'sha256':sha(p)}
        print('HASHED',rel,flush=True)
    p=out/'tloc10m.fbin'
    if not p.exists():fbin(p,np.loadtxt(ds/'T-loc/tloc_10m.txt',skiprows=1,dtype=np.float32))
    x=readbin(p);q=np.array(np.load(ds/'T-loc/tloc_1m.npy',mmap_mode='r')[:1000],copy=True)
    # Reject equal coordinates as well as shared source row identity.
    def key(a):return np.ascontiguousarray(a).view(np.dtype((np.void,a.dtype.itemsize*a.shape[1]))).ravel()
    assert not np.isin(key(x),key(q)).any(),'Query coordinates overlap real base'
    fbin(out/'tloc_query.fbin',q)
    for n in [1000000,3000000,10000000]:manifest['cases'].append({'family':'tloc','N':n,'D':2,'base':'data/tloc10m.fbin','query':'data/tloc_query.fbin','source':'real T-loc 10M prefix','synthetic':False})
    # Fixed 64 spatial clusters, fitted only to input points, never query performance.
    rng=np.random.default_rng(20261026);sample=np.asarray(x[rng.choice(len(x),32768,replace=False)],dtype=np.float64)
    means=sample[rng.choice(len(sample),64,replace=False)].copy()
    for _ in range(20):
        label=((sample[:,None]-means[None])**2).sum(2).argmin(1)
        for j in range(64):
            if (label==j).any():means[j]=sample[label==j].mean(0)
    weights=np.bincount(label,minlength=64)/len(label)
    cov=np.array([np.cov(sample[label==j].T)+np.eye(2)*1e-8 for j in range(64)])
    mixture={'seed':20261026,'clusters':64,'fit_sample_rows':32768,'iterations':20,'means':means.tolist(),'weights':weights.tolist(),'covariances':cov.tolist(),'real_quantiles':np.quantile(sample,[0,.01,.25,.5,.75,.99,1],axis=0).tolist()}
    (out/'mixture.json').write_text(json.dumps(mixture,indent=2)+'\n')
    p=out/'tloc_synthetic100m.fbin'
    if not p.exists():
        rng=np.random.default_rng(20261026);chol=np.linalg.cholesky(cov)
        with p.open('wb') as f:
            np.array([100000000,2],dtype='<i4').tofile(f)
            for start in range(0,100000000,100000):
                ids=rng.choice(64,100000,p=weights);z=rng.standard_normal((100000,2));b=means[ids]+np.einsum('nij,nj->ni',chol[ids],z);np.asarray(b,dtype='<f4').tofile(f)
    # Synthetic queries use a distinct seed and are not index objects.
    rng=np.random.default_rng(20261027);ids=rng.choice(64,1000,p=weights);z=rng.standard_normal((1000,2));sq=means[ids]+np.einsum('nij,nj->ni',np.linalg.cholesky(cov)[ids],z);fbin(out/'synthetic_query.fbin',sq)
    for n in [30000000,100000000]:manifest['cases'].append({'family':'tloc','N':n,'D':2,'base':'data/tloc_synthetic100m.fbin','query':'data/synthetic_query.fbin','source':'synthetic fitted Gaussian mixture','synthetic':True})
    deep=ds/'deep100m/base.100M.fbin';dq=readbin(ds/'deep100m/query.public.10K.fbin');fbin(out/'deep_query.fbin',dq[:1000]);os.symlink(deep,out/'deep100m.fbin') if not (out/'deep100m.fbin').exists() else None
    for n in [1000000,3000000,10000000,20000000]:manifest['cases'].append({'family':'deep','N':n,'D':96,'base':'data/deep100m.fbin','query':'data/deep_query.fbin','source':'Deep-1B official 100M prefix','synthetic':False})
    for case in manifest['cases']:case.update(k=8,Q=[1,32,1024],oracle=f'data/{case["family"]}_{case["N"]}.oracle')
    manifest['files']={str(p.relative_to(root)):{'sha256':sha(p),'bytes':p.stat().st_size} for p in out.iterdir() if p.is_file() and not p.is_symlink()}
    manifest['files']['data/deep100m.fbin']=manifest['inputs']['deep100m/base.100M.fbin']
    # Prefix content hashes distinguish each N; full source hashes alone are insufficient.
    for case in manifest['cases']:
        h=hashlib.sha256();remaining=case['N']*case['D']*4
        with (root/case['base']).open('rb') as f:
            f.seek(8)
            while remaining:
                b=f.read(min(8<<20,remaining));assert b;h.update(b);remaining-=len(b)
        case['prefix_sha256']=h.hexdigest()
    (root/'DATA_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n');print('DATA FROZEN',flush=True)
if __name__=='__main__':main(*sys.argv[1:])
