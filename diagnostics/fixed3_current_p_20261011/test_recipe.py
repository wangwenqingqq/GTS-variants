#!/usr/bin/env python3
"""Dependency-free static mapping/source checks and reproducible paired statistics."""
import json,sys,tempfile
from pathlib import Path
from prepare import PACKED,replace_once
from analyze import paired
r=Path(__file__).resolve().parent;c=json.loads((r/'CONTRACT.json').read_text())
for nl in range(1,20):
    for size in range(1,21):
        for mask in (0,(1<<nl)-1,sum(1<<i for i in range(0,nl,2))):
            slots=[]
            for block in range((nl+2)//3):
                for lane in range(32):
                    leaf=3*block+lane//10
                    if lane>=30 or leaf>=nl or not(mask>>leaf&1):continue
                    slots.extend(leaf*size+j for j in range(lane%10,size,10))
            wanted=[l*size+j for l in range(nl) if mask>>l&1 for j in range(size)]
            assert sorted(slots)==wanted and len(slots)==len(set(slots))
barrier=PACKED.index('__syncthreads()');assert PACKED.index('if(leaf>=3)return')>barrier and PACKED.index('if(nid<0)return')>barrier
assert 'target::hit' in PACKED and 'j+=10' in PACKED and 'leaf_count' in PACKED
try:replace_once('a a','a','b');raise RuntimeError('duplicate anchor admitted')
except AssertionError:pass
p=paired([2.]*6,[1.]*6,c['formal_orders'],'P1','P2',c['primary']['seed']);assert p['paired_geometric_ratio']==2 and p['bootstrap_95']==[2.,2.] and p['decision']=='confirmed_win'
assert c['process_budget']['maximum']==sum(c['process_budget'][k] for k in ('qualification','work','profile','formal'))==48
print('PASS: exact ownership for list lengths 1..19 and ALL leaf sizes 1..20; tails/inactive masks; barrier order; statistics; budget')
