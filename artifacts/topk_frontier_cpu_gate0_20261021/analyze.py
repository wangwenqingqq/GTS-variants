"""Read-only full raw audit and conservative decision;never launches a population."""
if not __debug__:raise SystemExit('Assertions required')
import argparse,importlib.util,json,random,struct
from pathlib import Path,PurePosixPath
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('topk_run',HERE/'run.py');run=importlib.util.module_from_spec(spec);spec.loader.exec_module(run)
def verify_seal(raw,seal):
 expected=run.load(seal)['files'];actual={str(p.relative_to(raw)):run.identity(p) for p in sorted(raw.rglob('*')) if p.is_file()}
 assert expected==actual and not (raw/'FAILURE.json').exists()
def verify_argv(command,name):
 assert len(command)==4
 origin=PurePosixPath(command[0]).parent.parent
 assert origin.is_absolute() and '..' not in origin.parts
 assert command==[str(origin/'build/probe'),str(origin/'inputs'/(name+'.trace')),str(origin/'inputs'/(name+'.ids')),str(origin/name)]
 return str(origin)
def dp(a,b):
 old=list(range(len(b)+1))
 for i,ca in enumerate(a,1):
  new=[i]
  for j,cb in enumerate(b,1):new.append(min(old[j]+1,new[-1]+1,old[j-1]+(ca!=cb)))
  old=new
 return old[-1]
