#!/usr/bin/env python3
"""Add removable observation-only sidecars to the pinned complete-output GTS."""
import argparse,hashlib,importlib.util,json,shutil
from pathlib import Path
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'native_knn_faiss_ivf_20261003'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def once(s,a,b):
    assert s.count(a)==1,(a,s.count(a))
    return s.replace(a,b)
def insert(s,name,anchor,code):
    start=s.index('__global__ void '+name+'(');end=s.index('\n}\n',start)+3
    body=s[start:end]
    body=once(body,anchor,anchor+'\n// LG_BEGIN\n#if LG_COUNTS\n'+code+'\n#endif\n// LG_END')
    return s[:start]+body+s[end:]
def instrument(s):
    s=insert(s,'nodeProcessKnn','\t\t\tif (dis_lb <= disk[qid])\n\t\t\t\tp_list_k[offset_p + ofst + i] = 1;',
      '            lg_rows[nid].tested=1; lg_rows[nid].lower=dis_lb;\n'
      '            lg_rows[nid].node_bound=disk[qid]; lg_rows[nid].passed=(dis_lb<=disk[qid]);')
    # Original bound-free prefix marking is counted separately, not invented as a lower bound.
    s=insert(s,'labelCNode','\t\t\tp_list_k[offset_p + ofst + i] = 1;',
      '            lg_rows[nid].tested=2; lg_rows[nid].passed=1;')
    s=insert(s,'getDisPQ','\t\t\tTN node = node_list[nid];',
      '            atomicAdd(&lg_pivots[0],1ULL); atomicAdd(&lg_pivots[1],(unsigned long long)data_info[0]);')
    s=insert(s,'dataProcessKnn','\tTN node = node_list[nid];',
      '    if(tid==0) {atomicAdd(&lg_rows[nid].visits,1U);lg_rows[nid].leaf_bound=disk[qid];lg_rows[nid].leaf_task=bid;}')
    s=insert(s,'dataProcessKnn','\t\t\tint data_id = id_list[node.lid + did];',
      '            atomicOr(&lg_rows[nid].valid_mask,1U<<did);\n'
      '            if(data_id!=qid_list[qid]) atomicOr(&lg_rows[nid].compute_mask,1U<<did);')
    s=insert(s,'dataProcessKnn','\t\t\tif (result > disk[qid])\n\t\t\t{\n\t\t\t\tresult = INFI_DIS;\n\t\t\t}',
      '            if(result<=disk[qid]) atomicOr(&lg_rows[nid].accepted_mask,1U<<did);')
    return s

def prepare(source,out):
    assert not out.exists();out.mkdir(parents=True)
    spec=importlib.util.spec_from_file_location('original_adapter',BASE/'prepare_gts.py')
    adapter=importlib.util.module_from_spec(spec);spec.loader.exec_module(adapter)
    adapter.prepare(source,out/'shared')
    original=(out/'shared/adapted/include/search_v2.cuh').read_text()
    shutil.copytree(out/'shared/adapted',out/'count')
    (out/'count/include/search_v2.cuh').write_text(instrument(original))
    shutil.copy2(HERE/'geometry.cuh',out/'count/include/geometry.cuh')
    driver=(BASE/'gts_bench.cu').read_text()
    driver=once(driver,'(batch==1||batch==32)','batch==1')
    driver=once(driver,'#include "search_v2.cuh"','#include "geometry.cuh"\n#include "search_v2.cuh"')
    driver=once(driver,'    std::ifstream cache(argv[6],std::ios::binary); bool cache_loaded=bool(cache);',
        '    std::ifstream cache(argv[6],std::ios::binary); bool cache_loaded=bool(cache);\n    require(cache_loaded,"reference index must exist");')
    driver=once(driver,'    double index_setup_ms=elapsed(index_begin);', '''    double index_setup_ms=elapsed(index_begin);
    lg_setup(max_nodes[0]);
    std::ofstream geometry;
#if LG_COUNTS
    geometry.open(std::string(argv[7])+".geometry.bin",std::ios::binary);
    int header[4]={0x4c474531,n,d,max_nodes[0]};geometry.write((char*)header,16);
#endif''')
    driver=once(driver,'        update_disk=false;','        lg_reset();\n        update_disk=false;')
    driver=once(driver,'        ck(cudaDeviceSynchronize());nvtxRangePop();',
        '        ck(cudaDeviceSynchronize());\n        if(collect) lg_save(geometry,query_ids[start]);\n        nvtxRangePop();')
    driver=once(driver,'    for(void* p:{','    lg_close();\n    for(void* p:{')
    (out/'bench.cu').write_text(driver)
    pins={'upstream':json.loads((out/'shared/SOURCE_PINS.json').read_text()),
          'generator_sha256':sha(Path(__file__)),'adapter_sha256':sha(BASE/'prepare_gts.py'),
          'base_driver_sha256':sha(BASE/'gts_bench.cu'),
          'files':{str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file()}}
    (out/'SOURCE_PINS.json').write_text(json.dumps(pins,indent=2)+'\n')
    return pins
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('out',type=Path)
    a=p.parse_args();prepare(a.source,a.out)
