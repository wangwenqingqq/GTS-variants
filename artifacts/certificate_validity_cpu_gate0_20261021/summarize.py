"""Post-run read-only source/input/output audit and descriptive accounting."""
if not __debug__:raise SystemExit('Assertions required')
import csv,json,random
from pathlib import Path
from run import HERE,PARENT,identity,load,freeze_sources,verify_target

def summarize(costs,queries,calibration,validity):
 for z in costs:
  for k in ['state','N','metric_calls','index_bytes','moved_certificate_entries','diagnostic_checked_entries','unaffected_old_entries_changed']:z[k]=int(z[k])
 for z in queries:
  for k in ['state','level','radius','N','Q','distance_calls','bound_calls','verify_calls','partition_calls','query_plan_calls','scalar_bound_checks','node_pair_visits','candidate_pairs','frontier_bytes','output_count','output_bytes']:z[k]=int(z[k])
 cells=[]
 for n in ['Words','DNA_GRCh38_chr1_108']:
  for state in range(3):
   cs=[z for z in costs if z['dataset']==n and z['state']==state];inc=next(z for z in cs if z['method']=='PIVOT_INCREMENTAL_CPU')
   assert inc['metric_calls']==[16384,0,128][state] and inc['unaffected_old_entries_changed']==0
   for level in range(3):
    qs=[z for z in queries if z['dataset']==n and z['state']==state and z['level']==level];by={z['method']:z for z in qs};assert len(qs)==4
    a=by['PIVOT_INCREMENTAL_CPU'];b=by['PIVOT_RECOMPUTE_ALL_WEAK']
    assert a['distance_calls']==b['distance_calls'] and a['output_count']==b['output_count']
    assert a['query_plan_calls']==256
    cells.append(dict(dataset=n,state=state,level=level,radius=a['radius'],N=a['N'],Q=a['Q'],output_count=a['output_count'],achieved_selectivity=a['output_count']/(a['N']*a['Q']),pivot_metric_calls=a['distance_calls'],pivot_scalar_checks=a['scalar_bound_checks'],gts_metric_calls=by['GTS_CACHED_SNAPSHOT_CPU']['distance_calls'],quickjoin_metric_calls=by['QUICKJOIN_FAMILY_CPU']['distance_calls'],source_bytes_unknown=True))
 return dict(decision='BASELINE_SUFFICIENT_FOR_VALIDITY',novelty_admitted=False,performance_admission='NOT_EVALUATED',native_SPB_executed=False,native_GTS_update_executed=False,GPU_starts=0,protected_GIST_heldout_accesses=0,campaign_validity=validity,costs=costs,queries=queries,calibration=calibration,cells=cells,
  scope='Two CPU subset diagnostics;ordinary incremental columns only. Raw payload movement symbolic;no full native update ACK,speedup,tail or new mechanism admission.',
  diagnostic_metric_calls_separate=sum(z['diagnostic_checked_entries'] for z in costs))

