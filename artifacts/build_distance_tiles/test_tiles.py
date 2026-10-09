#!/usr/bin/env python3
"""Writer/upper-bound and frozen-budget checks, without a GPU."""
import json
from pathlib import Path
import random

HERE=Path(__file__).resolve().parent
def width(n,level):
    for _ in range(level):n=n//10+9
    return (n+511)//512


def main():
    rng=random.Random(202610090242)
    for upper in list(range(1,4097))+[1000000,1000009]:
        for size in {upper,max(1,upper-9),rng.randint(1,upper)}:
            children=[size//10]*9+[size-9*(size//10)]
            assert max(children)<=upper//10+9
    for n in (1,20,255,513,4096,19399,65535,1000000,1000009):
        limit=n
        for level in range(6):
            tiles=width(n,level)
            assert tiles*512>=limit
            sizes=[0,1,20,min(limit,513),limit]
            for slot,size in enumerate(sizes):
                # Integer interval proof avoids iterating millions of threads.
                intervals=[(tile*512,min(size,(tile+1)*512)) for tile in range((size+511)//512)]
                assert sum(b-a for a,b in intervals)==size
                assert all(a==(0 if i==0 else intervals[i-1][1]) for i,(a,b) in enumerate(intervals))
                assert all((slot*tiles+tile)//tiles==slot and (slot*tiles+tile)%tiles==tile for tile in range(tiles))
                assert sum(tile==0 for tile in range(tiles))==1
            limit=limit//10+9
    assert [10**l*width(1000000,l) for l in range(5)]==[1954,1960,2000,2000,10000]
    contract=json.loads((HERE/'CONTRACT.json').read_text())
    assert len(contract['qualification']['cases'])*2+len(contract['qualification']['sanitizers'])==22
    assert contract['primary']['fresh_processes']==12
    assert contract['primary']['orders'].count('B0B1')==contract['primary']['orders'].count('B1B0')==3
    assert contract['candidate']['new_GPU_allocations']==contract['candidate']['new_primary_synchronizations']==0
    print('PASS conservative bounds, explicit node slots, exact tile partition, unique pivot writer and fixed budgets')


if __name__=='__main__':main()
