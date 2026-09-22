#!/usr/bin/env python3
"""Build bounded real-Words subsets and an independent CPU distance oracle."""
import argparse
import hashlib
import json
from pathlib import Path
import time


def distance(a, b):
    # Full integer DP table: independent of candidate GPU dispatch and pruning.
    dp = [list(range(len(b)+1))] + [[i]+[0]*len(b) for i in range(1,len(a)+1)]
    for i, x in enumerate(a,1):
        for j, y in enumerate(b,1):
            dp[i][j] = min(dp[i-1][j]+1, dp[i][j-1]+1, dp[i-1][j-1]+(x!=y))
    return dp[-1][-1]


def make(source, out, sizes=(1000,2000)):
    raw=source.read_bytes(); lines=raw.split(b'\n')
    width,n,metric=map(int,lines[0].split())
    rows=[s.removesuffix(b'\r') for s in lines[1:]]
    if rows and rows[-1]==b'': rows.pop()
    assert metric==6 and len(rows)==n
    assert all(b'\0' not in s and len(s)<109 for s in rows)
    assert not out.exists(),out
    out.mkdir(parents=True)
    meta={'source_sha256':hashlib.sha256(raw).hexdigest(),'source_n':n,'metric':6,'cases':{}}
    for size in sizes:
        assert 32 <= size <= n, size
        ids=[i*(n-1)//(size-1) for i in range(size)]
        data=[rows[i] for i in ids]
        qids=[q*(size-1)//31 for q in range(32)]
        name=f'words_{size}'
        (out/f'{name}.txt').write_bytes(f'{width} {size} 6\n'.encode()+b'\n'.join(data)+b'\n')
        (out/f'{name}.qid').write_text('32\n'+'\n'.join(map(str,qids))+'\n')
        (out/f'{name}.updates').write_text('32\n'+''.join(f'2 {q}\n' for q in qids))
        start=time.monotonic();counts=[];kth=[]
        for q in qids:
            distances=sorted(distance(data[q],word) for word in data)
            counts.append(sum(d<=4 for d in distances));kth.append(distances[3])
        meta['cases'][name]={'n':size,'q':32,'radius':4,'k':4,'source_indices':ids,
            'query_ids':qids,'range_counts':counts,'knn_kth':kth,'oracle_cpu_wall_s':time.monotonic()-start}
        print(name,'oracle ready',meta['cases'][name]['oracle_cpu_wall_s'],flush=True)
    meta['file_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.iterdir())}
    (out/'manifest.json').write_text(json.dumps(meta,indent=2)+'\n')


if __name__=='__main__':
    assert distance(b'',b'ab')==2 and distance(b'kitten',b'sitting')==3
    assert distance(b'\xff',b'\xfe')==1 and distance(b'ab',b'ab')==0
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('source',type=Path);ap.add_argument('out',type=Path)
    ap.add_argument('--sizes',nargs='+',type=int,default=[1000,2000])
    a=ap.parse_args();make(a.source,a.out,a.sizes)
