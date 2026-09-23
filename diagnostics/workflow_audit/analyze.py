#!/usr/bin/env python3
"""Curate immutable diagnostic evidence; never turn a missing profile into a pass."""
import argparse,csv,hashlib,json,re,sqlite3
from collections import defaultdict
from pathlib import Path
HERE=Path(__file__).resolve().parent
METRICS={
 'duration_ns':'gpu__time_duration.sum',
 'load_requests':'l1tex__t_requests_pipe_lsu_mem_global_op_ld.sum',
 'load_sectors':'l1tex__t_sectors_pipe_lsu_mem_global_op_ld.sum',
 'store_requests':'l1tex__t_requests_pipe_lsu_mem_global_op_st.sum',
 'store_sectors':'l1tex__t_sectors_pipe_lsu_mem_global_op_st.sum',
 'load_bytes_per_sector':'smsp__sass_average_data_bytes_per_sector_mem_global_op_ld.ratio',
 'store_bytes_per_sector':'smsp__sass_average_data_bytes_per_sector_mem_global_op_st.ratio',
 'atomic_requests':'l1tex__t_requests_pipe_lsu_mem_global_op_atom.sum',
 'reduction_requests':'l1tex__t_requests_pipe_lsu_mem_global_op_red.sum',
 'dram_read_bytes':'dram__bytes_op_read.sum','dram_write_bytes':'dram__bytes_op_write.sum',
 'registers_per_thread':'launch__registers_per_thread',
 'shared_bytes_per_block':'launch__shared_mem_per_block',
 'eligible_warps_per_active_cycle':'smsp__warps_eligible.avg.per_cycle_active',
 'active_warps_per_active_cycle':'smsp__warps_active.avg.per_cycle_active',
}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump_csv(path,rows):
 assert rows,path
 with path.open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
def phases(text):
 out={}
 for v in (x.split(',') for x in text.splitlines()):
  if len(v)==5 and v[0]=='GTS_DIAG' and v[2].isdigit():out[v[1]]={'count':int(v[2]),'inclusive_wall_s':float(v[3]),'inclusive_main_thread_cpu_s':float(v[4])}
 return out

