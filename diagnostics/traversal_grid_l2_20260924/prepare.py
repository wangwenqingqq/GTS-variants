#!/usr/bin/env python3
"""Generate a separate large-L2 traversal ablation from the audited driver."""
from pathlib import Path
import argparse
import importlib.util

HERE = Path(__file__).resolve().parent

def generated_base():
    path=HERE.parent/'fusion_large_l2_20260924/prepare.py'
    spec=importlib.util.spec_from_file_location('fusion_large_l2_prepare',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.driver(),module.runner()

def once(text, old, new):
    assert text.count(old) == 1, (old, text.count(old))
    return text.replace(old, new)

def render():
    source,runner=generated_base()
    source = once(source, '#include "fused_result.cuh"',
                  '#include "fused_result.cuh"\n#include "l2_traversal.cuh"')
    source = once(source, '    bool fused;\n', '    bool fused;\n    int traversal;\n')
    source = once(source, 'Fixed(int count_n,int h,bool f=false):fused(f),',
                  'Fixed(int count_n,int h,bool f=false,int t=0):fused(f),traversal(t),')
    native = ('            findNextRnn<<<1,THREAD_NUM,0,stream>>>(flags,start,node_list,radius,'
              'data_d,qid,num,max_node_num,data_info,empty_list,data_s,size_s);')
    grid = '''            if(traversal == 0) {
                findNextRnn<<<1,THREAD_NUM,0,stream>>>(flags,start,node_list,radius,data_d,qid,num,max_node_num,data_info,empty_list,data_s,size_s);
            } else if(traversal == 1) {
                l2Walk<false><<<1,THREAD_NUM,0,stream>>>(flags,start,node_list,radius,data_d,qid,num,max_node_num,data_info,empty_list);
            } else {
                l2Walk<true><<<(num+THREAD_NUM-1)/THREAD_NUM,THREAD_NUM,0,stream>>>(flags,start,node_list,radius,data_d,qid,num,max_node_num,data_info,empty_list);
            }'''
    source = once(source, native, grid)
    source = once(source, 'A|B|C|D|E radius', 'E|S|P radius')
    source = once(source, 'mode=="A"||mode=="B"||mode=="C"||mode=="D"||mode=="E")',
                  'mode=="E"||mode=="S"||mode=="P")')
    source = once(source, 'new Fixed(tree_size,tree_h,mode=="D"||mode=="E")',
                  'new Fixed(tree_size,tree_h,true,mode=="E"?0:(mode=="S"?1:2))')
    source = once(source, 'if(mode=="C"||mode=="E")',
                  'if(mode=="E"||mode=="S"||mode=="P")')
    source = once(source, 'mode=="C"||mode=="E");count=*fixed->hc;',
                  'mode=="E"||mode=="S"||mode=="P");count=*fixed->hc;')
    runner=runner.replace("choices=['A','B','C','D','E','T']",
                          "choices=['E','S','P']")
    return source,runner

def make(out):
    out.mkdir(parents=True, exist_ok=True)
    source,runner=render()
    (out/'graph_bench.cu').write_text(source)
    (out/'l2_traversal.cuh').write_bytes((HERE/'l2_traversal.cuh').read_bytes())
    (out/'run.py').write_text(runner)

if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('out',type=Path);a=p.parse_args();make(a.out)
