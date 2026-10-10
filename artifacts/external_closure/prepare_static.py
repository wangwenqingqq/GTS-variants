#!/usr/bin/env python3
"""Derive Host-only static P instrumentation from the exact admitted source."""
import argparse,json,shutil
from pathlib import Path
from common import outside_repo
from qualify import cpu
HERE=Path(__file__).resolve().parent

def once(s,old,new):
    assert s.count(old)==1,(old,s.count(old));return s.replace(old,new,1)

def prepare(parent,work):
    work=outside_repo(work);work.mkdir(parents=True,exist_ok=False)
    proof=json.loads((HERE.parent/'build_distance_tiles/evidence/QUALIFICATION.json').read_text())
    source=json.loads((parent/'PREPARED.json').read_text())
    assert cpu.sha(parent/'PREPARED.json')==proof['source']['prepared_sha256']
    assert source['sources']==proof['source']['source_hashes']
    assert all(cpu.sha(parent/'source'/k)==v for k,v in source['sources'].items())
    shutil.copytree(parent/'source',work/'source');inc=work/'source/include'
    shutil.copy2(HERE/'static_scope.hpp',inc/'static_scope.hpp')
    p=work/'source/src/main.cu';s=p.read_text()
    s=once(s,'#include "u10_trace.hpp"','#include "u10_trace.hpp"\n#include "static_scope.hpp"')
    s=once(s,'input.data.size()*sizeof(float)));','(input.data.size()+input.d)*sizeof(float)));')
    s=once(s,'u10.write(output);','closure::write(output,rex::bridge.setup_ms,u10.load_ms,u10.drain_ms);\n    u10.write(output);')
    s=once(s,'auto context_begin=U10Clock::now();','uk::require(input.events.size()==80&&input.queries==80,"static 80 query schedule");\n    closure::host=input.data.data();closure::n=input.n;closure::d=input.d;\n    auto context_begin=U10Clock::now();')
    s=once(s,'bool warmup=!warm_env||u10_env("TARGET_WARMUP");','uk::require(warm_env&&std::string(warm_env)=="0","static schedule owns warmup");\n    bool warmup=false;')
    p.write_text(s)
    p=inc/'update.cuh';s=p.read_text()
    anchor='\tauto s = std::chrono::high_resolution_clock::now();\n\tCHECK(cudaMallocManaged((void **)&is_delete_in'
    s=once(s,anchor,'\tclosure::buffer=U10Clock::now();\n'+anchor)
    s=once(s,'\tfor (int i = 0; i < update_num; i++)','\tclosure::buffer_prepare_ms=u10_ms(closure::buffer);\n\tfor (int i = 0; i < update_num; i++)')
    anchor='\t\tu10.begin_op(i,update_list[i].update_flag,tree_size,in_size);'
    s=once(s,anchor,'\t\tclosure::before(i,update_list[i].update_flag);\n'+anchor+'\n        closure::submit(data_d,update_list[i].update_id);')
    s=once(s,'count_update_s++;qid_list[0]=update_list[i].update_id;','count_update_s++;qid_list[0]=closure::n;')
    s=once(s,'qid_list[0] = update_list[i].update_id;','qid_list[0] = closure::n;')
    assert s.count('u10.deliver(i,qid_list[0],')==2
    s=s.replace('u10.deliver(i,qid_list[0],','u10.deliver(i,update_list[i].update_id,')
    s=once(s,'\t\tu10.end_op(tree_size,in_size);','\t\tu10.end_op(tree_size,in_size);\n        closure::after(i,update_list[i].update_flag);')
    s=once(s,'\tCHECK(cudaFree(obj_r.dis_q));','\tclosure::buffer=U10Clock::now();\n\tCHECK(cudaFree(obj_r.dis_q));')
    s=once(s,'\tcudaFree(is_delete_in_prefix);','\tcudaFree(is_delete_in_prefix);\n    u10_ck(cudaDeviceSynchronize());closure::buffer_release_ms=u10_ms(closure::buffer);')
    p.write_text(s)
    manifest=dict(parent_prepared_sha256=cpu.sha(parent/'PREPARED.json'),prepare_sha256=cpu.sha(__file__),scope_sha256=cpu.sha(HERE/'static_scope.hpp'),contract_sha256=cpu.sha(HERE/'STATIC_CONTRACT.json'),sources={str(p.relative_to(work/'source')):cpu.sha(p) for p in (work/'source').rglob('*') if p.is_file()},scope='Host main/query submission/timing only; every original GPU kernel body unchanged')
    cpu.save(work/'PREPARED.json',manifest);return manifest

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--parent',type=Path,required=True);p.add_argument('--work',type=Path,required=True);a=p.parse_args();prepare(a.parent,a.work)
