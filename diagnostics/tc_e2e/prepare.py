#!/usr/bin/env python3
"""Wire the frozen leaf kernels into pinned original GTS copies only."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('original_prepare',HERE.parent/'original_tree_profile/prepare.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)

def prepare(source,out,height):
    base.prepare(source,out)
    p=out/'GTS/include/tree.cuh';p.write_text(base.once(p.read_text(),'__managed__ int MAX_H = 3;',f'__managed__ int MAX_H = {height};'))
    p=out/'GTS/include/search_v2.cuh';text=p.read_text();prefix,marker,tail=text.partition('void searchIndexKnnV2(');assert marker
    # Keep traversal/list formation unchanged; only select the leaf/count body.
    a=prefix.index('\t\t\t// Processing data in leaf node.\n\t\t\tblock_num = lnum;')
    b=prefix.index('\n\t\t}\n\n\t\t// Update the query and storage space',a)
    old=prefix[a:b]
    replacement='\t\t\tif (tc_variant == \'O\') {\n'+old+'\n\t\t\t} else {\n\t\t\t\ttc_refine(data_d,qid_list,qnum,r,lnum,p_list,offset_p,size_list[cur_level]/(MAX_SIZE+3),res);\n\t\t\t}\n'
    prefix=prefix[:a]+replacement+prefix[b:]
    anchor='\tCHECK(cudaMallocManaged((void **)&res, qnum * sizeof(int)));'
    prefix=base.once(prefix,anchor,anchor+'\n\tif (tc_variant != \'O\') CK(cudaMemset(res,0,qnum*sizeof(int)));')
    prefix=base.once(prefix,'\tcout << "Searching..." << endl;','\t// Suppress diagnostic query printing identically for O/S/T.')
    prefix=base.once(prefix,'\t\t\t\tprintf("qnum_l_low: %d\\n", qnum_l_low);','\t\t\t\t// Suppress diagnostic query printing identically for O/S/T.')
    p.write_text(prefix+marker+tail)
    kernels=(HERE.parent/'tc_leaf_probe/probe.cu').read_text().split('int main(int argc,char** argv) try {')[0]
    assert kernels.count('__global__')==3 and 'int main(' not in kernels
    (out/'GTS/include/leaf_kernels.cuh').write_text('#pragma once\n'+kernels)
    shutil.copy2(HERE/'bridge.cuh',out/'GTS/include/tc_bridge.cuh')
    shutil.copy2(HERE/'driver.cu',out/'GTS/src/main.cu')
    manifest={str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.rglob('*')) if p.is_file() and p.name!='INSTRUMENTED_SHA256.json'}
    (out/'INSTRUMENTED_SHA256.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('source',type=Path);ap.add_argument('out',type=Path);ap.add_argument('--height',type=int,choices=[3,5],required=True);a=ap.parse_args();prepare(a.source,a.out,a.height)