def trace(path,exit_code=0):
 db=sqlite3.connect(path);db.row_factory=sqlite3.Row
 tables={r[0] for r in db.execute("select name from sqlite_master where type='table'")}
 def rows(t):return [dict(x) for x in db.execute('select * from '+t)] if t in tables else []
 names=dict(db.execute('select id,value from StringIds'));ranges=rows('NVTX_EVENTS');api=rows('CUPTI_ACTIVITY_KIND_RUNTIME')
 ranges=[x for x in ranges if x['eventType']==59]
 def label(x):return x['text'] or names.get(x['textId'],'unnamed')
 # NSYS may close unpopped ranges at process exit instead of storing NULL end.
 # The oracle exits inside the final op.query, so these three stack scopes cannot
 # have completed normally. Finished child scopes remain valid diagnostics.
 last_query=max((r['start'] for r in ranges if label(r)=='op.query'),default=-1)
 for r in ranges:r['audit_incomplete']=(r['end'] is None or (exit_code==23 and (label(r) in ('main.total','update.total') or (label(r)=='op.query' and r['start']==last_query))))
 def owner(a):
  match=[r for r in ranges if r['globalTid']==a['globalTid'] and r['start']<=a['start'] and (r['end'] is None or a['end']<=r['end'])]
  if not match:return 'outside_named_range'
  r=max(match,key=lambda r:r['start']);return ('incomplete:' if r['audit_incomplete'] else '')+label(r)
 # Correlation is local to this single-process trace; do not infer ownership from overlap.
 corr={a['correlationId']:owner(a) for a in api}
 kernels=defaultdict(lambda:{'calls':0,'gpu_ms':0,'blocks':set(),'threads':set(),'registers':set()})
 for r in rows('CUPTI_ACTIVITY_KIND_KERNEL'):
  k=(corr.get(r['correlationId'],'uncorrelated'),names[r['shortName']],names[r['demangledName']]);d=kernels[k];d['calls']+=1;d['gpu_ms']+=(r['end']-r['start'])/1e6
  d['blocks'].add(r['gridX']*r['gridY']*r['gridZ']);d['threads'].add(r['blockX']*r['blockY']*r['blockZ']);d['registers'].add(r['registersPerThread'])
 kr=[dict(scope=k[0],kernel=k[1],function=k[2],**{n:json.dumps(sorted(v)) if isinstance(v,set) else v for n,v in d.items()}) for k,d in sorted(kernels.items())]
 calls=defaultdict(lambda:{'calls':0,'inclusive_host_ms':0})
 for r in api:
  d=calls[(owner(r),names[r['nameId']])];d['calls']+=1;d['inclusive_host_ms']+=(r['end']-r['start'])/1e6
 ar=[dict(scope=k[0],api=k[1],**d) for k,d in sorted(calls.items())]
 labels={r['id']:r['label'] for r in rows('ENUM_CUDA_MEMCPY_OPER')};copies=defaultdict(lambda:{'calls':0,'bytes':0,'gpu_ms':0})
 for r in rows('CUPTI_ACTIVITY_KIND_MEMCPY'):
  d=copies[(corr.get(r['correlationId'],'uncorrelated'),labels.get(r['copyKind'],str(r['copyKind'])))];d['calls']+=1;d['bytes']+=r['bytes'];d['gpu_ms']+=(r['end']-r['start'])/1e6
 mr=[dict(scope=k[0],direction=k[1],**d) for k,d in sorted(copies.items())]
 scopes=defaultdict(lambda:{'completed_calls':0,'incomplete_calls':0,'inclusive_host_ms':0})
 for r in ranges:
  d=scopes[label(r)]
  if r['audit_incomplete']:d['incomplete_calls']+=1
  else:d['completed_calls']+=1;d['inclusive_host_ms']+=(r['end']-r['start'])/1e6
 for d in scopes.values():
  if not d['completed_calls']:d['inclusive_host_ms']=None
 db.close()
 return kr,ar,mr,[dict(scope=k,**d) for k,d in sorted(scopes.items())]

