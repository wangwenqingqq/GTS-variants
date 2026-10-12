#!/usr/bin/env python3
"""Explicitly registered single-reference recovery; never replace primary samples."""
import argparse,csv,hashlib,json,os,subprocess,time
from pathlib import Path
import numpy as np
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_text())
def main(a):
 r=a.root;w=r/'prepared_r2';original=read(w/'REGISTERED.json');b=r/'matched_build_r2/matched';old=read(r/'matched_guard/receipt.json');assert old['exit_code']==1 and not old['runtime_valid']
 assert sha(b)==read(r/'matched_build_r2/BUILD.json')['binary_sha256'];out=r/'matched_output_r2';guard=r/'matched_guard_r2'
 cmd=[str(b),original['data'],str(w/'qids.txt'),str(out)];env={**os.environ,**original['environment'],'REGION_MODE':'PAR_STRONG','KNN_MODE':'FULL','BUILD_MAPPING':'TILED','U10_TREE_AUDIT':'0','U10_OBSERVE':'0','OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1'}
 registration=r/'MATCHED_RECOVERY_REGISTERED.json';assert not registration.exists();registration.write_text(json.dumps(dict(human_authorized=True,before_execution=True,old_failure_retained_sha256=sha(r/'matched_guard/receipt.json'),command=cmd,environment={k:env[k] for k in ('REGION_MODE','KNN_MODE','BUILD_MAPPING','U10_TREE_AUDIT','U10_OBSERVE')},gpu=a.gpu,numa=a.numa,binary_sha256=sha(b),raw_ready_sha256=sha(w/'READY.json'),registered_unix=time.time(),scope='one reference only; no passed sample rerun/contract change'),indent=2)+'\n')
 launcher=['python3',str(r/'code_executor/artifacts/external_closure/static_guard.py'),'--gpu',a.gpu,'--numa-node',str(a.numa),'--output',str(guard),'--',*cmd]
 with (r/'matched_recovery.log').open('x') as log:subprocess.run(launcher,env=env,stdout=log,stderr=log,check=True)
 assert read(guard/'receipt.json')['runtime_valid']
 rows=list(csv.DictReader((out/'queries.csv').open()));qids=original['qids'];expected_order=[(-1,3,i,qids[i]) for i in range(8)]+[(0,3,i,qids[i]) for i in range(32)];assert [(int(x['pass']),int(x['mode']),int(x['query']),int(x['qid'])) for x in rows]==expected_order
 assert (out/'ids').stat().st_size%4==(out/'fields').stat().st_size%4==0;ids=np.fromfile(out/'ids','<i4');fields=np.fromfile(out/'fields','<f4');offset=0;radius=read(w/'READY.json')['calibration']['960']['mid']['radius']
 for row in rows:
  ref=np.memmap(w/'reference/960'/f"{row['qid']}.f64",dtype='<f8',mode='r');expected=np.flatnonzero(ref<=radius*radius);n=int(row['count']);assert int(row['offset'])==offset
  actual=ids[offset:offset+n];f=fields[offset:offset+n];assert np.array_equal(actual,expected) and f.view(np.uint32).tobytes()==np.sqrt(ref[expected]).astype('<f4').view(np.uint32).tobytes();offset+=n
  assert all(np.isfinite(float(row[k])) and float(row[k])>=0 for k in ('host_ms','front_ms','verify_ms','output_ms'))
 assert offset==len(ids)==len(fields)
 receipt=r/'MATCHED_CHECKED.json';assert not receipt.exists();receipt.write_text(json.dumps(dict(passed=True,query_rows=40,measured_rows=32,all_members_exact=True,all_fields_bit_exact=True,rows=rows,meta=read(out/'META.json'),raw_guard_sha256=sha(guard/'receipt.json'),registration_sha256=sha(registration),output_hashes={p.name:sha(p) for p in out.iterdir() if p.is_file()},scope='single ordered-FP64 SCAN_MATCHED diagnostic process, not native FP32 paired timing or algorithm speedup'),indent=2)+'\n');print('MATCHED RECOVERY PASSED',flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--gpu',required=True);p.add_argument('--numa',type=int,required=True);main(p.parse_args())
