#!/usr/bin/env python3
"""Build nested bit-preserving float32 fixtures and independent CPU L2 oracle."""
import argparse,hashlib,json,math,random,struct
from pathlib import Path
import numpy as np
SOURCES={
 'GIST':('gist1m/gist_base.fvecs',960,'73418110328f5aa522d9f6b0cd9115a6c515dc44e3c48420e506ddeddbdbdbc0'),
 'Deep':('deep1m/deep1M_base.fvecs',96,'4f418cbd3d87183ad2965fbf85b921c16b3702e973ad585edc4c791380abde90'),
 'Tloc':('T-loc/1_million_location_gts.txt',2,'a9c71ead1bdab0f254abfcdc8b947db56e3af50c571b3b5ad9fbe607fddb8677')}
SIZES=[65536,1000000]
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(8<<20),b''):h.update(b)
    return h.hexdigest()
def source_matrix(p,dim):
    if p.suffix=='.fvecs':
        a=np.memmap(p,dtype='<f4',mode='r',shape=(1000000,dim+1))
        assert np.all(a[:,0].view('<i4')==dim)
        return a[:,1:]
    with p.open() as f:assert list(map(int,f.readline().split()))==[2,1000000,2]
    a=np.loadtxt(p,skiprows=1,dtype='<f4')
    assert a.shape==(1000000,dim);return a
def generate(source_root,base,out):
    for name,(rel,dim,pin) in SOURCES.items():
        source=source_root/rel;assert sha(source)==pin,name
        src=source_matrix(source,dim)
        old=base/name/'fixtures';oldmeta=json.loads((old/'oracle.json').read_text())
        oldids=json.loads((old/'source_indices.json').read_text());qids=list(map(int,(old/'queries.qid').read_text().split()))
        assert qids.pop(0)==64 and len(oldids)==2000 and oldmeta['source_sha256']==pin
        assert np.array_equal(np.asarray(src[oldids],dtype='<f4'),np.loadtxt(old/'data.txt',skiprows=1,dtype='<f4'))
        querysource=[oldids[q] for q in qids[::8]]
        chosen=set(oldids);extra=random.Random(20260924).sample([i for i in range(1000000) if i not in chosen],1000000-2000)
        for n in SIZES:
            ids=sorted(oldids+extra[:n-2000]);assert len(ids)==n and (ids==list(range(n)) if n==1000000 else True)
            lookup={i:j for j,i in enumerate(ids)};qs=[lookup[x] for x in querysource]
            dest=out/'data'/name/str(n);f=dest/'fixtures';f.mkdir(parents=True)
            (dest/'runs').mkdir();(dest/'bin').symlink_to('../../../bin')
            (f/'indices.npy').write_bytes(np.asarray(ids,dtype='<i4').tobytes())
            (f/'queries.qid').write_text('8\n'+'\n'.join(map(str,qs))+'\n')
            for fn,subset in [('zero.qid',qs[:2]),('all.qid',qs[:1]),('negative.qid',qs[:2]),('check.qid',qs[:1]),('trace.qid',qs[:2])]:
                (f/fn).write_text(str(len(subset))+'\n'+'\n'.join(map(str,subset))+'\n')
            binary=f/'data.f32bin'
            with binary.open('wb') as output:
                output.write(struct.pack('<iii',dim,n,2))
                for start in range(0,n,8192):
                    block=np.ascontiguousarray(src[ids[start:start+8192]],dtype='<f4')
                    assert np.isfinite(block).all()
                    output.write(block.tobytes())
            assert binary.stat().st_size==12+n*dim*4
            (f/'query_source_ids.json').write_text(json.dumps(querysource)+'\n')
        large=out/'data'/name/'1000000'/'fixtures';x=np.memmap(large/'data.f32bin',dtype='<f4',mode='r',offset=12,shape=(1000000,dim))
        qlarge=list(map(int,(large/'queries.qid').read_text().split()))[1:]
        matrix=np.lib.format.open_memmap(large/'oracle.npy',mode='w+',dtype='<f8',shape=(8,1000000))
        for qi,q in enumerate(qlarge):
            query=x[q].astype(np.float64)
            for start in range(0,1000000,4096):
                stop=min(1000000,start+4096)
                diff=x[start:stop].astype(np.float64)-query
                matrix[qi,start:stop]=np.sqrt(np.sum(diff*diff,axis=1))
            assert matrix[qi,q]==0
        matrix.flush()
        rng=random.Random(481)
        for qi,i in [(0,0),(7,999999)]+[(rng.randrange(8),rng.randrange(1000000)) for _ in range(128)]:
            want=math.sqrt(math.fsum((float(a)-float(b))**2 for a,b in zip(x[i],x[qlarge[qi]])))
            assert abs(matrix[qi,i]-want)<=max(1e-12,1e-12*want)
        for n in SIZES:
            f=out/'data'/name/str(n)/'fixtures'
            if n==1000000:dist=matrix
            else:
                ids=np.fromfile(f/'indices.npy',dtype='<i4')
                dist=np.lib.format.open_memmap(f/'oracle.npy',mode='w+',dtype='<f8',shape=(8,n))
                dist[:]=matrix[:,ids];dist.flush()
            all_radius=float(np.float32(np.max(dist)+1.0))
            assert np.max(dist)<all_radius
            meta={'dataset':name,'n':n,'dimension':dim,'metric':'float32 L2','source_sha256':pin,
                  'source_relative':rel,'query_source_ids':querysource,
                  'radii':{'normal':oldmeta['radii']['normal'],'zero':0.0,'all':all_radius,'empty':-1.0},
                  'normal_count_min_median_max':[float(np.min(np.sum(dist<=oldmeta['radii']['normal'],axis=1))),
                                                 float(np.median(np.sum(dist<=oldmeta['radii']['normal'],axis=1))),
                                                 float(np.max(np.sum(dist<=oldmeta['radii']['normal'],axis=1)))],
                  'sha256':{p.name:sha(p) for p in f.iterdir() if p.name!='oracle.json'}}
            (f/'oracle.json').write_text(json.dumps(meta,indent=2)+'\n')
            print('PASS fixture',name,n,meta['normal_count_min_median_max'],flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ['source','base','output']:p.add_argument(k,type=Path)
    a=p.parse_args();generate(a.source,a.base,a.output)
