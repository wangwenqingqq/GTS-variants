#!/usr/bin/env python3
"""Serial bounded kNN campaign, explicitly authorized on physical GPU5 only."""
import argparse,fcntl,importlib.util,json,os,subprocess,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('base',HERE.parent/'original_tree_profile/run.py');base=importlib.util.module_from_spec(s);s.loader.exec_module(base)
CASES=[(2000,32,10)]+[(65536,q,k) for q in [32,128] for k in [10,100]]
def main():
 p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('--gpu',required=True);p.add_argument('--stage',required=True,choices=['preflight','gates','stress','timing','profile','sustained']);a=p.parse_args();root=a.root.resolve();(root/'runs').mkdir(exist_ok=True)
 lock=open('/tmp/gtspp_gpu5.lock','a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 assert base.snapshot(a.gpu)['gpu'].split(',')[0].strip()=='5','Only user-authorized physical GPU5'
 pins=json.loads((HERE.parent/'tc_leaf_probe/EVIDENCE.json').read_text())['fixtures']
 for n in [2000,65536]:
  m=json.loads((root/f'fixtures/n{n}/manifest.json').read_text());assert m==pins[f'n{n}']
  for f,h in m['file_sha256'].items():assert base.sha(root/f'fixtures/n{n}'/f)==h
 def run(label,v,n,q,k,mode='check',tool=None,api='ids'):
  out=root/'runs'/label;out.mkdir();binary=root/'bin'/v;before=base.snapshot(a.gpu);(out/'before.json').write_text(json.dumps(before,indent=2)+'\n');assert not before['apps'].strip(),'GPU5 busy; stop without disturbing it'
  cmd=[str(binary),str(root/f'fixtures/n{n}/data.txt'),str(root/f'fixtures/n{n}/q{q}.txt'),str(k),api,mode,'D']
  if tool in ['memcheck','synccheck','initcheck','racecheck']:cmd=['compute-sanitizer','--tool',tool,'--error-exitcode','90']+cmd
  if tool=='nsys':cmd=['nsys','profile','--trace=cuda,nvtx','--sample=none','--cpuctxsw=none','--capture-range=cudaProfilerApi','--capture-range-end=stop','--export=sqlite','--output='+str(out/'trace')]+cmd
  if tool=='ncu':
   (out/'home').mkdir();c=['sudo','-n','/usr/bin/timeout','--signal=TERM','--kill-after=10s','600s','/usr/bin/env','CUDA_VISIBLE_DEVICES='+a.gpu,'HOME='+str(out/'home'),'/opt/nvidia/nsight-compute/2025.4.1/ncu','--profile-from-start','off','--clock-control','none','--cache-control','none','--kernel-name','dataProcessKnn','--launch-count','1','--export',str(out/'trace')]
   for section in ['SpeedOfLight','MemoryWorkloadAnalysis_Tables','LaunchStats','Occupancy','SchedulerStats','WarpStateStats','SourceCounters','InstructionStats']:c+=['--section',section]
   cmd=c+cmd
  else:cmd=['/usr/bin/timeout','--signal=TERM','--kill-after=10s','300s']+cmd
  start=time.time()
  with (out/'stdout.log').open('w') as o,(out/'stderr.log').open('w') as er:rc=subprocess.run(cmd,cwd=out,env={**os.environ,'CUDA_VISIBLE_DEVICES':a.gpu},stdout=o,stderr=er).returncode
  after=base.snapshot(a.gpu);(out/'after.json').write_text(json.dumps(after,indent=2)+'\n');t=(out/'stdout.log').read_text()+(out/'stderr.log').read_text()
  r={'command':cmd,'exit_code':rc,'correct':'correct,full_integer_topk_oracle' in t and 'pass' in t.splitlines(),'post_clear':not after['apps'].strip(),'binary_sha256':base.sha(binary),'wall_s':time.time()-start,'variant':v,'n':n,'q':q,'k':k,'mode':mode,'tool':tool,'api':api}
  (out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');print(label,rc,r['correct'],r['wall_s'],flush=True);assert rc==0 and r['correct'] and r['post_clear'],'failed gate; retained, stop'
  if tool=='ncu':
   for page in ['raw','source','details']:
    c=['/opt/nvidia/nsight-compute/2025.4.1/ncu','--import',str(out/'trace.ncu-rep'),'--page',page]
    if page in ['raw','source']:c+=['--csv']
    if page=='raw':c+=['--print-units','base']
    if page=='source':c+=['--print-source','sass']
    if page=='details':c+=['--print-details','all']
    with (out/(page+'.txt' if page=='details' else page+'.csv')).open('w') as o:subprocess.run(c,stdout=o,stderr=subprocess.STDOUT,check=True)
 if a.stage in ['preflight','gates']:
  for v in ('A' if a.stage=='preflight' else 'AB'):
   prefix='pre' if a.stage=='preflight' else 'check'
   for n,q,k in CASES:run(f'{prefix}_{n}_{q}_{k}_{v}',v,n,q,k)
   for n,q,k in [CASES[0],CASES[-1]]:
    for api in ['vec','kth','vth']:run(f'{prefix}_{n}_{q}_{k}_{api}_{v}',v,n,q,k,api=api)
    for tool in ['memcheck','synccheck']:run(f'{prefix}_{tool}_{n}_{v}',v,n,q,k,tool=tool)
  if a.stage=='preflight':
   run('pre_timing_A','A',65536,128,100,'timing');run('pre_nsys_A','A',65536,128,100,'profile','nsys')
  else:
   for tool in ['racecheck','initcheck']:run(tool+'_B','B',2000,32,10,tool=tool)
 else:
  required=[]
  for v in 'AB':
   required += [(f'check_{n}_{q}_{k}_{v}',v) for n,q,k in CASES]
   for n,q,k in [CASES[0],CASES[-1]]:
    required += [(f'check_{n}_{q}_{k}_{api}_{v}',v) for api in ['vec','kth','vth']]
    required += [(f'check_{tool}_{n}_{v}',v) for tool in ['memcheck','synccheck']]
   if a.stage!='stress':required += [(f'stress_{q}_{k}_0_{v}',v) for n,q,k in [CASES[1],CASES[-1]]]
  required += [(tool+'_B','B') for tool in ['racecheck','initcheck']]
  for label,v in required:
   r=json.loads((root/'runs'/label/'receipt.json').read_text());assert r['exit_code']==0 and r['correct'] and r['post_clear'] and r['binary_sha256']==base.sha(root/'bin'/v)
  if a.stage=='timing':
   for n,q,k in CASES[1:]:
    for pair in range(6):
     for v in ('AB' if pair%2==0 else 'BA'):run(f'timing_{q}_{k}_{pair}_{v}',v,n,q,k,'timing')
  elif a.stage=='profile':
   for tool in ['nsys','ncu']:
    for v in 'AB':run(f'{tool}_{v}',v,65536,128,100,'profile',tool)
  else:
   for n,q,k in [CASES[1],CASES[-1]]:
    for pair in range(1 if a.stage=='stress' else 3):
     for v in ('AB' if pair%2==0 else 'BA'):run(f'{a.stage}_{q}_{k}_{pair}_{v}',v,n,q,k,a.stage)
if __name__=='__main__':main()
