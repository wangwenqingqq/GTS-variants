#!/usr/bin/env python3
"""Check the actual host/device address helper and source-transform invariants."""
import argparse,subprocess,tempfile,itertools
from pathlib import Path
from prepare import HERE,base,kernel,driver,support,runner,verifier
from suite import ORDERS,plan
for a,b in itertools.combinations('ESRT',2):assert sum(o.index(a)<o.index(b) for o in ORDERS)==2
assert len(plan('gates',{'normal':1}))==20
assert len(plan('screen',{'normal':1}))==16
assert len(plan('full',dict(empty=-1,zero=0,normal=1,all=10)))==31
code='''
#define __host__
#define __device__
#define __forceinline__ inline
#include "layout_index.cuh"
#include <cassert>
#include <set>
#include <vector>
int main(){
 for(int d:{2,7,8,9,31,33,96,960})for(int k:{1,2,3}){
  std::set<int> used;std::vector<float> p(pivotWords(k,d),0);
  for(int g=0;g<11;++g)for(int j=0;j<d;++j){
   int x=pivotOffset(k,g,j,d);assert(x>=0 && x<(int)p.size());assert(used.insert(x).second);
   p[x]=g*10000+j+1;
   if(k==2)assert(x==g*d+j);
   if(k==3 && g==0)assert(x==j);
   if(k==3 && j%8 && g>0)assert(x==pivotOffset(k,g,j-1,d)+1);
  }
  for(int g=0;g<11;++g)for(int j=0;j<d;++j)assert(p[pivotOffset(k,g,j,d)]==g*10000+j+1);
  for(int x=0;x<(int)p.size();++x)if(!used.count(x))assert(p[x]==0);
 }
}
'''
with tempfile.TemporaryDirectory() as td:
 p=Path(td);(p/'test.cpp').write_text(code)
 subprocess.run(['c++','-std=c++17','-O2','-I'+str(HERE),str(p/'test.cpp'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
s=(HERE.parent/'graph_query_20260923/graph_bench.cu').read_text();d=driver(s)
assert 'new PruneLayout(lm-1)' in d and 'layout_mode==4' in d
assert d.count('findNextLayout<2><<<')==d.count('findNextLayout<3><<<')==1
assert 'host[0]==host[4]' in support()
compile(runner((HERE.parent/'graph_query_20260923/run.py').read_text()),'runner','exec');compile(verifier(),'verifier','exec')
p=argparse.ArgumentParser();p.add_argument('--source',type=Path);a=p.parse_args()
if a.source:
 s=(a.source/'GTS/include/search.cuh').read_text();k=kernel(s)
 inverse=k.replace('#include "layout_index.cuh"\n','').replace('template<int Layout>','template<bool Packed>')
 inverse=inverse.replace('Layout ? packed[pivotOffset(Layout,(nid - 1) / 10,j,data_info[0])]','Packed ? packed[j * 16 + (nid - 1) / 10]')
 assert inverse==base.kernel(s)
print('PASS actual C++ offset bounds/bijection/padding, balanced order, inventory, source transform')
