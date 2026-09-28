#!/usr/bin/env python3
"""Add exact PCA-filtered F modes to the pinned flat-scan benchmark."""
import argparse
import importlib.util
from pathlib import Path

HERE=Path(__file__).resolve().parent

def once(s,old,new):
    assert s.count(old)==1,(old,s.count(old))
    return s.replace(old,new)

def render():
    path=HERE.parent/'flat_scan_l2_20260924/prepare.py'
    spec=importlib.util.spec_from_file_location('flat_prepare_pca',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    source,runner=module.render()
    source=once(source,'#include "flat_l2.cuh"','#include "flat_l2.cuh"\n#include "pca_l2.cuh"')
    source=once(source,'int query_slots=0,used_nodes=0,leaf_nodes=0;',
                'int query_slots=0,used_nodes=0,leaf_nodes=0;\nstd::string pca_path;')
    source=once(source,'    float *rawdis,*ds,*outdis;','    float *rawdis,*ds,*outdis;\n    float *pca_by_id=nullptr,*pca_by_dim=nullptr;')
    old='''        // Initialize inactive payload capacity so fixed-size host delivery is defined.
        ck(cudaMemset(outids,0,slots*sizeof(int)));ck(cudaMemset(outdis,0,slots*sizeof(float)));'''
    new='''        // Initialize inactive payload capacity so fixed-size host delivery is defined.
        ck(cudaMemset(outids,0,slots*sizeof(int)));ck(cudaMemset(outdis,0,slots*sizeof(float)));
        if(leaf_mode>=4) {
            std::ifstream in(pca_path,std::ios::binary);assert(in.good());
            int header[3];in.read(reinterpret_cast<char*>(header),sizeof(header));
            assert(in.gcount()==sizeof(header)&&header[0]==n&&header[1]==data_info[0]&&header[2]==64);
            std::vector<float> projected(size_t(n)*64);
            const auto bytes=std::streamsize(projected.size()*sizeof(float));
            in.read(reinterpret_cast<char*>(projected.data()),bytes);assert(in.gcount()==bytes);
            char extra;assert(!in.read(&extra,1));
            alloc(pca_by_id,projected.size());alloc(pca_by_dim,projected.size());
            ck(cudaMemcpyAsync(pca_by_id,projected.data(),size_t(bytes),cudaMemcpyHostToDevice,stream));
            pcaReorder<<<(n+255)/256,256,0,stream>>>(id_list,pca_by_id,pca_by_dim,n);
            ck(cudaStreamSynchronize(stream));
        }'''
    source=once(source,old,new)
    old='''        if(leaf_mode==3) {
            const float guarded=radius+0.001f;
            const double cutoff=double(guarded)*double(guarded);
            flatL2<<<(n+511)/512,512,0,stream>>>(id_list,data_d,qid,data_info,radius,
                is_delete,n,cutoff,hits,rawids,rawdis);'''
    new='''        if(leaf_mode>=3) {
            const float guarded=radius+0.001f;
            const double cutoff=double(guarded)*double(guarded);
            if(leaf_mode==3)
                flatL2<<<(n+511)/512,512,0,stream>>>(id_list,data_d,qid,data_info,radius,
                    is_delete,n,cutoff,hits,rawids,rawdis);
            else {
                const float pca_guarded=radius+0.01f;
                const double pca_cutoff=double(pca_guarded)*double(pca_guarded);
                pcaFlatL2<<<(n+511)/512,512,0,stream>>>(id_list,data_d,qid,data_info,radius,
                    is_delete,pca_by_dim,pca_by_id,n,leaf_mode==4?32:64,pca_cutoff,cutoff,
                    hits,rawids,rawdis);
            }'''
    source=once(source,old,new)
    source=once(source,'Q|H|J|F radius','Q|H|J|F|P32|P64 radius')
    source=source.replace('mode=="Q"||mode=="H"||mode=="J"||mode=="F"',
                          'mode=="Q"||mode=="H"||mode=="J"||mode=="F"||mode=="P32"||mode=="P64"')
    source=once(source,'mode=="Q"?0:(mode=="H"?1:(mode=="J"?2:3))',
                'mode=="Q"?0:(mode=="H"?1:(mode=="J"?2:(mode=="F"?3:(mode=="P32"?4:5))))')
    source=once(source,'auto process_start=Clock::now();loadBinaryL2(argv[1]);',
                'auto process_start=Clock::now();pca_path=std::string(argv[1])+".pca64";loadBinaryL2(argv[1]);')
    runner=runner.replace("choices=['Q','H','J','F']","choices=['Q','H','J','F','P32','P64']")
    return source,runner

def make(out):
    out.mkdir(parents=True,exist_ok=True)
    source,runner=render()
    (out/'graph_bench.cu').write_text(source)
    (out/'run.py').write_text(runner)
    for name,rel in [('flat_l2.cuh','flat_scan_l2_20260924'),
                     ('leaf_l2.cuh','leaf_early_l2_20260924'),
                     ('l2_traversal.cuh','traversal_grid_l2_20260924')]:
        (out/name).write_bytes((HERE.parent/rel/name).read_bytes())
    (out/'fused_result.cuh').write_bytes((HERE/'fused_result.cuh').read_bytes())
    (out/'pca_l2.cuh').write_bytes((HERE/'pca_l2.cuh').read_bytes())

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('out',type=Path);a=p.parse_args();make(a.out)
