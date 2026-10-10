#!/usr/bin/env python3
"""Read-only tracing overlay for the exact retained GPU-Tree R2 adapter."""
import argparse, hashlib, json, shutil, sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
from common import outside_repo

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def once(s,old,new):
    assert s.count(old)==1,(old,s.count(old))
    return s.replace(old,new)

def prepare(source,out):
    out=outside_repo(out)
    assert sha(source/'SOURCE.json')=='927ab4fcac69b7c28bee4874716292dc47a6533d9322717f6be0dd347008bb93'
    manifest=json.loads((source/'SOURCE.json').read_text())
    assert manifest['input_headers']==json.loads((HERE.parent/'UPSTREAM_HEADERS.json').read_text())
    assert manifest['output_headers']=={p.name:sha(p) for p in (source/'include').glob('*.cuh')}
    assert sha(source/'tree_service.cu')==manifest['adapter_sha256']
    assert manifest['output_headers']['search.cuh']=='f761c6282945c82e72a415e097021e5e8e195d16cf6fe58afd7c706f9a5e4dd7'
    shutil.copytree(source,out)
    shutil.copyfile(HERE/'trace.cuh',out/'include/trace.cuh')
    p=out/'include/search.cuh';s=p.read_bytes().decode('utf-8',errors='surrogateescape')
    s=once(s,'#include "config.cuh"','#include "config.cuh"\n#include "trace.cuh"')
    # Read-only traversal observations in both bound selection and full search.
    for func,end,queue,tag in [('searchKnnD','// Get low bounds','idx','SEARCH'),('getKnnBound','// Compute info','bid','BOUND')]:
        a=s.index('__global__ void '+func);b=s.index(end,a);part=s[a:b]
        old=f'popPQ(pq_c[{queue}], node_temp, dis_temp, id_temp);'
        code=f'if(trace_call_d==0)printf("TRACE {tag}_POP %d %d %.9g %.9g %d\\n",{queue},node_temp->idx[0],double(dis_temp),double(dis_k),pq_a[{queue}]->size_k);'
        part=once(part,old,old+'\n'+code)
        old=f'if (dis <= dis_k || (!isFullPQK(pq_a[{queue}])))'
        code=f'if(trace_call_d==0)printf("TRACE {tag}_LEAF %d %d %.9g %.9g %d\\n",{queue},data_id,double(dis),double(dis_k),pq_a[{queue}]->size_k);'
        part=once(part,old,code+'\n'+old)
        old='// Save result'
        code=f'if(trace_call_d==0)printf("TRACE {tag}_DIST %d %d %.9g %.9g %d\\n",{queue},data_id,double(result),double(dis_k),pq_a[{queue}]->size_k);'
        part=once(part,old,code+'\n'+old)
        s=s[:a]+part+s[b:]
    a=s.index('void search(');front=s[:a];body=s[a:]
    # Observe only after the author's existing synchronization boundaries.
    def after_launch(body,name,code):
        a=body.index(name+'<<<');b=body.index('cudaDeviceSynchronize();',a)+len('cudaDeviceSynchronize();')
        return body[:b]+'\n'+code+'\n'+body[b:]
    for name,code in [
        ('getPivotDis','trace_array("PIVOT",dis_pivot,PNUM);'),
        ('getDisBound','trace_array("LB",dis_lb,PNUM);trace_array("UB",dis_ub,PNUM);'),
        ('pivotFilterKnn','trace_array("PART_FIRST",isSatisfied,PNUM);'),
        ('getKnnBound','trace_array("BOUND",knn_bound,1);'),
        ('pivotFilterKnnAgain','trace_array("PART_FINAL",isSatisfied,PNUM);'),
        ('mergeRoot','trace_array("ROOT_BEFORE",root_idx,total_c);trace_array("PIVOT_BEFORE",pivot_flag,total_c);'),
        ('treeFilterKnn','trace_array("TREE_FLAGS",tree_filter,total_c);'),
        ('mergeTree','trace_array("ROOT_AFTER",root_idx_f,total_c_f);trace_array("PIVOT_AFTER",pivot_flag_f,total_c_f);'),
        ('searchKnnD','trace_heaps<<<1,1>>>(pq_a,total_c_f);trace_check(cudaDeviceSynchronize());'),
        ('mergeKnn','trace_array("MERGE_IDS",id_knn,total_c_f*k);trace_array("MERGE_DIST",dis_knn,total_c_f*k);')]:
        body=after_launch(body,name,code)
    assert body.count('cudaFree(root_idx_f);')==2
    body=body.replace('cudaFree(root_idx_f);','trace_array("SORT_IDS",id_knn,total_c_f*k);\n\t\tcudaFree(root_idx_f);',1)
    p.write_bytes((front+body).encode('utf-8',errors='surrogateescape'))
    p=out/'tree_service.cu';s=p.read_text()
    old='getIndex(root,part,object,total_nodes,trees,tree_prefix,total_trees,nodes,node_prefix);ck(cudaDeviceSynchronize());'
    s=once(s,old,old+'\n        trace_topology<<<1,1>>>(root,node_prefix,tree_prefix,trees);ck(cudaDeviceSynchronize());')
    old='qid[0]=row;';s=once(s,old,'++trace_call;ck(cudaMemcpyToSymbol(trace_call_d,&trace_call,sizeof(int)));'+old)
    s=once(s,'PNUM=8;', 'ck(cudaDeviceSetLimit(cudaLimitPrintfFifoSize,32<<20));PNUM=8;')
    p.write_text(s)
    (out/'TRACE_SOURCE.json').write_text(json.dumps(dict(parent=manifest,sources={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file()},overlay={p.name:sha(p) for p in HERE.iterdir() if p.is_file()}),indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('output',type=Path);a=p.parse_args();assert __debug__;prepare(a.source,a.output)
