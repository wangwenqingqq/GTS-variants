#!/usr/bin/env python3
"""Runnable outward rounding, directed bound and decision boundary checks."""
import math
from fractions import Fraction
import numpy as np
from aabb_math import *

def main():
    values=np.array([0.,-0.,1.,-1.,1+2**-25,-1-2**-25,1e-9,-1e-9,2.])
    assert np.all(outward32(values,-1).astype(float)<=values)
    assert np.all(outward32(values,1).astype(float)>=values)
    rng=np.random.default_rng(12);z=rng.uniform(-2,2,(17,10,128));q=rng.uniform(-4,4,128);lo,hi=endpoints(z)
    lb=bounds(lo,hi,q);ref=np.array([scalar_bounds(l,h,q) for l,h in zip(lo,hi)]).T;assert np.array_equal(lb,ref)
    for i,k in enumerate(KS):assert np.all(lb[i]<=np.sqrt(((z[:,:,:k]-q[:k])**2).sum(axis=2)).min(axis=1))
    assert np.all(lb[1:]>=lb[:-1]) and np.all(bounds(lo,hi,np.zeros(128))>=0)
    # Binary-rational check for the one-dimensional directed primitive.
    for i in range(17):
        j=0;ql=math.nextafter(float(q[j])-ETA,-math.inf);qh=math.nextafter(float(q[j])+ETA,math.inf)
        gap=max(Fraction(0),Fraction(float(lo[i,j]))-Fraction(qh),Fraction(ql)-Fraction(float(hi[i,j])))
        g=max(0.,math.nextafter(float(lo[i,j])-qh,-math.inf),math.nextafter(ql-float(hi[i,j]),-math.inf))
        assert Fraction(g)<=gap and Fraction(max(0.,math.nextafter(g*g,-math.inf)))<=gap*gap
    rows=[dict(k=k,level=l,hard_aabb_objects=70,hard_point_objects=100,hard_truth_objects=100,canary_aabb_objects=50,canary_point_objects=100) for k in KS for l in SIZES]
    assert stage_a(rows)['normal_promotion'];rows[4]['canary_aabb_objects']=49;assert not stage_a(rows)['stage_B_admitted']
    rows[4]['hard_aabb_objects']=49;rows[7]['hard_aabb_objects']=59;assert stage_a(rows)['kill_predicate']
    rows[4]['hard_aabb_objects']=50;assert stage_a(rows)['decision']=='INSUFFICIENT_EVIDENCE'
    assert ratio(0,0) is None and ratio(0,1)==0
    for bad in [np.nan,np.inf]:
        try:outward32(np.array([bad]),-1)
        except AssertionError:pass
        else:raise AssertionError('nonfinite accepted')
    print('Synthetic directed arithmetic + exact threshold tests PASS')

if __name__=='__main__':main()
