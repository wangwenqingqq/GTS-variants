#!/usr/bin/env python3
"""Whitelist scalar evidence; preserve raw provenance privately without destructive scrubbing."""
import argparse,csv,hashlib,json,shutil
from pathlib import Path

def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2)+'\n')
def main(a):
 raw=a.raw;w=raw/'prepared_r2';out=a.output;out.mkdir(exist_ok=False);ev=out/'evidence';ev.mkdir()
 source_dir=Path(__file__).resolve().parent
 for name in ('CONTRACT.json','CONTRACT_R0.json'):shutil.copyfile(source_dir/name,out/name)
 contract_hashes={name:sha(out/name) for name in ('CONTRACT.json','CONTRACT_R0.json')}
 for name in ('STATIC_STATS','DYNAMIC_STATS','STATIC_TIMELINE','DYNAMIC_TIMELINE'):
  v=read(raw/(name+'.json'));write(ev/(name+'.json'),v)
 # Device/runtime metadata is not copied wholesale from profiler reports.
 f=read(raw/'FORENSIC_R3.json');metrics={}
 for mode,v in f['metrics'].items():metrics[mode]={k:z for k,z in v.items() if k!='raw_metrics'}
 write(ev/'METRICS.json',dict(metrics=metrics,selected_function_identity={k:f[k] for k in ('full','distance')},full_module_image_hash=f['full_module_image_hash'],raw_vendor_code_publication=f['raw_vendor_code_publication'],L2_scope='main capture aggregate L2 bytes; approved separate supplement supplies read/write/Other request sectors, never blended with earlier capture',normalization_test='true opcode mutation changes hash; absolute PC/relative control target ASLR is normalized, other operands preserved'))
 ready=read(w/'READY.json');prep=read(w/'PREPARED.json');reg=read(w/'REGISTERED.json')
 write(ev/'CALIBRATION.json',dict(calibration=ready['calibration'],calibration_qids=ready['calibration_qids'],measured_qids=reg['qids'],seed=2026101112,original_first8_calibration=prep['calibration'],original_calibration_qids=list(range(8)),approved_before_GPU_timing=True,retuning_after_measurement=False,reference_array_hashes=prep['reference_hashes'],quality_scope='ordered FP64 complete-membership oracle with native-field scale tolerance5e-5; matched FP64 fields require bit equality; controls aggregate tolerance1e-4'))
 rows=[];timings=[];quality=[];sampling=[];source={}
 for stage in ('qualification','keeper','primary','scaling','dynamic'):
  result=read(w/stage/'RESULTS.json');registration=read(w/stage/'REGISTERED.json');assert result['complete'];source[stage]=dict(registration_sha256=sha(w/stage/'REGISTERED.json'),result_sha256=sha(w/stage/'RESULTS.json'))
  for job in result['rows']:
   label=job['label'];c=read(w/stage/(label+'.checked.json'));guard=read(w/stage/'guards'/label/'receipt.json');assert c['passed'] and guard['runtime_valid'];prefix=w/stage/'outputs'/label
   rows.append(dict(stage=stage,label=label,status='passed',N=job['N'],D=job['D'],mode=job['mode'],radius=job['radius'],binary_or_launcher_sha256=guard['binary_sha256'],checked_sha256=sha(w/stage/(label+'.checked.json')),raw_guard_sha256=sha(w/stage/'guards'/label/'receipt.json'),output_payload_hashes=c['output_hashes']))
   quality.append(dict(stage=stage,label=label,payloads=c.get('quality'),query_rows=c.get('query_rows'),scope='full membership/field validation or declared aggregate-only control'))
   suffix='.ops.csv' if stage=='dynamic' else '.queries.csv' if stage=='keeper' else '.rows.csv'
   with (Path(str(prefix)+suffix)).open() as file:
    for r in csv.DictReader(file):timings.append(dict(stage=stage,label=label,**r))
   gpu=w/stage/'guards'/label/'gpu.csv'
   if gpu.exists():
    with gpu.open() as file:
     for r in csv.reader(file):
      if len(r)==8:sampling.append(dict(stage=stage,label=label,memory_used_MiB=r[1].strip(),GPU_util_percent=r[2].strip(),power_W=r[3].strip(),SM_MHz=r[4].strip(),memory_MHz=r[5].strip(),temperature_C=r[6].strip(),pstate=r[7].strip()))
 for stage in ('nsys_static','ncu','nsys_dynamic'):
  proof=read(w/stage/'PROOF.json');assert proof['passed'];source[stage]=dict(registration_sha256=sha(w/stage/'REGISTERED.json'),proof_sha256=sha(w/stage/'PROOF.json'),raw_report_hashes={k:z for k,z in proof['raw_files'].items() if k.endswith(('.ncu-rep','.nsys-rep','.sqlite','.csv'))})
  modes=['FULL_OUTPUT'] if stage=='nsys_static' else ['dynamic'] if stage=='nsys_dynamic' else ['READ_ONLY','DISTANCE_ONLY','FULL_OUTPUT']
  for mode in modes:
   c=read(w/stage/(mode+'.checked.json'));g=read(w/stage/('guard_'+mode)/'receipt.json');assert g['runtime_valid']
   rows.append(dict(stage=stage,label=mode,status='passed',raw_guard_sha256=sha(w/stage/('guard_'+mode)/'receipt.json'),checked_sha256=sha(w/stage/(mode+'.checked.json')),scope='independent diagnostic, not primary latency'))
 failed=read(raw/'matched_guard/receipt.json');assert failed['exit_code']==1 and not failed['runtime_valid']
 rows.append(dict(stage='matched_initial_attempt',label='matched',status='failed_before_CUDA_initialization',exit_code=1,reason='missing BUILD_MAPPING=TILED in launcher; source guard rejected before data/context',raw_guard_sha256=sha(raw/'matched_guard/receipt.json'),binary_sha256=failed['binary_sha256'],no_valid_timing=True))
 matched=raw/'MATCHED_CHECKED.json';valid=matched.exists()
 if valid:
  c=read(matched);assert c['passed'];rows.append(dict(stage='matched_registered_recovery',label='matched',status='passed',checked_sha256=sha(matched),scope='one ordered-FP64 diagnostic reference; not paired/native comparison'));write(ev/'MATCHED.json',c)
 if (raw/'L2_SUPPLEMENT.json').exists():
  c=read(raw/'L2_SUPPLEMENT.json');assert c['passed'];rows.append(dict(stage='L2_supplement',label='FULL_OUTPUT_L2',status='passed',raw_guard_sha256=c['raw_guard_sha256'],quality_sha256=c['quality_sha256'],raw_report_sha256=c['raw_report_sha256'],scope='approved independent traffic supplement; postprocessor two-bucket assumption rejected offline, no GPU rerun'))
 write(ev/'PROCESS_RECEIPTS.json',dict(rows=rows,attempted_top_level_processes=len(rows),passed_top_level_processes=sum(r['status']=='passed' for r in rows),budget_limit=110,formal_primary_failed=0,matched_reference_valid=valid,first_failed_attempt_retained=True))
 write(ev/'QUALITY.json',dict(rows=quality,full_output_payloads_external=True,raw_ID_distance_vector_arrays_excluded=True))
 for name,rr in (('QUERY_OPERATIONS.csv',timings),('HARDWARE_SAMPLES.csv',sampling)):
  fields=list(dict.fromkeys(k for r in rr for k in r))
  with (ev/name).open('w') as file:
   writer=csv.DictWriter(file,fieldnames=fields,lineterminator='\n');writer.writeheader();writer.writerows(rr)
 write(ev/'BUILD.json',dict(**read(w/'build/BUILD.json'),matched_build=read(raw/'matched_build_r2/BUILD.json'),source_base_commit='77a8d887897ce7bdc9a7d3800cc886b322ec64f5',versions=dict(driver='590.48.01',nvcc='13.1.115',NCU='2025.4.1.0',NSYS='2025.5.2',cuVS='26.8.1',RAFT='26.8.0',RMM='26.8.0',cuPy='14.1.0',NVRTC_package='13.3.33'),scope='original pinned native keeper binaries reused and remeasured; diagnostic controls freshly compiled. Codegen/source identities are distinct from commit publication identity'))
 write(ev/'PROVENANCE.json',dict(raw_registration_hashes=source,original_raw_contract_R0_sha256='29ae0a69ec07fe6ae3f77966ebee6c8f56be83866d387b3bad2ba2fd97dbcb6d',original_raw_contract_R1_sha256=ready['contract_sha256'],data_sha256=reg['data_sha256'],prepared_sha256=sha(w/'PREPARED.json'),raw_READY_sha256=sha(w/'READY.json'),same_private_device_for_all_valid_runs=True,identity_mapping_private=True,scope='curated scalar receipts/hashes, not original raw registrations. Absolute paths/device identities/raw reports/vendor SASS kept outside Git',input_shapes='GIST N1M D960 FP32 L2 B1; dimensions128/256/512 and N-prefix controls; fixed336-event trace',curated_contract_sha256=contract_hashes,curation_only_source_changes='public contract placement prose; explicit --original-contract for archival calibration; delivered L2 helper --numa argument instead of measured fixed placement; curator provenance bridge and independent analysis/report/recovery helpers. CUDA probe/matched bodies unchanged'))
 identity={}
 native=[r for r in rows if r['stage']=='keeper' or (r['stage']=='primary' and r['mode']=='FULL_OUTPUT')]
 assert len(native)==12
 items=sum(int(r['count']) for r in timings if r['stage']=='keeper' and r['label']=='keeper_r1')
 for suffix,size in (('.ids.i32',4),('.dist.f32',4),('.native_squared.f64',8)):
  hashes={r['output_payload_hashes'][r['label']+suffix] for r in native};assert len(hashes)==1
  identity[suffix]=dict(all12_payloads_bit_identical=True,sha256=hashes.pop(),bytes=items*size)
 write(ev/'NATIVE_IDENTITY.json',dict(passed=True,scope='40 native complete answers including 8 warmup; 6 keeper and 6 FULL_OUTPUT raw payloads CPU-only SHA comparison',payloads=identity))
 write(ev/'FINAL_AUDIT.json',read(raw/'FINAL_AUDIT.json'))
 write(ev/'STATIC_DECISION.json',read(w/'STATIC_DECISION.json'))
 if (raw/'L2_SUPPLEMENT.json').exists():write(ev/'L2_SUPPLEMENT.json',read(raw/'L2_SUPPLEMENT.json'))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--raw',type=Path,required=True);p.add_argument('--output',type=Path,required=True);main(p.parse_args())
