#!/usr/bin/env python3
"""Apply ownership-only overlay to locally supplied pinned author GPU-Tree source."""
import argparse, hashlib, json, shutil
from pathlib import Path
from common import outside_repo
HERE=Path(__file__).resolve().parent

def prepare(upstream, out):
    out=outside_repo(out);assert not out.exists();out.mkdir(parents=True)
    src=upstream/'Source Code/GPU-Tree'
    binding={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (src/'include').glob('*.cuh')}
    assert binding==json.loads((HERE/'UPSTREAM_HEADERS.json').read_text()), 'upstream source identity mismatch'
    shutil.copytree(src/'include',out/'include')
    p=out/'include/search.cuh'; s=p.read_bytes().decode('utf-8',errors='surrogateescape')
    # These owners are shared across calls; release them only with the index.
    for name in ('isSatisfied','tree_num','tree_sum_prefix','node_sum_prefix'):
        old=f'cudaFree({name});';assert s.count(old)==2
        s=s.replace(old,f'#ifndef CLOSURE_REUSE\n        {old}\n#endif')
    # Private query filter arrays have no uses after root compaction completes.
    old='cudaFree(pivot_flag);';assert s.count(old)==2
    s=s.replace(old,old+'\n        cudaFree(tree_filter);\n        cudaFree(tree_filter_prefix);')
    anchor='tree_idx++;\n\t\t\t\tnid = node_sum_prefix[tree_idx];'
    assert s.count(anchor)==1
    s=s.replace(anchor,'tree_idx++;\n#ifdef CLOSURE_TAIL_SAFE\n                if (i + 1 < isSatisfied[bid * PNUM + id])\n#endif\n                nid = node_sum_prefix[tree_idx];')
    p.write_bytes(s.encode('utf-8',errors='surrogateescape'))
    p=out/'include/bplus_tree.cuh';s=p.read_bytes().decode('utf-8',errors='surrogateescape')
    anchor='CHECK(cudaMalloc((void **)&(node_idx), total_tree_num * sizeof(int)));'
    assert s.count(anchor)==1
    s=s.replace(anchor,'closure_capture_nodes(T, total_node_num);\n\t'+anchor)
    p.write_bytes(s.encode('utf-8',errors='surrogateescape'))
    shutil.copyfile(HERE/'tree_service.cu',out/'tree_service.cu')
    (out/'SOURCE.json').write_text(json.dumps(dict(upstream='ZJU-DAILY/GTS@3bac1b725e92e98e3b69d5cb79ad9c56ccb5e639',
        input_headers=binding,output_headers={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (out/'include').glob('*.cuh')},
        adapter_sha256=hashlib.sha256((out/'tree_service.cu').read_bytes()).hexdigest(),configuration=dict(PNUM=8,DNUM=500,M=4),
        native_abi='without CLOSURE_TAIL_SAFE: identical kernels; ownership differs at Host only',
        safe_abi='with CLOSURE_TAIL_SAFE: additionally skip unused next-root load after final iteration; separate identity required'),indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--upstream',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();prepare(a.upstream,a.output)
