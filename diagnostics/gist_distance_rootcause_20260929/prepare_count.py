#!/usr/bin/env python3
"""Build a separate non-timed dimension-counting version of the four modes."""
import argparse
import subprocess
import sys
from pathlib import Path

from prepare_rootcause import once


def main():
    p = argparse.ArgumentParser()
    p.add_argument("out", type=Path)
    a = p.parse_args()
    subprocess.run([sys.executable, str(Path(__file__).with_name("prepare_rootcause.py")), str(a.out)], check=True)
    path = a.out / "graph_bench.cu"
    s = path.read_text()
    s = once(s, "    float* packed;\n", "    float* packed;\n    int* processed=nullptr;\n")
    s = once(s, "        alloc(qid,1);alloc(flags,nodes);", "        if(root_mode)alloc(processed,n);\n        alloc(qid,1);alloc(flags,nodes);")
    for layout in ("false", "true"):
        for early in ("false", "true"):
            s = once(s, f"rootcauseFlat<{layout},{early}>", f"rootcauseFlat<{layout},{early},true>")
    assert s.count("hits,rawids,rawdis,nullptr);") == 4
    s = s.replace("hits,rawids,rawdis,nullptr);", "hits,rawids,rawdis,processed);")
    s = once(s, "        if(node_for_pos)ck(cudaFree(node_for_pos));",
             "        if(processed)ck(cudaFree(processed));\n        if(node_for_pos)ck(cudaFree(node_for_pos));")
    s = once(s, "    std::ofstream full,work,binary;",
             '''    const char* dims_path=getenv("GTS_DIMS_OUTPUT");
    std::ofstream dims_out;
    if(dims_path){dims_out.open(dims_path);assert(bool(dims_out));
        dims_out<<"qid,count,ordered_hash,sum_dims,dim_hist,group_max_hist\\n";}
    std::ofstream full,work,binary;''')
    s = once(s, "        counts.push_back(count);hashes.push_back(digest(count,ids,ds));",
             '''        counts.push_back(count);hashes.push_back(digest(count,ids,ds));
        if(dims_path) {
            std::vector<int> values(tree_size);std::vector<unsigned long long> hist((data_info[0]+31)/32+1,0);
            std::vector<unsigned long long> groups(hist.size(),0);
            ck(cudaMemcpy(values.data(),fixed->processed,size_t(tree_size)*sizeof(int),cudaMemcpyDeviceToHost));
            unsigned long long sum_dims=0;
            for(int pos=0;pos<tree_size;++pos){const int v=values[pos];
                assert(v>=0&&v<=data_info[0]);sum_dims+=v;++hist[(v+31)/32];}
            for(int first=0;first<tree_size;first+=32){int longest=0;
                for(int pos=first;pos<std::min(first+32,tree_size);++pos)
                    longest=std::max(longest,values[pos]);
                ++groups[(longest+31)/32];}
            dims_out<<q<<','<<count<<','<<hashes.back()<<','<<sum_dims<<',';
            for(size_t i=0;i<hist.size();++i){if(i)dims_out<<'|';dims_out<<hist[i];}
            dims_out<<',';for(size_t i=0;i<groups.size();++i){if(i)dims_out<<'|';dims_out<<groups[i];}
            dims_out<<'\\n';
        }''')
    path.write_text(s)


if __name__ == "__main__":
    main()
