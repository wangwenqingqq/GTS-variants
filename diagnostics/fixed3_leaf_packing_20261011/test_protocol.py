#!/usr/bin/env python3
"""CPU proof of complete slot ownership, tails and observation-only sidecars."""
import argparse,re,tempfile
from pathlib import Path
from prepare import prepare,leaf,sha
from analyze import paired
p=argparse.ArgumentParser();p.add_argument('source',type=Path);a=p.parse_args()
for tasks in range(1,65):
    seen=[]
    for block in range((tasks+2)//3):
        for lane in range(32):
            bid=3*block+lane//10
            if lane>=30 or bid>=tasks:continue
            for did in range(lane%10,20,10):seen.append((bid,did))
    assert sorted(seen)==[(bid,did) for bid in range(tasks) for did in range(20)]
    for size in range(1,21):assert sum(did<size for bid,did in seen)==tasks*size
local=Path(__file__).resolve().parent/'local';local.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(dir=local) as tmp:
    out=Path(tmp)/'code';pins=prepare(a.source,out)
    old=(out/'G0/include/search_v2.cuh').read_text()
    assert old==(out/'observed/shared/adapted/include/search_v2.cuh').read_text()
    body=leaf(old)[2];assert not any(x in body for x in ('__syncthreads','__shared__','blockDim','__shfl','__syncwarp'))
    for mode in ('G0','G1','G2'):
        s=(out/mode/'include/search_v2.cuh').read_text();b=leaf(s)[2]
        assert b[b.index('\t\tdouble result'):]==body[body.index('\t\tdouble result'):]
        observed=(out/(mode+'_count')/'include/search_v2.cuh').read_text()
        assert re.sub(r'\n// LG_BEGIN\n.*?\n// LG_END','',observed,flags=re.S)==s
    for name,digest in pins['files'].items():assert sha(out/name)==digest
orders=[['G0','G1','G2'],['G2','G1','G0'],['G1','G0','G2'],['G2','G0','G1'],['G1','G2','G0'],['G0','G2','G1']]
result=paired([2.]*6,[1.]*6,orders,'G1','G2',2026101101)
assert result['paired_geometric_ratio']==2 and result['bootstrap_95']==[2,2] and result['candidate_process_wins']==6
print('PASS original G0, identical distance/store bodies, all20 slots, sizes1..20, tails and removable counters')
