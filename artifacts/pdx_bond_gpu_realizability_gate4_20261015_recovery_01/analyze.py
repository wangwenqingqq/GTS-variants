"""Confirmed Gate4 priority and process-level estimator; no profiler latency promotion."""
if not __debug__:
    raise SystemExit('Optimized Python disables mandatory checks; run without -O/PYTHONOPTIMIZE.')
import math
import numpy as np


def summarize(pairs):
    assert len(pairs)==6
    x=np.asarray([[p[k] for k in ('keeper','candidate')] for p in pairs],dtype=float)
    assert x.shape==(6,2) and np.isfinite(x).all() and (x>0).all()
    logs=np.log(x[:,1]/x[:,0]);rng=np.random.default_rng(2026101302)
    bootstrap=np.exp(logs[rng.integers(0,6,size=(20000,6))].mean(axis=1))
    distributions={name:{'p10':float(np.quantile(x[:,j],.1)),'median':float(np.median(x[:,j])),
        'p90':float(np.quantile(x[:,j],.9)),'arithmetic_mean':float(np.mean(x[:,j])),
        'process_means':x[:,j].tolist()} for j,name in enumerate(('keeper','candidate'))}
    return {'modes':distributions,'latency_ratio':float(np.median(x[:,1])/np.median(x[:,0])),
        'paired_geometric_ratio':float(np.exp(logs.mean())),
        'paired_ratios':np.exp(logs).tolist(),'paired_95_CI':np.quantile(bootstrap,[.025,.975]).tolist(),
        'wins':int(np.count_nonzero(x[:,1]<x[:,0])),
        'arithmetic_mean_ratio':float(np.mean(x[:,1])/np.mean(x[:,0])),
        'mean_paired_ratio':float(np.exp(logs).mean()),
        'order_strata':{name:{'paired_geometric_ratio':float(np.exp(logs[index].mean())),
            'wins':int(np.count_nonzero(x[index,1]<x[index,0])),'pairs':3}
            for name,index in [('forward',[0,2,4]),('reverse',[1,3,5])]},
        'bootstrap':{'repeats':20000,'seed':2026101302,'unit':'matched process rounds','method':'percentile log-ratio resampling'}}


def classify(source_bytes,latency_ratio,dram_ratio,wins,ci_upper,quality=True):
    if not quality:return 'BASELINE_INVALID'
    assert all(math.isfinite(v) and v>=0 for v in (source_bytes,latency_ratio,dram_ratio,ci_upper))
    assert isinstance(wins,int) and 0<=wins<=6
    if latency_ratio<=.90 and dram_ratio<=.90 and wins>=5 and ci_upper<.97:
        return 'PRIOR_ART_WINS'
    if source_bytes<=800000000 and (dram_ratio>=.95 or latency_ratio>=.95):
        return 'LOGICAL_WIN_PHYSICAL_FAIL'
    if latency_ratio>=1 and dram_ratio>=1:return 'PRIOR_ART_LOSES'
    return 'UNCLASSIFIED'


def check():
    assert classify(711680776,.80,.80,6,.81)=='PRIOR_ART_WINS'
    assert classify(711680776,1.2,1.2,0,1.3)=='LOGICAL_WIN_PHYSICAL_FAIL'
    assert classify(900000000,1.2,1.2,0,1.3)=='PRIOR_ART_LOSES'
    assert classify(711680776,.93,.93,6,.94)=='UNCLASSIFIED'
    assert classify(711680776,.90,.90,5,.97)=='UNCLASSIFIED'
    assert classify(711680776,.90,.90,5,.96999)=='PRIOR_ART_WINS'
    assert classify(711680776,.80,.80,6,.81,False)=='BASELINE_INVALID'
    sample=[{'keeper':float(k),'candidate':float(k)*.75} for k in range(1,7)]
    s=summarize(sample);assert s['wins']==6 and s['latency_ratio']==.75
    assert all(abs(v-.75)<1e-14 for v in s['paired_95_CI'])
    print('PASS:priority,strict CI,gray zones,and paired process estimator')


if __name__=='__main__':check()
