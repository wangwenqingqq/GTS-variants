#!/usr/bin/env python3
"""Generate one isolated repaired V2 executor; never edits upstream or prior campaigns."""
import argparse
import difflib
import importlib.util
import json
from pathlib import Path
import shutil
from audit import sha, save, source_audit

HERE=Path(__file__).resolve().parent
BASE=HERE.parent.parent/'diagnostics/native_knn_faiss_ivf_20261003'


def once(s,old,new):
    if s.count(old)!=1:raise ValueError('source anchor drift: '+repr(old))
    return s.replace(old,new)


def kernel(s,name):
    start=s.index('__global__ void '+name+'(');end=s.index('\n}\n',start)+3
    return start,end,s[start:end]


def prepare(source,out):
    source_audit(source)
    spec=importlib.util.spec_from_file_location('shared_adapter',BASE/'prepare_gts.py')
    base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
    base.prepare(source,out)
    inc=out/'adapted/include';s=(inc/'search_v2.cuh').read_text();original=s
    # Common precise ranking arithmetic; the same function serves pivots and leaves.
    for name,old,new in [
        ('getDisPQ','dis_q += pow(data_d[node.pid * data_info[0] + j] - data_d[qid_list[qid] * data_info[0] + j], 2);',''),
        ('dataProcessKnn','result += pow(data_d[data_id * data_info[0] + j] - data_d[qid_list[qid] * data_info[0] + j], 2);','')]:
        a,b,k=kernel(s,name)
        if name=='getDisPQ':
            begin=k.index('\t\t\t\tfor (int j = 0; j < data_info[0]; j++)')
            end=k.index('\n\t\t\t}',begin)
            k=k[:begin]+'\t\t\t\tdis_q = nav_distance(data_d,node.pid,qid_list[qid],data_info[0],true);'+k[end:]
        else:
            # Include self in the same arithmetic/identity path.
            begin=k.index('\t\t\tresult = 0;');end=k.index('\n\t\t\telse if (data_info[2] == 1)',begin)
            k=k[:begin]+'\t\t\tresult = nav_distance(data_d,data_id,qid_list[qid],data_info[0],false);\n\t\t\tif (false) {}'+k[end:]
        s=s[:a]+k+s[b:]
    # Double thresholds and conservative native split tests are common repairs.
    s=s.replace('float *disk','double *disk')
    s=once(s,'CHECK(cudaMalloc((void **)&disk, qnum * sizeof(float)));',
             'CHECK(cudaMalloc((void **)&disk, qnum * sizeof(double)));')
    a,b,k=kernel(s,'initDisK')
    k=once(k,'disk[i] = INFI_DIS;','disk[i] = INFINITY;')
    s=s[:a]+k+s[b:]
    a,b,k=kernel(s,'nodeProcessKnn')
    k=once(k,'float dis_q =','double dis_q =').replace('float dis_lb =','double dis_lb =').replace('float dis_lb2 =','double dis_lb2 =')
    k=once(k,'node.min_dis - dis_q','double(node.min_dis) - .01 - (dis_q + 1e-6)')
    k=once(k,'dis_q - node_list[nid + 1].min_dis','(dis_q - 1e-6) - (double(node_list[nid + 1].min_dis) + .01)')
    k=once(k,'if (dis_lb <= disk[qid])','nav_count(7);\n            if (!nav.safe[nid] || dis_lb <= disk[qid] + 1e-6)')
    s=s[:a]+k+s[b:]
    # Replace only the current-level threshold implementation, not the native traversal.
    anchor='updateDisK<<<(qnum_l + THREAD_NUM - 1) / THREAD_NUM, THREAD_NUM>>>(qnum_l, p_list_k, disk, nnum_l, offset_p, qs, k);'
    s=once(s,anchor,'nav_update<<<1,1>>>(node_list,offset_n,pnum_level_total,p_list_k,offset_p,disk);')
    anchor='\n\t\t\t\t// Process the nodes of the current layer and determine if the node will be pruned.'
    start=s.index('void searchIndexKnnV2(')
    s=s[:start]+once(s[start:],anchor,'\n                nav_replay_level(disk);'+anchor)
    a=s.rindex('\n\t\t\t// Sort by distances.')
    b=s.index('\n\t\t}',a)
    s=s[:a]+'''
            // Stable complete output with exact squared-score keys and carried witnesses.
            CHECK(cudaMalloc((void**)&nav.keys,(size_t(lnum)*MAX_SIZE+k)*sizeof(NavKey)));
            int cap=size_list[cur_level]/(MAX_SIZE*3+3);
            nav_keys<<<(lnum*MAX_SIZE+k+255)/256,256>>>(node_list,id_list,p_list_k,offset_p,cap,lnum*MAX_SIZE);
            CHECK(cudaDeviceSynchronize());
            thrust::sort(thrust::device,nav.keys,nav.keys+lnum*MAX_SIZE+k,NavLess{});
            nav_emit<<<1,32>>>(lnum*MAX_SIZE);
            CHECK(cudaDeviceSynchronize());
''' + s[b:]
    start=s.index('void searchIndexKnnV2(')
    h=s[start:]
    h=once(h,'\n\tCHECK(cudaMallocManaged((void **)&res_dis,',
        '\n    if(qnum!=1 || k!=nav.k) throw std::runtime_error("B1/K contract");\n    nav_begin();\n\tCHECK(cudaMallocManaged((void **)&res_dis,')
    # Complete scores are exported before releasing per-query workspace.
    h=once(h,'\t// Release memory\n','\t// Release memory\n    nav_end();\n')
    s=s[:start]+h
    # Diagnostic copies are excluded from uninstrumented timing.
    anchor='\n\t\t// Update the query and storage space information and of lower layer.'
    start=s.index('void searchIndexKnnV2(')
    h=s[start:]
    h=once(h,anchor,'''\n        if(nav.counts && cur_level<tree_h) {
            nav_trace(cur_level,offset_n,nnum_l,p_list_k,offset_p,disk);
        }
''' + anchor)
    s=s[:start]+h
    (inc/'search_v2.cuh').write_text(s);shutil.copy2(HERE/'navigation.cuh',inc/'navigation.cuh')
    driver=(BASE/'gts_bench.cu').read_text()
    driver=once(driver,'#include "search_v2.cuh"','#include "navigation.cuh"\n#include "search_v2.cuh"')
    driver=once(driver,'(batch==1||batch==32)','batch==1')
    driver=once(driver,'input.read(reinterpret_cast<char*>(block.data()),count*sizeof(float)); require(bool(input),"data payload");',
        'input.read(reinterpret_cast<char*>(block.data()),count*sizeof(float)); require(bool(input),"data payload");\n        for(float x:block) require(std::isfinite(x)&&x>=0.f&&x<=2.f,"finite [0,2] geometry envelope");')
    driver=once(driver,'double index_setup_ms=elapsed(index_begin);', '''
    const int mode=std::stoi(std::getenv("NAV_MODE")?std::getenv("NAV_MODE"):"0");
    bool diagnostic=std::getenv("NAV_DIAGNOSTIC")!=nullptr;
    require(mode>=0&&mode<=3,"mode");
    if(const char* replay=std::getenv("NAV_REPLAY")) {
        require(diagnostic && warm==0 && repeats==1 && (mode&2),"diagnostic replay only");
        std::ifstream timeline(replay);require(bool(timeline),"replay open");
        double value;while(timeline>>value)nav_replay_upper.push_back(value);
        require(nav_replay_upper.size()==size_t(q)*(height-3),"replay length");
    }
    nav_setup(nodes,empty,max_nodes[0],n,height,k,mode,diagnostic,data,ids,d);
    double index_setup_ms=elapsed(index_begin);
    std::vector<double> result_scores(size_t(q)*k);std::vector<std::array<unsigned long long,8>> counts;
''')
    driver=once(driver,'diag_ids,size_t(count)*k*sizeof(int)','nav.out_ids,size_t(count)*k*sizeof(int)')
    driver=once(driver,'ck(cudaMemcpy(result_dist.data()+size_t(start)*k,diag_dist,size_t(count)*k*sizeof(float),cudaMemcpyDeviceToHost));',
        'ck(cudaMemcpy(result_scores.data()+size_t(start)*k,nav.out_scores,size_t(count)*k*sizeof(double),cudaMemcpyDeviceToHost));\n            for(int j=0;j<k;++j)result_dist[size_t(start)*k+j]=float(std::sqrt(result_scores[size_t(start)*k+j]));')
    driver=once(driver,'diag_ids,wi.size()*sizeof(int)','nav.out_ids,wi.size()*sizeof(int)')
    driver=once(driver,'ck(cudaMemcpy(wd.data(),diag_dist,wd.size()*sizeof(float),cudaMemcpyDeviceToHost));',
        'std::vector<double> ws(count*k);ck(cudaMemcpy(ws.data(),nav.out_scores,ws.size()*sizeof(double),cudaMemcpyDeviceToHost));')
    driver=once(driver,'ck(cudaDeviceSynchronize());nvtxRangePop();', '''
        ck(cudaDeviceSynchronize());
        if(collect && diagnostic) {std::array<unsigned long long,8> row;
            ck(cudaMemcpy(row.data(),nav.counts,8*sizeof(unsigned long long),cudaMemcpyDeviceToHost));counts.push_back(row);}
        nvtxRangePop();''')
    driver=once(driver,'write_vec(output,result_ids);write_vec(output,result_dist);','write_vec(output,result_ids);write_vec(output,result_scores);')
    driver=once(driver,'<<",\\\"height\\\":"<<height',
        '<<",\\\"metric_contract_id\\\":\\\"fp32_input_rn_fp64_ordered_squared_l2_id_v1\\\",\\\"uses_oracle\\\":false,\\\"mode\\\":"<<mode<<",\\\"diagnostic\\\":"<<(diagnostic?"true":"false")<<",\\\"height\\\":"<<height')
    driver=once(driver,'    for(void* p:{','''
    if(diagnostic) {
        std::ofstream work(std::string(argv[7])+".work.csv");work<<"qid,pivot_calls,leaf_calls,pivot_hits,leaf_hits,full_computations,coordinate_updates,cache_insertions,bound_tests\\n";
        for(size_t i=0;i<counts.size();++i){work<<query_ids[i%q];for(auto x:counts[i])work<<','<<x;work<<'\\n';}
    }
    for(void* p:{(void*)nav.slot,(void*)nav.safe,(void*)nav.out_ids,(void*)nav.out_scores,(void*)nav.counts})if(p)ck(cudaFree(p));
    for(void* p:{''')
    (out/'bench.cu').write_text(driver)
    (out/'common.patch').write_text(''.join(difflib.unified_diff(original.splitlines(True),s.splitlines(True),'shared/search_v2.cuh','repaired/search_v2.cuh')))
    save(out/'NAV_SOURCE.json',dict(metric_contract_id='fp32_input_rn_fp64_ordered_squared_l2_id_v1',
        upstream_commit='3bac1b725e92e98e3b69d5cb79ad9c56ccb5e639',generator_sha256=sha(__file__),
        shared_input_sha256={str(p.relative_to(HERE.parent.parent)):sha(p) for p in
            [BASE/'prepare_gts.py',BASE/'gts_bench.cu',BASE/'ORIGINAL_SOURCE_PINS.json']},
        files={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file()},
        prototype_only=True,all_required_edges_and_capacity_tests_pass=False))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('out',type=Path)
    a=p.parse_args();prepare(a.source,a.out)
