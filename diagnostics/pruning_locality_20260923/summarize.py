#!/usr/bin/env python3
"""Validate every frozen observation and curate the locality screen."""
import argparse,csv,importlib.util,json,math,sqlite3,statistics as st,sys
from pathlib import Path
from prepare import HERE,OLD,driver,kernel,runner,support,verifier
from suite import plan,ORDERS,GRAPH,FULL,STRESS,NCU,TOOLS,require
sys.path.insert(0,str(HERE.parent/'graph_query_20260923'))
from analyze import paired_interval,percentile

def read(p):return json.loads(p.read_text())
def trace(path):
 with sqlite3.connect(path) as db:
  rows=db.execute('SELECT s.value,k.gridX,k.gridY,k.gridZ,k.blockX,k.blockY,k.blockZ,k.registersPerThread,k.staticSharedMemory,k.dynamicSharedMemory,k.end-k.start FROM CUPTI_ACTIVITY_KIND_KERNEL k JOIN StringIds s ON s.id=k.demangledName ORDER BY k.start').fetchall()
  first=next(i for i,r in enumerate(rows) if r[0].startswith('initQnode('));rows=rows[first:]
  assert len(rows)==193*17
  sig=[list(x[:-1]) for x in rows[:17]]
  assert all([list(x[:-1]) for x in rows[i:i+17]]==sig for i in range(0,len(rows),17))
  assert db.execute('SELECT count(*) FROM CUPTI_ACTIVITY_KIND_RUNTIME WHERE returnValue!=0').fetchone()[0]==0
  api=dict(db.execute('SELECT s.value,count(*) FROM CUPTI_ACTIVITY_KIND_RUNTIME r JOIN StringIds s ON s.id=r.nameId GROUP BY r.nameId'))
  assert api['cudaGraphLaunch_v10000']==193
  return dict(signature=sig,kernels_per_query=17,query_instances=193,pruning_sum_us=sum(r[-1] for i,r in enumerate(rows) if i%17 in [1,3])/193/1000,all_kernel_sum_us=sum(r[-1] for r in rows)/193/1000,sqlite_sha256=sha(path))

