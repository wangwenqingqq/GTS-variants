#!/usr/bin/env python3
"""Independent CPU membership and native-bit full-output verification."""
import csv,hashlib,json,math,statistics as st,struct
from pathlib import Path
import numpy as np
DATASETS=['Words','GIST','Deep','Tloc']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def clean(r):assert r['exit_code']==0 and r['stop_reason'] is None and not r['runtime_errors'] and r['post_gpu_clear'],r
def radii(o,d):return {'normal':4,'zero':0,'all':256,'empty':-1} if d=='Words' else o['radii']
def digest(pairs):
    h=1469598103934665603
    for i,bits in pairs:
        for word in (i,bits):h=((h^word)*1099511628211)&((1<<64)-1)
    return str(((h^len(pairs))*1099511628211)&((1<<64)-1))
def full_one(root,label,dataset,radius,o):
    path=root/'runs'/label;rec=read(path/'receipt.json');clean(rec)
    assert rec['input_sha256']=={n:sha(root/'fixtures'/n) for n in ['data.txt','queries.qid']}
    binary='graph_bench_anchor' if label.startswith('anchor_') else 'graph_bench'
    assert rec['binary']==binary and rec['binary_sha256']==sha(root/'bin'/binary)
    qs=list(map(int,(root/'fixtures/queries.qid').read_text().split()));assert qs.pop(0)==len(qs)==64
    if dataset=='Words':
        matrix=np.memmap(root/'fixtures/oracle.bin',dtype=np.uint8,mode='r',shape=(64,2000))
        lookup={q:matrix[i] for i,q in enumerate(o['queries'])}
    else:lookup=dict(zip(o['queries'],o['distances']))
    out=[];lines=(path/'result.results').read_text().splitlines();rows=list(csv.DictReader((path/'result.csv').open()))
    assert len(lines)==len(rows)==64
    for q,line,row in zip(qs,lines,rows):
        fields=line.split();qid,count=map(int,fields[:2]);assert qid==q and row['qid']==str(q)
        pairs=[];parsed=[]
        for word in fields[2:]:
            idx,dist=word.split(':');idx=int(idx);dist=float(dist)
            assert 0<=idx<2000
            bits=struct.unpack('<I',struct.pack('<f',dist))[0]
            assert math.isfinite(dist)
            pairs.append((idx,bits));parsed.append((idx,dist))
        expect=[i for i,d in enumerate(lookup[q]) if d<=radius]
        assert count==len(pairs)==len(expect) and sorted(i for i,d in parsed)==expect,(dataset,label,q,'membership/count')
        if dataset=='Words':assert all(d==int(lookup[q][i]) for i,d in parsed)
        else:assert all(abs(d-lookup[q][i])<=max(2e-6,2e-5*lookup[q][i]) for i,d in parsed),(dataset,label,q,'distance')
        assert row['count']==str(count) and row['ordered_hash']==digest(pairs),(dataset,label,q,'ordered hash')
        out.append((q,pairs))
    return out
def full(root,dataset):
    o=read(root/'fixtures/oracle.json');f=root/'fixtures'
    if dataset=='Words':
        for n,h in o['sha256'].items():assert sha(f/n)==h
        assert o['n']==2000
    else:
        assert o['dataset']==dataset
        for name,key in [('data.txt','data_sha256'),('queries.qid','qids_sha256'),('source_indices.json','source_indices_sha256')]:assert sha(f/name)==o[key]
    checked={}
    for name,r in radii(o,dataset).items():
        ref=None
        for mode in ('CE' if name=='empty' else 'ACE'):
            label=f'full_{name}_{mode}';p=root/'runs'/label
            got=full_one(root,label,dataset,r,o)
            if ref is None:ref=got
            assert got==ref,(dataset,name,mode,'native ordered float32 bits')
            checked[label]=sha(p/'result.results')
        expected={str(q):[len(pairs),digest(pairs)] for q,pairs in ref}
        (f/f'expected_{r:g}.json').write_text(json.dumps(expected,indent=2)+'\n')
    if dataset=='Words':
        for m in 'CE':
            label='anchor_full_'+m;assert full_one(root,label,dataset,4,o)==full_one(root,'full_normal_A',dataset,4,o)
            checked[label]=sha(root/'runs'/label/'result.results')
    v={'dataset':dataset,'full_checks':checked,'oracle_sha256':sha(f/'oracle.json'),'binary_sha256':sha(root/'bin/graph_bench')}
    (root/'full_verified.json').write_text(json.dumps(v,indent=2)+'\n');return v
