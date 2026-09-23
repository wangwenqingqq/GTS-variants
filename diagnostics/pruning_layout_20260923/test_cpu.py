#!/usr/bin/env python3
"""Small regression check for generation, admission inventory and oracle failure."""
import csv,json,tempfile
from pathlib import Path
from prepare import driver,kernel,runner,HERE
from suite import gates
from verify_full import check,digest,check_summary
s=(HERE.parent/'graph_query_20260923/graph_bench.cu').read_text();d=driver(s)
assert d.count('findNextLayout<false><<<')==d.count('findNextLayout<true><<<')==1
assert 'new Fixed(tree_size,tree_h,true,lm)' in d and 'std::setprecision(9)' in d
r=runner((HERE.parent/'graph_query_20260923/run.py').read_text())
assert "nextcheck=start+.2" in r and "--cache-control','none" in r and "index+'.lock','r+'" in r
assert len(gates())==24 and len(set(x[0] for x in gates()))==24
try:kernel('source drift')
except AssertionError:pass
else:raise AssertionError('source drift accepted')
with tempfile.TemporaryDirectory() as tmp:
 p=Path(tmp);pairs=[(0,0.),(1,1.)]
 (p/'result.results').write_text('0 2 0:0 1:1\n')
 (p/'result.csv').write_text('qid,count,ordered_hash\n0,2,'+digest(pairs)+'\n')
 o={'queries':[0],'distances':[[0.,1.,2.]]}
 assert check(p,o,1)==[(0,pairs)]
 for bad in ['0 2 0:0 0:1\n','0 2 0:0 1:1.001\n']:
  (p/'result.results').write_text(bad)
  try:check(p,o,1)
  except AssertionError:pass
  else:raise AssertionError('corrupted output accepted')
print('PASS generation, 24-gate inventory, drift rejection, full-output corruption checks')

summary={'mode':'E','queries':64,'radius':1.,'sum_query_s':.000064,'layout_bytes':0}
receipt={'mode':'E','repeats':1,'radius':1.}
check_summary(summary,receipt,[{'query_us':'1'}]*64)
for key,value in [('mode','L'),('queries',32),('radius',2.),('sum_query_s',.000128)]:
 try:check_summary({**summary,key:value},receipt,[{'query_us':'1'}]*64)
 except AssertionError:pass
 else:raise AssertionError('mismatched summary accepted: '+key)
print('PASS wrong-mode/radius/count/time summaries rejected')
