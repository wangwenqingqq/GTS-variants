#!/usr/bin/env python3
"""Generate independent ablations from pinned external source; no GPU calls."""
import argparse
import hashlib
import importlib.util
from pathlib import Path
import shutil
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('fusion_prepare', HERE.parent/'fused_result_20260923/prepare.py')
base = importlib.util.module_from_spec(spec); spec.loader.exec_module(base)
once = base.replace_once


def function(source, name):
    start = source.index('__global__ void '+name+'(')
    opening = source.index('{', start)
    depth = 1; end = opening+1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}'); end += 1
    return source[start:end].replace('short *', 'float *')


def kernels(source):
    assert hashlib.sha256(source.encode()).hexdigest() == 'b7e717a2d5b27acbfb860f28a26696d283b00a75d06de2d32128ae975627080a'
    walk = function(source, 'findNextRnn')
    args = walk[walk.index('(')+1:walk.index(')')]
    distance = walk[walk.index('float dis_q = 0;'):walk.index('float dis_lb =')]
    predicate = walk[walk.index('float dis_lb ='):walk.rindex('\n\t\t}')]
    inline = once(walk, '__global__ void findNextRnn', 'template<bool Count> __device__ __forceinline__ void inlineWalk')
    inline = once(inline, 'int *size_s)', 'int *size_s, int *work)')
    inline = once(inline, 'float dis_q = 0;', 'if constexpr (Count) atomicAdd(work, 1);\n            float dis_q = 0;')
    init = function(source, 'initQnode').replace('__global__ void initQnode', '__device__ __forceinline__ void inlineInit')
    clear = function(source, 'updatePnodeFlag').replace('__global__ void updatePnodeFlag', '__device__ __forceinline__ void inlineClear')
    call = 'query_node_list, start_idx, node_list, r, data_d, qid_list, node_num, max_node_num, data_info, empty_list, data_s, size_s'
    return '#pragma once\n'+init+'\n'+clear+'\n'+inline+'\n'+f'''
// Counter variants are instantiated only by the diagnostic executable.
template<bool Count>
__global__ void auditLevel({args}, int *work) {{
    inlineWalk<Count>({call}, work);
}}

template<bool Count>
__global__ void fusedTraversal({args}, int height, int *work) {{
    inlineInit(query_node_list, 1, max_node_num);
    __syncthreads();
    for(int level=1; level<height; ++level) {{
        inlineWalk<Count>({call}, work);
        // Finish every read of the old parents before any lane clears one.
        __syncthreads();
        inlineClear(query_node_list, start_idx, node_num, max_node_num, empty_list);
        __syncthreads();
        start_idx += node_num; node_num *= TREE_ORDER;
    }}
}}

template<bool Count>
__global__ void dedupLevel({args}, int *work) {{
    // Bounded H=3 comparator: at most ten parent groups in this level.
    __shared__ float parent_dis[10];
    int tid=threadIdx.x, query_id=blockIdx.x;
    for(int group=tid; group<node_num/TREE_ORDER; group+=blockDim.x) {{
        int first=start_idx+group*TREE_ORDER;
        int parent=(first-1)/TREE_ORDER;
        if(query_node_list[query_id*max_node_num[0]+parent] != 1) continue;
        int nid=first;
        while(nid<first+TREE_ORDER && empty_list[nid]!=0) ++nid;
        if(nid==first+TREE_ORDER) continue;
        TN node=node_list[nid];
        if constexpr (Count) atomicAdd(work, 1);
        {distance}
        parent_dis[group]=dis_q;
    }}
    __syncthreads();
    for(int i=tid; i<node_num; i+=blockDim.x) {{
        int nid=start_idx+i, nid_parent=(nid-1)/TREE_ORDER;
        if(query_node_list[query_id*max_node_num[0]+nid_parent]==1 && empty_list[nid]==0) {{
            TN node=node_list[nid];
            float dis_q=parent_dis[i/TREE_ORDER];
            {predicate}
        }}
    }}
}}
'''


