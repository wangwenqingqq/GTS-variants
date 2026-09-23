#!/usr/bin/env python3
"""Add one bounded fusion to the pinned existing driver in a fresh private root."""
import argparse
import hashlib
import importlib.util
from pathlib import Path
import shutil
import sys
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('graph_prepare',HERE.parent/'graph_query_20260923/prepare.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
base_prepare=base.prepare


def replace_once(text,old,new):
    assert text.count(old)==1, old
    return text.replace(old,new)


def transform(text):
    assert hashlib.sha256(text.encode()).hexdigest()=='6065bd4b9f2de6cb231ca416afeea55dce395f5d2713c37aae1c79c0a60ee3a5'
    text=replace_once(text,'struct Fixed {','#include "fused_result.cuh"\n\nstruct Fixed {\n    bool fused;')
    text=replace_once(text,'Fixed(int count_n,int h):n(count_n),height(h)',
                      'Fixed(int count_n,int h,bool f=false):fused(f),n(count_n),height(h)')
    start='        ck(cub::DeviceReduce::Sum(temp,tempbytes,hits,hit_count,slots,stream));'
    end='        projectBounded<<<(slots+511)/512,512,0,stream>>>(count,outids,outdis,ids,ds,is_delete_prefix);'
    old=text[text.index(start):text.index(end)+len(end)]
    text=replace_once(text,old,'''        if(fused) {
            ck(cub::DeviceScan::InclusiveSum(temp,tempbytes,is_delete,is_delete_prefix,n,stream));
            fusedResultSelect<<<1,512,0,stream>>>(candidate_count,hits,rawids,rawdis,is_delete_prefix,count,outids,outdis);
        } else {
'''+old+'\n        }')
    text=text.replace('A|B|C radius','A|B|C|D|E radius')
    text=replace_once(text,'mode=="A"||mode=="B"||mode=="C"','mode=="A"||mode=="B"||mode=="C"||mode=="D"||mode=="E"')
    text=replace_once(text,'new Fixed(tree_size,tree_h)','new Fixed(tree_size,tree_h,mode=="D"||mode=="E")')
    assert text.count('mode=="C"')==3
    # The mode-admission condition may repeat E harmlessly; retain exact clarity.
    text=text.replace('if(mode=="C")','if(mode=="C"||mode=="E")')
    text=text.replace('fixed->query(q,radius,mode=="C")','fixed->query(q,radius,mode=="C"||mode=="E")')
    return text


def prepare(source,fixtures,out):
    base_prepare(source,fixtures,out)
    file=out/'graph_bench.cu';file.write_text(transform(file.read_text()))
    for name in ['fused_result.cuh','test_selector.cu','suite.py']:shutil.copy2(HERE/name,out/name)
    runner=out/'run.py';s=runner.read_text().replace("choices=['A','B','C']","choices=['A','B','C','D','E','T']")
    s=s.replace("'synccheck','initcheck']","'synccheck','initcheck','racecheck']")
    s=replace_once(s,"    if tool.startswith('nsys'):","    if mode=='T':cmd=[str(root/'bin/test_selector')]\n    if tool.startswith('nsys'):")
    s=replace_once(s,"gold=root/'fixtures'/f'expected_{radius:g}.json'", "gold=root/'fixtures'/('expected_selector.json' if mode=='T' else f'expected_{radius:g}.json')")
    s=replace_once(s,"    record={'label':label", "    if mode=='T':\n        validation={'pass':'PASS selector 132 cases' in logs,'scope':'standalone selector regression'}\n        if not validation['pass']:errors.append('selector check incomplete')\n    record={'label':label")
    s=replace_once(s,"(root/'bin/graph_bench').read_bytes()", "(root/'bin'/('test_selector' if mode=='T' else 'graph_bench')).read_bytes()")
    (out/'run_fusion.py').write_text(s)
    print('Added fused selector and D/E modes; prior driver and author sources untouched')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['source','fixtures','out']:p.add_argument(name,type=Path)
    a=p.parse_args();prepare(a.source,a.fixtures,a.out)
