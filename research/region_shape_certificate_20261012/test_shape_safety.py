#!/usr/bin/env python3
"""Runnable synthetic exact-rational dual proof and stored-shape regression fixtures."""
import math
from fractions import Fraction as F
import numpy as np
from shape_math import construct,all_bounds,ellipsoid_bound,pack,unpack,NAMES,ETA
from independent import reference_shapes,ball_lb,ellipsoid_lb,box_lb


def main():
    rng=np.random.default_rng(20261012)
    fixtures=[rng.normal(size=(4,10,8)),np.zeros((2,10,8)),
        np.array([[[1.,0.,0.,0.,0.,0.,0.,0.],[-1.,0.,0.,0.,0.,0.,0.,0.]]]),
        np.array([[[1e16]*8,[1.]*8,[-1e16]*8]])]
    tests=0
    for points in fixtures:
        meta,_=construct(points)
        for shape in NAMES:
            rebuilt=unpack(pack(meta,shape),shape)
            assert all(np.array_equal(meta[k],v) for k,v in rebuilt.items())
        for i,z in enumerate(points):
            ref=reference_shapes(z)
            for k,v in ref.items():assert np.array_equal(meta[k][i],v),k
        for q in [np.zeros(8),np.full(8,3.),rng.normal(size=8)]:
            bounds=all_bounds(meta,q);_,lam=ellipsoid_bound(meta['center'],meta['scale'],meta['factor'],q,True)
            for i,z in enumerate(points):
                assert bounds[1,i]==ball_lb(meta['center'][i],meta['radius'][i],q)
                assert bounds[2,i]==ball_lb(meta['minimax'][i],meta['minimax_radius'][i],q)
                assert bounds[3,i]==ellipsoid_lb(meta['center'][i],meta['scale'][i],meta['factor'][i],q)
                assert bounds[0,i]==box_lb(meta['low'][i],meta['high'][i],q)
                # Exact rational dual dominates the final squared LB after sqrt/margins.
                ll=F.from_float(float(lam[i]));dual=F(0)
                for j in range(8):
                    d=F.from_float(float(q[j]))-F.from_float(float(meta['center'][i,j]));s=F.from_float(float(meta['scale'][i,j]))
                    dual+=ll*d*d/(s*s+ll)
                r=F.from_float(float(meta['factor'][i]));dual-=ll*r*r
                assert F.from_float(float(bounds[3,i]))**2 <= max(F(0),dual)
                true_min=min(math.sqrt(sum((F.from_float(float(v))-F.from_float(float(qq)))**2 for v,qq in zip(row,q))) for row in z)
                assert np.all(bounds[:,i]<=true_min)
                tests+=1
    # Every prefix of [1e16,1,-1e16] must be a naive left fold, not Python 3.12 compensated sum.
    assert float(reference_shapes(fixtures[-1][0])['center'][0])==0.
    print('PASS: stored-center enclosure, zero spreads, ties, cancellation, scalar equality and exact-rational dual;',tests,'fixtures')


if __name__=='__main__':main()
