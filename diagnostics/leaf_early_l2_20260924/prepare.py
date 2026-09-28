#!/usr/bin/env python3
"""Compose the pinned Q driver with isolated specialized and early-exit leaf paths."""
import argparse
import importlib.util
from pathlib import Path

HERE=Path(__file__).resolve().parent

def once(text,old,new):
    assert text.count(old)==1,(old,text.count(old))
    return text.replace(old,new)

def base():
    path=HERE.parent/'traversal_count_combo_20260924/prepare.py'
    spec=importlib.util.spec_from_file_location('traversal_count_prepare_leaf',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.render()

def render():
    source,runner=base()
    source=once(source,'#include "l2_traversal.cuh"',
                '#include "l2_traversal.cuh"\n#include "leaf_l2.cuh"')
    source=once(source,'    bool skip_dead_count;\n',
                '    bool skip_dead_count;\n    int leaf_mode;\n')
    source=once(source,'int t=0,bool skip=false):fused(f),traversal(t),skip_dead_count(skip),',
                'int t=0,bool skip=false,int lm=0):fused(f),traversal(t),skip_dead_count(skip),leaf_mode(lm),')
    old='''        leafProcessRnnUpdate<<<nodes,512,0,stream>>>(candidates,node_list,id_list,queryids,data_d,qid,
            rawids,rawdis,data_info,radius,hits,candidate_count,data_s,size_s,is_delete);'''
    new='''        if(leaf_mode==0) {
            leafProcessRnnUpdate<<<nodes,512,0,stream>>>(candidates,node_list,id_list,queryids,data_d,qid,
                rawids,rawdis,data_info,radius,hits,candidate_count,data_s,size_s,is_delete);
        } else {
            const float guarded=radius+0.001f;
            const double cutoff=double(guarded)*double(guarded);
            if(leaf_mode==1) leafL2<false><<<nodes,512,0,stream>>>(candidates,node_list,id_list,queryids,data_d,qid,
                rawids,rawdis,data_info,radius,hits,candidate_count,is_delete,cutoff);
            else leafL2<true><<<nodes,512,0,stream>>>(candidates,node_list,id_list,queryids,data_d,qid,
                rawids,rawdis,data_info,radius,hits,candidate_count,is_delete,cutoff);
        }'''
    source=once(source,old,new)
    source=once(source,'E|P|R|Q radius','Q|H|J radius')
    source=once(source,'mode=="E"||mode=="P"||mode=="R"||mode=="Q") &&',
                'mode=="Q"||mode=="H"||mode=="J") &&')
    source=once(source,'new Fixed(tree_size,tree_h,true,(mode=="E"||mode=="R")?0:2,mode=="R"||mode=="Q")',
                'new Fixed(tree_size,tree_h,true,2,true,mode=="Q"?0:(mode=="H"?1:2))')
    source=once(source,'if(mode=="E"||mode=="P"||mode=="R"||mode=="Q")',
                'if(mode=="Q"||mode=="H"||mode=="J")')
    source=once(source,'mode=="E"||mode=="P"||mode=="R"||mode=="Q");count=*fixed->hc;',
                'mode=="Q"||mode=="H"||mode=="J");count=*fixed->hc;')
    runner=runner.replace("choices=['E','P','R','Q']","choices=['Q','H','J']")
    return source,runner

def make(out):
    out.mkdir(parents=True,exist_ok=True)
    source,runner=render()
    (out/'graph_bench.cu').write_text(source)
    (out/'l2_traversal.cuh').write_bytes((HERE.parent/'traversal_grid_l2_20260924/l2_traversal.cuh').read_bytes())
    (out/'leaf_l2.cuh').write_bytes((HERE/'leaf_l2.cuh').read_bytes())
    (out/'run.py').write_text(runner)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('out',type=Path);a=p.parse_args();make(a.out)
