#!/usr/bin/env python3
"""Instrument pinned kNN overloads with an optional bounded leaf-warp overlay."""
import argparse,hashlib,importlib.util,json,re,shutil
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
s=importlib.util.spec_from_file_location('base',HERE.parent/'cpu_io/prepare.py');base=importlib.util.module_from_spec(s);s.loader.exec_module(base)
def prepare(out,variant='A'):
    pins=json.loads((HERE.parent/'cpu_io/SOURCE_PINS.json').read_text())
    for name,h in pins['sha256'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==h,name
    out.mkdir(parents=True,exist_ok=False)
    for name in pins['sha256']:
        p=out/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,p)
    p=out/'include/search_v2.cuh';text=p.read_text();matches=list(re.finditer(r'(?m)^void searchIndexKnnV2\([^;{}]*\)\s*\{',text));assert len(matches)==4
    for m in reversed(matches):
        begin=m.end();end=begin;level=1
        while level:level+=(text[end]=='{')-(text[end]=='}');end+=1
        body=text[begin:end-1]
        body=base.replace_once(body,'\tcout << "Searching..." << endl;','\tQueryStages phase; phase.set("stage.alloc_init");')
        body=re.sub(r'^\s*printf\("qnum_l_low:[^\n]+','\n\t\t\t\t// Diagnostic printing disabled.',body,flags=re.M)
        for anchor,label in [('// Get the preparation information for queries','schedule'),('int pnum_level =','node_plan'),('labelCNode<<<','node_prune'),('// Get counts of query.','candidates'),('// Merge result.','aggregate'),('// Update the query and storage space information and of lower layer.','schedule'),('// Release memory','cleanup')]:
            replacement=f'phase.set("stage.{label}");\n\t\t'+anchor
            if anchor.startswith('// Update the query'):
                assert body.count(anchor) in [1,2];body=body.replace(anchor,replacement,1)
            else:body=base.replace_once(body,anchor,replacement)
        for pattern,label in [(r'getDisPQ(?:Vec)?<<<','pivot_distance'),(r'updateDisK<<<','threshold'),(r'nodeProcessKnn<<<','node_prune'),(r'dataProcessKnn(?:Vec)?<<<','leaf_distance')]:
            body,n=re.subn(pattern,lambda m:f'phase.set("stage.{label}");\n\t\t\t'+m.group(),body);assert n==1,(pattern,n)
        i=0
        def sort(m):
            nonlocal i
            label=['pivot_sort','result_sort'][i];i+=1;return f'phase.set("stage.{label}");\n\t\t\t'+m.group()
        body=re.sub(r'thrust::sort_by_key\(thrust::device',sort,body);assert i==2
        text=text[:begin]+body+text[end-1:]
    if variant in ['B','C','D']:
        start=text.index('__global__ void dataProcessKnn(')
        helper=(HERE/('leaf_warp_store.cuh' if variant=='D' else 'leaf_warp.cuh')).read_text()
        if variant=='C':helper=helper.replace('did+=16','did+=blockDim.x/32')
        text=text[:start]+helper+'\n'+text[start:]
        for kernel,call in [('dataProcessKnn','knnLeafL2Warp<false>(node_list,disk,data_d,qid_list,nullptr,data_info,p_list_k,offset_p,id_list,cur_level,size_list);'),('dataProcessKnnVec','knnLeafL2Warp<true>(node_list,disk,data_d,nullptr,query_data,data_info,p_list_k,offset_p,id_list,cur_level,size_list);')]:
            start=text.index('__global__ void '+kernel+'(');opening=text.index('{',start)
            text=text[:opening+1]+'\n\tif(data_info[2]==2){'+call+'return;}\n'+text[opening+1:]
    if variant in ['C','D']:
        text,n=re.subn(r'(dataProcessKnn(?:Vec)?<<<block_num, )THREAD_NUM(>>>)',r'\g<1>64\2',text);assert n==4
    p.write_text(text)
    shutil.copy2(HERE.parent/'query_breakdown/stages.hpp',out/'include/query_stages.hpp')
    shutil.copy2(HERE.parent/'cpu_io/profile.hpp',out/'include/gts_cpu_io_profile.hpp')
    shutil.copy2(HERE/'driver.cu',out/'src/main.cu')
    files={str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.rglob('*')) if p.is_file()}
    (out/'MANIFEST.json').write_text(json.dumps({'variant':variant,'files':files},indent=2)+'\n')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('out',type=Path);p.add_argument('--variant',choices=['A','B','C','D'],default='A');a=p.parse_args();prepare(a.out,a.variant)
