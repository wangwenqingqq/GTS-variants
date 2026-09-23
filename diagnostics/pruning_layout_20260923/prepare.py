#!/usr/bin/env python3
"""Generate a layout-only L2 screen from the pinned existing result-fusion driver."""
import argparse,hashlib,importlib.util,json,shutil
from pathlib import Path
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('fusion',HERE.parent/'fused_result_20260923/prepare.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
once=base.replace_once

def kernel(source):
    assert hashlib.sha256(source.encode()).hexdigest()=='b7e717a2d5b27acbfb860f28a26696d283b00a75d06de2d32128ae975627080a'
    start=source.index('__global__ void findNextRnn(');end=source.index('__global__ void findNextKnn(')
    s=source[start:end].replace('short *','float *')
    s=once(s,'__global__ void findNextRnn','template<bool Packed> __global__ void findNextLayout')
    s=once(s,'int *size_s)','int *size_s, const int *pids, const float *lower, const float *packed)')
    s=once(s,'TN node = node_list[nid];','TN node; node.pid = pids[nid]; node.min_dis = lower[nid];')
    s=s.replace('node_list[nid + 1].min_dis','lower[nid + 1]')
    operand='data_d[node.pid * data_info[0] + j]'
    assert s.count(operand)==6
    s=s.replace(operand,'(Packed ? packed[j * 16 + (nid - 1) / 10] : '+operand+')')
    return '#pragma once\n'+s

def driver(text):
    s=base.transform(text).replace('A|B|C|D|E radius','A|D|E|U|S|V|L radius')
    s=once(s,'struct Fixed {','#include "layout_generated.cuh"\n#include "layout_support.cuh"\n\nstruct Fixed {\n    int layout_mode;')
    s=once(s,'Fixed(int count_n,int h,bool f=false):fused(f),n(count_n),height(h)',
           'Fixed(int count_n,int h,bool f=false,int lm=0):layout_mode(lm),fused(f),n(count_n),height(h)')
    call='flags,start,node_list,radius,data_d,qid,num,max_node_num,data_info,empty_list,data_s,size_s'
    s=once(s,'            findNextRnn<<<1,THREAD_NUM,0,stream>>>('+call+');',
           '            if(layout_mode==1) findNextLayout<false><<<1,THREAD_NUM,0,stream>>>('+call+',prune_layout->pids,prune_layout->lower,prune_layout->packed);\n'
           '            else if(layout_mode==2) findNextLayout<true><<<1,THREAD_NUM,0,stream>>>('+call+',prune_layout->pids,prune_layout->lower,prune_layout->packed);\n'
           '            else findNextRnn<<<1,THREAD_NUM,0,stream>>>('+call+');')
    s=once(s,'mode=="A"||mode=="B"||mode=="C"||mode=="D"||mode=="E"','mode=="A"||mode=="D"||mode=="E"||mode=="U"||mode=="S"||mode=="V"||mode=="L"')
    s=once(s,'assert(data_info[1]==2000 && data_info[2]==6);','assert(data_info[1]==2000 && data_info[2]==2 && (data_info[0]==2 || data_info[0]==96 || data_info[0]==960));')
    s=once(s,'auto setup=Clock::now();Fixed* fixed=',
           'if(dump && mode=="E")auditPruning(queries,radius,out);\n'
           '    int lm=(mode=="U"||mode=="S")?1:((mode=="V"||mode=="L")?2:0);\n'
           '    if(lm)prune_layout=new PruneLayout(lm==2);\n'
           '    double layout_s=prune_layout?prune_layout->setup_s:0;size_t layout_bytes=prune_layout?prune_layout->bytes:0;\n'
           '    auto setup=Clock::now();Fixed* fixed=')
    s=once(s,'new Fixed(tree_size,tree_h,mode=="D"||mode=="E")','new Fixed(tree_size,tree_h,true,lm)')
    s=s.replace('mode=="C"||mode=="E"','mode=="E"||mode=="S"||mode=="L"')
    s=once(s,'std::ofstream full; if(dump)full.open(out+".results");','std::ofstream full; if(dump){full.open(out+".results");full<<std::setprecision(9);}')
    s=once(s,'<<",\\\"setup_s\\\":"<<setup_s',
           '<<",\\\"layout_setup_s\\\":"<<layout_s<<",\\\"layout_bytes\\\":"<<layout_bytes<<",\\\"setup_s\\\":"<<setup_s')
    s=once(s,'    delete fixed;','    delete fixed;delete prune_layout;')
    s=once(s,'(void*)data_info,(void*)data_s,(void*)size_s','(void*)data_info,(void*)data_d,(void*)data_s,(void*)size_s')
    return s

def runner(text):
    s=text.replace("fixtures/words_2000.txt","fixtures/data.txt")
    s=s.replace("'fixtures/words_2000.txt'","'fixtures/data.txt'")
    s=s.replace('nextcheck=start+1','nextcheck=start+.2').replace('nextcheck=time.monotonic()+1','nextcheck=time.monotonic()+.2')
    s=s.replace("time.sleep(.1)","time.sleep(.02)")
    s=s.replace("'error:' in x.lower()", "'==ERROR==' in x or 'error:' in x.lower()")
    s=s.replace("choices=['A','B','C']","choices=['A','D','E','U','S','V','L']")
    s=s.replace("'synccheck','initcheck']","'synccheck','initcheck','racecheck']")
    s=s.replace("index+'.lock','a'", "index+'.lock','r+'")
    s=once(s,"    record={'label':label", "    record={'input_sha256':{n:hashlib.sha256((root/'fixtures'/n).read_bytes()).hexdigest() for n in ['data.txt','queries.qid']},'label':label")
    sections=['SpeedOfLight','LaunchStats','Occupancy','SchedulerStats','WarpStateStats','MemoryWorkloadAnalysis','MemoryWorkloadAnalysis_Tables','InstructionStats']
    args=[a for section in sections for a in ['--section',section]]
    branch="""    elif tool=='ncu':
        cmd=['ncu','--kernel-name-base','demangled','--kernel-name','regex:findNext(Rnn|Layout)',
             '--launch-count','2','--clock-control','none','--cache-control','none',
             '--export',str(path/'profile')]+NCU_ARGS+cmd
"""
    s=once(s,"    elif tool!='clean':",branch+"    elif tool!='clean':")
    s=s.replace('import argparse\n','import argparse\nNCU_ARGS='+repr(args)+'\n')
    s=s.replace("'racecheck']","'racecheck','ncu']")
    return s

def prepare(source,out):
    pins=json.loads((HERE.parent/'original_tree_redundancy/SOURCE_PINS.json').read_text())['sha256']
    for name,h in pins.items():
        if not name.startswith('GTS/'):continue
        p=source/name;assert hashlib.sha256(p.read_bytes()).hexdigest()==h
        dest=out/'source'/name.removeprefix('GTS/');dest.parent.mkdir(parents=True,exist_ok=True)
        assert not dest.exists();shutil.copy2(p,dest)
    (out/'graph_bench.cu').write_text(driver((HERE.parent/'graph_query_20260923/graph_bench.cu').read_text()))
    (out/'layout_generated.cuh').write_text(kernel((source/'GTS/include/search.cuh').read_text()))
    (out/'run_layout.py').write_text(runner((HERE.parent/'graph_query_20260923/run.py').read_text()))
    for path in [HERE/'layout_support.cuh',HERE.parent/'fused_result_20260923/fused_result.cuh']:
        shutil.copy2(path,out/path.name)
    (out/'source_pins.json').write_text(json.dumps({n:h for n,h in pins.items() if n.startswith('GTS/')},indent=2)+'\n')
    print('Prepared layout-only source; no GPU call')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();prepare(a.source,a.output)
