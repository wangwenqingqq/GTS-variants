#!/usr/bin/env python3
"""Independent CPU full-output checks for the large float32 L2 fixtures."""
import csv,hashlib,json,math,struct
from pathlib import Path
import numpy as np
DATASETS=['GIST','Deep','Tloc'];SIZES=[65536,1000000]
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(8<<20),b''):h.update(b)
    return h.hexdigest()
def read(p):return json.loads(p.read_text())
def clean(x):assert x['exit_code']==0 and x['stop_reason'] is None and not x['runtime_errors'] and x['post_gpu_clear'],x
def qids(p):
    q=list(map(int,p.read_text().split()));assert q.pop(0)==len(q);return q
def check(root,label,mode,name,meta,matrix):
    p=root/'runs'/label;r=read(p/'receipt.json');clean(r)
    assert r['mode']==mode and r['radius']==meta['radii'][name] and r['dump'] and r['repeats']==1 and r['warmup']==0
    assert r['binary']=='graph_bench' and r['binary_sha256']==sha(root/'bin/graph_bench')
    assert r['input_sha256']['data.f32bin']==meta['sha256']['data.f32bin']
    assert r['input_sha256'][r['qfile']]==meta['sha256'][r['qfile']]
    requested=qids(root/'fixtures'/r['qfile']);allq=qids(root/'fixtures/queries.qid');lookup={q:i for i,q in enumerate(allq)}
    rows=list(csv.DictReader((p/'result.csv').open()));assert len(rows)==len(requested)
    digest=[];band=0
    with (p/'result.results').open() as out:
        for q,row in zip(requested,rows):
            fields=out.readline().split();gotq,count=map(int,fields[:2]);assert gotq==q and row['qid']==str(q)
            pairs=fields[2:];assert len(pairs)==count==int(row['count'])
            cpu=matrix[lookup[q]];radius=meta['radii'][name]
            eps=np.maximum(2e-6,2e-5*cpu)
            uncertain=np.abs(cpu-radius)<=eps;band+=int(np.count_nonzero(uncertain)) if name=='normal' else 0
            required=np.flatnonzero(cpu<radius-eps)
            forbidden=np.flatnonzero(cpu>radius+eps)
            seen=np.zeros(meta['n'],dtype=np.uint8);h=hashlib.sha256();fnv=1469598103934665603
            for word in pairs:
                i,d=word.split(':');i=int(i);d=float(d);assert 0<=i<meta['n'] and math.isfinite(d)
                assert seen[i]==0 and abs(d-float(cpu[i]))<=float(eps[i]),(label,q,i,'distance')
                seen[i]=1
                bits=struct.unpack('<I',struct.pack('<f',d))[0]
                h.update(struct.pack('<II',i,bits))
                for w in (i,bits):fnv=((fnv^w)*1099511628211)&((1<<64)-1)
            assert np.all(seen[required]) and not np.any(seen[forbidden]),(label,q,'definite membership')
            if name=='all':assert count==meta['n']
            if name=='empty':assert count==0
            fnv=((fnv^count)*1099511628211)&((1<<64)-1)
            assert row['ordered_hash']==str(fnv),(label,q,'GPU ordered bits')
            digest.append((q,count,h.hexdigest(),str(fnv)))
        assert not out.read().strip()
    return digest,band
def full(root,dataset,size):
    meta=read(root/'fixtures/oracle.json');assert meta['dataset']==dataset and meta['n']==size
    for n,h in meta['sha256'].items():assert sha(root/'fixtures'/n)==h,n
    matrix=np.load(root/'fixtures/oracle.npy',mmap_mode='r');assert matrix.shape==(8,size)
    checked={};bands={}
    for name in (['normal','zero','all','empty'] if size==1000000 else ['normal']):
        ref=None;countband=None
        for mode in ('CE' if name=='empty' else 'ACE'):
            label=f'full_{name}_{mode}';got,band=check(root,label,mode,name,meta,matrix)
            if ref is None:ref=got;countband=band
            assert got==ref,(dataset,size,name,mode,'native ordered float32 bits')
            checked[label]=sha(root/'runs'/label/'result.results')
        expected={str(q):[count,fnv] for q,count,_,fnv in ref}
        (root/'fixtures'/f"expected_{meta['radii'][name]:g}.json").write_text(json.dumps(expected,indent=2)+'\n')
        bands[name]=countband
    value={'dataset':dataset,'n':size,'checks':checked,'normal_ambiguous_distance_count':bands.get('normal',0),
           'oracle_sha256':sha(root/'fixtures/oracle.npy'),'binary_sha256':sha(root/'bin/graph_bench')}
    (root/'full_verified.json').write_text(json.dumps(value,indent=2)+'\n');return value
