#!/usr/bin/env python3
"""Offline three-bucket L2 accounting; preserve rejected two-bucket assumption."""
import argparse,csv,hashlib,json
from pathlib import Path
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_text())
def finalize(root):
 out=root/'l2_supplement';assert read(out/'guard/receipt.json')['runtime_valid'];assert read(out/'CHECKED.json')['passed']
 for name,h in read(out/'CHECKED.json')['output_hashes'].items():assert sha(out/name)==h
 h,u,z=list(csv.reader((out/'report_base.csv').read_text().splitlines()));v={k:dict(value=x,unit=y) for k,y,x in zip(h,u,z)};val=lambda k:int(v[k]['value']);total=val('lts__t_sectors.sum');reads=val('lts__t_sectors_op_read.sum');writes=val('lts__t_sectors_op_write.sum');bytes_=val('lts__t_bytes.sum');other=total-reads-writes
 assert v['Kernel Name']['value']=='pairwise_matrix_kernel' and 32*total==bytes_ and min(reads,writes,other)>=0
 rejected=out/'POSTPROCESSING_R1_REJECTED.json';assert not rejected.exists();rejected.write_text(json.dumps(dict(GPU_runtime_valid=True,all40_answers_valid=True,invalid_assumption='all L2 sector requests are read or write',observed_other_sectors=other,consequence='first offline two-bucket assertion failed; retain raw capture and use explicit unknown-subtype Other bucket; no GPU rerun'),indent=2)+'\n')
 result=dict(passed=True,all40_answers_correct=True,total_L2_sectors=total,read_L2_sectors=reads,write_L2_sectors=writes,other_L2_sectors=other,sector_bytes=32,total_L2_bytes=bytes_,read_L2_bytes=reads*32,write_L2_bytes=writes*32,other_L2_bytes=other*32,DRAM_bytes=val('dram__bytes.sum'),selected_duration_ns=val('gpu__time_duration.avg'),kernel='pairwise_matrix_kernel',binary_sha256=read(out/'REGISTERED.json')['binary_sha256'],scope='approved separate selected main-kernel NCU capture; request-sector bytes, not DRAM transfer or Host ACK; Other subtype not identified',raw_registration_sha256=sha(out/'REGISTERED.json'),raw_guard_sha256=sha(out/'guard/receipt.json'),raw_report_sha256=sha(out/'report.ncu-rep'),raw_csv_sha256=sha(out/'report_base.csv'),quality_sha256=sha(out/'CHECKED.json'),rejected_postprocessing_sha256=sha(rejected),CPU_only_interpretation_correction=True,GPU_process_count_unchanged=True)
 p=root/'L2_SUPPLEMENT.json';assert not p.exists();p.write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('root',type=Path);a=p.parse_args();print(json.dumps(finalize(a.root),indent=2))
