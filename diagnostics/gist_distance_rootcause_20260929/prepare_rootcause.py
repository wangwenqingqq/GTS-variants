#!/usr/bin/env python3
"""Generate the frozen strict driver with only the four flat 2x2 modes."""
import argparse
import shutil
from pathlib import Path
import sys

BASE = Path(__file__).resolve().parents[1] / "arithmetic_path_boundary_20260928"
sys.path.insert(0, str(BASE))
from prepare_strict import once, render  # noqa: E402


def main():
    p = argparse.ArgumentParser()
    p.add_argument("out", type=Path)
    a = p.parse_args()
    render(a.out)
    shutil.copyfile(Path(__file__).with_name("rootcause_l2.cuh"), a.out / "rootcause_l2.cuh")
    path = a.out / "graph_bench.cu"
    s = path.read_text()
    s = once(s, "#include <cstdlib>", "#include <cstdlib>\n#include <cmath>")
    s = once(s, '#include "strict_l2.cuh"',
             '#include "strict_l2.cuh"\n#include "rootcause_l2.cuh"')
    s = once(s, "    bool strict, fast;\n", "    bool strict, fast;\n    int root_mode;\n    float* packed;\n")
    s = once(s, "unsigned long long* ub=nullptr):fused(f),strict(sm),fast(fm),lower(lb),upper(ub),traversal(t)",
             "unsigned long long* ub=nullptr,int rm=0,float* pack=nullptr):fused(f),strict(sm),fast(fm),root_mode(rm),packed(pack),lower(lb),upper(ub),traversal(t)")
    old = '''                if(fast)strict_flat<true><<<(n+511)/512,512,0,stream>>>(id_list,data_d,qid,n,d,radius,hits,rawids,rawdis);
                else strict_flat<false><<<(n+511)/512,512,0,stream>>>(id_list,data_d,qid,n,d,radius,hits,rawids,rawdis);'''
    new = '''                if(root_mode==1)rootcauseFlat<false,false><<<(n+511)/512,512,0,stream>>>(id_list,data_d,packed,qid,n,d,radius,hits,rawids,rawdis,nullptr);
                else if(root_mode==2)rootcauseFlat<true,false><<<(n+511)/512,512,0,stream>>>(id_list,data_d,packed,qid,n,d,radius,hits,rawids,rawdis,nullptr);
                else if(root_mode==3)rootcauseFlat<false,true><<<(n+511)/512,512,0,stream>>>(id_list,data_d,packed,qid,n,d,radius,hits,rawids,rawdis,nullptr);
                else if(root_mode==4)rootcauseFlat<true,true><<<(n+511)/512,512,0,stream>>>(id_list,data_d,packed,qid,n,d,radius,hits,rawids,rawdis,nullptr);
                else if(fast)strict_flat<true><<<(n+511)/512,512,0,stream>>>(id_list,data_d,qid,n,d,radius,hits,rawids,rawdis);
                else strict_flat<false><<<(n+511)/512,512,0,stream>>>(id_list,data_d,qid,n,d,radius,hits,rawids,rawdis);'''
    s = once(s, old, new)
    s = once(s, '''    const bool strict=mode=="FR"''',
             '''    const bool rootcause=mode=="B"||mode=="L"||mode=="E64"||mode=="L_E64";
    const int root_mode=mode=="B"?1:(mode=="L"?2:(mode=="E64"?3:(mode=="L_E64"?4:0)));
    const bool strict=rootcause||mode=="FR"''')
    s = once(s, "    const bool fast=strict&&mode[1]=='F';",
             "    const bool fast=strict&&!rootcause&&mode[1]=='F';")
    s = once(s, "    auto process_start=Clock::now();loadBinaryL2(argv[1]);",
             '''    assert(std::isfinite(radius));
    auto process_start=Clock::now();loadBinaryL2(argv[1]);
    if(rootcause)for(size_t i=0;i<size_t(data_info[0])*data_info[1];++i)
        if(!std::isfinite(data_d[i])){fprintf(stderr,"Nonfinite input at %zu\\n",i);return 4;}''')
    s = once(s, "dim==960 || dim==96 || dim==2", "dim>=2 && dim<=960")
    s = once(s, "data_info[0]==960 || data_info[0]==96 || data_info[0]==2", "data_info[0]>=2 && data_info[0]<=960")
    s = once(s, '''    qnum_leaf=1;
    tree_size=data_info[1];''',
             '''    float* packed=nullptr;double layout_s=0;size_t layout_bytes=0;
    if(root_mode==2||root_mode==4) {
        auto layout_start=Clock::now();
        const size_t layout_items=size_t((data_info[1]+31)/32)*32*data_info[0];
        layout_bytes=layout_items*sizeof(float);
        alloc(packed,layout_items);
        rootcausePack32<<<(data_info[1]+511)/512,512>>>(id_list,data_d,packed,data_info[1],data_info[0]);
        ck(cudaGetLastError());ck(cudaDeviceSynchronize());
        layout_s=seconds(layout_start);
    }
    qnum_leaf=1;
    tree_size=data_info[1];''')
    s = once(s, "auto setup=Clock::now();int leaf_mode=strict?(mode[0]=='F'?5:(mode[0]=='C'?6:7)):",
             "auto setup=Clock::now();int leaf_mode=strict?(rootcause?5:(mode[0]=='F'?5:(mode[0]=='C'?6:7))):")
    s = once(s, "strict,fast,strict_low,strict_high);double capture_s=0;",
             "strict,fast,strict_low,strict_high,root_mode,packed);double capture_s=0;")
    s = once(s, '''<<",\\\"refit_s\\\":"<<refit_s<<",\\\"bounds_hash\\\":"<<bound_hash<<",\\\"setup_s\\\":"<<setup_s''',
             '''<<",\\\"refit_s\\\":"<<refit_s<<",\\\"bounds_hash\\\":"<<bound_hash<<",\\\"layout_s\\\":"<<layout_s<<",\\\"layout_bytes\\\":"<<layout_bytes<<",\\\"setup_s\\\":"<<setup_s''')
    s = once(s, "    delete fixed;\n    if(strict_low)", "    delete fixed;if(packed)ck(cudaFree(packed));\n    if(strict_low)")
    path.write_text(s)
    runner = a.out / "run.py"
    script = runner.read_text()
    script = once(script, "'CF5'],required=True", "'CF5','B','L','E64','L_E64'],required=True")
    script = once(script, "'CF5') else root/'fixtures'/'strict_external_audit_required.json'",
                  "'CF5','B','L','E64','L_E64') else root/'fixtures'/'strict_external_audit_required.json'")
    runner.write_text(script)


if __name__ == "__main__":
    main()
