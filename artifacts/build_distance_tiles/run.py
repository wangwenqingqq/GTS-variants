#!/usr/bin/env python3
"""One frozen scoring-mapping overlay; native arithmetic is copied unchanged."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys
import numpy as np

HERE=Path(__file__).resolve().parent
PARENT=HERE.parent/'unified_target_workflow/phase_b'
sys.path.insert(0,str(PARENT))
spec=importlib.util.spec_from_file_location('tiles_parent',PARENT/'run.py')
parent=importlib.util.module_from_spec(spec);spec.loader.exec_module(parent)
sha=parent.sha


def once(text,old,new):
    assert text.count(old)==1,('changed source anchor',old)
    return text.replace(old,new,1)


def prepare(work,upstream):
    manifest=parent.prepare(work,upstream);source=work/'source';inc=source/'include'
    (inc/'build_tiles.hpp').write_text((HERE/'build_tiles.hpp').read_text())
    path=inc/'tree.cuh';s=path.read_text()
    begin=s.index('__global__ void getPivotDis(');end=s.index('__global__ void nodeSplit(',begin)
    original=s[begin:end];candidate=original.replace('getPivotDis(', 'getPivotDisTiled(',1)
    candidate=once(candidate,'int *pid_list)\n','int *pid_list, int tiles_per_node)\n')
    candidate=once(candidate,'int bid = blockIdx.x;','int bid = int(blockIdx.x) / tiles_per_node;\n\tint tile = int(blockIdx.x) % tiles_per_node;')
    candidate=once(candidate,'pid_list[nid] = pid[0];','if (tile == 0) pid_list[nid] = pid[0];')
    loop='for (int i = tid + lid; (i >= lid && i <= rid); i += THREAD_NUM)'
    assert candidate.count(loop)==2
    candidate=candidate.replace(loop,'for (int i = tid + lid + tile * THREAD_NUM; (i >= lid && i <= rid && i < lid + (tile + 1) * THREAD_NUM); i += THREAD_NUM)')
    # Keep the complete metric/arithmetic body unchanged; only ownership/indexing differ.
    s=s[:end]+candidate+s[end:]
    s=once(s,'#include "numeric.cuh"','#include "numeric.cuh"\n#include "build_tiles.hpp"')
    s=once(s,'\tsplit_num[0] = 1;','\tbt::begin(data_info[1], data_info[0], max_node_num[0]);\n\tsplit_num[0] = 1;')
    old='\t\tgetPivotDis<<<block_num, THREAD_NUM>>>(data_d, data_s, size_s, node_list, split_list, dis_list, id_list,\n\t\t\t\t\t\t\t\t\t\t\t   start_idx, data_info, pid_list);'
    new='''        bt::before(cur_level,block_num,start_idx,node_list,empty_list,split_list,id_list);
        if(bt::tiled) {
            int width=bt::tiles(data_info[1],cur_level);
            getPivotDisTiled<<<bt::grid(block_num,width),THREAD_NUM>>>(data_d,data_s,size_s,node_list,split_list,dis_list,id_list,start_idx,data_info,pid_list,width);
        } else {
'''+old+'''\n        }
'''
    s=once(s,old,new)
    s=once(s,'\t\tthrust::sort_by_key','\t\tbt::distance(dis_list,pid_list);\n\t\tthrust::sort_by_key')
    s=once(s,'\t\tnodeSplit<<<','\t\tbt::sorted(dis_list,id_list);\n\t\tnodeSplit<<<')
    s=once(s,'\t\tstart_idx +=','\t\tbt::split(node_list,empty_list,split_list);\n\t\tstart_idx +=')
    path.write_text(s)
    p=inc/'numeric.cuh';s=p.read_text()
    # Forward declaration keeps the audit header after the existing TN/uk definitions.
    s=once(s,'namespace target {','namespace bt {void refit(const double*,const double*,const int*,int);}\nnamespace target {')
    s=once(s,'bounds_refresh_ms.push_back(u10_ms(start));','bounds_refresh_ms.push_back(u10_ms(start));bt::refit(bounds.lo,bounds.hi,empty,nn);')
    p.write_text(s)
    p=source/'src/main.cu';s=p.read_text()
    s=once(s,'if(argc!=7||','bt::configure();\n    if(argc!=7||')
    s=once(s,'uk::require(input.n>=255,','uk::require(input.n>=255||bt::auditing,')
    s=once(s,'u10_ck(cudaDeviceReset());return 0;','bt::write(argv[5]);u10_ck(cudaDeviceReset());return 0;')
    p.write_text(s)
    manifest['tiles_sources']={str(p.relative_to(source)):sha(p) for p in sorted(source.rglob('*')) if p.is_file()}
    manifest['sources']=manifest['tiles_sources']
    manifest['tiles_files']={p.name:sha(p) for p in HERE.iterdir() if p.name in ('run.py','build_tiles.hpp','CONTRACT.json')}
    manifest['tiles_contract_sha256']=sha(HERE/'CONTRACT.json')
    (work/'PREPARED.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest


def cases(work,data):
    x=parent.validate.verify_target_data(data);work.mkdir(parents=True,exist_ok=False)
    warm=[(2,0),(3,0),(0,0),(2,0),(3,0),(1,0),(2,0),(3,0)]+[(0,0)]*9+[(2,0),(3,0)]
    rng=np.random.default_rng(202610090242)
    for name,n in [('root20',20),('tail513',513),('entropy4096',4096),('mixed19399',19399),('equal4096',4096),('entropy65535',65535),('gist4096',4096),('stress4096',4096)]:
        value=x[:n] if name=='gist4096' else rng.uniform(-.05,.05,(n,128)).astype(np.float32)
        if name=='equal4096':value[:]=0
        ops=parent.short_operations(n) if name=='stress4096' else warm
        parent.validate.case(value,work/name,ops)
    parent.validate.event_case(work/'million_prefix',parent.short_operations(1000000)[:51])
    parent.validate.event_case(work/'primary',parent.short_operations(1000000))
    identities={str(p.relative_to(work)):sha(p) for p in work.rglob('*') if p.is_file()}
    (work/'CASES.json').write_text(json.dumps(identities,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=('prepare','build','cases'))
    p.add_argument('--work',type=Path,required=True);p.add_argument('--upstream',type=Path);p.add_argument('--data',type=Path);p.add_argument('--nvcc',default='nvcc')
    a=p.parse_args();assert __debug__;a.work=parent.base.outside_repo(a.work)
    if a.action=='prepare':prepare(a.work,a.upstream)
    elif a.action=='cases':assert a.data;cases(a.work,a.data)
    else:
        manifest=json.loads((a.work/'PREPARED.json').read_text())
        assert all(sha(HERE/name)==digest for name,digest in manifest['tiles_files'].items())
        parent.base.build(a.work,a.nvcc)
