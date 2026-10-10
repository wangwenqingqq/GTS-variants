#!/usr/bin/env python3
"""CPU-only identity, partition, pivot-alias and arithmetic-opportunity audit."""
import argparse
import array
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct

def audit(path):
    raw=path.read_bytes();n,d,h,c=struct.unpack_from('<4i',raw)
    assert 1<=n<=1000000 and d in (96,960) and 3<=h<=6
    assert len(raw)==16+4*n+24*c
    ids=array.array('i');ids.frombytes(raw[16:16+4*n])
    assert sorted(ids)==list(range(n))
    off=16+4*n
    nodes=list(struct.iter_unpack('<ifiii',raw[off:off+20*c]))
    flags=array.array('i');flags.frombytes(raw[off+20*c:])
    leaves=sorted((x[3],x[2]) for x,f in zip(nodes,flags) if f==0 and x[4])
    position=0
    for lid,size in leaves:
        assert lid==position and 0<size<=20
        position+=size
    assert position==n
    rows=[];evaluated=[];start=1
    for level in range(1,h):
        width=10**level;assert start+width<=c
        pivots=[]
        for nid in range(start,start+width,10):
            if flags[nid]:continue
            pid=nodes[nid][0];assert 0<=pid<n
            assert all(flags[i] or nodes[i][0]==pid for i in range(nid,nid+10))
            pivots.append(pid)
        rows.append({'level':level,'nonempty_groups':len(pivots),'unique_object_ids':len(set(pivots)),
                     'same_level_aliases':len(pivots)-len(set(pivots))})
        if level>2:evaluated+=pivots
        start+=width
    counts=Counter(evaluated)
    return {'index_sha256':hashlib.sha256(raw).hexdigest(),'N':n,'D':d,'height':h,'allocated_nodes':c,
            'leaf_count':len(leaves),'complete_id_permutation':True,'exact_disjoint_leaf_partition':True,
            'levels':rows,'evaluated_pivot_groups_if_all_live':len(evaluated),
            'unique_evaluated_objects':len(counts),'cross_level_repetitions':len(evaluated)-len(counts),
            'duplicate_object_ids':{str(k):v for k,v in counts.items() if v>1},
            'arithmetic_opportunity_no_pruning':len(evaluated)/(n+len(evaluated)),
            'scope':'Static structural screen, not active-query counts or measured latency'}

def warp_screen(path):
    """Post-collection cache-coverage bound; never a dynamic SASS count."""
    audit(path)
    raw=path.read_bytes();n,d,h,c=struct.unpack_from('<4i',raw);off=16+4*n
    ids=struct.unpack_from(f'<{n}i',raw,16)
    nodes=list(struct.iter_unpack('<ifiii',raw[off:off+20*c]))
    flags=struct.unpack_from(f'<{c}i',raw,off+20*c);pivots=set();start=1
    for level in range(1,h):
        width=10**level
        if level>2:pivots.update(nodes[i][0] for i in range(start,start+width,10) if not flags[i])
        start+=width
    sizes=Counter();misses=Counter();maxcached=0
    for node,flag in zip(nodes,flags):
        if not flag and node[4]:
            missing=sum(i not in pivots for i in ids[node[3]:node[3]+node[2]])
            sizes[node[2]]+=1;misses[missing]+=1;maxcached=max(maxcached,node[2]-missing)
    return {'scope':'Post-collection CPU-only static index bound, not dynamic SASS counters',
            'index_sha256':hashlib.sha256(raw).hexdigest(),'unique_evaluated_pivot_objects':len(pivots),
            'leaf_sizes':dict(sizes),'nonpivot_objects_per_leaf':dict(misses),
            'max_evaluated_pivots_in_one_leaf':maxcached,
            'leaves_with_at_most_one_nonpivot':sum(v for k,v in misses.items() if k<=1),
            'boundary':'The self-distance shortcut skips at most one remaining object; no dynamic instruction reduction is claimed from this static bound.'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('index',type=Path);p.add_argument('out',type=Path)
    p.add_argument('--warp-screen',action='store_true',help='Post-collection static leaf cache-coverage bound')
    a=p.parse_args();assert not a.out.exists();a.out.write_text(json.dumps((warp_screen if a.warp_screen else audit)(a.index),indent=2)+'\n')
