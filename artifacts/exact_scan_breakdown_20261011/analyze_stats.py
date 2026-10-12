#!/usr/bin/env python3
"""Offline process distributions; no GPU launch or radius selection."""
import argparse,csv,json,math
from pathlib import Path
import numpy as np

def read(p):return json.loads(Path(p).read_text())
def table(p):
 with Path(p).open() as f:return list(csv.DictReader(f))
def summary(x):
 x=np.array(x,float);assert len(x)==6 and np.isfinite(x).all()
 return dict(process_values=x.tolist(),p10=float(np.quantile(x,.1)),median=float(np.median(x)),p90=float(np.quantile(x,.9)),mean=float(x.mean()))
def paired(a,b):
 a=np.array(a,float);b=np.array(b,float);assert len(a)==len(b)==6 and (a>0).all() and (b>0).all()
 logs=np.log(a/b);rng=np.random.default_rng(2026101111);idx=rng.integers(0,6,(20000,6));boot=np.exp(logs[idx].mean(axis=1))
 return dict(marginal_median_ratio=float(np.median(a)/np.median(b)),paired_geometric_ratio=float(np.exp(logs.mean())),paired_ratio_ci95=np.quantile(boot,[.025,.975]).tolist(),process_ratios=(a/b).tolist(),process_wins=int(np.count_nonzero(a<b)),forward_geometric=float(np.exp(logs[::2].mean())),reverse_geometric=float(np.exp(logs[1::2].mean())),bootstrap='paired process log-mean,20000 draws,seed2026101111; diagnostic ratio, no promotion')
def analyze(w):
 out=dict(scope='unprofiled Host-ready-to-complete-ACK query intervals; median of six process mean queries',keeper={},modes={},scaling={},comparisons={})
 for stage in ('keeper','primary','scaling'):
  result=read(w/stage/'RESULTS.json');assert result['complete'];groups={}
  for j in result['rows']:
   c=read(w/stage/(j['label']+'.checked.json'));key='keeper' if stage=='keeper' else j['mode'] if stage=='primary' else j['label'].split('_',1)[1]
   x=dict(round=j['round'],label=j['label'],N=j['N'],D=j['D'],radius=j['radius'],mean_query_ms=c['process_mean_query_ms'],pass_ms=c['process_pass_ms'])
   if j['mode']=='COPY':x['copy_event_ms']=float(np.mean([float(r['p0']) for r in c['rows'][8:]]))
   else:x['mean_hits']=float(np.mean([r['reference_hit_count'] for r in c['quality'][8:]]))
   groups.setdefault(key,[]).append(x)
  dest=out['keeper'] if stage=='keeper' else out['modes'] if stage=='primary' else out['scaling']
  for key,rows in groups.items():
   rows.sort(key=lambda x:x['round']);dest[key]=dict(rows=rows,query_ms=summary([r['mean_query_ms'] for r in rows]),pass_ms=summary([r['pass_ms'] for r in rows]))
   if key=='bandwidth':dest[key]['copy_event_ms']=summary([r['copy_event_ms'] for r in rows])
 m=out['modes'];values=lambda k:[r['mean_query_ms'] for r in m[k]['rows']]
 for a,b in [('READ_ONLY','FULL_OUTPUT'),('DISTANCE_ONLY','FULL_OUTPUT'),('THRESHOLD_COUNT','FULL_OUTPUT'),('DISTANCE_ONLY','READ_ONLY'),('THRESHOLD_COUNT','DISTANCE_ONLY'),('FULL_OUTPUT','THRESHOLD_COUNT')]:out['comparisons'][a+'/'+b]=paired(values(a),values(b))
 sc=out['scaling'];out['comparisons']['high/low']=paired([r['mean_query_ms'] for r in sc['R_high']['rows']],[r['mean_query_ms'] for r in sc['R_low']['rows']])
 R=m['READ_ONLY']['query_ms']['median'];D=m['DISTANCE_ONLY']['query_ms']['median'];C=m['THRESHOLD_COUNT']['query_ms']['median'];F=m['FULL_OUTPUT']['query_ms']['median']
 copy=out['scaling']['bandwidth']['copy_event_ms']['median'];out['static_fractions']=dict(read_over_full=R/F,distance_minus_read_over_full=(D-R)/F,full_minus_count_over_full=(F-C)/F)
 out['streaming_calibration']=dict(READ_ONLY_logical_payload_GBs=3.84/R*1000,D2D_combined_read_write_event_GBs=7.68/copy*1000,reachable_reference_GBs=max(3.84/R*1000,7.68/copy*1000),scope='logical streaming controls, not counter traffic or universal hardware maximum')
 return out
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('work',type=Path);p.add_argument('output',type=Path);a=p.parse_args();v=analyze(a.work);assert not a.output.exists();a.output.write_text(json.dumps(v,indent=2)+'\n')
