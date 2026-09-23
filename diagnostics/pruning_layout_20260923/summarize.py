#!/usr/bin/env python3
"""Fail-closed same-contract analysis; raw inputs and machine records stay private."""
import argparse,csv,json,math,re,sqlite3,statistics as st,sys
from pathlib import Path
from verify_full import clean,sha,verify,check_summary
from suite import gates,require_gates,ORDERS,GRAPH,MODES
from prepare import driver,kernel,runner,HERE
sys.path.insert(0,str(HERE.parent/'graph_query_20260923'))
from analyze import paired_interval,percentile

def read(p):return json.loads(p.read_text())
def trace(path):
 with sqlite3.connect(path) as db:
  rows=db.execute('SELECT s.value,k.gridX,k.gridY,k.gridZ,k.blockX,k.blockY,k.blockZ,k.registersPerThread,k.staticSharedMemory,k.dynamicSharedMemory,k.end-k.start FROM CUPTI_ACTIVITY_KIND_KERNEL k JOIN StringIds s ON s.id=k.demangledName ORDER BY k.start').fetchall()
  first=next(i for i,r in enumerate(rows) if r[0].startswith('initQnode('));rows=rows[first:]
  assert len(rows)==193*17
  sig=[list(r[:-1]) for r in rows[:17]]
  assert all([list(r[:-1]) for r in rows[i:i+17]]==sig for i in range(0,len(rows),17))
  assert db.execute('SELECT count(*) FROM CUPTI_ACTIVITY_KIND_RUNTIME WHERE returnValue!=0').fetchone()[0]==0
  api=dict(db.execute('SELECT s.value,count(*) FROM CUPTI_ACTIVITY_KIND_RUNTIME r JOIN StringIds s ON s.id=r.nameId GROUP BY r.nameId'))
  assert api['cudaGraphLaunch_v10000']==193
  return {'kernels_per_query':17,'query_instances':193,'signature':sig,'prefix_kernels':first,'pruning_kernel_sum_us':sum(r[-1] for i,r in enumerate(rows) if i%17 in [1,3])/193/1000,'all_kernel_sum_us':sum(r[-1] for r in rows)/193/1000,'sqlite_sha256':sha(path)}

