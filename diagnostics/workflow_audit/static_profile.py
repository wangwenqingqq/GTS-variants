#!/usr/bin/env python3
"""Representative static-query counters using reverified prior native comparators."""
import argparse,fcntl,importlib.util,json,os,subprocess,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('base',HERE.parent/'original_tree_profile/run.py');base=importlib.util.module_from_spec(s);s.loader.exec_module(base)
RNN=['initPList','nodeProcessRnn','getQCount','mergeLNode','dataProcessRnn','mergeResRnn']
KNN=['initPListKnn','initDisK','labelCNode','getDisPQ','nodeProcessKnn','updateDisK','getQCountKnn','mergeLNodeKnn','dataProcessKnn','mergeResKnnIds']
def main():
 p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('--gpu',required=True);a=p.parse_args();root=a.root.resolve()
 lock=open('/tmp/gtspp_gpu0.lock','a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);assert base.snapshot(a.gpu)['gpu'].split(',')[0].strip()=='0'
 for typ,folder in [('rnn','gtspp_coalescing'),('knn','gtspp_knn')]:
  e=json.loads((HERE.parent/folder/'EVIDENCE.json').read_text());assert base.sha(root/'bin'/typ)==e['provenance']['binaries']['A']
 for f,h in json.loads((HERE.parent/'gtspp_knn/EVIDENCE.json').read_text())['fixtures']['n65536']['file_sha256'].items():assert base.sha(root/'fixtures/n65536'/f)==h
 cases=[('rnn','ids',x) for x in RNN]+[('knn','ids',x) for x in KNN]+[('knn','vec',x) for x in ['getDisPQVec','dataProcessKnnVec']]+[('knn','kth','mergeResKnn')]
 for typ,api,kernel in cases:
  out=root/'runs'/('static_'+api+'_'+kernel);out.mkdir();before=base.snapshot(a.gpu);(out/'before.json').write_text(json.dumps(before,indent=2)+'\n');assert not before['apps'].strip(),'GPU0 busy'
  fixture=root/'fixtures/n65536';cmd=[str(root/'bin'/typ),str(fixture/'data.txt'),str(fixture/'q128.txt')]+(['500','D','profile'] if typ=='rnn' else ['100',api,'profile','D'])
  (out/'home').mkdir();cmd=['sudo','-n','/usr/bin/timeout','--signal=TERM','--kill-after=10s','180s','/usr/bin/env','CUDA_VISIBLE_DEVICES='+a.gpu,'HOME='+str(out/'home'),'/opt/nvidia/nsight-compute/2025.4.1/ncu','--profile-from-start','off','--clock-control','none','--cache-control','none','--kernel-name',kernel,'--launch-count','1','--section','MemoryWorkloadAnalysis_Tables','--section','LaunchStats','--section','SchedulerStats','--section','SpeedOfLight','--export',str(out/'trace')]+cmd
  start=time.time()
  with (out/'stdout.log').open('w') as o,(out/'stderr.log').open('w') as e:rc=subprocess.run(cmd,cwd=out,stdout=o,stderr=e).returncode
  after=base.snapshot(a.gpu);(out/'after.json').write_text(json.dumps(after,indent=2)+'\n');t=(out/'stdout.log').read_text();r={'kind':typ,'api':api,'kernel':kernel,'command':cmd,'exit_code':rc,'binary_sha256':base.sha(root/'bin'/typ),'post_clear':not after['apps'].strip(),'wall_s':time.time()-start,'correct':'pass' in t.splitlines() and 'correct,full_integer' in t,'scope':'NCU representative native static query; not clean latency'}
  (out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');print(out.name,rc,r['correct'],flush=True);assert rc==0 and r['correct'] and r['post_clear']
  with (out/'raw.csv').open('w') as o:subprocess.run(['/opt/nvidia/nsight-compute/2025.4.1/ncu','--import',str(out/'trace.ncu-rep'),'--page','raw','--csv','--print-units','base'],stdout=o,check=True)
if __name__=='__main__':main()
