#!/usr/bin/env python3
"""Pin the exact keeper source; patch one pivot load and one Host hook."""
import argparse,difflib,hashlib,json,shutil
from pathlib import Path

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('keeper',type=Path);p.add_argument('root',type=Path);a=p.parse_args()
    expected=Path(__file__).resolve().parent.parent/'evidence/SOURCE_AUDIT.json'
    pins={str(f.relative_to(a.keeper)):sha(f) for f in sorted(a.keeper.rglob('*')) if f.is_file()}
    if expected.exists():assert pins==json.loads(expected.read_text())['keeper_files'],'keeper source drift'
    src=a.root/'source';shutil.copytree(a.keeper,src)
    before=(src/'include/tree.cuh').read_text();after=before
    replacements=[('#include "build_tiles.hpp"','#include "build_tiles.hpp"\n#include "counterfactual.hpp"'),
      ('\t\t\tpid[0] = id_list[(lid + rid) / 2];\n\t\t\tif (tile == 0)', '\t\t\tpid[0] = causal_forced && causal_forced[nid]>=0 ? causal_forced[nid] : id_list[(lid + rid) / 2];\n\t\t\tif (tile == 0)'),
      ('        bt::before(cur_level,block_num,start_idx,node_list,empty_list,split_list,id_list);','        bt::before(cur_level,block_num,start_idx,node_list,empty_list,split_list,id_list);\n        causal::before(cur_level,block_num,start_idx,node_list,id_list);')]
    for old,new in replacements:assert after.count(old)==1;after=after.replace(old,new)
    (src/'include/tree.cuh').write_text(after)
    shutil.copyfile(Path(__file__).parent/'counterfactual.hpp',src/'include/counterfactual.hpp')
    shutil.copyfile(Path(__file__).parent/'replay.cu',src/'src/replay.cu')
    audit={'keeper_files':{str(f.relative_to(a.keeper)):sha(f) for f in sorted(a.keeper.rglob('*')) if f.is_file()},
           'replay_files':{str(f.relative_to(src)):sha(f) for f in sorted(src.rglob('*')) if f.is_file()},
           'changes':['one optional selected-pivot load in getPivotDisTiled','one pre-launch Host hook','separate standalone main; no service edits'],
           'unchanged_device_functions':['getPivotDis','nodeSplit','initIndexData','target numeric helpers/refit'],'geometry':'unchanged TILED 512 threads'}
    (a.root/'SOURCE_AUDIT.json').write_text(json.dumps(audit,indent=2)+'\n')
    (a.root/'intervention.patch').write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='include/tree.cuh',tofile='include/tree.cuh',n=0)))
if __name__=='__main__':main()
