#!/usr/bin/env python3
"""Serialized, monitored locality screen; no production dispatcher changes."""
import argparse,fcntl,json,subprocess,sys
from pathlib import Path
GRAPH='ESRT';FULL='ESLBRTC';STRESS='ESRTBC';NCU='DUVBC'
ORDERS=['ESRT','TRSE','RTES','SETR']
TOOLS=['memcheck','synccheck','initcheck','racecheck']

def gates():return [(t,m) for t in TOOLS for m in (GRAPH+'BC' if t in TOOLS[:2] else GRAPH)]

def plan(stage,radii):
 normal=radii['normal']
 if stage=='full':return [(f'full_{n}_{m}',m,r,1,0,'clean',True) for n,r in radii.items() for m in (FULL if n=='empty' else 'A'+FULL)]
 if stage=='gates':return [(f'gate_{t}_{m}',m,normal,1,0,t,False) for t,m in gates()]
 if stage=='stress':return [('stress_'+m,m,normal,64,64,'clean',False) for m in STRESS]
 if stage=='screen':return [(f'screen_{i}_{m}',m,normal,8,64,'clean',False) for i,order in enumerate(ORDERS) for m in order]
 if stage=='sustained':return [(f'sustained_{i}_{m}',m,normal,64,64,'clean',False) for i,order in enumerate(['ESRT','TRSE']) for m in order]
 if stage=='trace':return [('nsys_'+m,m,normal,2,64,'nsys-node',False) for m in GRAPH]
 assert stage=='ncu';return [('ncu_'+m,m,normal,1,0,'ncu',False) for m in NCU]

def require(root,common,stage):
 from verify_full import clean,sha
 o=json.loads((root/'fixtures/oracle.json').read_text());binary=sha(common/'bin/graph_bench')
 if stage=='full':return
 verified=json.loads((root/'full_verified.json').read_text());assert verified['binary_sha256']==binary
 required=[]
 if stage in ['stress','screen','sustained','trace','ncu']:required+=plan('gates',o['radii'])
 if stage in ['screen','sustained','trace','ncu']:required+=plan('stress',o['radii'])
 for label,m,r,reps,w,t,dump in required:
  p=root/'runs'/label;x=json.loads((p/'receipt.json').read_text());clean(x)
  assert (x['label'],x['mode'],x['radius'],x['repeats'],x['warmup'],x['tool'],x['dump'])==(label,m,r,reps,w,t,dump)
  assert x['binary_sha256']==binary and x['runner_sha256']==sha(common/'run_layout.py') and x['validation']['pass']
  assert x['input_sha256']=={n:sha(root/'fixtures'/n) for n in ['data.txt','queries.qid']}
  if t in TOOLS:
   log=(p/'stdout.log').read_text()+(p/'stderr.log').read_text()
   assert ('RACECHECK SUMMARY: 0 hazards' if t=='racecheck' else 'ERROR SUMMARY: 0 errors') in log

def main():
 p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('stage',choices=['full','gates','stress','screen','sustained','trace','ncu']);p.add_argument('--gpu',required=True)
 a=p.parse_args();common=a.root.resolve();sys.path.insert(0,str(common))
 from run_layout import execute,snapshot
 from verify_full import verify
 state=snapshot(a.gpu);assert not state['apps'].strip();assert state['gpu'].split(',')[0].strip()=='5'
 assert state['gpu'].split(',')[1].strip()==a.gpu
 with open('/tmp/gtspp_gpu5.lock','r+') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  for ds in ['GIST','Deep','Tloc']:
   root=common/'data'/ds;(root/'runs').mkdir(exist_ok=True);require(root,common,a.stage)
   radii=json.loads((root/'fixtures/oracle.json').read_text())['radii']
   for label,m,r,reps,w,t,dump in plan(a.stage,radii):
    assert execute(root,a.gpu,label,m,r,reps,w,t,dump),(ds,label)
    if t=='ncu':
     for page,name in [('details','metrics.csv'),('raw','metrics_raw.csv')]:
      with (root/'runs'/label/name).open('w') as out:subprocess.run(['ncu','--import',str(root/'runs'/label/'profile.ncu-rep'),'--page',page,'--csv'],stdout=out,check=True)
   if a.stage=='full':print(ds,'PASS',len(verify(root)['full_output_checks']),'full outputs',flush=True)
if __name__=='__main__':main()
