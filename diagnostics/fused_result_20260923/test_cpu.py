#!/usr/bin/env python3
"""Minimal no-GPU guard for exact integration and drift rejection."""
from pathlib import Path
from prepare import transform,replace_once
p=Path(__file__).resolve().parent.parent/'graph_query_20260923/graph_bench.cu'
s=p.read_text();t=transform(s)
assert s in [p.read_text()]
assert t.count('fusedResultSelect<<<1,512')==1
assert t.count('getQresultCount<<<1,512')==1
assert 'if(mode=="C"||mode=="E")' in t
assert 'new Fixed(tree_size,tree_h,mode=="D"||mode=="E")' in t
for bad in [s+'\n',s.replace('slots=2220','slots=2221')]:
    try:transform(bad)
    except AssertionError:pass
    else:raise AssertionError('Unpinned comparator admitted')
try:replace_once('xx','x','a')
except AssertionError:pass
else:raise AssertionError('Ambiguous patch accepted')
print('PASS: pinned comparator, one fusion dispatch, graph modes and drift rejection')
