"""Data-free publication identity/scalar replay;not a replacement for full raw audit."""
if not __debug__:raise SystemExit('Assertions required')
import argparse,csv,hashlib,importlib.util,json,shutil,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
METHODS=['GTS_CACHED_ROOT_RESTART','RETAIN_FRONTIER','RESERVE_K32','FULL_RANK_CACHE','QUICKJOIN_TOPK_SEEDED','FIXED_TREE_THRESHOLD_ORACLE']
EPISODES=['INITIAL','RANDOM256','TARGET256','DRAIN_OLD_TOPK','RANDOM_MATCHED']
def load(p):return json.loads(p.read_text())
def identity(p):return dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
def rows(p):return list(csv.DictReader(p.open()))
def check(root):
 manifest=load(root/'MANIFEST.json')['files'];actual={str(p.relative_to(root)):identity(p) for p in sorted(root.rglob('*')) if p.is_file() and p!=root/'MANIFEST.json'}
 assert actual==manifest,'PUBLICATION_MANIFEST_MISMATCH'
 frozen=load(root/'SOURCE_FREEZE.json')['files']
 for rel,pin in frozen.items():assert identity(root.parent/rel)==pin,'EXECUTION_SOURCE_IDENTITY_MISMATCH'
 summary=load(root/'results/SUMMARY.json');seal=load(root/'evidence/RUN_SEAL.json')['files'];complete=load(root/'evidence/COMPLETE.json');near=[];count=0;observed=False
 assert complete['passed'] and complete['GPU_starts']==summary['GPU_starts']==0 and summary['novelty']=='NOT_ADMITTED' and summary['full_native_performance_admission']=='NOT_EVALUATED'
 for name,d in summary['datasets'].items():
  costs=rows(root/'results'/name/'COSTS.csv');front=rows(root/'results'/name/'FRONTIER.csv');episodes=rows(root/'results'/name/'EPISODES.csv');work=rows(root/'results'/name/'QUERY_WORK.csv')
  assert len(costs)==30 and len(front)==256 and len(episodes)==4
  assert {(z['episode'],z['method']) for z in costs}=={(e,m) for e in EPISODES for m in METHODS}
  get=lambda e,m:next(z for z in costs if z['episode']==e and z['method']==m)
  build=rows(root/'results'/name/'BUILD.csv')[0];proof=load(root/'evidence'/(name+'.PROOF.json'))
  assert proof['passed'] and proof['complete_output_streams_checked']==30 and len(proof['output_identities'])==30
  for filename,pin in proof['output_identities'].items():assert seal[name+'/'+filename]==pin
  assert identity(root/'results'/name/'COSTS.csv')==seal[name+'/COSTS.csv']
  for m in METHODS:
   assert d['initial'][m]['metric_calls']==int(get('INITIAL',m)['metric_calls'])
   assert d['initial'][m]['cache_payload_bytes']==int(get('INITIAL',m)['cache_payload_bytes'])
  assert d['retained_initial_pair_coverage']==int(get('INITIAL','RETAIN_FRONTIER')['metric_calls'])/262144
  for e in EPISODES[1:]:
   ep=d['episodes'][e];er=next(z for z in episodes if z['episode']==e);assert ep['pressure']=={k:int(v) for k,v in er.items() if k!='episode'}
   ff=[z for z in front if z['episode']==e];assert len(ff)==64
   for k in ['reopened_nodes','reopened_live_pairs','reopened_unknown_pairs']:assert sum(int(z[k]) for z in ff)==int(er[k])
   assert sum(int(z['true_replacements']) for z in ff)==int(er['true_replacements'])
   observed|=any(int(z['new_tau'])>int(z['old_tau']) and int(z['reopened_unknown_pairs'])>0 for z in ff)
   for m in METHODS:
    cc=get(e,m);assert int(cc['metric_calls'])==int(cc['bound_metric'])+int(cc['verify_metric'])==ep['repair_metric_calls'][m]
    assert int(cc['output_count'])==1360 and int(cc['output_bytes'])==27200
    if m=='FULL_RANK_CACHE':assert int(cc['metric_calls'])==0
    if m!='QUICKJOIN_TOPK_SEEDED':
     ww=[z for z in work if z['episode']==e and z['method']==m]
     assert sum(int(z['metric_calls']) for z in ww)==int(cc['metric_calls'])
     assert sum(int(z['missing_output_pair_floor']) for z in ww)==ep['repair_missing_output_pair_floor'][m]
    if m!='FIXED_TREE_THRESHOLD_ORACLE':
     life=int(get('INITIAL',m)['metric_calls'])+int(cc['metric_calls'])+(int(build['index_metric_calls']) if m in METHODS[:3] else 0)
     assert ep['lifecycle'][m]['metric_calls']==life
   if e in ['TARGET256','DRAIN_OLD_TOPK']:near.append(10*ep['repair_metric_calls']['RETAIN_FRONTIER']<=11*ep['repair_metric_calls']['FIXED_TREE_THRESHOLD_ORACLE'])
  count+=30
 assert observed and all(near) and summary['decision']=='LOCAL_REPAIR_NEAR_RESTRICTED_ORACLE' and summary['next_boundary']=='STOP_FIXED_TREE_REPAIR_FAMILY'
 return dict(passed=True,scope='Data-free publish identity/counter replay;full private streams and independent output scores audited separately',complete_output_streams=count,GPU_starts=0,decision=summary['decision'],mechanism_observation=summary['mechanism_observation'],novelty=summary['novelty'],performance_admission=summary['full_native_performance_admission'])
def test():
 with tempfile.TemporaryDirectory(prefix='topk_publish_check_') as tmp:
  root=Path(tmp)/'artifacts'/HERE.name;shutil.copytree(HERE,root)
  for rel in load(HERE/'SOURCE_FREEZE.json')['files']:
   p=root.parent/rel
   if not p.exists():p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(HERE.parent/rel,p)
  check(root)
  for rel in ['results/SUMMARY.json','results/Words/COSTS.csv','evidence/COMPLETE.json']:
   p=root/rel;old=p.read_bytes();p.write_bytes(old+b' ')
   try:check(root)
   except AssertionError as e:assert str(e)=='PUBLICATION_MANIFEST_MISMATCH'
   else:raise AssertionError('Tamper accepted')
   p.write_bytes(old)
  check(root)
  spec=importlib.util.spec_from_file_location('argv_audit',root/'analyze.py');audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)
  for origin in ['/task/run','/different/a_new_persistent_run']:
   command=[origin+'/build/probe',origin+'/inputs/Words.trace',origin+'/inputs/Words.ids',origin+'/Words'];assert audit.verify_argv(command,'Words')==origin
   command[-1]='/different/output'
   try:audit.verify_argv(command,'Words')
   except AssertionError:pass
   else:raise AssertionError('Mismatched argv root accepted')
 return 3
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--test',action='store_true');a=p.parse_args();result=check(HERE)
 if a.test:result['tamper_cases_rejected']=test()
 print(json.dumps(result,indent=2,sort_keys=True))
