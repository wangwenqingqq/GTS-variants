"""Freeze and run two bounded CPU semantic diagnostics;first failure stops."""
if not __debug__:raise SystemExit('Assertions required')
import argparse,csv,hashlib,json,os,platform,random,shutil,struct,subprocess,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
PARENT=HERE.parent/'shared_frontier_cpu_trace_20261021'
def identity(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return dict(bytes=p.stat().st_size,sha256=h.hexdigest())
def load(p):return json.loads(p.read_text())
def save(p,x):
 with p.open('x') as f:json.dump(x,f,indent=2,sort_keys=True);f.write('\n')
def freeze_sources():
 return {str(p.relative_to(HERE.parent)):identity(p) for p in [HERE/'CONTRACT.json',HERE/'probe.cpp',HERE/'run.py',PARENT/'trace.cpp',PARENT/'evidence/INPUTS.json']}
def verify_target(target,selection):
 costs=list(csv.DictReader((target/'COSTS.csv').open()));rows=list(csv.DictReader((target/'QUERY.csv').open()));cal=list(csv.DictReader((target/'CALIBRATION.csv').open()))
 assert len(costs)==12 and len(rows)==36 and len(cal)==3
 expected_methods={'PIVOT_INCREMENTAL_CPU','PIVOT_RECOMPUTE_ALL_WEAK','GTS_CACHED_SNAPSHOT_CPU','QUICKJOIN_FAMILY_CPU'}
 assert {(int(z['state']),z['method']) for z in costs}=={(s,m) for s in range(3) for m in expected_methods}
 assert {(int(z['state']),int(z['level']),z['method']) for z in rows}=={(s,l,m) for s in range(3) for l in range(3) for m in expected_methods}
 checked=0;records=0;hashes={}
 source_ids=selection['source_ids'];q=selection['q'];deleted=set(selection['deleted']);live=set(range(4096));self_hits=0
 for z in rows:
  state=int(z['state']);level=int(z['level']);method=z['method'];radius=int(z['radius']);assert radius==int(cal[level]['radius'])
  alive=live if state==0 else live-deleted if state==1 else live-deleted|set(range(4096,4128))
  assert int(z['N'])==len(alive) and int(z['Q'])==64
  assert int(z['candidate_pairs'])==int(z['verify_calls'])
  assert int(z['distance_calls'])==sum(int(z[k]) for k in ['bound_calls','verify_calls','partition_calls','query_plan_calls'])
  actual=target/f'S{state}_L{level}_{method}.bin';reference=target/f'S{state}_L{level}_REFERENCE.bin';data=actual.read_bytes()
  assert data==reference.read_bytes() and len(data)==int(z['output_bytes'])==20*int(z['output_count'])
  old=None;zero=set();liveids={source_ids[i] for i in alive}
  for qi,idx,score in struct.iter_unpack('<IQd',data):
   assert 0<=qi<64 and idx in liveids and score>=0 and score<=radius and score==int(score)
   key=(qi,idx);assert old is None or old<key;old=key
   if score==0:zero.add(key)
  assert all((qi,source_ids[v]) in zero for qi,v in enumerate(q));self_hits+=len(q)
  hashes[actual.name]=identity(actual);checked+=1;records+=len(data)//20
 for state in range(3):
  inc=next(z for z in costs if int(z['state'])==state and z['method']=='PIVOT_INCREMENTAL_CPU')
  assert int(inc['metric_calls'])==[4096*4,0,128][state]
  assert int(inc['unaffected_old_entries_changed'])==0
  assert int(inc['diagnostic_checked_entries'])==[4096*4,4064*4,4096*4][state]
 return dict(passed=True,complete_output_streams_checked=checked,records_checked=records,self_hits_checked=self_hits,output_identities=hashes,oracle='Same primitive full all-pair;581 DP pairs independently qualify arithmetic',GPU_starts=0)

def main(parent_inputs,out):
 assert os.getpriority(os.PRIO_PROCESS,0)==10 and not out.exists()
 assert shutil.disk_usage(out.parent).free>=1024**3
 assert identity(PARENT/'trace.cpp')==load(PARENT/'SOURCE_FREEZE.json')['files']['trace.cpp']
 frozen=load(HERE/'SOURCE_FREEZE.json');assert freeze_sources()==frozen['files']
 pins=load(PARENT/'evidence/INPUTS.json');out.mkdir();(out/'inputs').mkdir();(out/'build').mkdir()
 cpu=next(x.split(':',1)[1].strip() for x in Path('/proc/cpuinfo').read_text().splitlines() if x.startswith('model name'))
 save(out/'REGISTERED.json',dict(before_calibration=True,sources=freeze_sources(),CPU=cpu,Python=platform.python_version(),threads=1,nice=10,GPU_starts=0,compiler=subprocess.check_output(['g++','--version'],text=True)))
 try:
  helper=(PARENT/'trace.cpp').read_text().split('\nint main(',1)[0]+'\n'
  (out/'build/trace_helpers.hpp').write_text(helper);binary=out/'build/probe'
  command=['g++','-std=c++17','-O2','-fno-fast-math','-ffp-contract=off','-I',str(out/'build'),str(HERE/'probe.cpp'),'-o',str(binary)]
  p=subprocess.run(command,capture_output=True,text=True);(out/'build/compile.stdout').write_text(p.stdout);(out/'build/compile.stderr').write_text(p.stderr);assert p.returncode==0 and not p.stderr
  p=subprocess.run([str(binary),'--self-test'],capture_output=True,text=True);(out/'build/fixtures.stdout').write_text(p.stdout);(out/'build/fixtures.stderr').write_text(p.stderr);assert p.returncode==0 and not p.stderr
  save(out/'BUILD.json',dict(passed=True,binary=identity(binary),helper=identity(out/'build/trace_helpers.hpp'),fixture_stdout=identity(out/'build/fixtures.stdout')))
  plans={}
  for name in ['Words','DNA_GRCh38_chr1_108']:
   src=parent_inputs/(name+'.trace');sel=parent_inputs/(name+'.selection.json')
   assert identity(src)==pins['sources'][name]['trace_input'] and identity(sel)==pins['sources'][name]['selection']
   parent=load(sel);oldqueries=set(v for qs in parent['queries'].values() for v in qs)
   rng=random.Random(2026102141);rows=sorted(rng.sample(range(65536),4096))+list(range(65536,65568))
   allowed=[i for i,v in enumerate(rows[:4096]) if v not in oldqueries]
   qs=rng.sample(allowed,96);cal=qs[:32];q=qs[32:];piv=rng.sample([i for i in range(4096) if i not in qs],4)
   deleted=piv+rng.sample([i for i in range(4096) if i not in qs and i not in piv],28)
   assert len(set(q+cal+piv))==100 and len(set(deleted))==32
   raw=src.read_bytes().splitlines();assert len(raw)==65569
   trace=out/'inputs'/(name+'.trace')
   with trace.open('xb') as f:
    f.write(f'{name} 4128 1\n'.encode())
    for i in rows:f.write(raw[i+1]+b'\n')
   idfile=out/'inputs'/(name+'.ids')
   with idfile.open('x') as f:f.write('\n'.join(map(str,q+cal+piv+deleted))+'\n')
   selection=dict(parent_trace=identity(src),parent_selection=identity(sel),parent_rows=rows,source_ids=[int(raw[i+1].split(b'\t',1)[0]) for i in rows],q=q,calibration=cal,pivots=piv,deleted=deleted,trace=identity(trace),ids=identity(idfile))
   save(out/'inputs'/(name+'.selection.json'),selection);plans[name]=selection
  save(out/'INPUT_FREEZE.json',dict(before_calibration_and_evaluation=True,source_freeze=identity(HERE/'SOURCE_FREEZE.json'),plans=plans))
  records=[]
  for name,selection in plans.items():
   target=out/name;target.mkdir();trace=out/'inputs'/(name+'.trace');ids=out/'inputs'/(name+'.ids')
   assert identity(trace)==selection['trace'] and identity(ids)==selection['ids'] and freeze_sources()==frozen['files']
   assert [int(v) for v in ids.read_text().split()]==selection['q']+selection['calibration']+selection['pivots']+selection['deleted']
   command=[str(binary),str(trace),str(ids),str(target)]
   save(out/(name+'.START.json'),dict(before_start=True,command=command,binary=identity(binary),trace=identity(trace),ids=identity(ids),selection=identity(out/'inputs'/(name+'.selection.json'))))
   t=time.monotonic();p=subprocess.run(command,capture_output=True,text=True,timeout=600)
   (out/(name+'.stdout')).write_text(p.stdout);(out/(name+'.stderr')).write_text(p.stderr)
   save(out/(name+'.EXIT.json'),dict(returncode=p.returncode,wall_seconds=time.monotonic()-t));assert p.returncode==0 and not p.stderr
   proof=verify_target(target,selection);save(out/(name+'.PROOF.json'),proof);records.append(dict(dataset=name,proof=proof))
   assert sum(p.stat().st_size for p in out.rglob('*') if p.is_file())<=268435456
   print('PROCESS_PASS',name,flush=True)
  assert freeze_sources()==frozen['files']
  save(out/'COMPLETE.json',dict(passed=True,records=records,GPU_starts=0,novelty_admitted=False,performance_admitted=False,decision='BASELINE_SUFFICIENT_FOR_VALIDITY'))
  save(out.with_name(out.name+'.SEAL.json'),dict(before_analysis=True,files={str(p.relative_to(out)):identity(p) for p in sorted(out.rglob('*')) if p.is_file()}))
 except BaseException as e:
  save(out/'FAILURE.json',dict(error=repr(e),first_failure_stop=True,GPU_starts=0));raise
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--parent-inputs',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();main(a.parent_inputs.resolve(),a.out.resolve())
