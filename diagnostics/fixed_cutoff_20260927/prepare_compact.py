#!/usr/bin/env python3
"""Add a compact unresolved-frontier fallback to the fixed-depth driver."""
import argparse
import importlib.util
from pathlib import Path

HERE=Path(__file__).resolve().parent

def once(s,old,new):
    assert s.count(old)==1,(old,s.count(old))
    return s.replace(old,new)

def render():
    spec=importlib.util.spec_from_file_location('fixed_prepare_compact',HERE/'prepare.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    source,runner=module.render()
    source=once(source,'#include "cutoff_l2.cuh"',
                '#include "cutoff_l2.cuh"\n#include "compact_cutoff.cuh"')
    source=once(source,'    int* node_for_pos=nullptr;\n',
                '    int* node_for_pos=nullptr;\n    int* active=nullptr;\n    int* candidate_positions=nullptr;\n')
    source=once(source,
        'ck(cudaMallocHost(&hi,slots*sizeof(int)));ck(cudaMallocHost(&hd,slots*sizeof(float)));\n        size_t z=0;',
        'ck(cudaMallocHost(&hi,slots*sizeof(int)));ck(cudaMallocHost(&hd,slots*sizeof(float)));\n        if(leaf_mode==4) {alloc(active,n);alloc(candidate_positions,n);}\n        size_t z=0;')
    source=once(source,
        'ck(cub::DeviceScan::InclusiveSum(nullptr,z,is_delete,is_delete_prefix,n,stream));tempbytes=std::max(tempbytes,z);',
        '''ck(cub::DeviceScan::InclusiveSum(nullptr,z,is_delete,is_delete_prefix,n,stream));tempbytes=std::max(tempbytes,z);
        if(leaf_mode==4) {
            cub::CountingInputIterator<int> positions(0);
            ck(cub::DeviceSelect::Flagged(nullptr,z,positions,active,candidate_positions,candidate_count,n,stream));
            tempbytes=std::max(tempbytes,z);
        }''')
    old='''        ck(cudaMemcpyAsync(qid,hq,sizeof(int),cudaMemcpyHostToDevice,stream));
        if(leaf_mode==3) {'''
    new='''        ck(cudaMemcpyAsync(qid,hq,sizeof(int),cudaMemcpyHostToDevice,stream));
        if(leaf_mode==4) {
            initQnode<<<(nodes+511)/512,THREAD_NUM,0,stream>>>(flags,1,max_node_num);
            int start=1,num=TREE_ORDER;
            for(int level=1;level<=stop_depth;++level) {
                l2Walk<true><<<(num+THREAD_NUM-1)/THREAD_NUM,THREAD_NUM,0,stream>>>(
                    flags,start,node_list,radius,data_d,qid,num,max_node_num,data_info,empty_list);
                updatePnodeFlag<<<1,THREAD_NUM,0,stream>>>(flags,start,num,max_node_num,empty_list);
                start+=num;num*=TREE_ORDER;
            }
            frontierFlags<<<(n+511)/512,512,0,stream>>>(n,node_for_pos,flags,active);
            cub::CountingInputIterator<int> positions(0);
            ck(cub::DeviceSelect::Flagged(temp,tempbytes,positions,active,
                candidate_positions,candidate_count,n,stream));
            const float guarded=radius+0.001f;
            const double cutoff=double(guarded)*double(guarded);
            compactL2<<<(n+511)/512,512,0,stream>>>(id_list,data_d,qid,data_info,radius,
                is_delete,candidate_positions,candidate_count,cutoff,hits,rawids,rawdis);
            ck(cub::DeviceScan::InclusiveSum(temp,tempbytes,is_delete,is_delete_prefix,n,stream));
            compactResultSelect<<<1,512,0,stream>>>(candidate_count,n,hits,rawids,rawdis,
                is_delete_prefix,count,outids,outdis);
            ck(cudaMemcpyAsync(hc,count,sizeof(int),cudaMemcpyDeviceToHost,stream));
            ck(cudaMemcpyAsync(hi,outids,slots*sizeof(int),cudaMemcpyDeviceToHost,stream));
            ck(cudaMemcpyAsync(hd,outdis,slots*sizeof(float),cudaMemcpyDeviceToHost,stream));
            ck(cudaGetLastError());return;
        }
        if(leaf_mode==3) {'''
    source=once(source,old,new)
    source=once(source,'if(node_for_pos)ck(cudaFree(node_for_pos));',
                'if(node_for_pos)ck(cudaFree(node_for_pos));\n        if(active)ck(cudaFree(active));\n        if(candidate_positions)ck(cudaFree(candidate_positions));')
    modes='mode=="D1"||mode=="D2"||mode=="D3"||mode=="D4"||mode=="D5"'
    source=source.replace(modes,modes+'||mode=="C1"||mode=="C2"||mode=="C3"||mode=="C4"||mode=="C5"')
    source=once(source,'Q|H|J|F|D1|D2|D3|D4|D5 radius',
                'Q|H|J|F|D1|D2|D3|D4|D5|C1|C2|C3|C4|C5 radius')
    source=once(source,
        'new Fixed(tree_size,tree_h,true,2,true,mode=="Q"?0:(mode=="H"?1:(mode=="J"?2:3)),mode[0]==\'D\'?mode[1]-\'0\':0,&tree,&empty)',
        'new Fixed(tree_size,tree_h,true,2,true,mode=="Q"?0:(mode=="H"?1:(mode=="J"?2:(mode[0]==\'C\'?4:3))),(mode[0]==\'D\'||mode[0]==\'C\')?mode[1]-\'0\':0,&tree,&empty)')
    runner=runner.replace("choices=['Q','H','J','F','D1','D2','D3','D4','D5']",
                          "choices=['Q','H','J','F','D1','D2','D3','D4','D5','C1','C2','C3','C4','C5']")
    return source,runner

def make(out):
    out.mkdir(parents=True,exist_ok=True)
    source,runner=render()
    (out/'graph_bench.cu').write_text(source)
    (out/'run.py').write_text(runner)
    (out/'compact_cutoff.cuh').write_bytes((HERE/'compact_cutoff.cuh').read_bytes())
    for name in ('cutoff_l2.cuh','flat_l2.cuh','leaf_l2.cuh','l2_traversal.cuh','fused_result.cuh'):
        if name=='cutoff_l2.cuh': source_file=HERE/name
        else:
            lookup={'flat_l2.cuh':'flat_scan_l2_20260924',
                    'leaf_l2.cuh':'leaf_early_l2_20260924',
                    'l2_traversal.cuh':'traversal_grid_l2_20260924',
                    'fused_result.cuh':'pca_end_to_end_20260925'}
            source_file=HERE.parent/lookup[name]/name
        (out/name).write_bytes(source_file.read_bytes())

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('out',type=Path);a=p.parse_args();make(a.out)
