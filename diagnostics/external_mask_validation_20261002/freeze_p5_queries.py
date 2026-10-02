#!/usr/bin/env python3
"""Freeze unseen 1024-query sets after external choices are fixed."""
import hashlib
import json
from pathlib import Path
import random
import struct

ROOT=Path(__file__).resolve().parent
DIAG=ROOT.parent
P0=DIAG/'batch_exact_highdim_20261001/fixtures'
P4=DIAG/'batch_tree_inheritance_20261002/fixtures'
ARITH=DIAG/'arithmetic_path_boundary_20260928'


def ids(path):
    values=list(map(int,path.read_text().split()))
    assert values and values[0]==len(values)-1
    assert len(set(values[1:]))==values[0]
    return values[1:]


def freeze(dataset,seed):
    paths=sorted(P0.glob(f'{dataset}*.qid'))+[P4/f'{dataset}_final1024.qid']
    if dataset=='GIST':
        paths+=sorted(ARITH.glob('frozen*/*.qid'))
    assert all(p.exists() for p in paths)
    forbidden={q for p in paths for q in ids(p)}
    assert all(0<=q<1000000 for q in forbidden)
    before=set(forbidden)
    rng=random.Random(seed)
    chosen=[]
    while len(chosen)<1024:
        q=rng.randrange(1000000)
        if q not in forbidden:
            chosen.append(q);forbidden.add(q)
    assert len(set(chosen))==1024 and not (set(chosen)&before)
    target=ROOT/'fixtures'/f'{dataset}_p5_final1024.qid'
    assert not target.exists()
    target.parent.mkdir(exist_ok=True)
    target.write_text('1024\n'+''.join(f'{q}\n' for q in chosen))
    return {'seed':seed,'query_file':str(target.relative_to(ROOT)),
            'query_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
            'excluded_union_count':len(before),
            'excluded_ids_sha256':hashlib.sha256(b''.join(struct.pack('<i',q) for q in sorted(before))).hexdigest(),
            'intersection_count':len(set(chosen)&before),
            'excluded_files':{str(p.relative_to(DIAG)):hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in paths}}


def main():
    assert (ROOT/'frozen_external.json').exists()
    record={'GIST':freeze('GIST',2026100205),
            'Deep':freeze('Deep',2026100206)}
    (ROOT/'QUERY_SETS.json').write_text(json.dumps(record,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:{'sha256':v['query_sha256'],
                         'excluded_union_count':v['excluded_union_count']}
                      for k,v in record.items()}))


if __name__=='__main__':main()
