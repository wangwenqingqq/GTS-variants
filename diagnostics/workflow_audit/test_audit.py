#!/usr/bin/env python3
"""CPU-only reproducibility, unchanged-kernel and oracle regression checks."""
import csv,hashlib,json,re,shutil,subprocess,tempfile
from pathlib import Path
import analyze,catalog,prepare,traces
HERE=Path(__file__).resolve().parent

def kernels(t):
 t=catalog.strip(t);out={}
 for m in re.finditer(r'__global__\s+void\s+(\w+)\s*\(',t):
  start=t.index('{',m.end());depth=1;end=start+1
  while depth:
   depth+=(t[end]=='{')-(t[end]=='}');end+=1
  out[m[1]]=t[m.start():end]
 return out

def main():
 catalog.build();rows=list(csv.DictReader((HERE/'kernels.csv').open()));assert len(rows)==69
 assert sum('alternative' in r['reachability'] for r in rows)==14
 with tempfile.TemporaryDirectory() as temp:
  root=Path(temp);prepared=root/'native';prepare.prepare(prepared)
  count=0
  for rel in json.loads((HERE.parent/'cpu_io/SOURCE_PINS.json').read_text())['sha256']:
   if rel.endswith(('.cuh','.cu')):
    a=kernels((catalog.ROOT/rel).read_text());assert a==kernels((prepared/rel).read_text()),rel;count+=len(a)
  assert count==69
  # This manifest must equal the one used to build the measured native binary.
  evidence=HERE/'EVIDENCE.json'
  if evidence.exists():assert json.loads((prepared/'MANIFEST.json').read_text())==json.loads(evidence.read_text())['instrumented_source_sha256']
  traces.generate(root/'traces')
  if evidence.exists():
   e=json.loads(evidence.read_text())
   for n in traces.CASES:assert analyze.sha(root/'traces'/(n+'.txt'))==e['runs']['check_'+n]['trace_sha256']
  # Compile only the independent CPU oracle, not CUDA/native kernels.
  cxx=shutil.which('c++');assert cxx,'A standard C++ compiler is required for oracle regression'
  src=root/'oracle.cpp';src.write_text('#include <cstdio>\n#include <cstdlib>\n#include "'+str(HERE/'workflow.hpp')+'"\n'+'''
int main(int argc,char** argv){
 int info[]={128,2000,2};std::vector<float> x(2000*128,0);x[128]=201;x[256]=200;
 audit_init(info,x.data(),200);audit_begin(2,0,0);audit_result(1999);
 audit_begin(0,0,1);audit_result(2000);audit_begin(1,2000,2);audit_result(argc==1?1999:1998);
}
''');subprocess.run([cxx,'-std=c++17',str(src),'-o',str(root/'oracle')],check=True)
  ok=subprocess.run([str(root/'oracle')],capture_output=True,text=True);bad=subprocess.run([str(root/'oracle'),'fail'],capture_output=True,text=True)
  assert ok.returncode==0 and ok.stdout.count(',PASS')==3
  assert bad.returncode==23 and bad.stdout.splitlines()[-1]=='AUDIT_COUNT,2,1998,1999,1998,FAIL'
 assert analyze.phases('GTS_DIAG,op.query,2,0.12,0.11')['op.query']['count']==2
 if (HERE/'EVIDENCE.json').exists():
  e=json.loads((HERE/'EVIDENCE.json').read_text());assert e['coverage']['observed_selected_definitions']==35
  for f,h in e['portable_tables_sha256'].items():assert analyze.sha(HERE/f)==h
  assert e['runs']['ncu_rebuild_getNewData']['selected_profile_launches']==0
  assert e['runs']['ncu_rebuild_getNewData_envfix']['selected_profile_launches']==1
  assert not e['runs']['ncu_rebuild_getNewData_envfix']['count_check_pass']
  scope_rows=list(csv.DictReader((HERE/'runtime_scopes.csv').open()))
  for case in ('nsys_all_include','nsys_rebuild'):
   for name in ('main.total','update.total','op.query'):
    r=next(r for r in scope_rows if r['run']==case and r['scope']==name)
    assert r['incomplete_calls']=='1' and r['completed_calls']=='0' and r['inclusive_host_ms']==''
 print('PASS: 69 unchanged kernel bodies, deterministic traces, boundary/self/duplicate oracle, failure exit, exported coverage')
if __name__=='__main__':main()
