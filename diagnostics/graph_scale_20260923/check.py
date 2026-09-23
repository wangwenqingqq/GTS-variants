#!/usr/bin/env python3
"""Check complete outputs against independent CPU distances and native order."""
import csv,hashlib,json,struct
from pathlib import Path

def digest(pairs):
    h=1469598103934665603
    for i,d in pairs:
        for w in [i,struct.unpack('<I',struct.pack('<f',d))[0]]:h=((h^w)*1099511628211)&((1<<64)-1)
    return str(((h^len(pairs))*1099511628211)&((1<<64)-1))

def check(root,label,radius,reference=None,write=True):
    f=root/'fixtures';p=root/'runs'/label
    m=json.loads((f/'manifest.json').read_text());n=m['n'];raw=(f/'oracle.bin').read_bytes();assert len(raw)==n*64
    receipt=json.loads((p/'receipt.json').read_text());assert receipt['exit_code']==0 and not receipt['runtime_errors'] and not receipt['stop_reason'] and receipt['post_gpu_clear']
    with (p/'result.csv').open() as fd:samples=list(csv.DictReader(fd))
    qmap={q:i for i,q in enumerate(m['qids'])};gold={};ordered={}
    with (p/'result.results').open() as fd:
        for row,line in zip(samples,fd,strict=True):
            fields=line.split();q,count=map(int,fields[:2]);pairs=[(int(x.split(':')[0]),float(x.split(':')[1])) for x in fields[2:]]
            distances=raw[qmap[q]*n:(qmap[q]+1)*n];expected={i:d for i,d in enumerate(distances) if d<=radius}
            assert len(pairs)==count==len(expected) and len(dict(pairs))==count and dict(pairs)==expected,(label,q,'CPU mismatch')
            h=digest(pairs);assert [str(q),str(count),h]==[row['qid'],row['count'],row['ordered_hash']]
            gold[str(q)]=[count,h];ordered[q]=pairs
    if reference:
        # Native order agreement is exact because edit distances are integer FP32 values.
        assert ordered==reference,(label,'native order mismatch')
    assert len(samples)==receipt['validation'].get('rows',len(samples))
    if write:(p/'external_check.json').write_text(json.dumps({'pass':True,'rows':len(samples),'radius':radius,'oracle_sha256':hashlib.sha256(raw).hexdigest(),'native_order':reference is not None})+'\n')
    return ordered,gold
