#!/usr/bin/env python3
"""One locked GPU0 process at a time; failures are evidence, not timings to promote."""
import argparse,fcntl,hashlib,importlib.util,json,os,subprocess,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('base',HERE.parent/'original_tree_profile/run.py');base=importlib.util.module_from_spec(s);s.loader.exec_module(base)
CASES=['query_only','all_include','base_delete','direct_insert','direct_delete','buffer_query','buffer_delete','rebuild']
def main():
 p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('--gpu',required=True);p.add_argument('--stage',choices=['check','sanitizer','nsys','ncu'],required=True);p.add_argument('--case',choices=CASES);p.add_argument('--suffix',default='');a=p.parse_args();assert all(c.isalnum() or c in '_-' for c in a.suffix);root=a.root.resolve();(root/'runs').mkdir(exist_ok=True)
 lock=open('/tmp/gtspp_gpu0.lock','a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);assert base.snapshot(a.gpu)['gpu'].split(',')[0].strip()=='0'
 pins=json.loads((HERE.parent/'tc_leaf_probe/EVIDENCE.json').read_text())['fixtures']['n2000'];assert base.sha(root/'fixtures/n2000/data.txt')==pins['file_sha256']['data.txt']
 cases=[(x,None) for x in CASES]
 if a.stage=='ncu':cases=[('query_only',x) for x in ['initIndexData','getPivotDis','nodeSplit','initQnode','initRes','findNextRnn','updatePnodeFlag','collectLeafNodesSingleQuery','leafProcessRnnUpdate','compactResultSingleQuery','mergeTotalResult']]+[('buffer_delete','mergeInResult'),('rebuild','getNewData')]+[('buffer_query',x) for x in ['searchD','check','getRnn']]
 if a.case:cases=[x for x in cases if x[0]==a.case]
 for case,kernel in cases:
  name=a.stage+'_'+case+('_'+kernel if kernel else '')+('_'+a.suffix if a.suffix else '');out=root/'runs'/name;out.mkdir();before=base.snapshot(a.gpu);(out/'before.json').write_text(json.dumps(before,indent=2)+'\n');assert not before['apps'].strip(),'GPU0 busy'
  cmd=[str(root/'bin/native'),str(root/'fixtures/n2000/data.txt'),str(root/'traces'/f'{case}.txt'),'2','10000' if case=='all_include' else '200',str(out/'cost.txt')]
  if a.stage=='sanitizer':cmd=['compute-sanitizer','--tool','memcheck','--error-exitcode','90','--leak-check','no']+cmd
  if a.stage=='nsys':cmd=['nsys','profile','--trace=cuda,nvtx','--sample=none','--cpuctxsw=none','--export=sqlite','--output='+str(out/'trace')]+cmd
  if a.stage=='ncu':
   (out/'home').mkdir();cmd=['sudo','-n','/usr/bin/timeout','--signal=TERM','--kill-after=10s','180s','/usr/bin/env','CUDA_VISIBLE_DEVICES='+a.gpu,'GTS_DIAG_BLOCKING=0','GTSPP_MAX_IN_SIZE=2','HOME='+str(out/'home'),'/opt/nvidia/nsight-compute/2025.4.1/ncu','--clock-control','none','--cache-control','none','--kernel-name',kernel,'--launch-count','1','--section','MemoryWorkloadAnalysis_Tables','--section','LaunchStats','--section','SchedulerStats','--section','SpeedOfLight','--export',str(out/'trace')]+cmd
  if a.stage!='ncu':cmd=['/usr/bin/timeout','--signal=TERM','--kill-after=10s','180s']+cmd
  start=time.time()
  with (out/'stdout.log').open('w') as o,(out/'stderr.log').open('w') as e:rc=subprocess.run(cmd,cwd=out,env={**os.environ,'CUDA_VISIBLE_DEVICES':a.gpu,'GTS_DIAG_BLOCKING':'0','GTSPP_MAX_IN_SIZE':'2'},stdout=o,stderr=e).returncode
  after=base.snapshot(a.gpu);(out/'after.json').write_text(json.dumps(after,indent=2)+'\n');stdout=(out/'stdout.log').read_text();stderr=(out/'stderr.log').read_text()
  rows=[x for x in stdout.splitlines() if x.startswith('AUDIT_COUNT,')];r={'case':case,'stage':a.stage,'kernel':kernel,'command':cmd,'exit_code':rc,'binary_sha256':base.sha(root/'bin/native'),'trace_sha256':base.sha(root/'traces'/f'{case}.txt'),'post_clear':not after['apps'].strip(),'wall_s':time.time()-start,'oracle_rows':rows,'count_check_pass':bool(rows) and all(x.endswith(',PASS') for x in rows),'phases':{v[1]:{'count':int(v[2]),'inclusive_wall_s':float(v[3]),'inclusive_main_thread_cpu_s':float(v[4])} for v in (x.split(',') for x in stderr.splitlines()) if len(v)==5 and v[0]=='GTS_DIAG' and v[2].isdigit()},'sanitizer_summaries':[x for x in (stdout+'\n'+stderr).splitlines() if 'SUMMARY:' in x],'scope':'diagnostic-only; buffer_delete has no final query, not state-validated'}
  (out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');print(name,rc,rows,r['sanitizer_summaries'],flush=True);assert r['post_clear'],'GPU0 no longer clear'
  if a.stage=='ncu' and (out/'trace.ncu-rep').exists():
   with (out/'raw.csv').open('w') as o:subprocess.run(['/opt/nvidia/nsight-compute/2025.4.1/ncu','--import',str(out/'trace.ncu-rep'),'--page','raw','--csv','--print-units','base'],stdout=o,check=True)
if __name__=='__main__':main()
