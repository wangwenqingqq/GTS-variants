#!/usr/bin/env python3
"""Frozen layout experiment; serialize all stages on the admitted GPU."""
import argparse,fcntl,hashlib,json,subprocess,sys
from pathlib import Path
from verify_full import clean,sha,verify
MODES='DEUSVL';GRAPH='ESL';TOOLS=['memcheck','synccheck','initcheck','racecheck']
ORDERS=['ESL','LSE','SLE','ELS','LES','SEL']

def gates():return [(f'gate_{t}_{m}',m,t,1,0) for t in TOOLS for m in (MODES if t in TOOLS[:2] else GRAPH)]+[('stress_'+m,m,'clean',128,64) for m in MODES]

def require_gates(root,runner):
 binary=sha(root/'bin/graph_bench');o=json.loads((root/'fixtures/oracle.json').read_text())
 for label,m,t,reps,w in gates():
  path=root/'runs'/label;r=json.loads((path/'receipt.json').read_text());clean(r)
  assert (r['label'],r['mode'],r['tool'],r['repeats'],r['warmup'],r['radius'])==(label,m,t,reps,w,o['radii']['normal'])
  assert r['binary_sha256']==binary and r['runner_sha256']==sha(runner) and r['validation']['pass']
  assert r['input_sha256']=={n:sha(root/'fixtures'/n) for n in ['data.txt','queries.qid']}
  if t in TOOLS:
   logs=(path/'stdout.log').read_text()+(path/'stderr.log').read_text()
   assert ('RACECHECK SUMMARY: 0 hazards' if t=='racecheck' else 'ERROR SUMMARY: 0 errors') in logs,label

def main():
 p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('stage',choices=['smoke','gates','timing','trace','ncu']);p.add_argument('--gpu',required=True);p.add_argument('--gpu-index',type=int,choices=[0,1],default=1);p.add_argument('--datasets',nargs='+',choices=['GIST','Deep','Tloc'],default=['GIST','Deep','Tloc'])
 a=p.parse_args();root=a.root.resolve();sys.path.insert(0,str(root));from run_layout import execute,snapshot
 roots=[root/'data'/n for n in a.datasets]
 for d in roots:
  if a.stage!='smoke':assert json.loads((d/'full_verified.json').read_text())['binary_sha256']==sha(root/'bin/graph_bench')
  if a.stage in ['timing','trace','ncu']:require_gates(d,root/'run_layout.py')
 state=snapshot(a.gpu);assert not state['apps'].strip()
 assert int(state['gpu'].split(',')[0])==a.gpu_index and state['gpu'].split(',')[1].strip()==a.gpu
 with open(f'/tmp/gtspp_gpu{a.gpu_index}.lock','r+') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  for d in roots:
   radii=json.loads((d/'fixtures/oracle.json').read_text())['radii'];normal=radii['normal']
   def run(label,m,r=normal,reps=1,w=0,t='clean',dump=False):assert execute(d,a.gpu,label,m,r,reps,w,t,dump),label
   if a.stage=='smoke':
    for name,r in radii.items():
     for m in (MODES if name=='empty' else 'A'+MODES):run(f'full_{name}_{m}',m,r,dump=True)
    print(d.name,verify(d),flush=True)
   elif a.stage=='gates':
    for label,m,t,reps,w in gates():run(label,m,reps=reps,w=w,t=t)
   elif a.stage=='timing':
    for i,order in enumerate(ORDERS):
     for m in order:run(f'timing_{i}_{m}',m,reps=64,w=64)
    for name in ['zero','normal','all']:
     for i,order in enumerate(['ESL','LSE']):
      for m in order:run(f'sustained_{name}_{i}_{m}',m,radii[name],reps=128,w=64)
   elif a.stage=='trace':
    for m in GRAPH:run('nsys_'+m,m,reps=2,w=64,t='nsys-node')
   else:
    for m in 'DUV':
     run('ncu_'+m,m,t='ncu')
     for page,file in [('details','metrics.csv'),('raw','metrics_raw.csv')]:
      with (d/'runs'/('ncu_'+m)/file).open('w') as out:subprocess.run(['ncu','--import',str(d/'runs'/('ncu_'+m)/'profile.ncu-rep'),'--page',page,'--csv'],stdout=out,check=True)
if __name__=='__main__':main()
