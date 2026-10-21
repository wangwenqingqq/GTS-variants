"""Data-free publication replay. Does not launch targets or read raw datasets."""
import sys
sys.dont_write_bytecode=True
import argparse,copy,hashlib,json,subprocess,tempfile
from pathlib import Path
from analyze import collect,summarize
from run import identity,load,sources
HERE=Path(__file__).resolve().parent

def check():
 manifest=load(HERE/'MANIFEST.json')
 files={str(p.relative_to(HERE)):identity(p) for p in sorted(HERE.rglob('*')) if p.is_file() and p.name!='MANIFEST.json' and '__pycache__' not in p.parts}
 assert files==manifest['files'] and not any(p.is_symlink() for p in HERE.rglob('*'))
 assert sources()==load(HERE/'SOURCE_FREEZE.json')['files']
 ev=HERE/'evidence';raw=load(ev/'RAW_MEMBERS.json');seal=load(ev/'RUN_SEAL.json');aud=load(ev/'POSTRUN_AUDIT.json');complete=load(ev/'COMPLETE.json')
 assert aud['passed'] and aud['processes']==9 and aud['full_output_streams_checked']==90 and complete['passed']
 assert aud['contract']==identity(HERE/'CONTRACT.json') and aud['source_freeze']==identity(HERE/'SOURCE_FREEZE.json')
 assert aud['seal']==identity(ev/'RUN_SEAL.json')==raw['run.SEAL.json'] and aud['complete']==identity(ev/'COMPLETE.json')==raw['run/COMPLETE.json']
 assert aud['sealed_file_count']==len(seal['files'])==187 and aud['sealed_bytes']==sum(z['bytes'] for z in seal['files'].values())
 assert all(raw['run/'+k]==v for k,v in seal['files'].items())
 assert aud['GPU_starts']==aud['protected_GIST_heldout_accesses']==0
 pins=load(ev/'INPUTS.json');assert aud['input_manifest']==identity(ev/'INPUTS.json')==raw['prepared/INPUTS.json']
 for n,b in aud['bindings'].items():
  assert b['deterministic_membership_equal'] and b['selection']==pins['sources'][n]['selection']==raw[f'prepared/{n}.selection.json']
  assert b['trace_input']==pins['sources'][n]['trace_input']==raw[f'prepared/{n}.trace']
  for f,ident in b['actual_membership_files'].items():assert raw['prepared/'+f]==ident
 for key,proof in aud['proofs'].items():
  d=HERE/'results'/key
  assert load(d/'PROCESS.proof.json')==proof and load(d/'PROCESS.exit.json')['returncode']==0
  for f in ['COUNTERS.csv','BUILDS.csv']:assert identity(d/f)==raw[f'run/{key}/{f}']
  for suffix in ['proof.json','exit.json','stdout','stderr']:assert identity(d/('PROCESS.'+suffix))==raw[f'run/receipts/{key}.{suffix}']
  assert not (d/'PROCESS.stderr').read_bytes()
 for f in ['BUILD.json','qualification.stdout','qualification.stderr','compile.stdout','compile.stderr']:assert identity(ev/f)==raw['run/'+f]
 archive=load(ev/'RAW_RECEIPT.json');local=load(ev/'RAW_LOCAL_VERIFIED.json')
 assert archive['passed'] and local['passed'] and local['archive']==archive['archive'] and local['members_checked']==archive['members']==len(raw)
 assert archive['member_manifest']==identity(ev/'RAW_MEMBERS.json')
 rows,builds=collect(HERE/'results');assert len(rows)==90 and len(builds)==15
 s=summarize(rows,builds,aud);assert s==load(HERE/'results/SUMMARY.json')
 assert s['decision']=='NO_GO' and s['primary_cells_reaching10x']==0 and s['primary_cells']==12
 return dict(passed=True,processes=9,counter_rows=90,build_rows=15,primary_10x_cells=0,primary_cells=12,decision=s['decision'],GPU_starts=0,scope='Data-free integrity and exact counter decision replay;private full output equality was separately audited,not recomputed here')

def tamper_tests():
 # Test the shipped verifier from isolated copies,not the publication source.
 cases=[('results/SUMMARY.json',lambda b:b.replace(b'"NO_GO"',b'"GO_OPPORTUNITY_ONLY"',1)),('results/Words_static_2026102101/COUNTERS.csv',lambda b:b+b'\n'),('evidence/POSTRUN_AUDIT.json',lambda b:b.replace(b'"passed": true',b'"passed": false',1))]
 import shutil
 for name,mutate in cases:
  with tempfile.TemporaryDirectory() as td:
   dest=Path(td)/'artifact';shutil.copytree(HERE,dest,ignore=shutil.ignore_patterns('__pycache__'))
   f=dest/name;b=f.read_bytes();assert mutate(b)!=b;f.write_bytes(mutate(b))
   p=subprocess.run([sys.executable,str(dest/'check.py')],capture_output=True,text=True);assert p.returncode!=0
 return len(cases)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--test',action='store_true');a=p.parse_args();result=check()
 if a.test:result['tamper_cases_rejected']=tamper_tests()
 print(json.dumps(result,indent=2,sort_keys=True))
