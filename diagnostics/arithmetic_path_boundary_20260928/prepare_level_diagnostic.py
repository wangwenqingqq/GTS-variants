#!/usr/bin/env python3
"""Add per-level node counts to the separate non-timed work binary."""
import argparse
import shutil
from pathlib import Path


def once(source, old, new):
    assert source.count(old) == 1, (old, source.count(old))
    return source.replace(old, new)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("out", type=Path)
    out = parser.parse_args().out
    shutil.copytree(Path(__file__).resolve().parent / "work_build", out, symlinks=True)
    header = out / "strict_l2.cuh"
    h = header.read_text()
    h = once(h, "work_counters[7]", "work_counters[17]")
    h = once(h, "const unsigned long long* upper) {\n    const int i=blockIdx.x*blockDim.x+threadIdx.x;",
             "const unsigned long long* upper,int level) {\n    const int i=blockIdx.x*blockDim.x+threadIdx.x;")
    h = once(h, "    if(radius<0||flags[(nid-1)/TREE_ORDER]!=1||empty[nid]!=0)return;",
             "    if(radius<0||flags[(nid-1)/TREE_ORDER]!=1||empty[nid]!=0)return;\n    atomicAdd(work_counters+7+2*(level-1),1ull);")
    h = once(h, "    flags[nid]=1;", "    atomicAdd(work_counters+8+2*(level-1),1ull);\n    flags[nid]=1;")
    header.write_text(h)
    source = out / "graph_bench.cu"
    s = source.read_text()
    assert s.count("empty_list,lower,upper);") == 2
    s = s.replace("empty_list,lower,upper);", "empty_list,lower,upper,level);")
    s = once(s, "7*sizeof(unsigned long long)", "17*sizeof(unsigned long long)")
    s = once(s, "unsigned long long c[7]", "unsigned long long c[17]")
    s = once(s, "pivot_abnormal\\n\";}",
             "pivot_abnormal,level1_in,level1_out,level2_in,level2_out,level3_in,level3_out,level4_in,level4_out,level5_in,level5_out\\n\";}")
    source.write_text(s)


if __name__ == "__main__":
    main()
