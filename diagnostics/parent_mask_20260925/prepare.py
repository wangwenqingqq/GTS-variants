#!/usr/bin/env python3
"""Add parent-shared pivot distance and 10-bit masks to the pinned L2 driver."""
import argparse
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent


def once(source, old, new):
    assert source.count(old) == 1, (old, source.count(old))
    return source.replace(old, new)


def render():
    path = HERE.parent / 'traversal_count_combo_20260924' / 'prepare.py'
    spec = importlib.util.spec_from_file_location('parent_mask_base', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    source, runner = module.render()
    source = once(source, '#include "l2_traversal.cuh"',
                  '#include "l2_traversal.cuh"\n#include "parent_mask.cuh"')
    source = once(source,
                  '            } else {\n'
                  '                l2Walk<true><<<(num+THREAD_NUM-1)/THREAD_NUM,THREAD_NUM,0,stream>>>(flags,start,node_list,radius,data_d,qid,num,max_node_num,data_info,empty_list);\n'
                  '            }',
                  '            } else if (traversal == 2) {\n'
                  '                l2Walk<true><<<(num+THREAD_NUM-1)/THREAD_NUM,THREAD_NUM,0,stream>>>(flags,start,node_list,radius,data_d,qid,num,max_node_num,data_info,empty_list);\n'
                  '            } else if (traversal == 3) {\n'
                  '                parentMaskWalk<16><<<(num/10+15)/16,16,0,stream>>>(flags,start,node_list,radius,data_d,qid,data_info[0],empty_list,num/10);\n'
                  '            } else {\n'
                  '                parentMaskWalk<32><<<(num/10+31)/32,32,0,stream>>>(flags,start,node_list,radius,data_d,qid,data_info[0],empty_list,num/10);\n'
                  '            }')
    source = once(source, 'E|P|R|Q radius', 'E|P|R|Q|B16|B32 radius')
    source = source.replace('mode=="E"||mode=="P"||mode=="R"||mode=="Q"',
                            'mode=="E"||mode=="P"||mode=="R"||mode=="Q"||mode=="B16"||mode=="B32"')
    source = once(source,
                  'new Fixed(tree_size,tree_h,true,(mode=="E"||mode=="R")?0:2,mode=="R"||mode=="Q")',
                  'new Fixed(tree_size,tree_h,true,(mode=="E"||mode=="R")?0:(mode=="B16"?3:(mode=="B32"?4:2)),mode=="R"||mode=="Q"||mode=="B16"||mode=="B32")')
    runner = runner.replace("choices=['E','P','R','Q']",
                            "choices=['E','P','R','Q','B16','B32']")
    return source, runner


def make(out):
    out.mkdir(parents=True, exist_ok=True)
    source, runner = render()
    (out / 'graph_bench.cu').write_text(source)
    (out / 'run.py').write_text(runner)
    (out / 'l2_traversal.cuh').write_bytes(
        (HERE.parent / 'traversal_grid_l2_20260924' / 'l2_traversal.cuh').read_bytes())
    (out / 'parent_mask.cuh').write_bytes((HERE / 'parent_mask.cuh').read_bytes())


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('out', type=Path)
    make(parser.parse_args().out)
