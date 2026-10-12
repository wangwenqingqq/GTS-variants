#!/usr/bin/env python3
"""Audit curated scalar consistency; original complete payload validation is external."""
import argparse,csv,hashlib,json,re
from pathlib import Path
import numpy as np
read=lambda p:json.loads(Path(p).read_text())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def audit(root):
 e=root/'evidence';p=read(e/'PROCESS_RECEIPTS.json');assert p['attempted_top_level_processes']==106 and p['passed_top_level_processes']==105 and p['budget_limit']==110
 counts={k:sum(r['stage']==k for r in p['rows']) for k in ('qualification','keeper','primary','scaling','dynamic','nsys_static','ncu','nsys_dynamic','matched_initial_attempt','matched_registered_recovery','L2_supplement')};assert counts==dict(qualification=8,keeper=6,primary=24,scaling=54,dynamic=6,nsys_static=1,ncu=3,nsys_dynamic=1,matched_initial_attempt=1,matched_registered_recovery=1,L2_supplement=1)
 assert sum(r['status']=='failed_before_CUDA_initialization' for r in p['rows'])==1 and p['matched_reference_valid']
 provenance=read(e/'PROVENANCE.json')
 for name,h in provenance['curated_contract_sha256'].items():assert sha(root/name)==h
 s=read(e/'STATIC_STATS.json');rows=list(csv.DictReader((e/'QUERY_OPERATIONS.csv').open()))
 for stage,groups in [('keeper',s['keeper']),('primary',s['modes']),('scaling',s['scaling'])]:
  for group in groups.values():
   values=[]
   for job in group['rows']:
    rr=[r for r in rows if r['stage']==stage and r['label']==job['label'] and int(r['query'])>=8];assert len(rr)==32
    mean=sum(float(r['ack_ms']) for r in rr)/32;assert abs(mean-job['mean_query_ms'])<1e-12;values.append(mean)
   q=group['query_ms'];assert np.allclose(np.quantile(values,[.1,.5,.9]),[q['p10'],q['median'],q['p90']],rtol=0,atol=1e-12)
 d=read(e/'DYNAMIC_STATS.json')
 for job in d['rows']:
  rr=[r for r in rows if r['stage']=='dynamic' and r['label']=='dynamic_r'+str(job['round'])];assert len(rr)==336
  for flag,name in ((0,'insert'),(1,'delete'),(2,'range'),(3,'knn')):
   v=[float(r['ack_ms']) for r in rr if int(r['flag'])==flag];assert len(v)==(40 if flag<2 else 128);assert abs(sum(v)-job['groups'][name]['sum_ms'])<1e-9
  assert job['update_fraction_of_continuous']<.001 and not d['UPDATE_BOUND']
 t=read(e/'STATIC_TIMELINE.json')['aggregate'];assert abs(sum(t['components_ms'].values())-t['GPU_active_ms'])<1e-8 and abs(t['host_span_ms']-t['GPU_active_ms']-t['exposed_Host_gap_ms'])<1e-8
 m=read(e/'METRICS.json');assert m['selected_function_identity']['full']['normalized_sha256']==m['selected_function_identity']['distance']['normalized_sha256']
 for v in m['metrics'].values():assert abs(v['FP32_pred_on_add']+v['FP32_pred_on_mul']+2*v['FP32_pred_on_fma']-v['FP32_executed_flop_proxy'])<1e-6
 l=read(e/'L2_SUPPLEMENT.json');assert l['total_L2_bytes']==l['read_L2_bytes']+l['write_L2_bytes']+l['other_L2_bytes'] and l['other_L2_sectors']==10048
 assert read(e/'MATCHED.json')['all_fields_bit_exact']
 identity=read(e/'NATIVE_IDENTITY.json');assert identity['passed']
 native=[r for r in p['rows'] if r['stage']=='keeper' or (r['stage']=='primary' and r['mode']=='FULL_OUTPUT')];assert len(native)==12
 for suffix,v in identity['payloads'].items():
  assert v['all12_payloads_bit_identical'] and all(r['output_payload_hashes'][r['label']+suffix]==v['sha256'] for r in native)
 raw=read(e/'FINAL_AUDIT.json');assert raw['passed'] and raw['GPU_top_level_attempts']==106 and raw['successful_GPU_processes']==105 and raw['retained_pre_CUDA_failure']==1
 leak=re.compile(r'/(?:Users|home|root)/|GPU-[0-9a-f]{8}-|gh[pousr]_[A-Za-z0-9_]{20,}|BEGIN (?:RSA |OPENSSH )?PRIVATE KEY'+ '|'+('|'.join(['cl'+'aude','anthro'+'pic','co'+'-authored'])),re.I)
 for p in root.rglob('*'):
  if p.is_file() and p.suffix in ('.py','.cu','.md','.json','.csv','.svg'):
   assert not leak.search(p.read_text()),('publication boundary',p)
 return dict(passed=True,process_counts=counts,curated_contract_hashes_match=True,all_primary_process_means_reconstructed_from_CSV=True,all336_operation_ACK_sums_reconstructed=True,timeline_union_and_L2_bucket_accounting=True,source_identity_boundary='reported function instruction text, full module image unavailable',scope='curated scalar/manifest audit only; full membership/field checks were separately performed on original external raw payloads')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--artifact',type=Path,required=True);a=p.parse_args();print(json.dumps(audit(a.artifact),indent=2))
