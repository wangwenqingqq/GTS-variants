#!/usr/bin/env python3
"""Operation versus continuous-trace denominators, including client ACK and release."""
import argparse,json
from pathlib import Path
import numpy as np
from analyze_stats import summary
read=lambda p:json.loads(Path(p).read_text())
def analyze(w):
 names={0:'insert',1:'delete',2:'range',3:'knn'};rows=[]
 for i in range(1,7):
  c=read(w/'dynamic'/f'dynamic_r{i}.checked.json');m=c['meta'];ops=c['operations'];assert len(ops)==336
  group={}
  for flag,name in names.items():
   v=[float(r['ack_ms']) for r in ops if int(r['flag'])==flag];assert len(v)==(40 if flag<2 else 128)
   group[name]=dict(count=len(v),sum_ms=sum(v),p10=float(np.quantile(v,.1)),p50=float(np.median(v)),p90=float(np.quantile(v,.9)),p95=float(np.quantile(v,.95)),p99=float(np.quantile(v,.99)))
  total=sum(g['sum_ms'] for g in group.values());update=group['insert']['sum_ms']+group['delete']['sum_ms'];continuous=float(m['trace_ms']);assert continuous>=total
  rows.append(dict(round=i,groups=group,ACK_sum_ms=total,continuous_trace_ms=continuous,release_ms=m['release_ms'],setup_ms=m['setup_ms'],cpu_user_s=m['cpu_user_s'],cpu_system_s=m['cpu_system_s'],CPU_core_equivalent=(m['cpu_user_s']+m['cpu_system_s'])/(continuous/1000),update_fraction_of_continuous=update/continuous,update_fraction_of_ACK=update/total,query_ACK_ms=group['range']['sum_ms']+group['knn']['sum_ms'],update_ACK_ms=update,inserted_H2D_bytes=m['inserted_H2D_bytes'],swap_D2D_bytes=m['swap_D2D_bytes'],swap_deletes=m['swap_deletes'],rebuilds=m['rebuilds']))
 return dict(scope='unchanged qualified E_ADAPT,336 events, six fresh processes; continuous trace includes service release, setup/context/warmup/disk outside',rows=rows,continuous_trace_ms=summary([r['continuous_trace_ms'] for r in rows]),ACK_sum_ms=summary([r['ACK_sum_ms'] for r in rows]),update_fraction_of_continuous=summary([r['update_fraction_of_continuous'] for r in rows]),CPU_core_equivalent=summary([r['CPU_core_equivalent'] for r in rows]),operations={name:{key:summary([r['groups'][name][key] for r in rows]) for key in ('sum_ms','p10','p50','p90','p95','p99')} for name in names.values()},UPDATE_BOUND=all(r['update_fraction_of_continuous']>.5 and r['update_ACK_ms']>r['query_ACK_ms'] for r in rows),scope_correction='previous0.532743/0.293380 ms values are median40-operation ACK sums, not per-operation latency; old event p50 .013173/.006351 ms',source_scope_note='CPU time is rusage for measured trace+release; NSYS GPU-active fraction is diagnostic operation scopes, excludes teardown; CPU sampled stacks unavailable, no independent CPU-compute attribution')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('work',type=Path);p.add_argument('output',type=Path);a=p.parse_args();assert not a.output.exists();a.output.write_text(json.dumps(analyze(a.work),indent=2)+'\n')
