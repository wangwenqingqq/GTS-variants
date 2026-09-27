#!/usr/bin/env python3
"""Extend the parent-mask experiment to blocks of 64–512 parents."""
import argparse
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / 'parent_mask_20260925'


def once(source, old, new):
    assert source.count(old) == 1, (old, source.count(old))
    return source.replace(old, new)


def render():
    spec = importlib.util.spec_from_file_location('parent_mask_base', BASE / 'prepare.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    source, runner = module.render()
    old = ('            } else {\n'
           '                parentMaskWalk<32><<<(num/10+31)/32,32,0,stream>>>(flags,start,node_list,radius,data_d,qid,data_info[0],empty_list,num/10);\n'
           '            }')
    branches = []
    for traversal, group in enumerate((32, 64, 128, 256), start=4):
        branches.append(
            f'            }} else if (traversal == {traversal}) {{\n'
            f'                parentMaskWalk<{group}><<<(num/10+{group-1})/{group},{group},0,stream>>>(flags,start,node_list,radius,data_d,qid,data_info[0],empty_list,num/10);\n')
    branches.append(
        '            } else {\n'
        '                parentMaskWalk<512><<<(num/10+511)/512,512,0,stream>>>(flags,start,node_list,radius,data_d,qid,data_info[0],empty_list,num/10);\n'
        '            }')
    source = once(source, old, ''.join(branches))
    source = once(source, 'E|P|R|Q|B16|B32 radius',
                  'E|P|R|Q|B16|B32|B64|B128|B256|B512 radius')
    source = once(source,
                  'new Fixed(tree_size,tree_h,true,(mode=="E"||mode=="R")?0:(mode=="B16"?3:(mode=="B32"?4:2)),mode=="R"||mode=="Q"||mode=="B16"||mode=="B32")',
                  'new Fixed(tree_size,tree_h,true,(mode=="E"||mode=="R")?0:(mode=="B16"?3:(mode=="B32"?4:(mode=="B64"?5:(mode=="B128"?6:(mode=="B256"?7:(mode=="B512"?8:2)))))),mode=="R"||mode=="Q"||mode=="B16"||mode=="B32"||mode=="B64"||mode=="B128"||mode=="B256"||mode=="B512")')
    source = source.replace(
        'mode=="E"||mode=="P"||mode=="R"||mode=="Q"||mode=="B16"||mode=="B32"',
        'mode=="E"||mode=="P"||mode=="R"||mode=="Q"||mode=="B16"||mode=="B32"||mode=="B64"||mode=="B128"||mode=="B256"||mode=="B512"')
    runner = once(runner,
                  "choices=['E','P','R','Q','B16','B32']",
                  "choices=['E','P','R','Q','B16','B32','B64','B128','B256','B512']")
    return source, runner


def make(out):
    out.mkdir(parents=True, exist_ok=True)
    source, runner = render()
    (out / 'graph_bench.cu').write_text(source)
    (out / 'run.py').write_text(runner)
    (out / 'l2_traversal.cuh').write_bytes(
        (HERE.parent / 'traversal_grid_l2_20260924' / 'l2_traversal.cuh').read_bytes())
    (out / 'parent_mask.cuh').write_bytes((BASE / 'parent_mask.cuh').read_bytes())


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('out', type=Path)
    make(parser.parse_args().out)
