#!/usr/bin/env python3
"""Build an F versus point-tiled SoA exact scan comparison driver."""
import argparse
import importlib.util
from pathlib import Path

HERE=Path(__file__).resolve().parent


def once(source,old,new):
    assert source.count(old)==1,(old,source.count(old))
    return source.replace(old,new)


def render():
    path=HERE.parent/'flat_scan_l2_20260924/prepare.py'
    spec=importlib.util.spec_from_file_location('highdim_flat_prepare',path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    source,runner=module.render()
    source=once(source,'#include "flat_l2.cuh"',
                '#include "flat_l2.cuh"\n#include "soa_l2.cuh"\n#include "fast_filter_l2.cuh"')
    source=once(source,'    int leaf_mode;\n',
                '    int leaf_mode;\n    float* soa=nullptr;\n')
    source=once(source,
                '        // Initialize inactive payload capacity so fixed-size host delivery is defined.',
                '''        if(leaf_mode==4) {
            const int dim=data_info[0];
            const size_t elements=size_t((n+31)/32)*size_t(dim)*32;
            ck(cudaMalloc(&soa,elements*sizeof(float)));
            reorderSoA32<<<(n+255)/256,256,0,stream>>>(id_list,data_d,soa,n,dim);
            ck(cudaGetLastError());
            ck(cudaStreamSynchronize(stream));
        }
        // Initialize inactive payload capacity so fixed-size host delivery is defined.''')
    source=once(source,'        if(leaf_mode==3) {',
                '        if(leaf_mode==3 || leaf_mode==4 || leaf_mode==5) {')
    source=once(source,
                '''            flatL2<<<(n+511)/512,512,0,stream>>>(id_list,data_d,qid,data_info,radius,
                is_delete,n,cutoff,hits,rawids,rawdis);''',
                '''            if(leaf_mode==3)
                flatL2<<<(n+511)/512,512,0,stream>>>(id_list,data_d,qid,data_info,radius,
                    is_delete,n,cutoff,hits,rawids,rawdis);
            else if(leaf_mode==4)
                soaFlatL2<<<(n+511)/512,512,0,stream>>>(id_list,soa,data_d,qid,data_info,radius,
                    is_delete,n,cutoff,hits,rawids,rawdis);
            else {
                const float quick_guard=radius+0.01f;
                const double quick_cutoff=double(quick_guard)*double(quick_guard);
                filteredFlatL2<<<(n+511)/512,512,0,stream>>>(id_list,data_d,qid,data_info,radius,
                    is_delete,n,cutoff,quick_cutoff,hits,rawids,rawdis);
            }''')
    source=once(source,
                '        if(executable)ck(cudaGraphExecDestroy(executable));if(graph)ck(cudaGraphDestroy(graph));',
                '        if(executable)ck(cudaGraphExecDestroy(executable));if(graph)ck(cudaGraphDestroy(graph));\n        if(soa)ck(cudaFree(soa));')
    source=once(source,'Q|H|J|F radius','Q|H|J|F|S|M radius')
    source=source.replace('mode=="Q"||mode=="H"||mode=="J"||mode=="F"',
                          'mode=="Q"||mode=="H"||mode=="J"||mode=="F"||mode=="S"||mode=="M"')
    source=once(source,'mode=="Q"?0:(mode=="H"?1:(mode=="J"?2:3))',
                'mode=="Q"?0:(mode=="H"?1:(mode=="J"?2:(mode=="F"?3:(mode=="S"?4:5))))')
    runner=runner.replace("choices=['Q','H','J','F']",
                          "choices=['Q','H','J','F','S','M']")
    return source,runner


def make(out):
    out.mkdir(parents=True,exist_ok=True)
    source,runner=render()
    (out/'graph_bench.cu').write_text(source)
    (out/'run.py').write_text(runner)
    (out/'soa_l2.cuh').write_bytes((HERE/'soa_l2.cuh').read_bytes())
    (out/'fast_filter_l2.cuh').write_bytes((HERE/'fast_filter_l2.cuh').read_bytes())
    for name,directory in [('flat_l2.cuh','flat_scan_l2_20260924'),
                           ('leaf_l2.cuh','leaf_early_l2_20260924'),
                           ('l2_traversal.cuh','traversal_grid_l2_20260924'),
                           ('fused_result.cuh','pca_end_to_end_20260925')]:
        (out/name).write_bytes((HERE.parent/directory/name).read_bytes())


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('out',type=Path)
    make(parser.parse_args().out)
