#!/usr/bin/env python3
"""Compose the preserved traversal and layout generators in a separate scratch."""
import argparse
import importlib.util
import shutil
from pathlib import Path
HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


layout = load('locality_combo', HERE.parent/'pruning_locality_20260923/prepare.py')
traversal = load('traversal_combo', HERE.parent/'traversal_ablation_20260923/prepare.py')
once = layout.once
GRAPH = 'ERTFXY'
STREAM = 'DBCGJK'
ORDERS = ['ERTFXY', 'YXFTRE', 'FXYERT', 'TREYXF']


def kernels(source):
    native = traversal.kernels(source).split('template<bool Count>\n__global__ void dedupLevel')[0]
    walk = layout.kernel(source).removeprefix('#pragma once\n#include "layout_index.cuh"\n')
    walk = once(walk, '__global__ void findNextLayout', '__device__ __forceinline__ void inlineWalkLayout')
    start = native.index('template<bool Count>\n__global__ void fusedTraversal')
    fused = native[start:]
    fused = once(fused, 'template<bool Count>', 'template<int Layout>')
    fused = once(fused, 'void fusedTraversal(', 'void fusedTraversalLayout(')
    fused = once(fused, 'int height, int *work)',
                 'int height, const int *pids, const float *lower, const float *packed)')
    fused = once(fused, 'inlineWalk<Count>', 'inlineWalkLayout<Layout>')
    fused = once(fused, 'size_s, work);', 'size_s, pids, lower, packed);')
    return native+'\n'+walk+'\n'+fused


def driver(text):
    s = layout.driver(text)
    s = once(s, '#include "layout_support.cuh"', '#include "layout_support.cuh"\n#include "traversal_layout_generated.cuh"\n#include "audit_combo.cuh"')
    s = once(s, 'int layout_mode;', 'int layout_mode;\n    bool traversal_fused;')
    s = once(s, 'int lm=0):layout_mode(lm)', 'int lm=0,bool tf=false):layout_mode(lm),traversal_fused(tf)')
    start = s.index('        initQnode<<<1,THREAD_NUM,0,stream>>>')
    end = s.index('        ck(cub::DeviceReduce::Sum(temp,tempbytes,flags,candidate_count,nodes,stream));', start)
    old = s[start:end]
    call = 'flags,1,node_list,radius,data_d,qid,10,max_node_num,data_info,empty_list,data_s,size_s,height'
    dispatch = '        if(traversal_fused) {\n'
    dispatch += '            if(layout_mode==0) fusedTraversal<false><<<1,THREAD_NUM,0,stream>>>('+call+',nullptr);\n'
    for mode, kind in [(3, 2), (4, 3)]:
        dispatch += f'            else if(layout_mode=={mode}) fusedTraversalLayout<{kind}><<<1,THREAD_NUM,0,stream>>>('+call+',prune_layout->pids,prune_layout->lower,prune_layout->packed);\n'
    dispatch += '            else { fprintf(stderr,"Invalid fused layout\\n");exit(4); }\n        } else {\n'+old+'        }\n'
    s = once(s, old, dispatch)
    s = once(s, 'A|D|E|U|S|V|L|B|R|C|T radius', 'A|D|E|U|S|V|L|B|R|C|T|F|G|X|J|Y|K radius')
    s = once(s, 'mode=="C"||mode=="T") && repeats', 'mode=="C"||mode=="T"||mode=="F"||mode=="G"||mode=="X"||mode=="J"||mode=="Y"||mode=="K") && repeats')
    s = once(s, 'if(dump && mode=="E")auditPruning(queries,radius,out);',
             'if(dump && mode=="E")auditPruning(queries,radius,out);\n    if(dump && mode=="F")auditCombo(queries,radius);')
    s = once(s, 'mode=="B"||mode=="R")?3:', 'mode=="B"||mode=="R"||mode=="X"||mode=="J")?3:')
    s = once(s, 'mode=="C"||mode=="T")?4:', 'mode=="C"||mode=="T"||mode=="Y"||mode=="K")?4:')
    s = once(s, 'new Fixed(tree_size,tree_h,true,lm)', 'new Fixed(tree_size,tree_h,true,lm,mode=="F"||mode=="G"||mode=="X"||mode=="J"||mode=="Y"||mode=="K")')
    predicate = 'mode=="E"||mode=="S"||mode=="L"||mode=="R"||mode=="T"'
    assert s.count(predicate) == 2
    return s.replace(predicate, predicate+'||mode=="F"||mode=="X"||mode=="Y"')


def runner(text):
    s = layout.runner(text)
    s = once(s, "'B','R','C','T']", "'B','R','C','T','F','G','X','J','Y','K']")
    return s


def verifier():
    s = layout.verifier()
    s = once(s, "'ESLBRTC' if name=='empty' else 'AESLBRTC'", "'ERTFXYDBCGJK' if name=='empty' else 'AERTFXYDBCGJK'")
    marker = "  assert 'PASS layout bit-audit and 128 per-level flag cases' in log"
    s = once(s, marker, marker+"\n  assert 'PASS combo 80 flag cases' in (root/'runs'/f'full_{name}_F/stdout.log').read_text()")
    return s


def suite():
    s = (layout.HERE/'suite.py').read_text()
    s = once(s, "GRAPH='ESRT';FULL='ESLBRTC';STRESS='ESRTBC';NCU='DUVBC'", "GRAPH='ERTFXY';FULL='ERTFXYDBCGJK';STRESS=FULL;NCU=''" )
    s = once(s, "ORDERS=['ESRT','TRSE','RTES','SETR']", 'ORDERS='+repr(ORDERS))
    s = once(s, "GRAPH+'BC' if t in TOOLS[:2] else GRAPH", "FULL if t in TOOLS[:2] else GRAPH")
    s = once(s, "1,0,t,False) for t,m in gates()", "1,0,t,m=='F') for t,m in gates()")
    s = once(s, "['ESRT','TRSE']", repr(ORDERS[:2]))
    s = once(s, "p.add_argument('--gpu',required=True)", "p.add_argument('--gpu',required=True);p.add_argument('--gpu-index',type=int,default=0)")
    s = once(s, "=='5'", "==str(a.gpu_index)")
    s = once(s, "'/tmp/gtspp_gpu5.lock'", "f'/tmp/gtspp_gpu{a.gpu_index}.lock'")
    s = once(s, "choices=['full','gates','stress','screen','sustained','trace','ncu']", "choices=['full','gates','stress','screen','sustained','trace']")
    return s


def prepare(source, out):
    layout.prepare(source, out)
    original = (HERE.parent/'graph_query_20260923/graph_bench.cu').read_text()
    (out/'graph_bench.cu').write_text(driver(original))
    (out/'traversal_layout_generated.cuh').write_text(kernels((source/'GTS/include/search.cuh').read_text()))
    (out/'run_layout.py').write_text(runner((HERE.parent/'graph_query_20260923/run.py').read_text()))
    (out/'verify_full.py').write_text(verifier())
    (out/'suite.py').write_text(suite())
    for name in ['audit_combo.cuh', 'CONTRACT.md']:
        shutil.copy2(HERE/name, out/name)
    print('Prepared 2 x 3 combination; CUDA compilation and all GPU gates pending')


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('source', type=Path); p.add_argument('output', type=Path)
    a = p.parse_args(); prepare(a.source, a.output)
