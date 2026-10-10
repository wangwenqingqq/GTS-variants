#!/usr/bin/env python3
"""Generate four isolated original-kNN variants from pinned caller source."""
import argparse
import difflib
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil

HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'native_knn_faiss_ivf_20261003'

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def once(s,a,b):
    assert s.count(a)==1,(a,s.count(a))
    return s.replace(a,b)

def kernel(s,name):
    start=s.index('__global__ void '+name+'(')
    end=s.index('\n}\n',start)+3
    return start,end,s[start:end]

def instrument(s,enabled,counts):
    if not(enabled or counts): return s
    for name in ('getDisPQ','dataProcessKnn'):
        start,end,k=kernel(s,name)
        close=k.index(')\n{')
        k=k[:close]+', int *pr_slot, int *pr_valid, double *pr_distance'+k[close:]
        if name=='getDisPQ':
            k=once(k,'\t\t\tdis_q = 0;', '''
            const int slot=pr_slot[node.pid];
            PR_ADD(0,1); // Encountered pivot objects, not arithmetic calls.
            PR_ADD(9,1);
            if(pr_valid[slot]==0) PR_ADD(2,1);
#if PR_ENABLED
            if(pr_valid[slot]) {
                dis_q=pr_distance[slot];PR_ADD(3,1);PR_ADD(10,8);
#if PR_COUNTS
                pr_bridge(dis_q,data_d,node.pid,qid_list[qid],data_info[0]);
#endif
            } else
#endif
            {
            PR_ADD(1,1);PR_ADD(7,data_info[0]);
\t\t\tdis_q = 0;''')
            k=once(k,'\n\t\t}\n\n\t\t// Save result.', '''
            }
            if(pr_valid[slot]==0) {
                pr_distance[slot]=dis_q;pr_valid[slot]=1;PR_ADD(11,12);
            }
\t\t}
\n\t\t// Save result.''')
        else:
            k=once(k,'\t\t\tresult = 0;', '''
            PR_ADD(4,1);PR_ADD(20,data_id);
            const int slot=pr_slot[data_id];PR_ADD(9,1);
            const bool hit=slot>=0 && pr_valid[slot];
            if(hit) PR_ADD(5,1);
#if PR_ENABLED
            if(hit) {
                result=pr_distance[slot];PR_ADD(6,1);PR_ADD(10,8);
#if PR_COUNTS
                pr_bridge(result,data_d,data_id,qid_list[qid],data_info[0]);
#endif
            } else
#endif
            {
            if(data_id!=qid_list[qid]) {PR_ADD(8,1);PR_ADD(7,data_info[0]);}
\t\t\tresult = 0;''')
            k=once(k,'\n\t\t\tif (result > disk[qid])','\n            }\n\t\t\tif (result > disk[qid])')
            k=once(k,'\tTN node = node_list[nid];',
                   '\tTN node = node_list[nid];\n    if(tid==0) PR_ADD(12,1);')
        s=s[:start]+k+s[end:]
    # Exact native host callsites. Original work and bounds remain in place.
    start=s.index('void searchIndexKnnV2(')
    h=s[start:]
    h=once(h,'qs, qs_up, pnum_level_total);','qs, qs_up, pnum_level_total, pr_slot, pr_valid, pr_distance);')
    h=once(h,'offset_p, id_list, cur_level, size_list, nnum_up);',
           'offset_p, id_list, cur_level, size_list, nnum_up, pr_slot, pr_valid, pr_distance);')
    h=once(h,'\n\tCHECK(cudaMallocManaged((void **)&res_dis,',
           '\n    if(qnum!=1) throw std::runtime_error("reuse requires sequential B1");\n    pr_begin();\n\tCHECK(cudaMallocManaged((void **)&res_dis,')
    h=once(h,'\t// Release memory\n','\t// Release memory\n    pr_end();\n')
    s=s[:start]+h
    if counts:
        start,end,k=kernel(s,'nodeProcessKnn')
        k=once(k,'\t\t\tTN node = node_list[nid];',
               '\t\t\tTN node = node_list[nid];\n            PR_ADD(13,1);')
        k=once(k,'\t\t\tif (dis_lb <= disk[qid])\n\t\t\t\tp_list_k[offset_p + ofst + i] = 1;',
                   '\t\t\tif (dis_lb <= disk[qid]) {\n                PR_ADD(14,1);PR_ADD(21,nid);\n\t\t\t\tp_list_k[offset_p + ofst + i] = 1;\n            }')
        s=s[:start]+k+s[end:]
        start,end,k=kernel(s,'updateDisK')
        k=once(k,'\t\t\tdisk[qid] =', '\t\t\tPR_ADD(15,1);\n            if(disk[qid]>=INFI_DIS) {PR_ADD(16,1);PR_ADD(17,nnum_l);}\n\t\t\tdisk[qid] =')
        s=s[:start]+k+s[end:]
    return s

