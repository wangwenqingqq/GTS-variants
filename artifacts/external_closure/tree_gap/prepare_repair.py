#!/usr/bin/env python3
"""Minimal admissible-bound repair on top of the separately identified tail-safe adapter."""
import argparse,json,shutil
from pathlib import Path
from prepare_trace import sha,once,HERE,outside_repo

def repair_text(s):
    # A maximum over fewer than K answers is not a kth-distance upper bound.
    assert s.count('dis_k = dis_res;')==2
    for name,end,owner in [('searchKnnD','// Get low bounds','idx'),('getKnnBound','// Compute info','bid')]:
        a=s.index('__global__ void '+name);b=s.index(end,a);part=s[a:b]
        part=once(part,'dis_k = dis_res;',f'if (isFullPQK(pq_a[{owner}])) dis_k = dis_res;')
        if owner=='bid':
            part=once(part,'float dis_k = 99999;','float dis_k = CUDART_INF_F;')
            part=once(part,'knn_bound[bid] = dis_res;','knn_bound[bid] = isFullPQK(pq_a[bid]) ? dis_res : CUDART_INF_F;')
        s=s[:a]+part+s[b:]
    return once(s,'#include "config.cuh"','#include "config.cuh"\n#include <math_constants.h>')

def prepare(source,out):
    out=outside_repo(out)
    assert sha(source/'SOURCE.json')=='2ae6127690744f640ae7149d95c281321ce2a6f9a4d325147b8279baecef9c6d'
    manifest=json.loads((source/'SOURCE.json').read_text())
    assert manifest['input_headers']==json.loads((HERE.parent/'UPSTREAM_HEADERS.json').read_text())
    assert manifest['output_headers']=={p.name:sha(p) for p in (source/'include').glob('*.cuh')}
    assert sha(source/'tree_service.cu')==manifest['adapter_sha256']
    assert '#ifdef CLOSURE_TAIL_SAFE' in (source/'include/search.cuh').read_text(errors='surrogateescape')
    shutil.copytree(source,out)
    p=out/'include/search.cuh';s=p.read_bytes().decode('utf-8',errors='surrogateescape');p.write_bytes(repair_text(s).encode('utf-8',errors='surrogateescape'))
    (out/'REPAIR_SOURCE.json').write_text(json.dumps(dict(identity='GPU_TREE_SAFE_KBOUND_ADAPT',parent=manifest,scope='Do not tighten a kth-distance bound until K occurrences have been collected; native queues, traversal, partitioning and full output remain',sources={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file()},overlay_sha256=sha(__file__)),indent=2)+'\n')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('output',type=Path);a=p.parse_args();assert __debug__;prepare(a.source,a.output)
