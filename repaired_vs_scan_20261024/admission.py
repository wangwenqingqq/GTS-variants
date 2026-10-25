"""Record a fail-closed GPU-0 preflight; this tool never launches GPU work."""
import csv
import datetime
import fcntl
import json
from pathlib import Path
import subprocess
import sys

UUID='GPU-9bd364a9-9d88-0b78-ef55-caac6f73d6b1'
FIELDS='uuid,name,driver_version,memory.used,utilization.gpu,pstate,power.draw,clocks.current.graphics,clocks.current.memory'

def gate(gpu,apps):
    row=next(csv.reader([gpu.strip()]),[])
    if len(row)!=9:return ['unparseable_gpu_state']
    row=[s.strip() for s in row]
    errors=[]
    if row[0]!=UUID:errors.append('wrong_gpu_uuid')
    try:
        if int(row[3])>256:errors.append('memory_above_256_MiB')
        if int(row[4])!=0:errors.append('nonzero_gpu_utilization')
    except ValueError:errors.append('unparseable_gpu_metrics')
    if apps.strip():errors.append('foreign_compute_process_present')
    return errors

def record(root,lock_path='/tmp/gtspp_gpu0.lock'):
    root=Path(root);out=root/'logs/admission.json';assert not out.exists()
    handles=[]
    for p in [Path(lock_path),root/'campaign.lock']:
        f=p.open('r+' if p.exists() else 'x+')
        fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);handles.append(f)
    rec={'time_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
         'gpu_index':0,'gpu_work_launched':False,'advisory_locks_acquired':True}
    try:
        def query(args):return subprocess.check_output(['nvidia-smi','-i','0',*args,'--format=csv,noheader,nounits'],text=True,timeout=10)
        rec['gpu']=query(['--query-gpu='+FIELDS])
        rec['apps']=query(['--query-compute-apps=pid,process_name,used_memory'])
        rec['errors']=gate(rec['gpu'],rec['apps'])
    except (subprocess.SubprocessError,OSError) as e:
        rec['errors']=['telemetry_failed'];rec['exception_type']=type(e).__name__
    rec['admitted']=not rec['errors'];out.write_text(json.dumps(rec,indent=2)+'\n')
    if not rec['admitted']:(root/'STOP_GPU').write_text('Admission failed. No automatic retry or replacement observations.\n')
    for f in handles:f.close()
    print(json.dumps(rec));return 0 if rec['admitted'] else 75

if __name__=='__main__':sys.exit(record(sys.argv[1]))
