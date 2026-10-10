#!/usr/bin/env python3
"""Bounded, CPU-only source/ownership audit; never certifies CUDA execution."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct

HERE = Path(__file__).resolve().parent
PINS = HERE.parent.parent / 'diagnostics/native_knn_faiss_ivf_20261003/ORIGINAL_SOURCE_PINS.json'


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(8 << 20), b''): h.update(block)
    return h.hexdigest()


def save(path, value):
    with Path(path).open('x') as f: json.dump(value, f, indent=2); f.write('\n')


def load_index(path):
    b = Path(path).read_bytes()
    if len(b) < 16: raise ValueError('truncated header')
    n, d, height, capacity = struct.unpack_from('<4i', b)
    if not (n > 0 and d > 0 and 2 <= height <= 6 and capacity == (10**height-1)//9):
        raise ValueError('unsupported tree identity')
    if len(b) != 16 + 4*n + 24*capacity: raise ValueError('index byte count')
    ids = struct.unpack_from('<' + str(n) + 'i', b, 16)
    start = 16 + 4*n
    nodes = [struct.unpack_from('<ifiii', b, start+20*i) for i in range(capacity)]
    flags = struct.unpack_from('<' + str(capacity) + 'i', b, start+20*capacity)
    if sorted(ids) != list(range(n)): raise ValueError('not an ID permutation')
    if any(x not in (0,1) for x in flags): raise ValueError('invalid occupancy flag')
    coverage = bytearray(n)
    for i, (pid, bound, size, lid, leaf) in enumerate(nodes):
        if flags[i]: continue
        if not (0 <= lid < n and 0 < size <= n-lid and leaf in (0,1)):
            raise ValueError('node extent/leaf flag')
        if i and not 0 <= pid < n: raise ValueError('invalid pivot row')
        if leaf:
            if size > 20: raise ValueError('leaf capacity')
            for j in range(lid, lid+size):
                if coverage[j]: raise ValueError('duplicate leaf ownership')
                coverage[j] = 1
        else:
            children = list(range(10*i+1, 10*i+11))
            if children[-1] >= capacity: raise ValueError('unfinished internal node')
            active = [nodes[j] for j in children if not flags[j]]
            if len(active) != 10 or len({x[0] for x in active}) != 1:
                raise ValueError('incomplete sibling family/pivot')
            end = lid
            for child in active:
                if child[3] != end: raise ValueError('child ownership gap/overlap')
                end += child[2]
            if end != lid+size: raise ValueError('child ownership does not cover parent')
    if any(x != 1 for x in coverage): raise ValueError('missing leaf ownership')
    return n, d, height, ids, nodes, flags


def source_audit(source):
    pins = json.loads(PINS.read_text())
    hashes = {}
    for name, expected in pins['sha256'].items():
        path = source / name.removeprefix('GTS/')
        actual = sha(path)
        if actual != expected: raise ValueError('source drift: '+name)
        hashes[name] = actual
    main = (source/'src/main.cu').read_text()
    body = (source/'include/search_v2.cuh').read_text()
    checks = ['getDisPQ<<<', 'updateDisK<<<', 'nodeProcessKnn<<<',
              'mergeLNodeKnn<<<', 'dataProcessKnn<<<', 'mergeResKnn<<<']
    if 'searchIndexKnnV2(' not in main or any(x not in body for x in checks):
        raise ValueError('entrypoint/call-site identity')
    return dict(upstream_commit=pins['commit'], source_sha256=hashes,
                entrypoint='searchIndexKnnV2', call_sites=checks,
                runtime_call_trace_verified=False,
                arithmetic='upstream FP32 subtraction, pow-based mixed arithmetic; not the proposed RN FP64 score',
                level_policy='skip pivot computation for the first two levels when update_disk is false',
                current_layer_threshold=True, cross_layer_distinct_candidate_state=False,
                pivot_to_leaf_memo=False,
                full_output_upstream=False)


def tree_audit(index):
    n,d,h,ids,nodes,flags = load_index(index)
    levels=[]; start=1
    for level in range(1,h):
        width=10**level
        active=[i for i in range(start,start+width) if not flags[i]]
        pivots=[nodes[i][0] for i in range(start,start+width,10) if not flags[i]]
        levels.append(dict(level=level,nodes=len(active),leaves=sum(nodes[i][4] for i in active),
                           group_pivots=len(pivots),distinct_group_pivots=len(set(pivots)),
                           pivot_rows=pivots))
        start+=width
    queried=[p for x in levels if x['level']>=3 for p in x['pivot_rows']]
    leaf_sizes=Counter(nodes[i][2] for i in range(len(nodes)) if not flags[i] and nodes[i][4])
    return dict(kind='static CPU tree inventory, not runtime traversal',N=n,D=d,height=h,
                capacity=len(nodes),tree_sha256=sha(index),leaf_size_histogram=dict(leaf_sizes),
                complete_unique_leaf_ownership=True,
                queried_pivot_slots_all_regions=len(queried),
                queried_distinct_pivot_rows_all_regions=len(set(queried)),
                pivot_to_pivot_repeats_all_regions=len(queried)-len(set(queried)),
                full_leaf_visit_conditional_saved_distance_fraction=len(queried)/(n+len(queried)),
                denominator='distance invocations with all regions visited; not time, coordinate updates or DRAM bytes',
                levels=[{k:v for k,v in x.items() if k!='pivot_rows'} for x in levels])


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True);p.add_argument('--index',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=False)
    save(a.out/'source.json',source_audit(a.source))
    save(a.out/'tree.json',tree_audit(a.index))
    print('PASS source hashes and exact tree ownership; runtime/correctness/performance NOT verified')


if __name__=='__main__': main()