def audit(root,parent_inputs):
 assert not (root/'FAILURE.json').exists();complete=load(root/'COMPLETE.json');assert complete['passed'] and len(complete['records'])==2
 actual={str(p.relative_to(root)):identity(p) for p in sorted(root.rglob('*')) if p.is_file()}
 seal=load(root.with_name(root.name+'.SEAL.json'));assert seal['before_analysis'] and actual==seal['files']
 frozen=load(HERE/'SOURCE_FREEZE.json');assert freeze_sources()==frozen['files']==load(root/'REGISTERED.json')['sources']
 reg=load(root/'REGISTERED.json');assert reg['threads']==1 and reg['nice']==10 and reg['GPU_starts']==0
 inputs=load(root/'INPUT_FREEZE.json');assert inputs['before_calibration_and_evaluation'] and inputs['source_freeze']==identity(HERE/'SOURCE_FREEZE.json')
 binary=root/'build/probe';assert identity(binary)==load(root/'BUILD.json')['binary']
 expected_helper=(PARENT/'trace.cpp').read_text().split('\nint main(',1)[0]+'\n';assert (root/'build/trace_helpers.hpp').read_text()==expected_helper
 assert not (root/'build/compile.stderr').read_bytes() and not (root/'build/fixtures.stderr').read_bytes()
 costs=[];queries=[];calibration=[];checked=0;pins=load(PARENT/'evidence/INPUTS.json');bindings={}
 for i,n in enumerate(['Words','DNA_GRCh38_chr1_108']):
  selection=load(root/'inputs'/(n+'.selection.json'));assert selection==inputs['plans'][n]
  rng=random.Random(2026102141);rows=sorted(rng.sample(range(65536),4096))+list(range(65536,65568))
  parent_sel=load(parent_inputs/(n+'.selection.json'));assert identity(parent_inputs/(n+'.trace'))==pins['sources'][n]['trace_input'] and identity(parent_inputs/(n+'.selection.json'))==pins['sources'][n]['selection']
  oldqueries=set(v for qs in parent_sel['queries'].values() for v in qs);qs=rng.sample([j for j,v in enumerate(rows[:4096]) if v not in oldqueries],96)
  piv=rng.sample([j for j in range(4096) if j not in qs],4);deleted=piv+rng.sample([j for j in range(4096) if j not in qs and j not in piv],28)
  assert selection['parent_rows']==rows and selection['q']==qs[32:] and selection['calibration']==qs[:32] and selection['pivots']==piv and selection['deleted']==deleted
  trace=root/'inputs'/(n+'.trace');ids=root/'inputs'/(n+'.ids')
  assert identity(trace)==selection['trace'] and identity(ids)==selection['ids']
  assert [int(v) for v in ids.read_text().split()]==qs[32:]+qs[:32]+piv+deleted
  raw=(parent_inputs/(n+'.trace')).read_bytes().splitlines();assert trace.read_bytes()==f'{n} 4128 1\n'.encode()+b''.join(raw[j+1]+b'\n' for j in rows)
  start=load(root/(n+'.START.json'));cmd=start['command'];original_root=Path(cmd[0]).parent.parent
  assert cmd==[str(original_root/'build/probe'),str(original_root/'inputs'/(n+'.trace')),str(original_root/'inputs'/(n+'.ids')),str(original_root/n)] and start['before_start']
  assert start['binary']==identity(binary) and start['trace']==identity(trace) and start['ids']==identity(ids) and start['selection']==identity(root/'inputs'/(n+'.selection.json'))
  ex=load(root/(n+'.EXIT.json'));assert ex['returncode']==0 and ex['wall_seconds']<=600 and not (root/(n+'.stderr')).read_bytes()
  proof=verify_target(root/n,selection);assert proof==load(root/(n+'.PROOF.json'))==complete['records'][i]['proof'];assert complete['records'][i]['dataset']==n
  checked+=proof['complete_output_streams_checked'];bindings[n]=dict(start=identity(root/(n+'.START.json')),trace=identity(trace),ids=identity(ids),selection=identity(root/'inputs'/(n+'.selection.json')),parent_trace=selection['parent_trace'])
  costs.extend(dict(dataset=n,**z) for z in csv.DictReader((root/n/'COSTS.csv').open()))
  queries.extend(csv.DictReader((root/n/'QUERY.csv').open()))
  calibration.extend(dict(dataset=n,**z) for z in csv.DictReader((root/n/'CALIBRATION.csv').open()))
 assert len(costs)==24 and len(queries)==72 and len(calibration)==6 and checked==72
 assert sum(p['bytes'] for p in actual.values())<=268435456
 validity=dict(passed=True,source_freeze=identity(HERE/'SOURCE_FREEZE.json'),contract=identity(HERE/'CONTRACT.json'),seal=identity(root.with_name(root.name+'.SEAL.json')),sealed_files=len(actual),sealed_bytes=sum(p['bytes'] for p in actual.values()),input_freeze=identity(root/'INPUT_FREEZE.json'),complete=identity(root/'COMPLETE.json'),complete_streams_checked=checked,bindings=bindings)
 return summarize(costs,queries,calibration,validity)
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--parent-inputs',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 result=audit(a.run,a.parent_inputs)
 with a.out.open('x') as f:json.dump(result,f,indent=2,sort_keys=True);f.write('\n')
