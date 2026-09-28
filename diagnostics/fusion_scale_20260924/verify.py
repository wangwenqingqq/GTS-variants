#!/usr/bin/env python3
import csv,hashlib,json,struct
from pathlib import Path
import numpy as np
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def clean(v):assert v['exit_code']==0 and v['stop_reason'] is None and not v['runtime_errors'] and v['post_gpu_clear'],v
def digest(pairs):
    h=1469598103934665603
    for i,d in pairs:
        for w in [i,struct.unpack('<I',struct.pack('<f',d))[0]]:h=((h^w)*1099511628211)&((1<<64)-1)
    return str(((h^len(pairs))*1099511628211)&((1<<64)-1))
def check(root,label):
    p=root/'runs'/label;rec=json.loads((p/'receipt.json').read_text());clean(rec)
    o=json.loads((root/'fixtures/oracle.json').read_text());n=o['n'];r=rec['radius']
    assert sha(root/'bin'/rec['binary'])==rec['binary_sha256']
    assert rec['input_sha256']=={name:sha(root/'fixtures'/name) for name in ['data.txt',rec['qfile']]}
    for name,h in o['sha256'].items():assert sha(root/'fixtures'/name)==h,name
    matrix=np.memmap(root/'fixtures/oracle.bin',dtype=np.uint8,mode='r',shape=(64,n));lookup={q:i for i,q in enumerate(o['queries'])}
    qs=list(map(int,(root/'fixtures'/rec['qfile']).read_text().split()));assert qs.pop(0)==len(qs)
    rows=list(csv.DictReader((p/'result.csv').open()));gold={}
    with (p/'result.results').open() as f:
        for q,row in zip(qs,rows):
            fields=f.readline().split();assert int(fields[0])==q;count=int(fields[1]);pairs=[]
            for word in fields[2:]:
                i,d=word.split(':');i=int(i);d=float(d);assert 0<=i<n and d==int(matrix[lookup[q],i]);pairs.append((i,d))
            expected=np.flatnonzero(matrix[lookup[q]].astype(np.int16)<=r).tolist()
            assert len(pairs)==count==len(expected) and sorted(i for i,d in pairs)==expected,(label,q)
            h=digest(pairs);assert row['qid']==str(q) and int(row['count'])==count and row['ordered_hash']==h
            gold[str(q)]=[count,h]
        assert not f.read().strip()
    assert len(rows)==len(qs)
    return gold
def full(root):
    out={};checks={}
    for r in [4,0,256,-1]:
        ref=None
        for m in ('CE' if r==-1 else 'ACE'):
            label=f'full_{r}_{m}';actual=check(root,label)
            if ref is None:ref=actual
            assert ref==actual,(root,r,m,'ordered native bits')
            checks[label]=sha(root/'runs'/label/'result.results')
        out[r]=ref;(root/'fixtures'/f'expected_{r}.json').write_text(json.dumps(ref,indent=2)+'\n')
    if root.name=='2000':
        for m in 'CE':assert check(root,'anchor_full_'+m)==out[4]
    v=dict(full_checks=checks,binary_sha256=sha(root/'bin/graph_bench'),oracle_sha256=sha(root/'fixtures/oracle.bin'))
    (root/'full_verified.json').write_text(json.dumps(v,indent=2)+'\n');return v
