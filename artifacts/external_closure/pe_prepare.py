#!/usr/bin/env python3
"""Derive a request/ID adapter; preserve every admitted P GPU function body."""
if not __debug__:raise RuntimeError('Python assertions must remain enabled')
import argparse,json,shutil,subprocess
from pathlib import Path
from common import outside_repo
from prepare_static import once,HERE
from qualify import cpu

def prepare(parent,work):
    work=outside_repo(work);assert not work.exists();work.mkdir(parents=True);source=json.loads((parent/'PREPARED.json').read_text())
    proof=json.loads((HERE.parent/'build_distance_tiles/evidence/QUALIFICATION.json').read_text())
    assert cpu.sha(parent/'PREPARED.json')==proof['source']['prepared_sha256']
    assert source['sources']==proof['source']['source_hashes']
    assert all(cpu.sha(parent/'source'/k)==v for k,v in source['sources'].items())
    shutil.copytree(parent/'source',work/'source');inc=work/'source/include'
    for n in ('pe_common.hpp','pe_p.hpp'):shutil.copy2(HERE/n,inc/n)
    p=work/'source/src/main.cu';s=p.read_text()
    s=once(s,'#include "u10_trace.hpp"','#include "u10_trace.hpp"\n#include "pe_p.hpp"')
    s=once(s,'input.data.size()*sizeof(float)));','(input.data.size()+11*input.d)*sizeof(float)));')
    s=once(s,'auto setup_begin=U10Clock::now();auto start=setup_begin;','auto setup_begin=U10Clock::now();auto start=setup_begin;\n    pe::begin(warm,input.n,input.d,int(input.events.size()));')
    s=once(s,'start=U10Clock::now();uk::live.finish();','start=U10Clock::now();pe::finish();uk::live.finish();')
    s=once(s,'u10.write(output);','pe::write(output);u10.write(output);')
    s=once(s,'double parse_ms=u10_ms(parse_begin);','pe::load();double parse_ms=u10_ms(parse_begin);')
    p.write_text(s)
    p=inc/'update.cuh';s=p.read_text()
    anchor='\t\tu10.begin_op(i,update_list[i].update_flag,tree_size,in_size);'
    s=once(s,anchor,anchor+'\n        pe::submit(i,update_list[i].update_flag,data_d,tree_size,in_size,insert_list,update_list[i].update_id);')
    # All ten pending insertion vectors remain addressable until compaction.
    assert s.count('uk::data_bytes(data_info[1],data_info[0])')==3
    s=s.replace('uk::data_bytes(data_info[1],data_info[0])','uk::data_bytes(data_info[1]+11,data_info[0])')
    assert s.count('u10.deliver(i,qid_list[0],')==2
    s=s.replace('u10.deliver(i,qid_list[0],','u10.deliver(i,pe::original_index,')
    for end in ('uk::live.distances);','total_result_dis);\n\n\t\t\tCHECK(cudaFree(total_result_id))'):
        if end.startswith('uk:'):s=once(s,end,end+'pe::delivered();')
        else:s=once(s,end,end.replace(');\n\n',');pe::delivered();\n\n',1))
    p.write_text(s)
    # No original kernel source/header besides Host update orchestration changes.
    changed=[k for k,v in source['sources'].items() if cpu.sha(work/'source'/k)!=v]
    assert sorted(changed)==['include/update.cuh','src/main.cu']
    cpu.save(work/'PREPARED.json',dict(parent_prepared_sha256=cpu.sha(parent/'PREPARED.json'),changed=changed,sources={str(p.relative_to(work/'source')):cpu.sha(p) for p in (work/'source').rglob('*') if p.is_file()}))
    (work/'bin').mkdir();cmd=json.loads((parent/'BUILD.json').read_text())['command']
    cmd=[v.replace(str(parent/'source'),str(work/'source')).replace(str(parent/'bin/target'),str(work/'bin/target')) for v in cmd]
    cpu.save(work/'BUILD_REGISTERED.json',dict(command=cmd,prepare_sha256=cpu.sha(__file__)))
    with (work/'compile.log').open('x') as f:subprocess.run(cmd,stdout=f,stderr=f,check=True)
    cpu.save(work/'BUILD.json',dict(command=cmd,binary_sha256=cpu.sha(work/'bin/target')))

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('parent','work'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();prepare(a.parent.resolve(),a.work.resolve())
