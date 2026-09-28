#!/usr/bin/env python3
"""Build a separate diagnostic binary that writes the pinned tree pivots."""
import argparse
from pathlib import Path

from prepare_strict import render, once


def main():
    p = argparse.ArgumentParser()
    p.add_argument("out", type=Path)
    p.add_argument("--timed", action="store_true")
    a = p.parse_args()
    render(a.out)
    path = a.out / "graph_bench.cu"
    s = path.read_text()
    s = once(s, "    uint64_t idlist_hash=1469598103934665603ull;",
             '''    if(const char* dump=getenv("GTS_DUMP_INDEX")) {
        std::ofstream file(dump,std::ios::binary);
        int32_t header[3]={data_info[0],data_info[1],int32_t(tree.size())};
        file.write(reinterpret_cast<const char*>(header),sizeof(header));
        file.write(reinterpret_cast<const char*>(tree.data()),tree.size()*sizeof(TN));
        file.write(reinterpret_cast<const char*>(empty.data()),empty.size()*sizeof(int));
        file.write(reinterpret_cast<const char*>(ids.data()),ids.size()*sizeof(int));
        assert(bool(file));return 0;
    }
    uint64_t idlist_hash=1469598103934665603ull;''')
    if a.timed:
        s = once(s, "auto process_start=Clock::now();loadBinaryL2(argv[1]);",
                 "auto process_start=Clock::now();auto load_start=Clock::now();loadBinaryL2(argv[1]);double load_s=seconds(load_start);")
        s = once(s, "    indexConstru(data_d,data_s,size_s,data_info,id_list,node_list,max_node_num,tree_h,empty_list);ck(cudaDeviceSynchronize());",
                 "    auto index_start=Clock::now();indexConstru(data_d,data_s,size_s,data_info,id_list,node_list,max_node_num,tree_h,empty_list);ck(cudaDeviceSynchronize());double index_s=seconds(index_start);")
        s = once(s, "        assert(bool(file));return 0;",
                 "        assert(bool(file));printf(\"COLD load_s=%.9f index_s=%.9f\\n\",load_s,index_s);return 0;")
    path.write_text(s)


if __name__ == "__main__":
    main()