def dataset(root,common,interrupted=False):
 full=verify(root);require_gates(root,common/'run_layout.py');o=read(root/'fixtures/oracle.json');runs=root/'runs'
 expected=set(full['full_output_checks'])|{x[0] for x in gates()}|{'nsys_'+m for m in GRAPH}|{'ncu_'+m for m in 'DUV'}
 expected|={f'timing_{i}_{m}' for i in range(6) for m in GRAPH}|{f'sustained_{r}_{i}_{m}' for r in ['zero','normal','all'] for i in range(2) for m in GRAPH}
 missing={f'sustained_all_1_{m}' for m in GRAPH} if interrupted else set()
 assert {p.name for p in runs.iterdir()}==expected-missing
 gold={r:read(root/'fixtures'/f'expected_{r:g}.json') for r in o['radii'].values()}
 inv={};coverage=[];runtimes=[]
 for p in sorted(runs.iterdir()):
  r=read(p/'receipt.json')
  assert r['input_sha256']=={n:sha(root/'fixtures'/n) for n in ['data.txt','queries.qid']}
  if interrupted and p.name=='sustained_all_0_L':
   assert (r['label'],r['mode'],r['radius'],r['repeats'],r['warmup'],r['tool'])==('sustained_all_0_L','L',o['radii']['all'],128,64,'clean')
   assert r['binary_sha256']==sha(common/'bin/graph_bench') and r['runner_sha256']==sha(common/'run_layout.py')
   assert r['stop_reason']=='foreign GPU activity' and r['exit_code']==-15 and not r['validation']['pass']
   assert any(x['foreign'] for x in read(p/'checks.json'))
   assert not (p/'result.json').exists() and not (p/'result.csv').exists()
   before=read(p/'before.json');assert not before['apps'].strip() and read(common/'logs/admission.json')['gpu_uuid'] in before['gpu']
   assert not r['post_gpu_clear'] and not r['runtime_errors']
   inv[p.name]={'state':'aborted: foreign GPU activity; not a correctness failure','receipt_sha256':sha(p/'receipt.json'),'checks_sha256':sha(p/'checks.json')}
   continue
  clean(r);rows=list(csv.DictReader((p/'result.csv').open()))
  assert r['label']==p.name and r['mode']==p.name[-1] and r['binary_sha256']==sha(common/'bin/graph_bench') and r['runner_sha256']==sha(common/'run_layout.py')
  assert r['input_sha256']=={n:sha(root/'fixtures'/n) for n in ['data.txt','queries.qid']}
  for phase in ['before','after']:
   v=read(p/(phase+'.json'));assert not v['apps'].strip() and read(common/'logs/admission.json')['gpu_uuid'] in v['gpu']
  checks=read(p/'checks.json');assert all(not x['foreign'] for x in checks)
  ticks=[0]+[x['elapsed_s'] for x in checks]+[r['wall_s']];coverage.extend(b-a for a,b in zip(ticks,ticks[1:]));runtimes.append(len(checks))
  assert len(rows)==64*r['repeats'] and [int(x['qid']) for x in rows]==o['queries']*r['repeats']
  assert all([int(x['count']),x['ordered_hash']]==gold[r['radius']][x['qid']] for x in rows)
  summary=check_summary(read(p/'result.json'),r,rows)
  assert summary['layout_bytes']==(0 if r['mode'] in 'ADE' else 888 if r['mode'] in 'US' else 888+64*o['dimension'])
  if not p.name.startswith('full_'):assert r['validation']['pass']
  if p.name.startswith('timing_'):assert (r['tool'],r['repeats'],r['warmup'],r['radius'])==('clean',64,64,o['radii']['normal'])
  if p.name.startswith('sustained_'):assert (r['tool'],r['repeats'],r['warmup'])==('clean',128,64) and r['radius']==o['radii'][p.name.split('_')[1]]
  if p.name.startswith('nsys_'):assert (r['tool'],r['repeats'],r['warmup'],r['radius'])==('nsys-node',2,64,o['radii']['normal'])
  if p.name.startswith('ncu_'):assert (r['tool'],r['repeats'],r['warmup'],r['radius'])==('ncu',1,0,o['radii']['normal'])
  inv[p.name]={'receipt_sha256':sha(p/'receipt.json'),'samples_sha256':sha(p/'result.csv'),'mode':r['mode'],'tool':r['tool'],'radius':r['radius'],'repeats':r['repeats']}
 times={};stats={}
 for m in GRAPH:
  v=[read(runs/f'timing_{i}_{m}/result.json') for i in range(6)]
  xs=[[float(x['query_us']) for x in csv.DictReader((runs/f'timing_{i}_{m}/result.csv').open())] for i in range(6)]
  times[m]=[x['sum_query_s']*1e6/x['queries'] for x in v]
  assert all(math.isclose(st.mean(x),t,rel_tol=1e-9) for x,t in zip(xs,times[m]))
  stats[m]={'process_mean_query_us':times[m],'median_process_mean_query_us':st.median(times[m]),'p10_p50_p90_query_us':[[percentile(x,p) for p in [.1,.5,.9]] for x in xs],
   'layout_setup_us':[x['layout_setup_s']*1e6 for x in v],'layout_bytes':sorted(set(x['layout_bytes'] for x in v)),
   'setup_us':[x['setup_s']*1e6 for x in v],'capture_us':[x['capture_instantiate_s']*1e6 for x in v],
   'first_query_us':[x['first_query_s']*1e6 for x in v],
   'setup_first_plus_4096_queries_us_per_query':[(x['layout_setup_s']+x['setup_s']+x['first_query_s']+x['sum_query_s'])*1e6/4096 for x in v],
   'cpu_one_core_percent':[100*x['loop_cpu_s']/x['loop_wall_s'] for x in v]}
 pairs={}
 for a,b in ['ES','EL','SL']:
  pairs[a+b]=paired_interval(times[a],times[b]);pairs[a+b]['ratio_of_medians']=st.median(times[a])/st.median(times[b])
  pairs[a+b]['order_split']={s:[times[a][i]/times[b][i] for i,o in enumerate(ORDERS) if (o.index(a)<o.index(b))==(s==a+b)] for s in [a+b,b+a]}
 sustained=[]
 for name in ['zero','normal','all']:
  for i,order in enumerate(['ESL','LSE']):
   ts={m:(lambda x:x['sum_query_s']*1e6/x['queries'])(read(runs/f'sustained_{name}_{i}_{m}/result.json')) for m in GRAPH if (runs/f'sustained_{name}_{i}_{m}/result.json').exists() and not (interrupted and (name,i,m)==('all',0,'L'))}
   sustained.append({'radius_class':name,'radius':o['radii'][name],'order':order,'query_us':ts,'complete':len(ts)==3,'ratios':{a+b:ts[a]/ts[b] for a,b in ['ES','EL','SL'] if a in ts and b in ts}})
 traces={m:trace(runs/f'nsys_{m}/trace.sqlite') for m in GRAPH}
 assert traces['E']['signature'][5:]==traces['S']['signature'][5:]==traces['L']['signature'][5:]
 for m,marker in [('E','findNextRnn('),('S','void findNextLayout<(bool)0>('),('L','void findNextLayout<(bool)1>(')]:
  assert all(traces[m]['signature'][i][0].startswith(marker) for i in [1,3])
  assert all(traces[m]['signature'][i]==traces['E']['signature'][i] for i in [0,2,4])
 decisions={}
 for m in 'SL':
  pair=pairs['E'+m];gate={'six_wins':pair['wins']==6,'lower_95_gt_1_05':pair['bootstrap_95'][0]>1.05,'complete_sustained_matrix':all(x['complete'] for x in sustained),'sustained_no_gt_5pct_regression':all('E'+m in x['ratios'] and x['ratios']['E'+m]>=1/1.05 for x in sustained)}
  decisions[m]={'status':'accepted bounded prototype' if all(gate.values()) else 'not promoted: performance gate not met','gates':gate}
 work={}
 for name in o['radii']:
  path=runs/f'full_{name}_E/result.flags.csv';rows=list(csv.DictReader(path.open()));assert len(rows)==128
  work[name]={'surviving_leaf_nodes':[sum(map(int,x['flags'][11:])) for x in rows if x['level']=='2'],'evaluated_child_distances':sum(int(x['evaluated_children']) for x in rows),'mean_per_query':sum(int(x['evaluated_children']) for x in rows)/64,'flags_sha256':sha(path),'tree_sha256':sha(path.with_name('result.tree.csv'))}
 return {'gpu_index':read(common/'logs/admission.json')['gpu_index'],'interrupted':interrupted,'missing_runs':sorted(missing),'fixture':{k:v for k,v in o.items() if k not in ['distances','queries','source_relative']},'full_verified':full,'run_inventory':inv,'safety':{'process_checks_total':sum(runtimes),'process_check_gap_median_s':st.median(coverage),'process_check_gap_max_s':max(coverage),'runs_without_inprocess_check':sum(x==0 for x in runtimes)},'statistics':stats,'paired':pairs,'sustained':sustained,'nsys':traces,'decisions':decisions,'logical_work':work}

