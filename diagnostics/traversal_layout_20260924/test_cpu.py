#!/usr/bin/env python3
"""Source composition and scheduling checks, explicitly not CUDA validation."""
import argparse
import itertools
import tempfile
import subprocess
from pathlib import Path
from prepare import HERE, GRAPH, STREAM, ORDERS, driver, kernels, layout, traversal, suite, runner, verifier, prepare

p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);a=p.parse_args()
source=(a.source/'GTS/include/search.cuh').read_text()
k=kernels(source)
assert k.startswith(traversal.kernels(source).split('template<bool Count>\n__global__ void dedupLevel')[0])
walk=layout.kernel(source).removeprefix('#pragma once\n#include "layout_index.cuh"\n').replace('__global__ void findNextLayout','__device__ __forceinline__ void inlineWalkLayout')
assert walk in k
assert k.count('__syncthreads();')==6
assert 'dedupLevel' not in k and k.count('size_s, pids, lower, packed);')==1
text=(HERE.parent/'graph_query_20260923/graph_bench.cu').read_text()
d=driver(text);old=layout.driver(text)
start='        ck(cub::DeviceReduce::Sum(temp,tempbytes,flags,candidate_count,nodes,stream));'
end='    double capture('
assert d[d.index(start):d.index(end)]==old[old.index(start):old.index(end)]
assert d.count('fusedTraversalLayout<2><<<')==d.count('fusedTraversalLayout<3><<<')==1
assert 'new Fixed(tree_size,tree_h,true,lm' in d
for left,right in itertools.combinations(GRAPH,2):
    assert sum(order.index(left)<order.index(right) for order in ORDERS)==2
ns={};exec(compile(suite(),'suite','exec'),ns)
radii=dict(empty=-1,zero=0,normal=1,all=10)
assert len(ns['plan']('full',radii))==51
assert len(ns['plan']('gates',radii))==36
assert len(ns['plan']('stress',radii))==12
assert len(ns['plan']('screen',radii))==24
assert len(ns['plan']('sustained',radii))==12
assert len(ns['plan']('trace',radii))==6
assert sum(row[6] for row in ns['plan']('gates',radii))==4
for mode in GRAPH+STREAM:
    assert all(any(row[1]==mode and row[2]==radius for row in ns['plan']('full',radii)) for radius in radii.values())
compile(runner((HERE.parent/'graph_query_20260923/run.py').read_text()),'runner','exec')
compile(verifier(),'verifier','exec')
with tempfile.TemporaryDirectory() as td:
    out=Path(td)/'prepared';prepare(a.source,out)
    assert (out/'graph_bench.cu').read_text()==d
    assert (out/'traversal_layout_generated.cuh').read_text()==k
    assert (out/'CONTRACT.md').read_bytes()==(HERE/'CONTRACT.md').read_bytes()
subprocess.run(['python3',str(layout.HERE/'test_cpu.py'),'--source',str(a.source)],check=True)
print('PASS composition, unchanged distance/downstream code, all six mode pairs, balanced orders and plan; NO CUDA validation')
