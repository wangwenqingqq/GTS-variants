#!/usr/bin/env python3
"""Frozen same-round complete-query estimator and disjoint profiler evidence."""
import argparse,csv,importlib.util,json,statistics as st
from collections import defaultdict
from pathlib import Path
HERE=Path(__file__).resolve().parent
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
prior=module('prior',HERE.parent/'gtspp_coalescing/analyze.py');stats=prior.stats;timeline=prior.timeline;ncu=prior.ncu
paired=prior.paired;observations=prior.observations
SOURCES=['CONTRACT.md','README.md','prepare.py','driver.cu','leaf_warp.cuh','leaf_warp_store.cuh','run.py','record.py','analyze.py','test_prepare.py','test_analysis.py']
def analyze(root,out):
 out.mkdir(exist_ok=False);p=json.loads((root/'logs/provenance.json').read_text())
 e={'experiment':'gtspp_20260923_knn_warp'+({'C':'64','D':'64_store'}.get(p.get('candidate_source_variant'),'512'))+'_l2','scope':'complete warm exact top-k ID query, self included, default waiting and residual mode0 unchanged; not full startup/calibrated ANN','candidate_role_B':{'C':'C64','D':'D64_store'}.get(p.get('candidate_source_variant'),'B512'),'provenance':p,'runs':{},'cases':{},'sustained':{},'traces':{},'ncu':{},'private_raw_files':{},'delivery_source_sha256':{f:stats.sha(HERE/f) for f in SOURCES if (HERE/f).exists()}}
 for v in 'AB':assert p['binaries'][v]==stats.sha(root/'bin'/v)
 for run in sorted((root/'runs').iterdir()):
  if not run.is_dir():continue
  r=json.loads((run/'receipt.json').read_text());assert r['exit_code']==0 and r['correct'] and r['post_clear'];assert r['binary_sha256']==p['binaries']['preflightA' if run.name.startswith('pre_') else r['variant']]
  o,s,b,flags=observations(run/'stdout.log');assert '\npruning,0\n' in (run/'stdout.log').read_text()
  if r['mode']=='stress':assert len(o)==64
  e['runs'][run.name]={k:r[k] for k in ['exit_code','correct','post_clear','binary_sha256','variant','n','q','k','api','mode','tool','wall_s']};e['runs'][run.name]['device_flags']=flags
  e['runs'][run.name]['sanitizer_summaries']=[l for l in (run/'stderr.log').read_text().splitlines() if 'SUMMARY:' in l]
  for f in run.iterdir():
   if f.is_file():e['private_raw_files'][str(f.relative_to(root))]={'bytes':f.stat().st_size,'sha256':stats.sha(f)}
  if r['tool']=='nsys':e['traces'][run.name]=timeline.trace(run/'trace.sqlite')
 with (out/'samples.csv').open('w',newline='') as f,(out/'stages.csv').open('w',newline='') as sf:
  w=csv.writer(f,lineterminator='\n');w.writerow(['q','k','pair','order','variant','sample','wall_s','thread_cpu_s','process_cpu_s','residual_s'])
  sw=csv.writer(sf,lineterminator='\n');sw.writerow(['q','k','pair','order','variant','sample','stage','calls','wall_s','thread_cpu_s','wall_fraction'])
  for q in [32,128]:
   for k in [10,100]:
    data={v:[] for v in 'AB'};phases={v:defaultdict(list) for v in 'AB'};med={v:[] for v in 'AB'};cpu={v:[] for v in 'AB'}
    for pair in range(6):
     order='AB' if pair%2==0 else 'BA'
     for v in order:
      o,s,b,flags=observations(root/'runs'/f'timing_{q}_{k}_{pair}_{v}'/'stdout.log');assert sorted(o)==list(range(8))
      for i,(wall,thread,process) in o.items():
       assert len(s[i])>=10;residual=wall-sum(x[1] for x in s[i].values());assert residual>=-1e-6
       w.writerow([q,k,pair,order,v,i,wall,thread,process,residual]);data[v].append({'wall_ms':wall*1000,'thread_cpu_ms':thread*1000,'process_cpu_ms':process*1000,'thread_one_core_fraction':thread/wall,'residual_ms':residual*1000})
       for name,(calls,pw,pc) in s[i].items():sw.writerow([q,k,pair,order,v,i,name,calls,pw,pc,pw/wall]);phases[v][name].append({'wall_ms':pw*1000,'thread_cpu_ms':pc*1000,'wall_fraction':pw/wall})
      med[v].append(st.median(x[0] for x in o.values()));cpu[v].append(st.median(x[1] for x in o.values()))
    c={'timing':{v:{key:stats.dist([x[key] for x in data[v]]) for key in data[v][0]} for v in 'AB'},'stages':{v:{name:{key:stats.dist([x[key] for x in values]) for key in values[0]} for name,values in phases[v].items()} for v in 'AB'},'wall_ratio':paired(med['A'],med['B']),'cpu_ratio':paired(cpu['A'],cpu['B'])}
    c['wall_ratio']['sample_marginal_A_over_B']=c['timing']['A']['wall_ms']['median']/c['timing']['B']['wall_ms']['median'];c['wall_ratio']['pair_observation']='process median of eight retained queries'
    c['short_query_gate']=c['wall_ratio']['ci95'][0]>1.02 and c['wall_ratio']['B_process_wins']>=5;e['cases'][f'q{q}_k{k}']=c
 for q,k in [(32,10),(128,100)]:
  vals={v:[] for v in 'AB'};cpu={v:[] for v in 'AB'}
  for pair in range(3):
   for v in ('AB' if pair%2==0 else 'BA'):
    _,_,batch,_=observations(root/'runs'/f'sustained_{q}_{k}_{pair}_{v}'/'stdout.log');assert batch is not None;vals[v].append(batch[0]);cpu[v].append(batch[1])
  e['sustained'][f'q{q}_k{k}']={'wall_ratio':paired(vals['A'],vals['B']),'cpu_ratio':paired(cpu['A'],cpu['B']),'per_query_wall_ms':{v:stats.dist([x*1000/64 for x in vals[v]]) for v in 'AB'},'scope':'64 complete queries, includes preallocated CPU ID/distance-history copy, every output checked after timer'}
 with (out/'ncu_metrics.csv').open('w',newline='') as f,(out/'instruction_ledger.csv').open('w',newline='') as lf:
  w=csv.writer(f,lineterminator='\n');w.writerow(['variant','metric','unit','value']);lw=csv.writer(lf,lineterminator='\n');lw.writerow(['variant','function','opcode']+list(ncu.COUNTS))
  for v in 'AB':
   run=root/'runs'/f'ncu_{v}';units,rows=ncu.raw_metrics(run/'raw.csv');assert len(rows)==1;d=rows[0];assert d['Kernel Name'].startswith('dataProcessKnn') and units['gpu__time_duration.sum'] in ['ns','nsecond']
   e['ncu'][v]={'kernel':d['Kernel Name'],'grid':d['Grid Size'],'block':d['Block Size'],'source':[]}
   for key,value in d.items():
    if key.startswith(ncu.PREFIXES+('sass__',)) and key!='launch__function_pcs' and not key.endswith('_id'):w.writerow([v,key,units[key],value])
   for g in ncu.source_groups(run/'source.csv'):
    summary=ncu.summarize_group(g)
    for op,counts in summary.pop('opcodes').items():
     if any(counts.values()):lw.writerow([v,summary['function'],op]+[counts[key] for key in ncu.COUNTS])
    e['ncu'][v]['source'].append(summary)
   sw=sum(x['totals']['warp_instructions'] for x in e['ncu'][v]['source']);assert sw==int(d['sass__inst_executed_per_opcode'])
   hw=int(d['smsp__inst_executed.sum']);e['ncu'][v]['instruction_accounting']={'source_sum':sw,'sass_opcode_total':int(d['sass__inst_executed_per_opcode']),'hardware_total':hw,'hardware_minus_source':hw-sw,'relative_gap':(hw-sw)/hw,'scope':'SASS-patched source/opcode counts reconcile; hardware counter is separate. Nonzero hardware/source gaps remain unresolved, not normalized away.'}
 for directory in ['logs','gate_round1']:
  if not (root/directory).exists():continue
  for f in (root/directory).rglob('*'):
   if f.is_file():e['private_raw_files'][str(f.relative_to(root))]={'bytes':f.stat().st_size,'sha256':stats.sha(f)}
 e['fixtures']={f'n{n}':json.loads((root/f'fixtures/n{n}/manifest.json').read_text()) for n in [2000,65536]}
 e['decision']={'all_short_gates':all(c['short_query_gate'] for c in e['cases'].values()),'sustained_nonregression':all(c['wall_ratio']['ci95'][0]>=1 for c in e['sustained'].values()),'scope':'bounded exact SIFT kNN prototype, RP mode0, native tree and sort; not production or calibrated ANN'}
 (out/'EVIDENCE.json').write_text(json.dumps(e,indent=2)+'\n')
 for name,c in e['cases'].items():print(name,{v:c['timing'][v]['wall_ms']['median'] for v in 'AB'},c['wall_ratio']['paired_geomean_A_over_B'],c['wall_ratio']['ci95'])
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('out',type=Path);a=p.parse_args();analyze(a.root,a.out)