def analyze(root,out):
 out.mkdir(exist_ok=False)
 e={'scope':'Representative diagnostic-only; source-complete is not workload-complete; no optimization/speedup promotion',
    'parent_commit':'6b303b428f7f2cecc9d569398e1c29cbdbf368f0',
    'hardware':{'gpu':'RTX PRO 6000 Blackwell Server Edition','physical_gpu':0,'sm_count':188,'driver':'590.48.01','toolkit':'13.1.115','ncu':'2025.4.1','nsys':'2025.5.2','clock_control':'none','cache_control':'none'},
    'workloads':{'native':'N2000 D128 integer FP32 L2, query row0, r200 except all_include r10000, original-row replay, buffer threshold2 except first native NCU attempt', 'static':'N65536 D128 integer FP32 L2 Q128; r500/k100; first matching measured launch only'},
    'source_pins':json.loads((HERE.parent/'cpu_io/SOURCE_PINS.json').read_text()),
    'instrumented_source_sha256':json.loads((root/'native/MANIFEST.json').read_text()),
    'runs':{},'private_raw_files':{},'metric_names':METRICS}
 nr=[];kr=[];ar=[];mr=[];sr=[];observed=defaultdict(set)
 expected_native='040caca811f70450f7b076431786c6b4c8699a1949923f1a3fd4acae1caf67d9'
 for p in sorted((root/'runs').iterdir()):
  r=json.loads((p/'receipt.json').read_text());before=json.loads((p/'before.json').read_text());after=json.loads((p/'after.json').read_text())
  assert not before['apps'].strip() and not after['apps'].strip() and r['post_clear'],p
  assert before['gpu'].split(',')[0].strip()=='0' and r['exit_code'] in (0,23),p
  stdout=(p/'stdout.log').read_text();stderr=(p/'stderr.log').read_text();counts=[x for x in stdout.splitlines() if x.startswith('AUDIT_COUNT,')]
  if p.name.startswith('static_'):
   folder='gtspp_coalescing' if r['kind']=='rnn' else 'gtspp_knn';expected=json.loads((HERE.parent/folder/'EVIDENCE.json').read_text())['provenance']['binaries']['A']
   assert r['binary_sha256']==expected and r['exit_code']==0 and r['correct'],p
  else:
   assert r['binary_sha256']==expected_native and counts==r['oracle_rows'],p
   assert sha(root/'traces'/(r['case']+'.txt'))==r['trace_sha256']
  s={k:v for k,v in r.items() if k not in ['command','phases','sanitizer_summaries','wall_s']}
  s['recovered_phases']=phases(stderr);s['sanitizer_summaries']=[x for x in (stdout+'\n'+stderr).splitlines() if 'SUMMARY:' in x]
  s['timing_complete']=r['exit_code']==0;s['selected_profile_launches']=0
  if p.name=='ncu_rebuild_getNewData':s['diagnosis']='INVALID TARGET: sudo omitted threshold2; no rebuild and no matching kernel; count pass is not post-rebuild evidence'
  if p.name.startswith(('ncu_','static_')):
   if (p/'raw.csv').exists():
    z=csv.DictReader((p/'raw.csv').open());units=next(z);launches=list(z);assert len(launches)==1 and (p/'trace.ncu-rep').exists(),p
    d=launches[0];n=d['Kernel Name'].split('(')[0].strip();assert n==r['kernel'],(p,n)
    s['selected_profile_launches']=1;observed[n].add(p.name)
    v=dict(run=p.name,kernel=n,scope='static N65536 Q128' if p.name.startswith('static') else 'native N2000',grid=d['Grid Size'],block=d['Block Size'])
    v.update({k:d.get(m,'') for k,m in METRICS.items()});nr.append(v)
   else:assert p.name=='ncu_rebuild_getNewData' and 'No kernels were profiled' in stdout,p
  if (p/'trace.sqlite').exists():
   a,b,c,d=trace(p/'trace.sqlite',r['exit_code'])
   for target,items in [(kr,a),(ar,b),(mr,c),(sr,d)]:target.extend(dict(run=p.name,**v) for v in items)
   for v in a:observed[v['kernel']].add(p.name)
  e['runs'][p.name]=s
  for f in sorted(p.iterdir()):
   if f.is_file():e['private_raw_files'][str(f.relative_to(root))]={'bytes':f.stat().st_size,'sha256':sha(f)}
 assert len(e['runs'])==60 and len(nr)==35
 coverage=[]
 for r in csv.DictReader((HERE/'kernels.csv').open()):
  alt=Path(r['file']).name.startswith('update_');seen=sorted(observed[r['kernel']]) if not alt else []
  coverage.append(dict(file=r['file'],line=r['line'],kernel=r['kernel'],observed_runs=';'.join(seen),state='representative observed; branches not exhaustive' if seen else 'source-only; '+r['reachability']))
 e['coverage']={'definitions':len(coverage),'selected_header_definitions':55,'observed_selected_definitions':sum(bool(x['observed_runs']) for x in coverage),'ncu_selected_launches':len(nr),'nsys_traces':8,'process_runs':len(e['runs'])}
 exports={'ncu_summary.csv':nr,'runtime_kernels.csv':kr,'runtime_api.csv':ar,'runtime_copies.csv':mr,'runtime_scopes.csv':sr,'runtime_coverage.csv':coverage}
 for name,rows in exports.items():dump_csv(out/name,rows)
 e['portable_tables_sha256']={name:sha(out/name) for name in exports}
 e['delivery_source_sha256']={p.name:sha(p) for p in sorted(HERE.iterdir()) if p.is_file() and p.name!='EVIDENCE.json' and p.suffix in ('.py','.hpp','.md')}
 (out/'EVIDENCE.json').write_text(json.dumps(e,indent=2,sort_keys=True)+'\n')
 print(json.dumps(e['coverage'],indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('out',type=Path);a=p.parse_args();analyze(a.root,a.out)
