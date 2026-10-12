#!/usr/bin/env python3
"""Small regression check for membership correspondence, ties, and identity."""
import numpy as np
from analyze import correspondence,sig,sparse_correspondence

def main():
    old=np.repeat(np.arange(3,dtype=np.int32),4);new=np.array([2]*4+[0]*4+[1]*4,dtype=np.int32)
    matches,c=correspondence(old,new,3);assert matches=={0:1,1:2,2:0};assert c.sum()==12
    sparse,overlap=sparse_correspondence(old,new,3);assert sparse==matches and sum(overlap.values())==12
    rng=np.random.default_rng(73)
    for slots in (2,3,10):
        old=rng.integers(slots,size=99);new=rng.integers(slots,size=99)
        assert sparse_correspondence(old,new,slots)[0]==correspondence(old,new,slots)[0]
    # Storage label equality cannot establish semantic correspondence.
    assert matches[0]!=0
    matches,c=correspondence(np.array([0,1,0,1]),np.array([0,0,1,1]),2);assert not matches
    matches,c=correspondence(np.array([0,0,1]),np.array([0,1,1]),2);assert matches=={}
    assert sig(np.array([2,1,3]))==sig(np.array([3,2,1]))
    assert sig(np.array([2,1,3]))!=sig(np.array([2,1,4]))
    a=np.array([8,9,10,11]);b=np.array([9,10,11,12]);assert np.count_nonzero((a<10)!=(b<10))==1
    print('PASS membership correspondence, ambiguous fallback, exact signature, boundary crossing')
if __name__=='__main__':main()
