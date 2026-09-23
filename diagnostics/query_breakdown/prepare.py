#!/usr/bin/env python3
"""Stage-only instrumentation in verified source copies; no kernel changes."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('base',HERE.parent/'original_tree_profile/prepare.py');base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)

def prepare(source,out,height):
    base.prepare(source,out)
    p=out/'GTS/include/tree.cuh';p.write_text(base.once(p.read_text(),'__managed__ int MAX_H = 3;',f'__managed__ int MAX_H = {height};'))
    p=out/'GTS/include/search_v2.cuh';text=p.read_text();pre,marker,post=text.partition('void searchIndexKnnV2(');assert marker
    pre=base.once(pre,'\tcout << "Searching..." << endl;','\tQueryStages phase; phase.set("stage.alloc_init");')
    pre=base.once(pre,'\t\t\t\tprintf("qnum_l_low: %d\\n", qnum_l_low);','\t\t\t\t// Diagnostic printing disabled.')
    anchors=[('\t\t// Get the preparation information for queries','stage.schedule'),
             ('\t\t\tnodeProcessRnn<<<','stage.node_distance_prune'),
             ('\t\t\t// Get query information.','stage.candidates'),
             ('\t\t\t// Processing data in leaf node.\n\t\t\tblock_num = lnum;','stage.leaf_distance'),
             ('\t\t\t// Merge result.','stage.aggregate'),
             ('\n\t\t// Update the query and storage space information and of lower layer.','stage.schedule'),
             ('\t// Release memory','stage.cleanup')]
    for anchor,name in anchors:pre=base.once(pre,anchor,f'\tphase.set("{name}");\n'+anchor)
    p.write_text(pre+marker+post)
    shutil.copy2(HERE/'stages.hpp',out/'GTS/include/query_stages.hpp')
    shutil.copy2(HERE/'driver.cu',out/'GTS/src/main.cu')
    m={str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.rglob('*')) if p.is_file() and p.name!='INSTRUMENTED_SHA256.json'}
    (out/'INSTRUMENTED_SHA256.json').write_text(json.dumps(m,indent=2)+'\n')

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('source',type=Path);ap.add_argument('out',type=Path);ap.add_argument('--height',choices=[3,5],type=int,required=True);a=ap.parse_args();prepare(a.source,a.out,a.height)
