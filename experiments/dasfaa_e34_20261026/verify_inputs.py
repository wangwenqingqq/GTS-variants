"""Read-only vector provenance, oracle-shape, and exact-value holdout verification."""
import hashlib,json,sys,time
from pathlib import Path
import numpy as np


def sha(path,offset=0,length=None):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        f.seek(offset)
        while length is None or length:
            b=f.read(8<<20 if length is None else min(8<<20,length))
            if not b:
                if length:raise ValueError('truncated input')
                break
            h.update(b)
            if length is not None:length-=len(b)
    return h.hexdigest()


def rows(path):
    path=Path(path);shape=tuple(np.fromfile(path,dtype='<i4',count=2))
    assert len(shape)==2 and min(shape)>0
    assert path.stat().st_size==8+int(shape[0])*int(shape[1])*4
    return np.memmap(path,dtype='<f4',mode='r',offset=8,shape=shape)


def keys(x):
    # IEEE +0 and -0 compare equal; reject NaNs rather than hiding their semantics.
    x=np.array(x,dtype='<f4',order='C',copy=True)
    assert np.isfinite(x).all()
    x[x==0]=0
    return x.view(np.dtype(('V',x.shape[1]*4))).reshape(-1)


def overlap(base,query,n,chunk=100000):
    q=np.sort(keys(query));count=0;first=[]
    for start in range(0,n,chunk):
        k=keys(base[start:min(start+chunk,n)]);pos=np.searchsorted(q,k)
        hit=(pos<len(q)) & (q[np.minimum(pos,len(q)-1)]==k)
        count+=int(hit.sum())
        if len(first)<10:first.extend((np.flatnonzero(hit)+start).tolist()[:10-len(first)])
    return {'matching_base_rows':count,'first_matching_ids':first,'disjoint':count==0}


def verify(root):
    root=Path(root);m=json.loads((root/'DATA_MANIFEST.json').read_text())
    out={'time_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'files':{},'cases':[]}
    for name,v in m['files'].items():
        path=root/name;got=sha(path)
        assert path.stat().st_size==v['bytes'] and got==v['sha256'],name
        out['files'][name]={'sha256':got,'bytes':v['bytes']}
        print('HASH',name,flush=True)
    for c in m['cases']:
        base=rows(root/c['base']);q=rows(root/c['query']);n=c['N'];assert n<=len(base) and q.shape==(1000,c['D'])
        assert sha(root/c['base'],8,n*c['D']*4)==c['prefix_sha256']
        path=root/c['oracle'];raw=path.read_bytes();assert len(raw)==120000,str(path)
        ids=np.frombuffer(raw,dtype='<i4',count=10000).reshape(1000,10)
        ds=np.frombuffer(raw,dtype='<f8',offset=40000).reshape(1000,10)
        assert ((ids>=0)&(ids<n)).all() and np.isfinite(ds).all() and (ds>=0).all()
        assert (np.diff(ds,axis=1)>=0).all() and all(len(set(r))==10 for r in ids)
        # This is a structural check, NOT a fresh independent recomputation of GT.
        actual=np.sqrt(((base[ids].astype(np.float64)-q[:,None,:].astype(np.float64))**2).sum(2))
        assert np.allclose(actual,ds,rtol=1e-12,atol=1e-12)
        iso=overlap(base,q,n)
        row={'family':c['family'],'N':n,'prefix_sha256':c['prefix_sha256'],'oracle_sha256':sha(path),'oracle_shape_and_distances_valid':True,'oracle_zero_nearest_queries':int((ds[:,0]==0).sum()),'holdout':iso}
        out['cases'].append(row);print(json.dumps(row),flush=True)
    return out


def test():
    x=np.array([[0,-0.],[1,2],[3,4]],dtype=np.float32)
    assert overlap(x,np.array([[-0.,0]],dtype=np.float32),3,1)['matching_base_rows']==1
    assert overlap(x,np.array([[9.,9]],dtype=np.float32),3)['disjoint']
    try:keys(np.array([[np.nan]],dtype=np.float32))
    except AssertionError:pass
    else:raise AssertionError('NaNs admitted')
    print('PASS signed-zero collision, disjoint fixture, nonfinite rejection')

if __name__=='__main__':
    if sys.argv[1:] == ['--test']:test()
    else:
        out=verify(sys.argv[1]);p=Path(sys.argv[2])
        with p.open('x') as f:json.dump(out,f,indent=2);f.write('\n')
        if any(not c['holdout']['disjoint'] for c in out['cases']):raise SystemExit(21)
