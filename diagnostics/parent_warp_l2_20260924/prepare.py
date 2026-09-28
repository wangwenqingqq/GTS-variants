#!/usr/bin/env python3
"""Compose the pinned grid/count driver with warp-per-parent pivot reuse."""
import argparse
import importlib.util
from pathlib import Path

HERE=Path(__file__).resolve().parent

def once(text,old,new):
    assert text.count(old)==1,(old,text.count(old))
    return text.replace(old,new)

def base():
    path=HERE.parent/'traversal_count_combo_20260924/prepare.py'
    spec=importlib.util.spec_from_file_location('traversal_count_prepare',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.render()

def render():
    source,runner=base()
    source=once(source,'#include "l2_traversal.cuh"',
                '#include "l2_traversal.cuh"\n#include "warp_parent.cuh"')
    old='''            } else {
                l2Walk<true><<<(num+THREAD_NUM-1)/THREAD_NUM,THREAD_NUM,0,stream>>>(flags,start,node_list,radius,data_d,qid,num,max_node_num,data_info,empty_list);
            }'''
    new='''            } else if(traversal == 2) {
                l2Walk<true><<<(num+THREAD_NUM-1)/THREAD_NUM,THREAD_NUM,0,stream>>>(flags,start,node_list,radius,data_d,qid,num,max_node_num,data_info,empty_list);
            } else {
                warpParentL2<<<(num/TREE_ORDER+7)/8,256,0,stream>>>(flags,start,node_list,radius,data_d,qid,num,data_info,empty_list);
            }'''
    source=once(source,old,new)
    source=once(source,'E|P|R|Q radius','E|P|R|Q|W radius')
    source=once(source,'mode=="E"||mode=="P"||mode=="R"||mode=="Q") &&',
                'mode=="E"||mode=="P"||mode=="R"||mode=="Q"||mode=="W") &&')
    source=once(source,'(mode=="E"||mode=="R")?0:2,mode=="R"||mode=="Q"',
                '(mode=="E"||mode=="R")?0:(mode=="W"?3:2),mode=="R"||mode=="Q"||mode=="W"')
    source=once(source,'if(mode=="E"||mode=="P"||mode=="R"||mode=="Q")',
                'if(mode=="E"||mode=="P"||mode=="R"||mode=="Q"||mode=="W")')
    source=once(source,'mode=="E"||mode=="P"||mode=="R"||mode=="Q");count=*fixed->hc;',
                'mode=="E"||mode=="P"||mode=="R"||mode=="Q"||mode=="W");count=*fixed->hc;')
    marker='    assert(std::all_of(cover.begin(),cover.end(),[](int x){return x==1;}));'
    source=once(source,marker,marker+'''
    for(size_t parent=0; parent*TREE_ORDER+1<tree.size(); ++parent) {
        int sibling_pid=-1;
        for(int child=1; child<=TREE_ORDER && parent*TREE_ORDER+child<tree.size(); ++child) {
            size_t nid=parent*TREE_ORDER+child;
            if(empty[nid]) continue;
            if(sibling_pid<0) sibling_pid=tree[nid].pid;
            else assert(sibling_pid==tree[nid].pid);
        }
    }''')
    runner=runner.replace("choices=['E','P','R','Q']","choices=['E','P','R','Q','W']")
    return source,runner

def make(out):
    out.mkdir(parents=True,exist_ok=True)
    source,runner=render()
    (out/'graph_bench.cu').write_text(source)
    (out/'l2_traversal.cuh').write_bytes((HERE.parent/'traversal_grid_l2_20260924/l2_traversal.cuh').read_bytes())
    (out/'warp_parent.cuh').write_bytes((HERE/'warp_parent.cuh').read_bytes())
    (out/'run.py').write_text(runner)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('out',type=Path);a=p.parse_args();make(a.out)