def analyze(raw,parent_inputs,seal):
 verify_seal(raw,seal);freeze=run.load(raw/'INPUT_FREEZE.json');registered=run.load(raw/'REGISTERED.json');built=run.load(raw/'BUILD.json');complete=run.load(raw/'COMPLETE.json')
 assert complete['passed'] and complete['GPU_starts']==0 and run.freeze_sources()==registered['sources']==run.load(HERE/'SOURCE_FREEZE.json')['files']
 assert run.identity(raw/'build/probe')==built['binary']
 origins=set()
 summary={'GPU_starts':0,'novelty':'NOT_ADMITTED','full_native_performance_admission':'NOT_EVALUATED','datasets':{}}
 for name,plan in freeze['plans'].items():
  trace=raw/'inputs'/(name+'.trace');idfile=raw/'inputs'/(name+'.ids');selection=raw/'inputs'/(name+'.selection.json');target=raw/name
  assert run.identity(trace)==plan['trace'] and run.identity(idfile)==plan['ids'] and run.load(selection)==plan
  start=run.load(raw/(name+'.START.json'));assert start['binary']==built['binary'] and start['trace']==plan['trace'] and start['ids']==plan['ids'] and start['selection']==run.identity(selection)
  origins.add(verify_argv(start['command'],name));assert len(origins)==1
  assert run.load(raw/(name+'.EXIT.json'))['returncode']==0 and not (raw/(name+'.stderr')).read_bytes()
  original=parent_inputs/(name+'.trace');parent_selection=parent_inputs/(name+'.selection.json');assert run.identity(original)==plan['parent_trace'] and run.identity(parent_selection)==plan['parent_selection']
  data=original.read_bytes().splitlines();selected=trace.read_bytes().splitlines();assert len(selected)==4161
  for row,idx in zip(selected[1:],plan['parent_rows']):assert row==data[idx+1]
  assert [int(v.split(b'\t',1)[0]) for v in selected[1:]]==plan['source_ids']
  prior=run.load(run.PREVIOUS/'evidence/INPUT_FREEZE.json')['plans'][name];assert plan['parent_rows'][:4096]==prior['parent_rows'][:4096]
  old={v for qs in run.load(parent_selection)['queries'].values() for v in qs};excluded=set(plan['parent_rows'][:4096])|old;rng=random.Random(2026102151);q=rng.sample([i for i in range(65536) if i not in excluded],64);rng.shuffle(q);assert q==plan['parent_rows'][4096:]
  proof=run.verify_target(target,plan);assert proof==run.load(raw/(name+'.PROOF.json'))
  costs=run.rows(target/'COSTS.csv');episodes=run.rows(target/'EPISODES.csv');work=run.rows(target/'QUERY_WORK.csv');build=run.rows(target/'BUILD.csv')[0];posts=run.rows(target/'POSTINGS.csv')[0]
  get=lambda e,m:next(z for z in costs if z['episode']==e and z['method']==m)
  initial={m:{'metric_calls':int(get('INITIAL',m)['metric_calls']),'cache_payload_bytes':int(get('INITIAL',m)['cache_payload_bytes'])} for m in run.METHODS}
  rr={};near=[];head=[];allpairs=set()
  for e in run.EPISODES:
   for qi,id,score in run.triples(target/(e+'_REFERENCE.bin')):allpairs.add((qi,id,int(score)))
  # Independent output-score rederivation;not an all-pair membership oracle.
  values={int(z.split(b'\t',1)[0]):z.split(b'\t',1)[1] for z in selected[1:]};sources=plan['source_ids'];checked=0
  for qi,id,score in sorted(allpairs):assert dp(values[sources[4096+qi]],values[id])==score;checked+=1
  for er in episodes:
   e=er['episode'];online=int(get(e,'RETAIN_FRONTIER')['metric_calls']);oracle=int(get(e,'FIXED_TREE_THRESHOLD_ORACLE')['metric_calls'])
   if e in ['TARGET256','DRAIN_OLD_TOPK']:near.append(10*online<=11*oracle);head.append(online>0 and online>=5*oracle)
   lifecycle={}
   for m in run.METHODS[:-1]:
    index=int(build['index_metric_calls']) if m in run.METHODS[:3] else 0
    life=index+int(get('INITIAL',m)['metric_calls'])+int(get(e,m)['metric_calls'])
    seconds=(float(build['index_seconds']) if index else 0)+float(posts['seconds'])+sum(float(get(ph,m)[k]) for ph in ['INITIAL',e] for k in ['compute_seconds','serialize_seconds'])
    lifecycle[m]={'metric_calls':life,'instrumented_seconds':seconds,'complete_output_bytes':54400}
   best=min(v['metric_calls'] for v in lifecycle.values())
   rr[e]={'pressure':{k:int(v) for k,v in er.items() if k!='episode'},'repair_metric_calls':{m:int(get(e,m)['metric_calls']) for m in run.METHODS},'repair_missing_output_pair_floor':{m:sum(int(z['missing_output_pair_floor']) for z in work if z['episode']==e and z['method']==m) for m in run.METHODS if m!='QUICKJOIN_TOPK_SEEDED'},'lifecycle':lifecycle,'best_ordinary_lifecycle_metric_calls':best,'root_vs_best_lifecycle_factor':lifecycle['GTS_CACHED_ROOT_RESTART']['metric_calls']/best,'retained_vs_threshold_oracle_metric_factor':online/oracle if oracle else (1.0 if not online else None),'by_k':{str(k):{m:sum(int(z['metric_calls']) for z in work if z['episode']==e and z['method']==m and int(z['k'])==k) for m in ['RETAIN_FRONTIER','RESERVE_K32','FIXED_TREE_THRESHOLD_ORACLE']} for k in [1,4,16,64]}}
  summary['datasets'][name]={'N':4096,'Q':64,'k':[1,4,16,64],'complete_method_streams':proof['complete_output_streams_checked'],'independent_output_score_pairs_DP_checked':checked,'index_metric_calls':int(build['index_metric_calls']),'index_payload_bytes':int(build['index_bytes']),'reverse_posting_payload_bytes':int(posts['bytes']),'initial':initial,'retained_initial_pair_coverage':initial['RETAIN_FRONTIER']['metric_calls']/262144,'episodes':rr,'near_restricted_oracle_on_both_target_episodes':all(near),'fivefold_restricted_headroom_on_both_target_episodes':all(head)}
 allnear=all(d['near_restricted_oracle_on_both_target_episodes'] for d in summary['datasets'].values());allhead=all(d['fivefold_restricted_headroom_on_both_target_episodes'] for d in summary['datasets'].values())
 observed=any(int(z['new_tau'])>int(z['old_tau']) and int(z['reopened_unknown_pairs'])>0 for name in summary['datasets'] for z in run.rows(raw/name/'FRONTIER.csv'))
 summary['mechanism_observation']='THRESHOLD_EXPANSION_OBSERVED' if observed else 'NO_EXPANSION_OBSERVED_IN_SCOPE'
 summary['decision']='LOCAL_REPAIR_NEAR_RESTRICTED_ORACLE' if allnear else 'RESTRICTED_WORK_HEADROOM_ONLY' if allhead else 'UNCLASSIFIED_STOP'
 summary['next_boundary']='STOP_FIXED_TREE_REPAIR_FAMILY' if allnear else 'NO_AUTOMATIC_GPU_OR_INDEX_ADMISSION'
 summary['scope']='Fixed ten-way tree,retained evaluated-score cache,N4096,Q64,one atomic deletion per independent episode. Oracle has only future tau,not arbitrary new certificates or joint-query execution.'
 return summary
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--parent-inputs',type=Path,required=True);p.add_argument('--seal',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();s=analyze(a.run.resolve(),a.parent_inputs.resolve(),a.seal.resolve());run.save(a.out,s);print(json.dumps(s,indent=2))