def prepare(source,out):
    assert not out.exists(),out
    spec=importlib.util.spec_from_file_location('original_adapter',BASE/'prepare_gts.py')
    base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
    out.mkdir(parents=True)
    base.prepare(source,out/'shared')
    shared=json.loads((out/'shared/SOURCE_PINS.json').read_text())
    pins={'upstream':shared,'generator_sha256':digest(Path(__file__)),
          'shared_adapter_sha256':digest(BASE/'prepare_gts.py'),
          'shared_driver_sha256':digest(BASE/'gts_bench.cu'),'variants':{}}
    driver=(BASE/'gts_bench.cu').read_text()
    driver=once(driver,'(batch==1||batch==32)','batch==1')
    driver=once(driver,'#include "search_v2.cuh"','#include "reuse.cuh"\n#include "search_v2.cuh"')
    driver=once(driver,'double index_setup_ms=elapsed(index_begin);',
                'double index_setup_ms=elapsed(index_begin);\n    pr_setup(nodes,empty,max_nodes[0],n,height);')
    driver=once(driver,'ck(cudaDeviceSynchronize());nvtxRangePop();', '''ck(cudaDeviceSynchronize());
#if PR_COUNTS
        std::array<unsigned long long,24> record;std::copy(pr_count,pr_count+24,record.begin());
        if(collect) pr_records.push_back(record);
#endif
        nvtxRangePop();''')
    driver=once(driver,'    for(void* p:{', '''
    std::ofstream meta(std::string(argv[7])+".reuse.json");
    meta<<"{\\"mapping_ms\\":"<<pr_mapping_ms<<",\\"mapping_bytes\\":"<<pr_mapping_bytes
        <<",\\"pivot_capacity\\":"<<pr_capacity<<",\\"query_workspace_bytes\\":"<<pr_capacity*12<<"}\\n";
#if PR_COUNTS
    std::ofstream counts(std::string(argv[7])+".work.csv");
    counts<<"qid,pivot_seen,pivot_computed,unique_pivot_pairs,pivot_hits,leaf_seen,pivot_leaf_seen,leaf_hits,computed_dimensions,leaf_computed,map_lookups,cache_read_bytes,cache_write_bytes,leaf_nodes,node_tests,node_pass,bound_updates,first_bound_count,first_bound_level_width,bridge_calls,bridge_mismatches,leaf_id_sum,node_id_sum,reserved22,reserved23\\n";
    require(pr_records.size()==size_t(q)*repeats,"count records");
    for(size_t i=0;i<pr_records.size();++i) {
        counts<<query_ids[i%q];for(auto value:pr_records[i]) counts<<','<<value;counts<<'\\n';
    }
#endif
    if(pr_slot) ck(cudaFree(pr_slot));
    for(void* p:{''')
    (out/'bench.cu').write_text(driver)
    for mode,enabled,counts in [('G0',0,0),('G1',1,0),('G0_count',0,1),('G1_count',1,1)]:
        target=out/mode
        shutil.copytree(out/'shared/adapted',target)
        shutil.copy2(HERE/'reuse.cuh',target/'include/reuse.cuh')
        p=target/'include/search_v2.cuh';old=p.read_text();p.write_text(instrument(old,enabled,counts))
        (out/(mode+'.patch')).write_text(''.join(difflib.unified_diff(old.splitlines(True),p.read_text().splitlines(True),
                                                                   'shared/search_v2.cuh',mode+'/search_v2.cuh')))
        pins['variants'][mode]={'enabled':enabled,'counts':counts,
            'search_sha256':digest(p),'support_sha256':digest(target/'include/reuse.cuh')}
    pins['driver_sha256']=digest(out/'bench.cu')
    (out/'SOURCE_PINS.json').write_text(json.dumps(pins,indent=2)+'\n')
    return pins

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('out',type=Path)
    a=p.parse_args();prepare(a.source,a.out)
