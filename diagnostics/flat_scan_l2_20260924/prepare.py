#!/usr/bin/env python3
"""Compose the pinned Q/J driver with an exact scan bypassing tree traversal."""
from pathlib import Path
import argparse,importlib.util

HERE=Path(__file__).resolve().parent

def once(s,old,new):
    assert s.count(old)==1,(old,s.count(old))
    return s.replace(old,new)

def render():
    path=HERE.parent/'leaf_early_l2_20260924/prepare.py'
    spec=importlib.util.spec_from_file_location('leaf_early_prepare_flat',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    source,runner=module.render()
    source=once(source,'#include "leaf_l2.cuh"',
                '#include "leaf_l2.cuh"\n#include "flat_l2.cuh"')
    old='''    void enqueue(float radius) {
        ck(cudaMemcpyAsync(qid,hq,sizeof(int),cudaMemcpyHostToDevice,stream));'''
    new='''    void enqueue(float radius) {
        ck(cudaMemcpyAsync(qid,hq,sizeof(int),cudaMemcpyHostToDevice,stream));
        if(leaf_mode==3) {
            const float guarded=radius+0.001f;
            const double cutoff=double(guarded)*double(guarded);
            flatL2<<<(n+511)/512,512,0,stream>>>(id_list,data_d,qid,data_info,radius,
                is_delete,n,cutoff,hits,rawids,rawdis);
            ck(cub::DeviceScan::InclusiveSum(temp,tempbytes,is_delete,is_delete_prefix,n,stream));
            flatResultSelect<<<1,512,0,stream>>>(n,hits,rawids,rawdis,is_delete_prefix,
                count,outids,outdis);
            ck(cudaMemcpyAsync(hc,count,sizeof(int),cudaMemcpyDeviceToHost,stream));
            ck(cudaMemcpyAsync(hi,outids,slots*sizeof(int),cudaMemcpyDeviceToHost,stream));
            ck(cudaMemcpyAsync(hd,outdis,slots*sizeof(float),cudaMemcpyDeviceToHost,stream));
            ck(cudaGetLastError());return;
        }'''
    source=once(source,old,new)
    source=once(source,'Q|H|J radius','Q|H|J|F radius')
    source=source.replace('mode=="Q"||mode=="H"||mode=="J"',
                          'mode=="Q"||mode=="H"||mode=="J"||mode=="F"')
    source=once(source,'mode=="Q"?0:(mode=="H"?1:2)',
                'mode=="Q"?0:(mode=="H"?1:(mode=="J"?2:3))')
    runner=runner.replace("choices=['Q','H','J']","choices=['Q','H','J','F']")
    return source,runner

def make(out):
    out.mkdir(parents=True,exist_ok=True)
    source,runner=render()
    (out/'graph_bench.cu').write_text(source)
    (out/'run.py').write_text(runner)
    (out/'flat_l2.cuh').write_bytes((HERE/'flat_l2.cuh').read_bytes())
    (out/'leaf_l2.cuh').write_bytes((HERE.parent/'leaf_early_l2_20260924/leaf_l2.cuh').read_bytes())
    (out/'l2_traversal.cuh').write_bytes((HERE.parent/'traversal_grid_l2_20260924/l2_traversal.cuh').read_bytes())

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('out',type=Path);a=p.parse_args();make(a.out)