def layout_bytes(mode,d):
 if mode in 'ADE':return 0
 if mode in 'SU':return 888
 return 888+4*({'L':16*d,'V':16*d,'R':11*d,'B':11*d,'T':((d+7)//8)*104,'C':((d+7)//8)*104}[mode])

def profiles(data,root,o):
 spec=importlib.util.spec_from_file_location('ncu_fields',OLD/'summarize_ncu.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
 output={}
 for mode,marker in [('D','findNextRnn('),('U','findNextLayout<0>'),('V','findNextLayout<1>'),('B','findNextLayout<2>'),('C','findNextLayout<3>')]:
  p=data/'runs'/('ncu_'+mode);cmd=read(p/'command.json')
  prefix=['ncu','--kernel-name-base','demangled','--kernel-name','regex:findNext(Rnn|Layout)','--launch-count','2','--clock-control','none','--cache-control','none','--export']
  assert cmd[:len(prefix)]==prefix and cmd[len(prefix)+1:len(prefix)+1+16]==[a for s in mod.SECTIONS for a in ['--section',s]]
  raw=list(csv.reader((p/'metrics_raw.csv').open()));assert len(raw)==4
  details=list(csv.DictReader((p/'metrics.csv').open()));units=dict(zip(raw[0],raw[1]));ks=[];total={}
  for i,row in enumerate(raw[2:]):
   v=dict(zip(raw[0],row));assert v['ID']==str(i) and marker in v['Kernel Name']
   assert float(v['profiler__replayer_passes'])==34 and int(v['device__attribute_multiprocessor_count'])==188
   d={x['Metric Name']:{'value':x['Metric Value'],'unit':x['Metric Unit']} for x in details if x['ID']==str(i) and x['Metric Name'] in mod.DETAILS}
   assert set(d)==mod.DETAILS and d['Grid Size']['value']=='1' and d['Block Size']['value']=='512'
   metrics={k:{'value':v[k],'unit':units[k]} for k in mod.RAW};ks.append(dict(kernel=v['Kernel Name'],details=d,raw=metrics))
   for k in mod.RAW:
    if k.endswith('.sum') and k!='gpu__time_duration.sum':total[k]=total.get(k,0)+float(v[k])
   u=units['gpu__time_duration.sum'];factor={'us':1,'ms':1000,'nsecond':.001,'usecond':1,'msecond':1000}[u]
   total['replay_duration_us']=total.get('replay_duration_us',0)+float(v['gpu__time_duration.sum'])*factor
  output[mode]=dict(kernels=ks,sum_two_levels=total,raw_metrics_sha256=sha(p/'metrics_raw.csv'),details_sha256=sha(p/'metrics.csv'))
 return output

def dataset(root,common):
 o=read(root/'fixtures/oracle.json')
 prior=read(OLD/'EVIDENCE.json')['datasets'][o['dataset']]
 for k in ['data_sha256','qids_sha256','source_indices_sha256','source_sha256','dimension','radii']:assert o[k]==prior['fixture'][k],k
 assert sha(root/'fixtures/source_indices.json')==o['source_indices_sha256']
 assert sha(root/'fixtures/oracle.json')==prior['full_verified']['oracle_sha256']
 full=verify(root);require(root,common,'ncu')
 stages=['full','gates','stress','screen','sustained','trace','ncu'];expected={r[0]:r for s in stages for r in plan(s,o['radii'])}
 assert {p.name for p in (root/'runs').iterdir()}==set(expected)
 gold={r:read(root/'fixtures'/f'expected_{r:g}.json') for r in o['radii'].values()};inv={};gaps=[];no_checks=0
 for label,mode,radius,reps,warmup,tool,dump in expected.values():
  p=root/'runs'/label;x=read(p/'receipt.json');clean(x)
  assert tuple(x[k] for k in ['label','mode','radius','repeats','warmup','tool','dump'])==(label,mode,radius,reps,warmup,tool,dump)
  assert x['binary_sha256']==sha(common/'bin/graph_bench') and x['runner_sha256']==sha(common/'run_layout.py')
  assert x['input_sha256']=={n:sha(root/'fixtures'/n) for n in ['data.txt','queries.qid']}
  for phase in ['before','after']:
   v=read(p/(phase+'.json'));assert not v['apps'].strip() and read(common/'logs/admission.json')['gpu_uuid'] in v['gpu']
  checks=read(p/'checks.json');assert all(not c['foreign'] for c in checks)
  ts=[0]+[c['elapsed_s'] for c in checks]+[x['wall_s']];gaps.extend(b-a for a,b in zip(ts,ts[1:]));no_checks+=not bool(checks)
  rows=list(csv.DictReader((p/'result.csv').open()));assert [int(r['qid']) for r in rows]==o['queries']*reps
  assert all([int(r['count']),r['ordered_hash']]==gold[radius][r['qid']] for r in rows)
  summary=check_summary(read(p/'result.json'),x,rows);assert summary['layout_bytes']==layout_bytes(mode,o['dimension'])
  if not label.startswith('full_'):assert x['validation']['pass']
  if tool in TOOLS:
   log=(p/'stdout.log').read_text()+(p/'stderr.log').read_text();assert ('RACECHECK SUMMARY: 0 hazards' if tool=='racecheck' else 'ERROR SUMMARY: 0 errors') in log
  inv[label]=dict(mode=mode,tool=tool,radius=radius,queries=len(rows),receipt_sha256=sha(p/'receipt.json'),samples_sha256=sha(p/'result.csv'))
 stats={};times={}
 for m in GRAPH:
  vs=[read(root/'runs'/f'screen_{i}_{m}/result.json') for i in range(4)]
  xs=[[float(r['query_us']) for r in csv.DictReader((root/'runs'/f'screen_{i}_{m}/result.csv').open())] for i in range(4)]
  times[m]=[v['sum_query_s']*1e6/v['queries'] for v in vs]
  assert all(math.isclose(st.mean(a),b,rel_tol=1e-9) for a,b in zip(xs,times[m]))
  stats[m]=dict(process_mean_query_us=times[m],median_process_mean_query_us=st.median(times[m]),p10_p50_p90_query_us=[[percentile(a,p) for p in [.1,.5,.9]] for a in xs],layout_bytes=layout_bytes(m,o['dimension']),layout_setup_us=[v['layout_setup_s']*1e6 for v in vs],first_query_us=[v['first_query_s']*1e6 for v in vs],setup_us=[v['setup_s']*1e6 for v in vs],capture_us=[v['capture_instantiate_s']*1e6 for v in vs],cpu_one_core_percent=[100*v['loop_cpu_s']/v['loop_wall_s'] for v in vs],setup_first_plus_512_queries_us_per_query=[(v['layout_setup_s']+v['setup_s']+v['first_query_s']+v['sum_query_s'])*1e6/512 for v in vs])
 pairs={}
 for a,b in ['ES','ER','ET','SR','ST','RT']:
  v=paired_interval(times[a],times[b]);v['method']='Exact percentile bootstrap of four paired process log ratios; 4^4 resamples'
  v['ratio_of_medians']=st.median(times[a])/st.median(times[b]);v['order_split']={s:[times[a][i]/times[b][i] for i,o in enumerate(ORDERS) if (o.index(a)<o.index(b))==(s==a+b)] for s in [a+b,b+a]};pairs[a+b]=v
 sustained=[]
 for i,order in enumerate(['ESRT','TRSE']):
  ts={m:(lambda v:v['sum_query_s']*1e6/v['queries'])(read(root/'runs'/f'sustained_{i}_{m}/result.json')) for m in GRAPH}
  sustained.append(dict(order=order,query_us=ts,ratios={a+b:ts[a]/ts[b] for a,b in ['ER','ET','SR','ST','RT']}))
 decisions={}
 for m in 'RT':
  gates={b:dict(four_wins=pairs[b+m]['wins']==4,lower_95_gt_1_03=pairs[b+m]['bootstrap_95'][0]>1.03,sustained_no_gt_5pct_regression=all(s['ratios'][b+m]>=1/1.05 for s in sustained)) for b in 'ES'}
  decisions[m]=dict(followup_warranted=all(all(g.values()) for g in gates.values()),gates=gates,production_promoted=False,scope='Four-process screen and normal-only sustained; no all-radius promotion')
 traces={m:trace(root/'runs'/('nsys_'+m)/'trace.sqlite') for m in GRAPH}
 for m,marker in [('E','findNextRnn('),('S','findNextLayout<0>'),('R','findNextLayout<2>'),('T','findNextLayout<3>')]:
  assert traces[m]['signature'][5:]==traces['E']['signature'][5:]
  assert all(marker in traces[m]['signature'][i][0].replace('<(int)','<') for i in [1,3])
  assert all(traces[m]['signature'][i]==traces['E']['signature'][i] for i in [0,2,4])
 work={}
 for name in o['radii']:
  p=root/'runs'/f'full_{name}_E/result.flags.csv';rows=list(csv.DictReader(p.open()));assert len(rows)==128
  work[name]=dict(flags_sha256=sha(p),tree_sha256=sha(p.with_name('result.tree.csv')),evaluated_child_distances=sum(int(r['evaluated_children']) for r in rows),surviving_leaf_nodes=[sum(map(int,r['flags'][11:])) for r in rows if r['level']=='2'])
 return dict(fixture={k:v for k,v in o.items() if k not in ['distances','queries','source_relative']},full_verified=full,inventory=inv,statistics=stats,paired=pairs,sustained=sustained,decisions=decisions,nsys=traces,ncu=profiles(root,common,o),logical_work=work,safety=dict(process_check_gap_median_s=st.median(gaps),process_check_gap_max_s=max(gaps),runs_without_inprocess_checks=no_checks))

def main(root,out,allow_rebuild=False):
 global sha,clean,verify,check_summary
 sys.path.insert(0,str(root))
 from verify_full import sha,clean,verify,check_summary
 assert (root/'graph_bench.cu').read_text()==driver((HERE.parent/'graph_query_20260923/graph_bench.cu').read_text())
 assert (root/'layout_generated.cuh').read_text()==kernel((root/'source/include/search.cuh').read_text())
 assert (root/'layout_support.cuh').read_text()==support() and (root/'verify_full.py').read_text()==verifier()
 assert (root/'run_layout.py').read_text()==runner((HERE.parent/'graph_query_20260923/run.py').read_text())
 for f in ['layout_index.cuh','suite.py','CONTRACT.md']:assert sha(root/f)==sha(HERE/f)
 pins=read(HERE.parent/'original_tree_redundancy/SOURCE_PINS.json')['sha256']
 for n,h in pins.items():
  if n.startswith('GTS/'):assert sha(root/'source'/n.removeprefix('GTS/'))==h
 historical_binary=sha(root/'bin/graph_bench')==read(HERE/'STATIC_EVIDENCE.json')['binary_sha256']
 assert historical_binary or allow_rebuild,'New binary: use --allow-rebuild for unpromoted replication; fresh static audit required'
 admission=read(root/'logs/admission.json');assert admission['gpu_index']==5 and admission['driver']=='590.48.01' and admission['cuda']=='13.1.115'
 for stage in ['full','gates','stress','screen','sustained','trace','ncu']:
  observed=[json.loads(s)['label'] for s in (root/'logs'/(stage+'.txt')).read_text().splitlines() if s.startswith('{')]
  expected=[r[0] for ds in ['GIST','Deep','Tloc'] for r in plan(stage,read(root/'data'/ds/'fixtures/oracle.json')['radii'])]
  assert observed==expected,stage
 result=dict(experiment='gts_20260923_pruning_locality_screen_l2_2000',state='screen only; no production promotion',scope='Hot completed batch-one query including transfers/synchronization; construction/layout/setup/capture/hashing excluded. Setup charged separately, not a cold-application claim.',hardware={k:admission[k] for k in ['gpu_index','gpu_name','driver','power_limit','arch','cuda','clocks_locked','clock_policy','verified_at_utc']},source_commit='3bac1b725e92e98e3b69d5cb79ad9c56ccb5e639',common_keeper_commit='a184d7aa074939d637273edff394860f5553752c',binary_sha256=sha(root/'bin/graph_bench'),runner_sha256=sha(root/'run_layout.py'),contract_sha256=sha(HERE/'CONTRACT.md'),orders=ORDERS,datasets={ds:dataset(root/'data'/ds,root) for ds in ['GIST','Deep','Tloc']})
 result['matches_archived_static_binary']=historical_binary
 if not historical_binary:
  result['state']='replication measurements only; new binary requires separate static/SASS audit'
  for v in result['datasets'].values():
   for decision in v['decisions'].values():decision['followup_warranted']=False;decision['static_audit_pending']=True
 out.write_text(json.dumps(result,indent=2)+'\n')
 for ds,v in result['datasets'].items():print(ds,json.dumps(dict(medians={m:s['median_process_mean_query_us'] for m,s in v['statistics'].items()},paired=v['paired'],decisions=v['decisions'])))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('out',type=Path);p.add_argument('--allow-rebuild',action='store_true');a=p.parse_args();main(a.root.resolve(),a.out,a.allow_rebuild)