def transform(text):
    text = base.transform(text)
    text = once(text, '#include "fused_result.cuh"', '#include "fused_result.cuh"\n#include "traversal_generated.cuh"')
    text = once(text, 'bool fused;', 'bool fused;\n    int traversal;')
    text = once(text, 'Fixed(int count_n,int h,bool f=false):fused(f),n(count_n),height(h)',
                'Fixed(int count_n,int h,bool f=false,int t=0):fused(f),traversal(t),n(count_n),height(h)')
    start = '        initQnode<<<1,THREAD_NUM,0,stream>>>(flags,1,max_node_num);'
    end = '        ck(cub::DeviceReduce::Sum(temp,tempbytes,flags,candidate_count,nodes,stream));'
    old = text[text.index(start):text.index(end)]
    call = 'flags,start,node_list,radius,data_d,qid,num,max_node_num,data_info,empty_list,data_s,size_s'
    changed = once(old, '            findNextRnn<<<1,THREAD_NUM,0,stream>>>('+call+');',
                   '            if(traversal==2) dedupLevel<false><<<1,THREAD_NUM,0,stream>>>('+call+',nullptr);\n'
                   '            else findNextRnn<<<1,THREAD_NUM,0,stream>>>('+call+');')
    text = once(text, old, '''        if(traversal==1) {
            fusedTraversal<false><<<1,THREAD_NUM,0,stream>>>(flags,1,node_list,radius,data_d,qid,10,max_node_num,data_info,empty_list,data_s,size_s,height,nullptr);
        } else {
'''+changed+'        }\n')
    text = once(text, 'new Fixed(tree_size,tree_h,mode=="D"||mode=="E")',
                'new Fixed(tree_size,tree_h,mode!="B"&&mode!="C",(mode=="F"||mode=="G")?1:((mode=="P"||mode=="Q")?2:0))')
    text = once(text, 'mode=="A"||mode=="B"||mode=="C"||mode=="D"||mode=="E"',
                'mode=="A"||mode=="B"||mode=="C"||mode=="D"||mode=="E"||mode=="F"||mode=="G"||mode=="P"||mode=="Q"')
    text = text.replace('mode=="C"||mode=="E")', 'mode=="C"||mode=="E"||mode=="F"||mode=="P")')
    text = text.replace('A|B|C|D|E radius', 'A|B|C|D|E|F|G|P|Q radius')
    text = once(text, 'int main(int argc,char** argv)', '#ifndef GTS_ABLATION_NO_MAIN\nint main(int argc,char** argv)')+'\n#endif\n'
    marker = '    for(auto node:tree)if(node.is_leaf==1)assert(node.size<=20);'
    text = once(text, marker, marker+'''
    std::vector<int> empty(111);ck(cudaMemcpy(empty.data(),empty_list,111*sizeof(int),cudaMemcpyDeviceToHost));
    for(int parent=0;parent<11;++parent) {
        int pivot=-1;
        for(int nid=parent*10+1;nid<=parent*10+10;++nid)if(!empty[nid]) {
            if(pivot<0)pivot=tree[nid].pid; else assert(pivot==tree[nid].pid);
        }
    }''')
    return text


def prepare(source, fixtures, out):
    base.prepare(source, fixtures, out)
    original = (HERE.parent/'graph_query_20260923/graph_bench.cu').read_text()
    (out/'graph_bench.cu').write_text(transform(original))
    (out/'traversal_generated.cuh').write_text(kernels((out/'source/include/search.cuh').read_text()))
    for name in ['test_traversal.cu', 'suite.py']: shutil.copy2(HERE/name, out/name)
    runner = (out/'run_fusion.py').read_text()
    runner = runner.replace('test_selector', 'test_traversal').replace("mode=='T'", "mode=='V'")
    runner = runner.replace("'D','E','T'", "'D','E','F','G','P','Q','V'")
    runner = runner.replace('expected_selector.json', 'expected_traversal.json')
    runner = runner.replace('PASS selector 132 cases', 'PASS traversal 352 cases')
    runner = runner.replace('selector regression', 'traversal regression').replace('selector check', 'traversal check')
    runner = once(runner, "cmd=[str(root/'bin/test_traversal')]", "cmd=[str(root/'bin/test_traversal'),str(root/'fixtures/words_2000.txt'),str(root/'fixtures/queries.qid')]")
    (out/'run_ablation.py').write_text(runner)
    # Old expected hashes are deliberately re-admitted by independent full checks.
    for p in (out/'fixtures').glob('expected_*.json'): p.unlink()
    print('Prepared separate F and P candidates; original and inherited source preserved')


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['source','fixtures','out']: p.add_argument(name,type=Path)
    a=p.parse_args(); prepare(a.source,a.fixtures,a.out)