def main(root,out,continuation=None):
 commons=[root]+([continuation] if continuation else [])
 for common in commons:
  assert (common/'graph_bench.cu').read_text()==driver((HERE.parent/'graph_query_20260923/graph_bench.cu').read_text())
  assert (common/'layout_generated.cuh').read_text()==kernel((common/'source/include/search.cuh').read_text())
  assert (common/'run_layout.py').read_text()==runner((HERE.parent/'graph_query_20260923/run.py').read_text())
  pins=read(HERE.parent/'original_tree_redundancy/SOURCE_PINS.json')['sha256']
  for n,h in pins.items():
   if n.startswith('GTS/'):assert sha(common/'source'/n.removeprefix('GTS/'))==h
  for p in ['layout_support.cuh','verify_full.py']:assert sha(common/p)==sha(HERE/p)
  admission=read(common/'logs/admission.json')
  assert admission['driver']=='590.48.01' and admission['cuda']=='13.1.115'
  names=['GIST','Deep','Tloc'] if not continuation else ['GIST'] if common==root else ['Deep','Tloc']
  observed=[read(common/'data'/n/'runs'/f'timing_{i}_{m}/receipt.json')['label'] for n in names for i,order in enumerate(ORDERS) for m in order]
  log=[json.loads(x)['label'] for x in (common/'logs/timing.txt').read_text().splitlines() if x.startswith('{') and '"label": "timing_' in x]
  assert observed==log
 if continuation:
  assert sha(root/'bin/graph_bench')==sha(continuation/'bin/graph_bench')
  assert read(root/'logs/admission.json')['gpu_index']==1 and read(continuation/'logs/admission.json')['gpu_index']==0
 results={n:dataset((root if n=='GIST' or not continuation else continuation)/'data'/n,root if n=='GIST' or not continuation else continuation,interrupted=(n=='GIST' and bool(continuation))) for n in ['GIST','Deep','Tloc']}
 hardware={str(read(c/'logs/admission.json')['gpu_index']):{k:v for k,v in read(c/'logs/admission.json').items() if k not in ['gpu_uuid','build_command']} for c in commons}
 record={'hardware':hardware,'experiment':'gts_20260923_pruning_layout_l2_2000','binary_sha256':sha(root/'bin/graph_bench'),'runner_sha256':sha(root/'run_layout.py'),'contract_sha256':sha(HERE/'CONTRACT.md'),'continuation_contract_sha256':sha(HERE/'CONTINUATION.md') if continuation else None,'source_commit':'3bac1b725e92e98e3b69d5cb79ad9c56ccb5e639','common_keeper_commit':'19641087f2873919575d6854d611bd6d9926c98d','scope':'hot completed batch-one queries, immutable N2000 H3, full ordered host output; construction excluded, layout/setup separately charged. Same-device pairs only; per-dataset interrupted flag records any incomplete sustained matrix.','timing_orders':ORDERS,'datasets':results,'suite_sha256_by_gpu':{str(read(c/'logs/admission.json')['gpu_index']):sha(c/'suite.py') for c in commons}}
 out.write_text(json.dumps(record,indent=2)+'\n')
 for n,r in results.items():print(n,json.dumps({'paired':r['paired'],'decisions':r['decisions']}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('out',type=Path);p.add_argument('--continuation',type=Path);a=p.parse_args();main(a.root,a.out,a.continuation)
