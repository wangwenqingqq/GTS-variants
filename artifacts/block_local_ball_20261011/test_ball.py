#!/usr/bin/env python3
"""Ten numerical/input categories plus frozen gate tests; no benchmark data."""
import argparse
import tempfile
import unittest
from decimal import Decimal,localcontext
from pathlib import Path
import numpy as np
from ball import library,pair_scores,centers,ball_keep,interval,radius_upper,raw,decision


def pairs(x,left,right):return pair_scores(LIB,np.ascontiguousarray(x,dtype=np.float32),np.array(left,dtype=np.int64),np.array(right,dtype=np.int64))


class BallTests(unittest.TestCase):
    def test_center_equals_query(self):
        s=pairs([[0],[1]],[0,0],[0,1]);cover=interval(s,1)[1].max()
        self.assertTrue(ball_keep(s[:1],np.array([cover]),1,0.)[0])

    def test_duplicate_vectors_and_occurrence_tie(self):
        scores=np.zeros((4,4));occ=np.array([9,3,8,2]);perm=np.array([1,3,0,2]);starts=np.array([0])
        c,mu=centers(scores,occ,perm,starts);self.assertEqual(c.tolist(),[3]);self.assertTrue(np.all(mu==0))
        self.assertTrue(np.all(pairs([[2],[2]],[0,1],[1,0])==0))

    def test_exact_cover_plus_range_boundary(self):
        s=pairs([[0],[-1],[1],[2]],[0,0,0,3],[0,1,2,0]);cover=interval(s[:3],1)[1].max()
        self.assertTrue(ball_keep(s[3:],np.array([cover]),1,1.)[0])

    def test_zero_radius_block(self):
        s=pairs([[0],[0],[1]],[0,0,2],[0,1,0]);cover=interval(s[:2],1)[1].max()
        self.assertFalse(ball_keep(s[2:],np.array([cover]),1,0.)[0])

    def test_zero_range_radius(self):
        x=np.array([[0],[1],[1]],dtype=np.float32);s=pairs(x,[0,0,0],[0,1,2]);cover=interval(s[:2],1)[1].max()
        self.assertTrue(ball_keep(s[2:],np.array([cover]),1,0.)[0])

    def test_extreme_finite_fp32_and_ordered_decimal(self):
        rng=np.random.default_rng(37)
        cases=[rng.normal(size=(3,d)).astype(np.float32) for d in (1,32,960,4096)]
        a=np.array([np.finfo(np.float32).max,-np.finfo(np.float32).max,np.nextafter(np.float32(0),np.float32(1)),0,1,-1],dtype=np.float32)
        cases.append(np.stack([a,-a,np.nextafter(a,np.float32(0))]))
        for x in cases:
            s=pairs(x,[0,0,1],[0,1,2]);lo,hi=interval(s,x.shape[1])
            with localcontext() as ctx:
                ctx.prec=220
                for i,(a,b) in enumerate([(0,0),(0,1),(1,2)]):
                    exact=sum((Decimal.from_float(float(u))-Decimal.from_float(float(v)))**2 for u,v in zip(x[a],x[b])).sqrt()
                    self.assertLessEqual(Decimal.from_float(float(lo[i])),exact);self.assertGreaterEqual(Decimal.from_float(float(hi[i])),exact)
                    ordered=0.
                    for u,v in zip(x[a],x[b]):delta=float(u)-float(v);ordered+=delta*delta
                    self.assertEqual(s[i].view(np.uint64),np.float64(ordered).view(np.uint64))

    def test_identical_vector_block_all_queries_safe(self):
        x=np.ones((8,3),dtype=np.float32);s=pairs(x,list(range(8)),[0]*8);cover=interval(s,3)[1].max()
        self.assertTrue(np.all(ball_keep(s,np.full(8,cover),3,0.)))

    def test_final_partial_block(self):
        n=258;perm=np.arange(n);starts=np.array([0,256]);occ=perm.copy();x=np.arange(n,dtype=np.float32)[:,None]
        scores=np.stack([(x[:,0]-p).astype(np.float64)**2 for p in (0,20,40,200)])
        c,_=centers(scores,occ,perm,starts);self.assertTrue(256<=c[1]<258)
        sizes=np.diff(np.r_[starts,n]);s=pairs(x,perm,np.repeat(c,sizes));cover=np.maximum.reduceat(interval(s,1)[1],starts)
        for q in (0,256,257):
            qs=pairs(x,[q,q],c);keep=ball_keep(qs,cover,1,0.);hit=np.maximum.reduceat((x[:,0]-x[q,0])**2<=0,starts)
            self.assertTrue(np.all(keep[hit]))

    def test_nextafter_boundary(self):
        above=np.nextafter(np.float32(2),np.float32(np.inf));below=np.nextafter(np.float32(2),np.float32(0))
        s=pairs([[0],[1],[above],[below]],[1,2,3],[0,0,0]);cover=interval(s[:1],1)[1]
        keep=ball_keep(s[1:],np.repeat(cover,2),1,1.)
        self.assertEqual(keep.tolist(),[False,True])

    def test_malformed_nan_inf_and_invalid_index(self):
        for bad in (np.nan,np.inf,-np.inf):
            with self.assertRaises(AssertionError):pairs([[bad],[0]],[0],[1])
        with self.assertRaises(AssertionError):pairs([[0]],[1],[0])
        with self.assertRaises(AssertionError):pairs([[0]],[-1],[0])
        with self.assertRaises(AssertionError):ball_keep(np.array([0.]),np.array([0.]),1,.1)
        with self.assertRaises(AssertionError):centers(np.zeros((4,2)),np.array([0,0]),np.array([0,1]),np.array([0]))
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'short';p.write_bytes(b'abc')
            with self.assertRaises(AssertionError):raw(p,'<f8',(1,))

    def test_gate_mean_tail_and_same_snapshot_conjunction(self):
        def run(m,t,g):
            s=[dict(snapshot=n,statistics={'local_ball_survival_fraction':{'mean':m[i],'p90':t[i]},
                 'global4_survival_fraction':{'mean':g[i]},'local_ball_false_prune':{'max':0}}) for i,n in enumerate(('initial','first_rebuilt'))]
            return decision(s)
        self.assertEqual(run([.5,.5],[.7,.7],[.68,.68])['decision'],'GO_LOCAL')
        self.assertFalse(run([.35,.35],[.71,.7],[.68,.68])['strong_GO'])
        self.assertEqual(run([.52,.52],[.7,.7],[.69,.68])['reason'],'specified_conditional_band')
        self.assertEqual(run([.6,.6],[.8,.8],[.69,.68])['reason'],'uncovered_interval')
        self.assertEqual(run([.66,.4],[.9,.7],[.69,.68])['decision'],'NO_GO_LOCAL_BALL')
        self.assertEqual(run([.66,.6],[.9,.7],[.9,.65])['decision'],'CONDITIONAL_LOCAL')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--library',type=Path,required=True);a,rest=p.parse_known_args()
    LIB=library(a.library);unittest.main(argv=['test_ball.py',*rest])
