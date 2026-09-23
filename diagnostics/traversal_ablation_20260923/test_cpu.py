#!/usr/bin/env python3
"""No-GPU regression: exact comparator, separate dispatch, balanced orders."""
from pathlib import Path
from prepare import transform
from suite import ORDERS,MODES,TOOLS,expected_tool
p=Path(__file__).resolve().parent.parent/'graph_query_20260923/graph_bench.cu'
s=p.read_text();t=transform(s)
assert t.count('fusedTraversal<false><<<')==1
assert t.count('dedupLevel<false><<<')==1
assert t.count('findNextRnn<<<')==1
assert t.count('fusedResultSelect<<<')==1
assert 'mode=="C"||mode=="E"||mode=="F"||mode=="P")' in t
assert 'mode!="B"&&mode!="C"' in t
for order in ORDERS:assert set(order)==set(MODES) and len(order)==6
for a,b in ['EF','EP','DG','DQ']:
    assert sum(o.index(a)<o.index(b) for o in ORDERS)==3
for tool in TOOLS:
    assert expected_tool('gate_'+tool+'_F')==tool
    assert expected_tool('traversal_'+tool)==tool
assert expected_tool('nsys_F')=='nsys-node'
assert expected_tool('stress_P')=='clean'
for bad in [s+'\n',s.replace('slots=2220','slots=2221')]:
    try:transform(bad)
    except AssertionError:pass
    else:raise AssertionError('Source drift admitted')
print('PASS pinned comparator, independent F/P dispatch, common result path, balanced orders')
