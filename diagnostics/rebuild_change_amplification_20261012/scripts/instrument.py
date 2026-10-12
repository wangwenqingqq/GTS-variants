#!/usr/bin/env python3
"""Make a separate Host observer; fail closed on keeper drift or device edits."""
import argparse,difflib,hashlib,json,re,shutil
from pathlib import Path

def kernels(text):
    out=[]
    for m in re.finditer(r'__(?:global|device)__',text):
        start=text.find('{',m.end());level=1;end=start+1
        while level and end<len(text):
            level+=(text[end]=='{')-(text[end]=='}');end+=1
        assert not level
        out.append(text[m.start():end])
    return out

def main():
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    shutil.copytree(a.source,a.output)
    replacements={
      'include/tree.cuh':[
       ('#include "build_tiles.hpp"','#include "build_tiles.hpp"\n#include "build_counts.hpp"'),
       ('        bt::before(cur_level,block_num,start_idx,node_list,empty_list,split_list,id_list);',
        '        rca::before_build(cur_level,block_num,start_idx,node_list,split_list);\n        bt::before(cur_level,block_num,start_idx,node_list,empty_list,split_list,id_list);')],
      'include/update.cuh':[
       ('void updateIndexRnn(short *&data_d','#include "snapshot.hpp"\n\nvoid updateIndexRnn(short *&data_d'),
       ('        pe::submit(i,update_list[i].update_flag,data_d,tree_size,in_size,insert_list,update_list[i].update_id);',
        '        pe::submit(i,update_list[i].update_flag,data_d,tree_size,in_size,insert_list,update_list[i].update_id);\n        rca::event(i,update_list[i].update_flag);'),
       ('\t\t\t\tu10.begin_rebuild();','\t\t\t\tu10.begin_rebuild();\n                rca::pre(node_list,empty_list,id_list,max_node_num[0],tree_size,data_info[0],is_delete,insert_list,in_size);'),
       ('\t\t\t\tu10.end_rebuild();','                rca::post(node_list,empty_list,id_list,max_node_num[0],tree_size,data_info[0],is_delete,insert_list,in_size);\n\t\t\t\tu10.end_rebuild();')]
    }
    diffs=[];pins={};counts=0
    for f in sorted(a.source.rglob('*')):
        if not f.is_file():continue
        rel=f.relative_to(a.source);old=f.read_text();new=old
        for before,after in replacements.get(str(rel),[]):
            assert new.count(before)==1,(rel,before);new=new.replace(before,after)
        (a.output/rel).write_text(new)
        assert kernels(old)==kernels(new),('device body changed',rel)
        counts+=len(kernels(old));pins[str(rel)]=hashlib.sha256(f.read_bytes()).hexdigest()
        if new!=old:diffs.extend(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile=str(rel),tofile=str(rel),n=0))
    for name in ('build_counts.hpp','snapshot.hpp'):shutil.copyfile(Path(__file__).parent/name,a.output/'include'/name)
    (a.output.parent/'observer.patch').write_text(''.join(diffs))
    (a.output.parent/'SOURCE_AUDIT.json').write_text(json.dumps({'keeper_files':pins,'device_function_definitions_unchanged':counts,'host_patch_files':list(replacements)},indent=2)+'\n')

if __name__=='__main__':main()
