#!/usr/bin/env python3
"""Generate exact fixed-depth tree-prefix plus flat-fallback experiment."""
import argparse
import importlib.util
from pathlib import Path

HERE=Path(__file__).resolve().parent

def once(s,old,new):
    assert s.count(old)==1,(old,s.count(old))
    return s.replace(old,new)

def render():
    path=HERE.parent/'flat_scan_l2_20260924/prepare.py'
    spec=importlib.util.spec_from_file_location('flat_prepare_cutoff',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    source,runner=module.render()
    source=once(source,'#include "flat_l2.cuh"',
                '#include "flat_l2.cuh"\n#include "cutoff_l2.cuh"')
    source=once(source,'    int leaf_mode;\n',
                '    int leaf_mode;\n    int stop_depth;\n    int* node_for_pos=nullptr;\n')
    source=once(source,
        'int t=0,bool skip=false,int lm=0):fused(f),traversal(t),skip_dead_count(skip),leaf_mode(lm),',
        'int t=0,bool skip=false,int lm=0,int sd=0,const std::vector<TN>* host_tree=nullptr,const std::vector<int>* host_empty=nullptr):fused(f),traversal(t),skip_dead_count(skip),leaf_mode(lm),stop_depth(sd),')
    old='''        ck(cudaMemset(outids,0,slots*sizeof(int)));ck(cudaMemset(outdis,0,slots*sizeof(float)));
    }
    void enqueue(float radius) {'''
    new='''        ck(cudaMemset(outids,0,slots*sizeof(int)));ck(cudaMemset(outdis,0,slots*sizeof(float)));
        if(stop_depth>0) {
            assert(host_tree && host_empty && stop_depth<height);
            int first=0, width=1;
            for(int level=0;level<stop_depth;++level) { first+=width; width*=TREE_ORDER; }
            assert(first+width<=int(host_tree->size()));
            std::vector<int> mapping(n,-1);
            for(int nid=first;nid<first+width;++nid) {
                if((*host_empty)[nid]!=0)continue;
                const TN& node=(*host_tree)[nid];
                assert(node.lid>=0 && node.size>0 && node.lid+node.size<=n);
                for(int pos=node.lid;pos<node.lid+node.size;++pos) {
                    assert(mapping[pos]==-1);mapping[pos]=nid;
                }
            }
            assert(std::all_of(mapping.begin(),mapping.end(),[](int nid){return nid>=0;}));
            alloc(node_for_pos,n);
            ck(cudaMemcpyAsync(node_for_pos,mapping.data(),n*sizeof(int),cudaMemcpyHostToDevice,stream));
            ck(cudaStreamSynchronize(stream));
        }
    }
    void enqueue(float radius) {'''
    source=once(source,old,new)
    old='''        if(leaf_mode==3) {
            const float guarded=radius+0.001f;
            const double cutoff=double(guarded)*double(guarded);
            flatL2<<<(n+511)/512,512,0,stream>>>(id_list,data_d,qid,data_info,radius,
                is_delete,n,cutoff,hits,rawids,rawdis);'''
    new='''        if(leaf_mode==3) {
            if(stop_depth>0) {
                initQnode<<<(nodes+511)/512,THREAD_NUM,0,stream>>>(flags,1,max_node_num);
                int start=1, num=TREE_ORDER;
                for(int level=1;level<=stop_depth;++level) {
                    l2Walk<true><<<(num+THREAD_NUM-1)/THREAD_NUM,THREAD_NUM,0,stream>>>(
                        flags,start,node_list,radius,data_d,qid,num,max_node_num,data_info,empty_list);
                    updatePnodeFlag<<<1,THREAD_NUM,0,stream>>>(flags,start,num,max_node_num,empty_list);
                    start+=num;num*=TREE_ORDER;
                }
            }
            const float guarded=radius+0.001f;
            const double cutoff=double(guarded)*double(guarded);
            if(stop_depth==0)
                flatL2<<<(n+511)/512,512,0,stream>>>(id_list,data_d,qid,data_info,radius,
                    is_delete,n,cutoff,hits,rawids,rawdis);
            else
                cutoffL2<<<(n+511)/512,512,0,stream>>>(id_list,data_d,qid,data_info,radius,
                    is_delete,n,cutoff,node_for_pos,flags,hits,rawids,rawdis);'''
    source=once(source,old,new)
    source=once(source,
        'if(executable)ck(cudaGraphExecDestroy(executable));if(graph)ck(cudaGraphDestroy(graph));',
        'if(executable)ck(cudaGraphExecDestroy(executable));if(graph)ck(cudaGraphDestroy(graph));\n        if(node_for_pos)ck(cudaFree(node_for_pos));')
    modes='mode=="Q"||mode=="H"||mode=="J"||mode=="F"'
    extended=modes+'||mode=="D1"||mode=="D2"||mode=="D3"||mode=="D4"||mode=="D5"'
    source=source.replace(modes,extended)
    source=once(source,'Q|H|J|F radius','Q|H|J|F|D1|D2|D3|D4|D5 radius')
    source=once(source,
        'new Fixed(tree_size,tree_h,true,2,true,mode=="Q"?0:(mode=="H"?1:(mode=="J"?2:3)))',
        'new Fixed(tree_size,tree_h,true,2,true,mode=="Q"?0:(mode=="H"?1:(mode=="J"?2:3)),mode[0]==\'D\'?mode[1]-\'0\':0,&tree,&empty)')
    runner=runner.replace("choices=['Q','H','J','F']",
                          "choices=['Q','H','J','F','D1','D2','D3','D4','D5']")
    return source,runner

def make(out):
    out.mkdir(parents=True,exist_ok=True)
    source,runner=render()
    (out/'graph_bench.cu').write_text(source)
    (out/'run.py').write_text(runner)
    (out/'cutoff_l2.cuh').write_bytes((HERE/'cutoff_l2.cuh').read_bytes())
    for name,directory in [('flat_l2.cuh','flat_scan_l2_20260924'),
                           ('leaf_l2.cuh','leaf_early_l2_20260924'),
                           ('l2_traversal.cuh','traversal_grid_l2_20260924'),
                           ('fused_result.cuh','pca_end_to_end_20260925')]:
        (out/name).write_bytes((HERE.parent/directory/name).read_bytes())

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('out',type=Path);a=p.parse_args();make(a.out)
