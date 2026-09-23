#!/usr/bin/env python3
"""Pinned GTSPP copy with host-only stages and an optional isolated aggregation control."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil

HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[1]
spec=importlib.util.spec_from_file_location('base',HERE.parent/'cpu_io/prepare.py');base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
def prepare(out,variant):
    pins=json.loads((HERE.parent/'cpu_io/SOURCE_PINS.json').read_text())
    for name,h in pins['sha256'].items(): assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==h,name
    out.mkdir(parents=True,exist_ok=False)
    for name in pins['sha256']:
        p=out/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,p)
    p=out/'include/search_v2.cuh';s=p.read_text();pre,marker,rest=s.partition('void searchIndexRnnV2(');assert marker
    body,end,post=rest.partition('void searchIndexKnnV2(');assert end
    body=base.replace_once(body,'\tcout << "Searching..." << endl;','\tQueryStages phase; phase.set("stage.alloc_init");')
    body=base.replace_once(body,'\tsize_t limit = 4ULL * 1024 * 1024 * 1024;', '\tsize_t limit = 256ULL * 1024 * 1024;')
    body=base.replace_once(body,'\t\t\t\tprintf("qnum_l_low: %lu\\n", qnum_l_low);','\t\t\t\t// Diagnostic printing disabled.')
    for anchor,name in [('\t\t// Get the preparation information for queries','stage.schedule'),('\t\t\tnodeProcessRnn<<<','stage.node_distance_prune'),('\t\t\t// Get query information.','stage.candidates'),('\t\t\t// Processing data in leaf node.\n\t\t\tblock_num = lnum;','stage.leaf_distance'),('\t\t\t// Merge result.','stage.aggregate'),('\n\t\t// Update the query and storage space information and of lower layer.','stage.schedule'),('\t// Release memory','stage.cleanup')]:
        body=base.replace_once(body,anchor,f'\tphase.set("{name}");\n'+anchor)
    if variant=='B':
        begin=pre.index('__global__ void mergeResRnn('); opening=pre.index('{',begin); level=1; closing=opening+1
        while level:
            level+=(pre[closing]=='{')-(pre[closing]=='}'); closing+=1
        pre=pre[:opening+1]+'\n'+(HERE/'aggregate_block.cuh').read_text()+pre[closing-1:]
        body=base.replace_once(body,'block_num = (le - ls + THREAD_NUM - 1) / THREAD_NUM;', 'block_num = le - ls;')
    p.write_text(pre+marker+body+end+post)
    shutil.copy2(HERE.parent/'query_breakdown/stages.hpp',out/'include/query_stages.hpp')
    shutil.copy2(HERE.parent/'cpu_io/profile.hpp',out/'include/gts_cpu_io_profile.hpp')
    shutil.copy2(HERE/'driver.cu',out/'src/main.cu')
    files={str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.rglob('*')) if p.is_file()}
    (out/'MANIFEST.json').write_text(json.dumps({'variant':variant,'files':files},indent=2)+'\n')
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('out',type=Path);p.add_argument('--variant',choices=['A','B'],required=True);a=p.parse_args();prepare(a.out,a.variant)
