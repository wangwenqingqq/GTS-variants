#!/usr/bin/env python3
"""Deterministic native replay: original-row inserts, logical-row deletes, query 0."""
import argparse
from pathlib import Path
CASES={
 'query_only':[(2,0)]*8,
 'all_include':[(2,0)],
 'base_delete':[(1,1),(2,0)],
 'direct_insert':[(0,0),(2,0)],
 'direct_delete':[(0,0),(1,2000),(2,0)],
 'buffer_query':[(0,0)]*65+[(2,0)],
 'buffer_delete':[(0,0)]*65+[(1,2000),(1,2000)],
 'rebuild':[(0,0)]*66+[(2,0)],
}
def generate(out):
 out.mkdir(exist_ok=False,parents=True)
 for name,ops in CASES.items():(out/(name+'.txt')).write_text(str(len(ops))+'\n'+''.join(f'{flag} {idx}\n' for flag,idx in ops))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('out',type=Path);generate(p.parse_args().out)
