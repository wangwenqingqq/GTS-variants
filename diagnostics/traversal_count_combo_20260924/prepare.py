#!/usr/bin/env python3
"""Extend the pinned traversal ablation with dead count-stage removal."""
import argparse
import importlib.util
from pathlib import Path

HERE=Path(__file__).resolve().parent

def grid_source():
    path=HERE.parent/'traversal_grid_l2_20260924/prepare.py'
    spec=importlib.util.spec_from_file_location('traversal_grid_l2_prepare',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.render()

def once(text,old,new):
    assert text.count(old)==1,(old,text.count(old))
    return text.replace(old,new)

def render():
    text,runner=grid_source()
    text=once(text,'    int traversal;\n','    int traversal;\n    bool skip_dead_count;\n')
    text=once(text,'int t=0):fused(f),traversal(t),',
              'int t=0,bool skip=false):fused(f),traversal(t),skip_dead_count(skip),')
    old='''        getQnodeCount<<<1,512,0,stream>>>(1,flags,max_node_num,nodecount,0);
        ck(cub::DeviceScan::ExclusiveSum(temp,tempbytes,nodecount,nodeprefix,1,stream));'''
    new='''        if(!skip_dead_count) {
            getQnodeCount<<<1,512,0,stream>>>(1,flags,max_node_num,nodecount,0);
            ck(cub::DeviceScan::ExclusiveSum(temp,tempbytes,nodecount,nodeprefix,1,stream));
        }'''
    text=once(text,old,new)
    text=once(text,'E|S|P radius','E|P|R|Q radius')
    text=once(text,'mode=="E"||mode=="S"||mode=="P") &&',
              'mode=="E"||mode=="P"||mode=="R"||mode=="Q") &&')
    text=once(text,'new Fixed(tree_size,tree_h,true,mode=="E"?0:(mode=="S"?1:2))',
              'new Fixed(tree_size,tree_h,true,(mode=="E"||mode=="R")?0:2,mode=="R"||mode=="Q")')
    text=once(text,'if(mode=="E"||mode=="S"||mode=="P")',
              'if(mode=="E"||mode=="P"||mode=="R"||mode=="Q")')
    text=once(text,'mode=="E"||mode=="S"||mode=="P");count=*fixed->hc;',
              'mode=="E"||mode=="P"||mode=="R"||mode=="Q");count=*fixed->hc;')
    runner=runner.replace("choices=['E','S','P']",
                          "choices=['E','P','R','Q']")
    return text,runner

def make(out):
    out.mkdir(parents=True,exist_ok=True)
    text,runner=render()
    (out/'graph_bench.cu').write_text(text)
    (out/'l2_traversal.cuh').write_bytes((HERE.parent/'traversal_grid_l2_20260924/l2_traversal.cuh').read_bytes())
    (out/'run.py').write_text(runner)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('out',type=Path);a=p.parse_args();make(a.out)
