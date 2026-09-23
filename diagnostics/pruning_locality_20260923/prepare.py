#!/usr/bin/env python3
"""Extend the frozen layout driver; retain prior experiments unmodified."""
import argparse,importlib.util,shutil
from pathlib import Path
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'pruning_layout_20260923'
spec=importlib.util.spec_from_file_location('old_layout',OLD/'prepare.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
once=base.once

def kernel(source):
 s=base.kernel(source).replace('template<bool Packed>','template<int Layout>')
 s=once(s,'#pragma once','#pragma once\n#include "layout_index.cuh"')
 s=s.replace('Packed ? packed[j * 16 + (nid - 1) / 10]', 'Layout ? packed[pivotOffset(Layout,(nid - 1) / 10,j,data_info[0])]')
 assert s.count('pivotOffset(Layout,')==6
 return s

def driver(text):
 s=base.driver(text).replace('A|D|E|U|S|V|L radius','A|D|E|U|S|V|L|B|R|C|T radius')
 s=once(s,'mode=="A"||mode=="D"||mode=="E"||mode=="U"||mode=="S"||mode=="V"||mode=="L"','mode=="A"||mode=="D"||mode=="E"||mode=="U"||mode=="S"||mode=="V"||mode=="L"||mode=="B"||mode=="R"||mode=="C"||mode=="T"')
 s=once(s,'((mode=="V"||mode=="L")?2:0)','((mode=="V"||mode=="L")?2:((mode=="B"||mode=="R")?3:((mode=="C"||mode=="T")?4:0)))')
 s=once(s,'new PruneLayout(lm==2)','new PruneLayout(lm-1)')
 line=next(x for x in s.splitlines() if 'else if(layout_mode==2)' in x)
 s=once(s,line,line+'\n'+line.replace('layout_mode==2','layout_mode==3').replace('<true>','<2>')+'\n'+line.replace('layout_mode==2','layout_mode==4').replace('<true>','<3>'))
 s=s.replace('mode=="E"||mode=="S"||mode=="L"','mode=="E"||mode=="S"||mode=="L"||mode=="R"||mode=="T"')
 return s

def support():
 s=(OLD/'layout_support.cuh').read_text()
 s=once(s,'int dim,int* pids,float* lower,float* packed)','int dim,int kind,int* pids,float* lower,float* packed)')
 s=once(s,'packed[i]=valid?data[tree[child].pid*dim+j]:0;','if(valid)packed[pivotOffset(kind,group,j,dim)]=data[tree[child].pid*dim+j];')
 s=once(s,'int dim,const int* pids,','int dim,int kind,const int* pids,')
 s=once(s,'packed[j*16+(n-1)/10]','packed[pivotOffset(kind,(n-1)/10,j,dim)]')
 s=s.replace('explicit PruneLayout(bool with_pivots)','explicit PruneLayout(int kind)')
 s=once(s,'if(with_pivots){alloc(packed,16*data_info[0]);bytes+=16*data_info[0]*sizeof(float);}',
  'if(kind){int words=pivotWords(kind,data_info[0]);alloc(packed,words);bytes+=words*sizeof(float);ck(cudaMemset(packed,0,words*sizeof(float)));}')
 s=once(s,'data_info[0],pids,lower,packed);','data_info[0],kind,pids,lower,packed);')
 s=once(s,'PruneLayout layout(true);','PruneLayout layout(1),row(2),tile(3);')
 s=once(s,'data_info[0],layout.pids,layout.lower,layout.packed);','data_info[0],1,layout.pids,layout.lower,layout.packed);\n'
  '    checkPruning<<<1,128>>>(node_list,empty_list,data_d,data_info[0],2,row.pids,row.lower,row.packed);\n'
  '    checkPruning<<<1,128>>>(node_list,empty_list,data_d,data_info[0],3,tile.pids,tile.lower,tile.packed);')
 s=s.replace('host[3]','host[5]').replace('flags[3]','flags[5]').replace('k<3','k<5')
 line=next(x for x in s.splitlines() if 'findNextLayout<true><<<' in x)
 s=once(s,line,line+'\n'+line.replace('<true>','<2>').replace('flags[2]','flags[3]').replace('layout.','row.')+'\n'+line.replace('<true>','<3>').replace('flags[2]','flags[4]').replace('layout.','tile.'))
 s=once(s,'host[0]==host[1] && host[0]==host[2]','host[0]==host[1] && host[0]==host[2] && host[0]==host[3] && host[0]==host[4]')
 return s

def runner(text):
 return base.runner(text).replace("choices=['A','D','E','U','S','V','L']","choices=['A','D','E','U','S','V','L','B','R','C','T']")

def verifier():
 return (OLD/'verify_full.py').read_text().replace("'DEUSVL' if name=='empty' else 'ADEUSVL'","'ESLBRTC' if name=='empty' else 'AESLBRTC'")

def prepare(source,out):
 base.prepare(source,out)
 (out/'graph_bench.cu').write_text(driver((HERE.parent/'graph_query_20260923/graph_bench.cu').read_text()))
 (out/'layout_generated.cuh').write_text(kernel((source/'GTS/include/search.cuh').read_text()))
 (out/'layout_support.cuh').write_text(support())
 (out/'run_layout.py').write_text(runner((HERE.parent/'graph_query_20260923/run.py').read_text()))
 (out/'verify_full.py').write_text(verifier())
 for name in ['layout_index.cuh','suite.py','CONTRACT.md']:shutil.copy2(HERE/name,out/name)
 print('Prepared contiguous/tiled controls; no GPU call')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('output',type=Path);a=p.parse_args();prepare(a.source,a.output)
