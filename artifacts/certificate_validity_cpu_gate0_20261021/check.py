"""Data-free artifact replay;never launches the measured C++ program."""
import sys
sys.dont_write_bytecode=True
if not __debug__:raise SystemExit('Assertions required')
import argparse,csv,json,shutil,subprocess,tempfile
from pathlib import Path
from run import HERE,PARENT,identity,load,freeze_sources
from summarize import summarize
def check():
 actual={str(p.relative_to(HERE)):identity(p) for p in sorted(HERE.rglob('*')) if p.is_file() and p.name!='MANIFEST.json' and '__pycache__' not in p.parts}
 assert actual==load(HERE/'MANIFEST.json')['files'] and not any(p.is_symlink() for p in HERE.rglob('*'))
 assert freeze_sources()==load(HERE/'SOURCE_FREEZE.json')['files']
 e=HERE/'evidence';raw=load(e/'RAW_MEMBERS.json');seal=load(e/'RUN_SEAL.json');receipt=load(e/'RAW_RECEIPT.json');local=load(e/'RAW_LOCAL_VERIFIED.json')
 assert receipt['passed'] and local['passed'] and receipt['archive']==local['archive'] and receipt['members']==local['members']==len(raw)==146
 assert receipt['manifest']==identity(e/'RAW_MEMBERS.json')
 assert raw['run.SEAL.json']==identity(e/'RUN_SEAL.json') and all(raw['run/'+n]==v for n,v in seal['files'].items())
 assert all(not Path(n).is_absolute() and '..' not in Path(n).parts for n in raw)
 complete=load(e/'COMPLETE.json');assert complete['passed'] and complete['decision']=='BASELINE_SUFFICIENT_FOR_VALIDITY' and not complete['novelty_admitted'] and not complete['performance_admitted']
 assert identity(e/'COMPLETE.json')==raw['run/COMPLETE.json'] and identity(e/'INPUT_FREEZE.json')==raw['run/INPUT_FREEZE.json']
 inputs=load(e/'INPUT_FREEZE.json');assert inputs['before_calibration_and_evaluation'] and inputs['source_freeze']==identity(HERE/'SOURCE_FREEZE.json')
 summary=load(HERE/'results/SUMMARY.json');v=summary['campaign_validity'];assert v['passed'] and v['complete_streams_checked']==72
 assert v['source_freeze']==identity(HERE/'SOURCE_FREEZE.json') and v['contract']==identity(HERE/'CONTRACT.json')
 assert v['seal']==identity(e/'RUN_SEAL.json') and v['sealed_files']==len(seal['files']) and v['sealed_bytes']==sum(z['bytes'] for z in seal['files'].values())
 assert v['input_freeze']==identity(e/'INPUT_FREEZE.json') and v['complete']==identity(e/'COMPLETE.json')
 env=load(e/'ENVIRONMENT.json');assert env['threads']==1 and env['nice']==10 and env['GPU_starts']==0 and env['sources']==freeze_sources()
 assert identity(e/'ENVIRONMENT.json')==raw['run/REGISTERED.json'] and identity(e/'BUILD.json')==raw['run/BUILD.json'] and identity(e/'fixtures.stdout')==raw['run/build/fixtures.stdout']
 assert load(e/'BUILD.json')['binary']==raw['run/build/probe']
 costs=[];queries=[];calibration=[]
 for i,n in enumerate(['Words','DNA_GRCh38_chr1_108']):
  d=HERE/'results'/n;proof=load(d/'PROCESS.PROOF.json');assert complete['records'][i]==dict(dataset=n,proof=proof) and proof['passed'] and proof['complete_output_streams_checked']==36
  for f in ['COSTS.csv','QUERY.csv','CALIBRATION.csv']:assert identity(d/f)==raw[f'run/{n}/{f}']
  for suffix in ['stdout','stderr','EXIT.json','PROOF.json']:assert identity(d/('PROCESS.'+suffix))==raw[f'run/{n}.{suffix}']
  ex=load(d/'PROCESS.EXIT.json');assert ex['returncode']==0 and ex['wall_seconds']<=600 and not (d/'PROCESS.stderr').read_bytes()
  for name,ident in proof['output_identities'].items():
   assert ident==raw[f'run/{n}/{name}']
   state,level=name.split('_')[:2];assert ident==raw[f'run/{n}/{state}_{level}_REFERENCE.bin']
  binding=v['bindings'][n]
  for f,suffix in [('trace','trace'),('ids','ids'),('selection','selection.json')]:assert binding[f]==raw[f'run/inputs/{n}.{suffix}']
  assert binding['start']==raw[f'run/{n}.START.json']
  assert binding['trace']==inputs['plans'][n]['trace'] and binding['ids']==inputs['plans'][n]['ids']
  costs.extend(dict(dataset=n,**z) for z in csv.DictReader((d/'COSTS.csv').open()))
  queries.extend(csv.DictReader((d/'QUERY.csv').open()))
  calibration.extend(dict(dataset=n,**z) for z in csv.DictReader((d/'CALIBRATION.csv').open()))
 assert len(costs)==24 and len(queries)==72 and len(calibration)==6
 rebuilt=summarize(costs,queries,calibration,v);assert rebuilt==summary
 assert summary['diagnostic_metric_calls_separate']==98048 and summary['performance_admission']=='NOT_EVALUATED'
 assert all(z['gts_metric_calls']<5*z['pivot_metric_calls'] for z in summary['cells'] if z['radius']>0)
 return dict(passed=True,decision=summary['decision'],performance_admission='NOT_EVALUATED',novelty_admitted=False,population_CPU_targets=2,complete_output_streams=72,construction_update_rows=24,quantile_rows=6,GPU_starts=0,scope='Data-free identity/scalar replay;private input/full-output audit performed separately')
def tamper_tests():
 cases=[('results/SUMMARY.json',lambda b:b.replace(b'"NOT_EVALUATED"',b'"GO"',1)),('results/Words/COSTS.csv',lambda b:b+b'\n'),('evidence/COMPLETE.json',lambda b:b.replace(b'"passed": true',b'"passed": false',1))]
 for name,mutate in cases:
  with tempfile.TemporaryDirectory() as td:
   d=Path(td)/'artifacts'/HERE.name;d.parent.mkdir();shutil.copytree(HERE,d)
   for source in [PARENT/'trace.cpp',PARENT/'evidence/INPUTS.json']:
    target=d.parent/PARENT.name/source.relative_to(PARENT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
   f=d/name;b=f.read_bytes();assert mutate(b)!=b;f.write_bytes(mutate(b))
   p=subprocess.run([sys.executable,str(d/'check.py')],capture_output=True,text=True);assert p.returncode!=0
 return len(cases)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--test',action='store_true');a=p.parse_args();result=check()
 if a.test:result['tamper_cases_rejected']=tamper_tests()
 print(json.dumps(result,indent=2,sort_keys=True))
