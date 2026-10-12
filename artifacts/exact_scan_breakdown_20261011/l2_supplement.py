#!/usr/bin/env python3
"""Approved independent L2 traffic supplement; primary observations stay immutable."""
import argparse,csv,hashlib,json,os,subprocess,sys,time
from pathlib import Path
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_text())
def main(a):
 r=a.root;w=r/'prepared_r2';sys.path.insert(0,str(r/'code_executor/artifacts/exact_scan_breakdown_20261011'))
 from campaign import check_static,verify_stage
 from prepare import EXT
 assert read(r/'MATCHED_CHECKED.json')['passed']
 for stage in ('qualification','keeper','primary','scaling','dynamic'):verify_stage(w,stage,w/'READY.json',a.gpu,a.numa)
 original=read(w/'REGISTERED.json');ready=read(w/'READY.json');out=r/'l2_supplement';out.mkdir(exist_ok=False);binary=w/'build/probe';assert sha(binary)==read(w/'build/BUILD.json')['binaries']['probe']
 metrics=['gpu__time_duration.avg','dram__bytes.sum','lts__t_bytes.sum','lts__t_sectors.sum','lts__t_sectors_op_read.sum','lts__t_sectors_op_write.sum'];inventory=set(l.split()[0] for l in (r/'ncu_metrics_all.txt').read_text().splitlines() if l.split());assert all(m.split('.')[0] in inventory for m in metrics)
 radius=ready['calibration']['960']['mid']['radius'];cmd=[str(binary),original['data'],str(w/'qids.txt'),'1000000','960',str(radius),'FULL_OUTPUT',str(out/'out'),'1'];env={**os.environ,**original['environment'],'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1'}
 launcher=['/usr/bin/sudo','-n','env','CUDA_VISIBLE_DEVICES='+a.gpu,'LD_LIBRARY_PATH='+env['LD_LIBRARY_PATH'],'/usr/local/bin/ncu','--profile-from-start','off','--kernel-name-base','demangled','--kernel-name','pairwise_matrix_kernel','--launch-count','1','--cache-control','none','--clock-control','none','--section','LaunchStats','--metrics',','.join(metrics),'-o',str(out/'report'),*cmd]
 (out/'REGISTERED.json').write_text(json.dumps(dict(before_execution=True,human_authorized=True,command=launcher,metrics=metrics,binary_sha256=sha(binary),raw_READY_sha256=sha(w/'READY.json'),selected_kernel='pairwise_matrix_kernel',scope='one supplemental diagnostic; no old capture or primary observation replacement',registered_unix=time.time()),indent=2)+'\n')
 guard=['python3',str(EXT/'static_guard.py'),'--gpu',a.gpu,'--numa-node',str(a.numa),'--output',str(out/'guard'),'--',*launcher]
 with (out/'outer.log').open('x') as f:subprocess.run(guard,env=env,stdout=f,stderr=f,check=True)
 assert read(out/'guard/receipt.json')['runtime_valid'];quality=check_static(out/'out',dict(kind='probe',mode='FULL_OUTPUT',label='L2',N=1000000,D=960,radius=radius,diagnostic=1),w,original['qids'],None)
 (out/'CHECKED.json').write_text(json.dumps(quality,indent=2)+'\n')
 with (out/'report_base.csv').open('x') as f:subprocess.run(['/usr/local/bin/ncu','--import',str(out/'report.ncu-rep'),'--page','raw','--csv','--print-units','base'],stdout=f,check=True)
 rows=list(csv.reader((out/'report_base.csv').open()));assert len(rows)==3;h,u,z=rows;v={k:dict(value=x,unit=y) for k,y,x in zip(h,u,z)};assert v['Kernel Name']['value']=='pairwise_matrix_kernel'
 val=lambda k:float(v[k]['value']);total=val('lts__t_sectors.sum');reads=val('lts__t_sectors_op_read.sum');writes=val('lts__t_sectors_op_write.sum');bytes_=val('lts__t_bytes.sum');assert 32*total==bytes_ and reads+writes==total
 result=dict(passed=True,all40_answers_correct=True,total_L2_sectors=int(total),read_L2_sectors=int(reads),write_L2_sectors=int(writes),sector_bytes=32,total_L2_bytes=int(bytes_),read_L2_bytes=int(reads*32),write_L2_bytes=int(writes*32),DRAM_bytes=int(val('dram__bytes.sum')),selected_duration_ns=int(val('gpu__time_duration.avg')),kernel='pairwise_matrix_kernel',binary_sha256=sha(binary),scope='approved separate first-measured-query main-kernel NCU capture; L2 request-sector bytes, not DRAM transfer or Host ACK',raw_registration_sha256=sha(out/'REGISTERED.json'),raw_guard_sha256=sha(out/'guard/receipt.json'),raw_report_sha256=sha(out/'report.ncu-rep'),raw_csv_sha256=sha(out/'report_base.csv'),quality_sha256=sha(out/'CHECKED.json'))
 (r/'L2_SUPPLEMENT.json').write_text(json.dumps(result,indent=2)+'\n');print('L2 SUPPLEMENT PASSED',reads*32,writes*32,flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--gpu',required=True);p.add_argument('--numa',type=int,required=True);main(p.parse_args())
