#!/usr/bin/env python3
"""Runnable rational interval, nesting and preregistered classification checks."""
from fractions import Fraction
import numpy as np
from common import KS,gram_interval,row_sum_up,envelope,prefix_distances,level_decision,arithmetic_proof

def main():
    assert arithmetic_proof()['sum_below_RHO']
    rng=np.random.default_rng(20261012)
    for n,d in [(1,3),(4,7),(8,12)]:
        p=rng.standard_normal((n,d));lo,hi=gram_interval(p)
        for i in range(n):
            for j in range(n):
                exact=sum((Fraction.from_float(float(p[i,k]))*Fraction.from_float(float(p[j,k])) for k in range(d)),Fraction(0))
                assert Fraction.from_float(float(lo[i,j]))<=exact<=Fraction.from_float(float(hi[i,j]))
        a=np.maximum(np.abs(lo),np.abs(hi));s=row_sum_up(a)
        for i in range(n):assert Fraction.from_float(float(s[i]))>=sum(map(lambda v:Fraction.from_float(float(v)),a[i]),Fraction(0))
    z=rng.standard_normal((32,960));q=z[0];d=prefix_distances(z,q);lo,hi=envelope(d)
    assert np.all(np.diff(d,axis=1)>=0) and np.all(np.diff(lo,axis=1)>=0) and np.all(np.diff(hi,axis=1)>=0)
    for u in [0.,.1,1.,20.,50.]:
        masks=lo>u;assert np.all(~masks[:,:-1]|masks[:,1:])
    def make(n,w=20):return [dict(k=k,hard_safe_objects=n,hard_possible_objects=n,hard_truth_objects=600,hard_safe_counts=[w]+[(n-w)//5]*5,hard_possible_counts=[w]+[(n-w)//5]*5,hard_truth_counts=[100]*6) for k in KS]
    assert level_decision(make(300))['decision']=='PCA_DIRECTION_LIMITED'
    assert level_decision(make(480,40))['decision']=='CAPACITY_LIMITED'
    rows=make(300)
    for r in rows:
        if r['k']>=128:r.update(hard_safe_objects=450,hard_possible_objects=450,hard_safe_counts=[20,86,86,86,86,86],hard_possible_counts=[20,86,86,86,86,86])
    out=level_decision(rows);assert out['decision']=='PCA_DIRECTION_LIMITED' and out['predicates']['MODERATE_CAPACITY_REQUIREMENT']
    rows=make(300,50)
    for r in rows:
        if r['k']>=128:r.update(hard_safe_objects=450,hard_possible_objects=450,hard_safe_counts=[75]*6,hard_possible_counts=[75]*6)
    assert level_decision(rows)['decision']=='MODERATE_CAPACITY_REQUIREMENT'
    rows=make(300,50)
    for r in rows:
        if r['k'] in (256,512):r.update(hard_safe_objects=390,hard_possible_objects=390,hard_safe_counts=[65]*6,hard_possible_counts=[65]*6)
        if r['k']==960:r.update(hard_safe_objects=600,hard_possible_objects=600,hard_safe_counts=[100]*6,hard_possible_counts=[100]*6)
    assert level_decision(rows)['decision']=='HIGH_DIMENSION_INTRINSIC'
    print('PASS exact-rational Gram intervals, nonnegative nested distance/envelopes/masks, D1-D4 overlaps')

if __name__=='__main__':main()
