"""Frozen Gate2 decision and process-paired statistics; no profiler timing promotion."""
import math
import numpy as np
def classify(dram,ratio,ci_upper,control_share,quality=True):
    values=(dram,ratio,ci_upper,control_share)
    if not quality or not all(math.isfinite(v) for v in values) or min(dram,ratio,ci_upper)<0 or not 0<=control_share<=1:
        return 'UNCLASSIFIED'
    if dram<=1.60e9 and ratio<=.80 and ci_upper<.90:return 'GO_PROGRESSIVE_GPU'
    if dram>2.20e9 or (ratio>=1 and control_share<=.20):return 'NO_GO_PROGRESSIVE_GPU'
    if dram<=1.60e9 and ratio>.90:return 'BYTE_SAVING_BUT_CONTROL_BOUND'
    return 'UNCLASSIFIED'
def summarize(processes):
    # One row per matched round; aggregate each process before uncertainty.
    assert len(processes)==6
    a=np.asarray([[r[m] for m in ('B0','B1','P1')] for r in processes],dtype=float)
    assert a.shape==(6,3) and np.isfinite(a).all() and (a>0).all()
    distributions={m:dict(p10=float(np.quantile(a[:,i],.1)),median=float(np.median(a[:,i])),p90=float(np.quantile(a[:,i],.9)),process_means=a[:,i].tolist()) for i,m in enumerate(('B0','B1','P1'))}
    logs=np.log(a[:,2]/a[:,1]);rng=np.random.default_rng(2026101302)
    boot=np.exp(logs[rng.integers(0,6,size=(20000,6))].mean(axis=1))
    return dict(modes=distributions,latency_ratio=float(np.median(a[:,2])/np.median(a[:,1])),paired_geometric_ratio=float(np.exp(logs.mean())),paired_95_CI=np.quantile(boot,[.025,.975]).tolist(),paired_ratios=np.exp(logs).tolist(),wins=int(np.count_nonzero(a[:,2]<a[:,1])),order_strata={name:dict(paired_geometric_ratio=float(np.exp(logs[idx].mean())),wins=int(np.count_nonzero(a[idx,2]<a[idx,1])),pairs=3) for name,idx in [('forward',[0,2,4]),('reverse',[1,3,5])]},bootstrap=dict(repeats=20000,seed=2026101302,unit='matched process rounds',method='percentile log-ratio resampling'))
