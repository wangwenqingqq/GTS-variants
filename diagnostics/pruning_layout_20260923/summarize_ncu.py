#!/usr/bin/env python3
"""Curate fixed first-query profiles, never use replay duration as public latency."""
import argparse,csv,json
from pathlib import Path
from verify_full import clean,sha
RAW=['sm__pipe_fp64_cycles_active.avg.pct_of_peak_sustained_elapsed','sm__pipe_fp64_cycles_active.max.pct_of_peak_sustained_elapsed','gpu__time_duration.sum','profiler__replayer_passes','device__attribute_multiprocessor_count','smsp__inst_executed.sum',
'l1tex__t_requests_pipe_lsu_mem_global_op_ld.sum','l1tex__t_sectors_pipe_lsu_mem_global_op_ld.sum',
'l1tex__t_sectors_pipe_lsu_mem_global_op_ld_lookup_hit.sum','l1tex__t_sectors_pipe_lsu_mem_global_op_ld_lookup_miss.sum',
'l1tex__t_sectors_pipe_lsu_mem_local_op_st.sum','l1tex__t_sectors_pipe_lsu_mem_local_op_ld.sum','lts__t_sectors_srcunit_tex_op_read.sum','lts__t_sectors_srcunit_tex_op_read_lookup_miss.sum','dram__bytes_op_read.sum',
'smsp__warps_eligible.avg.per_cycle_active','smsp__warps_active.avg.per_cycle_active',
'smsp__thread_inst_executed_per_inst_executed.ratio',
'smsp__average_warps_issue_stalled_wait_per_issue_active.ratio',
'smsp__average_warps_issue_stalled_long_scoreboard_per_issue_active.ratio',
'smsp__average_warps_issue_stalled_short_scoreboard_per_issue_active.ratio']
DETAILS={'Grid Size','Block Size','# SMs','Registers Per Thread','Duration','Compute (SM) Throughput','DRAM Throughput','Achieved Occupancy','No Eligible','Eligible Warps Per Scheduler','Issued Warp Per Scheduler','Avg. Active Threads Per Warp','Avg. Not Predicated Off Threads Per Warp','Executed Instructions'}
SECTIONS=['SpeedOfLight','LaunchStats','Occupancy','SchedulerStats','WarpStateStats','MemoryWorkloadAnalysis','MemoryWorkloadAnalysis_Tables','InstructionStats']
def read(p):return json.loads(p.read_text())
def main(root,out,continuation=None):
 result={'scope':'First query, two level kernels, 34-pass kernel replay, identical sections; no clock/cache control. Setup/cache state differs by layout. Diagnostic only, not hot-query latency or a 64-query average.','sections':SECTIONS,'order':'D/U/V in each dataset','datasets':{}}
 for name in ['GIST','Deep','Tloc']:
  common=root if name=='GIST' or not continuation else continuation
  data=common/'data'/name;o=read(data/'fixtures/oracle.json');gold=read(data/'fixtures'/f"expected_{o['radii']['normal']:g}.json");modes={}
  for m,marker in [('D','findNextRnn('),('U','findNextLayout<0>'),('V','findNextLayout<1>')]:
   path=data/'runs'/('ncu_'+m);r=read(path/'receipt.json');clean(r)
   assert (r['tool'],r['mode'],r['repeats'],r['warmup'],r['radius'])==('ncu',m,1,0,o['radii']['normal'])
   assert r['binary_sha256']==sha(common/'bin/graph_bench') and r['runner_sha256']==sha(common/'run_layout.py') and r['validation']['pass']
   rows=list(csv.DictReader((path/'result.csv').open()));assert [int(x['qid']) for x in rows]==o['queries']
   assert all([int(x['count']),x['ordered_hash']]==gold[x['qid']] for x in rows)
   cmd=read(path/'command.json');prefix=['ncu','--kernel-name-base','demangled','--kernel-name','regex:findNext(Rnn|Layout)','--launch-count','2','--clock-control','none','--cache-control','none','--export']
   assert cmd[:len(prefix)]==prefix and cmd[len(prefix)+1:len(prefix)+1+len(SECTIONS)*2]==[a for s in SECTIONS for a in ['--section',s]]
   raw=list(csv.reader((path/'metrics_raw.csv').open()));details=list(csv.DictReader((path/'metrics.csv').open()));assert len(raw)==4
   units=dict(zip(raw[0],raw[1]));kernels=[];totals={}
   for i,row in enumerate(raw[2:]):
    v=dict(zip(raw[0],row));assert v['ID']==str(i) and marker in v['Kernel Name']
    assert float(v['profiler__replayer_passes'])==34 and int(v['device__attribute_multiprocessor_count'])==188
    d={x['Metric Name']:{'value':x['Metric Value'],'unit':x['Metric Unit']} for x in details if x['ID']==str(i) and x['Metric Name'] in DETAILS}
    assert set(d)==DETAILS and d['Grid Size']['value']=='1' and d['Block Size']['value']=='512'
    metrics={k:{'value':v[k],'unit':units[k]} for k in RAW}
    kernels.append({'kernel':v['Kernel Name'],'details':d,'raw':metrics})
    for k in RAW:
     if k.endswith('.sum') and k!='gpu__time_duration.sum':totals[k]=totals.get(k,0)+float(v[k])
    unit=units['gpu__time_duration.sum'];assert unit in ['us','ms','nsecond','usecond','msecond']
    totals['replay_duration_us']=totals.get('replay_duration_us',0)+float(v['gpu__time_duration.sum'])*{'us':1,'ms':1000,'nsecond':.001,'usecond':1,'msecond':1000}[unit]
   modes[m]={'kernels':kernels,'sum_two_levels':totals,'metrics_sha256':sha(path/'metrics.csv'),'raw_metrics_sha256':sha(path/'metrics_raw.csv'),'receipt_sha256':sha(path/'receipt.json')}
  result['datasets'][name]=modes
 out.write_text(json.dumps(result,indent=2)+'\n')
 for n,v in result['datasets'].items():
  for m,x in v.items():print(n,m,x['sum_two_levels'])
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('output',type=Path);p.add_argument('--continuation',type=Path);a=p.parse_args();main(a.root,a.output,a.continuation)
