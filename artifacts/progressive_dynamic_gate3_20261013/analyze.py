"""Predeclared process-level Gate3 estimators and fail-closed decision priority."""
import math
import numpy as np
def summary(pairs):
    assert len(pairs) in (3,6)
    a=np.array([[p['D0'],p['D1']] for p in pairs],float)
    assert a.shape==(len(pairs),2) and np.isfinite(a).all() and (a>0).all()
    logs=np.log(a[:,1]/a[:,0]);rng=np.random.default_rng(2026101303)
    boot=np.exp(logs[rng.integers(0,len(pairs),(20000,len(pairs)))].mean(axis=1))
    return dict(modes={m:dict(process_totals=a[:,i].tolist(),p10=float(np.quantile(a[:,i],.1)),median=float(np.median(a[:,i])),p90=float(np.quantile(a[:,i],.9))) for i,m in enumerate(('D0','D1'))},ratio=float(np.median(a[:,1])/np.median(a[:,0])),paired_geometric_ratio=float(np.exp(logs.mean())),paired_CI95=np.quantile(boot,[.025,.975]).tolist(),wins=int((a[:,1]<a[:,0]).sum()),pairs=len(pairs),order_strata={order:dict(pairs=len(idx),ratio=float(np.exp(logs[idx].mean())),wins=int((a[idx,1]<a[idx,0]).sum())) for order,idx in [('forward',list(range(0,len(pairs),2))),('reverse',list(range(1,len(pairs),2)))]},bootstrap=dict(seed=2026101303,repeats=20000,unit='matched fresh processes',method='percentile log ratio'))
def classify(trace,range_ratio,insert,delete,upper,wins,quality=True):
    if not quality:return 'NO_GO_DYNAMIC_PROGRESSIVE'
    if not all(math.isfinite(x) and x>0 for x in (trace,range_ratio,insert,delete,upper)) or not isinstance(wins,int) or not 0<=wins<=6:return 'UNCLASSIFIED'
    if max(insert,delete)>1.5:return 'UPDATE_REGRESSION'
    if trace<=.85 and range_ratio<=.60 and upper<.92 and wins>=5:return 'GO_DYNAMIC_PROGRESSIVE'
    if trace>=.95 or range_ratio>.75:return 'NO_GO_DYNAMIC_PROGRESSIVE'
    return 'UNCLASSIFIED'
def gate_b(range_ratio,insert,delete,quality=True):
    return bool(quality and all(math.isfinite(x) and x>0 for x in (range_ratio,insert,delete)) and range_ratio<=.65 and max(insert,delete)<=1.25)
