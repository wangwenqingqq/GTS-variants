#!/usr/bin/env python3
"""Build a separate counter-instrumented binary; never use it for timing."""
import argparse
from pathlib import Path

from prepare_strict import render, once


def main():
    p = argparse.ArgumentParser()
    p.add_argument("out", type=Path)
    a = p.parse_args()
    render(a.out)
    header = a.out / "strict_l2.cuh"
    h = header.read_text()
    h = once(h, "// For D<=960,", "__device__ unsigned long long work_counters[7];\n\n// For D<=960,")
    h = once(h, '''    if constexpr(Fast) {
        bool abnormal=false;
        const float sum=strict_fast_sum(data,d,a,b,abnormal);
        if(!abnormal) {''', '''    atomicAdd(work_counters+4,1ull);
    if constexpr(Fast) {
        bool abnormal=false;
        const float sum=strict_fast_sum(data,d,a,b,abnormal);
        if(abnormal)atomicAdd(work_counters+6,1ull);
        if(!abnormal) {''')
    h = once(h, '''    ref_norm_interval(strict_ref_sum(data,d,a,b),lo,hi);''',
             '''    atomicAdd(work_counters+5,1ull);
    ref_norm_interval(strict_ref_sum(data,d,a,b),lo,hi);''')
    h = once(h, '''    if(radius<0)return false;
    const double cutoff=double(radius)*double(radius);''',
             '''    if(radius<0)return false;
    atomicAdd(work_counters+0,1ull);
    const double cutoff=double(radius)*double(radius);''')
    h = once(h, '''        if(!abnormal && double(sum)>cutoff*(1.0+fast_eta(d)))return false;''',
             '''        if(abnormal)atomicAdd(work_counters+3,1ull);
        if(!abnormal && double(sum)>cutoff*(1.0+fast_eta(d))) {
            atomicAdd(work_counters+1,1ull);return false;
        }''')
    h = once(h, '''    const double sum=strict_ref_sum(data,d,a,b);
    if(sum>cutoff)return false;''',
             '''    atomicAdd(work_counters+2,1ull);
    const double sum=strict_ref_sum(data,d,a,b);
    if(sum>cutoff)return false;''')
    header.write_text(h)
    source = a.out / "graph_bench.cu"
    s = source.read_text()
    s = once(s, '''        *hq=q;
        if(replay)ck(cudaGraphLaunch(executable,stream));''',
             '''        *hq=q;
        void* counters=nullptr;ck(cudaGetSymbolAddress(&counters,work_counters));
        ck(cudaMemsetAsync(counters,0,7*sizeof(unsigned long long),stream));
        if(replay)ck(cudaGraphLaunch(executable,stream));''')
    s = once(s, '''    std::vector<double> us;std::vector<int> counts;std::vector<uint64_t> hashes;''',
             '''    const char* work_path=getenv("GTS_WORK_OUTPUT");
    std::ofstream detailed;
    if(work_path){detailed.open(work_path);
        detailed<<"qid,point_pairs,point_fast_rejected,point_ref_calls,point_abnormal,pivot_pairs,pivot_ref_calls,pivot_abnormal\\n";}
    std::vector<double> us;std::vector<int> counts;std::vector<uint64_t> hashes;''')
    s = once(s, '''        counts.push_back(count);hashes.push_back(digest(count,ids,ds));''',
             '''        counts.push_back(count);hashes.push_back(digest(count,ids,ds));
        if(work_path){unsigned long long c[7];
            ck(cudaMemcpyFromSymbol(c,work_counters,sizeof(c)));
            detailed<<q;for(auto v:c)detailed<<','<<v;detailed<<'\\n';}''')
    source.write_text(s)


if __name__ == "__main__":
    main()
