"""Freeze and execute two bounded CPU top-k/deletion targets;first failure stops."""
if not __debug__:raise SystemExit('Assertions required')
import argparse,csv,hashlib,json,os,platform,random,shutil,struct,subprocess,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
PARENT=HERE.parent/'shared_frontier_cpu_trace_20261021'
PREVIOUS=HERE.parent/'certificate_validity_cpu_gate0_20261021'
METHODS=['GTS_CACHED_ROOT_RESTART','RETAIN_FRONTIER','RESERVE_K32','FULL_RANK_CACHE','QUICKJOIN_TOPK_SEEDED','FIXED_TREE_THRESHOLD_ORACLE']
EPISODES=['INITIAL','RANDOM256','TARGET256','DRAIN_OLD_TOPK','RANDOM_MATCHED']
def identity(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return dict(bytes=p.stat().st_size,sha256=h.hexdigest())
def load(p):return json.loads(p.read_text())
def save(p,x):
 with p.open('x') as f:json.dump(x,f,indent=2,sort_keys=True);f.write('\n')
def rows(p):return list(csv.DictReader(p.open()))
def freeze_sources():
 paths=[HERE/'CONTRACT.json',HERE/'probe.cpp',HERE/'run.py',PARENT/'trace.cpp',PARENT/'evidence/INPUTS.json',PREVIOUS/'evidence/INPUT_FREEZE.json']
 return {str(p.relative_to(HERE.parent)):identity(p) for p in paths}
def triples(p):return list(struct.iter_unpack('<IQd',p.read_bytes()))
def verify_target(target,selection):
 costs=rows(target/'COSTS.csv');front=rows(target/'FRONTIER.csv');episodes=rows(target/'EPISODES.csv');work=rows(target/'QUERY_WORK.csv')
 assert len(costs)==30 and len(front)==256 and len(episodes)==4
 assert {(z['episode'],z['method']) for z in costs}=={(e,m) for e in EPISODES for m in METHODS}
 ids=selection['source_ids'];allids=set(ids[:4096]);live={e:allids.copy() for e in EPISODES};deleted={}
 for e in EPISODES[1:]:
  d=list(map(int,(target/(e+'.delete')).read_text().split()));assert len(d)==len(set(d)) and all(0<=v<4096 for v in d)
  deleted[e]=d;live[e]-={ids[v] for v in d}
 assert len(deleted['RANDOM256'])==len(deleted['TARGET256'])==256 and len(deleted['DRAIN_OLD_TOPK'])==len(deleted['RANDOM_MATCHED'])<=1360
 ref={};ks=[1,4,16,64]*16
 for e in EPISODES:
  ref[e]=triples(target/(e+'_REFERENCE.bin'));assert len(ref[e])==1360
  for qi in range(64):
   v=[z for z in ref[e] if z[0]==qi];assert len(v)==ks[qi] and len({z[1] for z in v})==ks[qi]
   assert all(z[1] in live[e] and z[2]==int(z[2]) and 0<=z[2]<=128 for z in v)
   assert [(z[2],z[1]) for z in v]==sorted((z[2],z[1]) for z in v)
 expected_union={i for _,i,_ in ref['INITIAL']};assert {ids[v] for v in deleted['DRAIN_OLD_TOPK']}==expected_union
 order=[];seen=set()
 old={qi:[z[1] for z in ref['INITIAL'] if z[0]==qi] for qi in range(64)}
 for rank in range(64):
  for qi in range(64):
   if rank<len(old[qi]) and old[qi][rank] not in seen:seen.add(old[qi][rank]);order.append(old[qi][rank])
 assert [ids[v] for v in deleted['TARGET256']][:min(256,len(order))]==order[:256]
 checks=0;hashes={}
 for z in costs:
  e,m=z['episode'],z['method'];actual=target/(e+'_'+m+'.bin');reference=target/(e+'_REFERENCE.bin')
  assert actual.read_bytes()==reference.read_bytes() and actual.stat().st_size==27200==int(z['output_bytes']) and int(z['output_count'])==1360
  assert int(z['N'])==len(live[e]) and int(z['Q'])==64
  assert int(z['metric_calls'])==int(z['bound_metric'])+int(z['verify_metric'])
  assert all(float(z[k])>=0 for k in ['compute_seconds','serialize_seconds','mutation_seconds'])
  if m=='FULL_RANK_CACHE':assert int(z['metric_calls'])==(262144 if e=='INITIAL' else 0)
  hashes[actual.name]=identity(actual);checks+=1
 for e in EPISODES[1:]:
  ff=[z for z in front if z['episode']==e];assert len(ff)==64 and {int(z['qi']) for z in ff}==set(range(64))
  er=next(z for z in episodes if z['episode']==e);assert int(er['deletes'])==len(deleted[e])
  affected=0;up=0;removedsum=0;replacedsum=0
  for z in ff:
   qi=int(z['qi']);before=[v for v in ref['INITIAL'] if v[0]==qi];after=[v for v in ref[e] if v[0]==qi];oldset={v[1] for v in before};newset={v[1] for v in after}
   removed=len(oldset-live[e]);replaced=len(newset-oldset);assert removed==replaced==int(z['removed_answers'])==int(z['true_replacements'])
   assert int(z['old_tau'])==int(before[-1][2]) and int(z['new_tau'])==int(after[-1][2])>=int(z['old_tau'])
   assert int(z['k'])==ks[qi] and int(z['reopened_unknown_pairs'])<=int(z['reopened_live_pairs'])
   if z['new_tau']==z['old_tau']:assert int(z['reopened_nodes'])==0
   affected+=removed>0;up+=int(z['new_tau'])>int(z['old_tau']);removedsum+=removed;replacedsum+=replaced
  assert (affected,up,removedsum,replacedsum)==tuple(int(er[k]) for k in ['affected_queries','tau_up_queries','removed_answers','true_replacements'])
  for k in ['reopened_nodes','reopened_live_pairs','reopened_unknown_pairs']:assert sum(int(z[k]) for z in ff)==int(er[k])
  for m in METHODS:
   cc=next(z for z in costs if z['episode']==e and z['method']==m);assert int(cc['affected_queries'])==affected
   if m!='QUICKJOIN_TOPK_SEEDED':
    ww=[z for z in work if z['episode']==e and z['method']==m];assert len(ww)==affected
    assert sum(int(z['metric_calls']) for z in ww)==int(cc['metric_calls'])
 for m in METHODS[:4]:
  assert sum(int(z['metric_calls']) for z in work if z['episode']=='INITIAL' and z['method']==m)==int(next(z for z in costs if z['episode']=='INITIAL' and z['method']==m)['metric_calls'])
 return dict(passed=True,complete_output_streams_checked=checks,output_records_checked=checks*1360,output_identities=hashes,GPU_starts=0,reference_scope='Same edit primitive;581 independent DP pairs plus dynamic fixtures separately qualify arithmetic')
def main(parent_inputs,out):
 assert os.getpriority(os.PRIO_PROCESS,0)==10 and not out.exists() and shutil.disk_usage(out.parent).free>=1024**3
 frozen=load(HERE/'SOURCE_FREEZE.json');assert freeze_sources()==frozen['files'];out.mkdir();(out/'inputs').mkdir();(out/'build').mkdir()
 cpu=next(x.split(':',1)[1].strip() for x in Path('/proc/cpuinfo').read_text().splitlines() if x.startswith('model name'))
 save(out/'REGISTERED.json',dict(before_population=True,sources=freeze_sources(),CPU=cpu,Python=platform.python_version(),threads=1,nice=10,GPU_starts=0,compiler=subprocess.check_output(['g++','--version'],text=True)))
 try:
  helper=(PARENT/'trace.cpp').read_text().split('\nint main(',1)[0]+'\n';(out/'build/trace_helpers.hpp').write_text(helper);binary=out/'build/probe'
  command=['g++','-std=c++17','-O2','-fno-fast-math','-ffp-contract=off','-I',str(out/'build'),str(HERE/'probe.cpp'),'-o',str(binary)]
  p=subprocess.run(command,capture_output=True,text=True);(out/'build/compile.stdout').write_text(p.stdout);(out/'build/compile.stderr').write_text(p.stderr);assert p.returncode==0 and not p.stderr
  p=subprocess.run([str(binary),'--self-test'],capture_output=True,text=True,timeout=60);(out/'build/fixtures.stdout').write_text(p.stdout);(out/'build/fixtures.stderr').write_text(p.stderr);assert p.returncode==0 and not p.stderr
  save(out/'BUILD.json',dict(passed=True,binary=identity(binary),helper=identity(out/'build/trace_helpers.hpp'),fixture_stdout=identity(out/'build/fixtures.stdout')))
  pins=load(PARENT/'evidence/INPUTS.json');prior=load(PREVIOUS/'evidence/INPUT_FREEZE.json');plans={}
  for name in ['Words','DNA_GRCh38_chr1_108']:
   src=parent_inputs/(name+'.trace');sel=parent_inputs/(name+'.selection.json');assert identity(src)==pins['sources'][name]['trace_input'] and identity(sel)==pins['sources'][name]['selection']
   selection=load(sel);oldqueries={v for qs in selection['queries'].values() for v in qs};refs=prior['plans'][name]['parent_rows'][:4096];assert len(refs)==len(set(refs))==4096
   excluded=set(refs)|oldqueries;allowed=[v for v in range(65536) if v not in excluded];rng=random.Random(2026102151);query=rng.sample(allowed,64);rng.shuffle(query);positions=refs+query
   raw=src.read_bytes().splitlines();assert len(raw)==65569;trace=out/'inputs'/(name+'.trace');ids=out/'inputs'/(name+'.ids')
   with trace.open('xb') as f:
    f.write(f'{name} 4160 1\n'.encode())
    for i in positions:f.write(raw[i+1]+b'\n')
   with ids.open('x') as f:f.write('\n'.join(str(4096+i) for i in range(64))+'\n')
   plan=dict(parent_trace=identity(src),parent_selection=identity(sel),parent_rows=positions,source_ids=[int(raw[i+1].split(b'\t',1)[0]) for i in positions],q=list(range(4096,4160)),k=[1,4,16,64]*16,trace=identity(trace),ids=identity(ids))
   assert len(set(plan['source_ids']))==4160 and not set(positions[:4096])&set(positions[4096:])
   save(out/'inputs'/(name+'.selection.json'),plan);plans[name]=plan
  save(out/'INPUT_FREEZE.json',dict(before_population=True,source_freeze=identity(HERE/'SOURCE_FREEZE.json'),plans=plans))
  records=[]
  for name,selection in plans.items():
   target=out/name;target.mkdir();trace=out/'inputs'/(name+'.trace');ids=out/'inputs'/(name+'.ids')
   assert identity(trace)==selection['trace'] and identity(ids)==selection['ids'] and freeze_sources()==frozen['files']
   command=[str(binary),str(trace),str(ids),str(target)];save(out/(name+'.START.json'),dict(before_start=True,command=command,binary=identity(binary),trace=identity(trace),ids=identity(ids),selection=identity(out/'inputs'/(name+'.selection.json'))))
   t=time.monotonic();p=subprocess.run(command,capture_output=True,text=True,timeout=900);(out/(name+'.stdout')).write_text(p.stdout);(out/(name+'.stderr')).write_text(p.stderr)
   save(out/(name+'.EXIT.json'),dict(returncode=p.returncode,wall_seconds=time.monotonic()-t));assert p.returncode==0 and not p.stderr
   proof=verify_target(target,selection);save(out/(name+'.PROOF.json'),proof);records.append(dict(dataset=name,proof=proof))
   assert sum(p.stat().st_size for p in out.rglob('*') if p.is_file())<=268435456;print('PROCESS_PASS',name,flush=True)
  assert freeze_sources()==frozen['files'];save(out/'COMPLETE.json',dict(passed=True,records=records,GPU_starts=0,novelty_admitted=False,performance_admitted=False))
  save(out.with_name(out.name+'.SEAL.json'),dict(before_analysis=True,files={str(p.relative_to(out)):identity(p) for p in sorted(out.rglob('*')) if p.is_file()}))
 except BaseException as e:save(out/'FAILURE.json',dict(error=repr(e),first_failure_stop=True,GPU_starts=0));raise
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--parent-inputs',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();main(a.parent_inputs.resolve(),a.out.resolve())
