"""Bounded serial CPU campaign. First failure stops; no implicit recovery."""
if not __debug__:raise SystemExit('Assertions required')
import argparse,csv,hashlib,json,os,platform,subprocess,time,shutil
from pathlib import Path
HERE=Path(__file__).resolve().parent

def identity(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return dict(bytes=p.stat().st_size,sha256=h.hexdigest())
def load(p):return json.loads(p.read_text())
def save(p,x):
 with p.open('x') as f:json.dump(x,f,indent=2,sort_keys=True);f.write('\n')
def sources():return {n:identity(HERE/n) for n in ['CONTRACT.json','prepare.py','trace.cpp','run.py','verify.py']}
def main(inputs,out):
 assert os.getpriority(os.PRIO_PROCESS,0)==10
 assert not out.is_relative_to(HERE.parent.parent)
 frozen=load(HERE/'SOURCE_FREEZE.json');assert sources()==frozen['files']
 c=load(HERE/'CONTRACT.json');pin=load(inputs/'INPUTS.json')
 assert pin['passed'] and pin['preparer']==identity(HERE/'prepare.py') and pin['contract']==identity(HERE/'CONTRACT.json')
 for name in c['data']:
  assert identity(inputs/(name+'.trace'))==pin['sources'][name]['trace_input']
  assert identity(inputs/(name+'.selection.json'))==pin['sources'][name]['selection']
 assert shutil.disk_usage(out.parent).free>=5*1024**3
 out.mkdir();(out/'receipts').mkdir();lib=out/'trace_cpu'
 command=['g++','-std=c++17','-O2','-fno-fast-math','-ffp-contract=off',str(HERE/'trace.cpp'),'-o',str(lib)]
 cpu=next(x.split(':',1)[1].strip() for x in Path('/proc/cpuinfo').read_text().splitlines() if x.startswith('model name'))
 save(out/'REGISTERED.json',dict(before_compile_and_population=True,sources=sources(),input_manifest=identity(inputs/'INPUTS.json'),input_directory=str(inputs),compile_command=command,CPU_model=cpu,Python=platform.python_version(),compiler=subprocess.check_output(['g++','--version'],text=True),nice=10,threads=1,GPU_starts=0))
 records=[]
 try:
  p=subprocess.run(command,capture_output=True,text=True)
  (out/'compile.stdout').write_text(p.stdout);(out/'compile.stderr').write_text(p.stderr);assert p.returncode==0 and not p.stderr
  p=subprocess.run([str(lib),'--self-test'],capture_output=True,text=True)
  (out/'qualification.stdout').write_text(p.stdout);(out/'qualification.stderr').write_text(p.stderr);assert p.returncode==0 and not p.stderr
  save(out/'BUILD.json',dict(passed=True,binary=identity(lib),qualification_stdout=identity(out/'qualification.stdout')))
  ledger=(out/'STARTS.jsonl').open('x')
  for name in c['data']:
   spent=0
   for mode,seed in [('static',s) for s in c['sample']['query_seeds']]+[('updates',c['sample']['query_seeds'][0])]:
    assert sources()==frozen['files'] and identity(lib)==load(out/'BUILD.json')['binary']
    key=f'{name}_{mode}_{seed}';target=out/key;target.mkdir()
    command=[str(lib),str(inputs/(name+'.trace')),str(inputs/(name+f'.{seed}.qid')),str(inputs/(name+'.delete')),str(target),mode]
    record=dict(index=len(records),dataset=name,mode=mode,seed=seed,command=command,before_start=True,binary=identity(lib))
    save(out/'receipts'/(key+'.command.json'),record);ledger.write(json.dumps(record)+'\n');ledger.flush()
    t=time.monotonic();p=subprocess.run(command,capture_output=True,text=True,timeout=max(.1,1800-spent));wall=time.monotonic()-t;spent+=wall
    (out/'receipts'/(key+'.stdout')).write_text(p.stdout);(out/'receipts'/(key+'.stderr')).write_text(p.stderr)
    exit_record=dict(dataset=name,mode=mode,seed=seed,returncode=p.returncode,wall_seconds=wall)
    save(out/'receipts'/(key+'.exit.json'),exit_record);assert p.returncode==0 and not p.stderr,(key,p.stdout[-1000:],p.stderr)
    from verify import verify_target
    proof=verify_target(target,inputs,name,mode,seed);save(out/'receipts'/(key+'.proof.json'),proof)
    records.append(exit_record)
    assert sum(p.stat().st_size for p in out.rglob('*') if p.is_file())<=c['resource']['raw_disk_budget_bytes']
    print('PROCESS_PASS',key,'full output equality;0GPU',flush=True)
  ledger.close();assert sources()==frozen['files']
  save(out/'COMPLETE.json',dict(passed=True,records=records,GPU_starts=0,protected_GIST_heldout_accesses=0))
  save(out.with_name(out.name+'.SEAL.json'),dict(before_postrun_review=True,files={str(p.relative_to(out)):identity(p) for p in sorted(out.rglob('*')) if p.is_file()}))
 except BaseException as e:
  save(out/'FAILURE.json',dict(error=repr(e),valid_prior_processes=records,first_failure_stop=True,GPU_starts=0));raise
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--inputs',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();main(a.inputs.resolve(),a.out.resolve())
