#!/usr/bin/env python3
"""Numerical boundaries and admission tests; synthetic fixtures, not variants."""
import argparse
import sys
import unittest
from decimal import Decimal,localcontext
from fractions import Fraction
import numpy as np
from box import project,library,projection_interval,gram_proof,lower2,keep,threshold,decision,select_directions
LIB=None


def fixture(x,u=None):
    x=np.ascontiguousarray(x,dtype=np.float32)
    if u is None:u=np.eye(x.shape[1],4,dtype=np.float64)
    u=np.ascontiguousarray(u,dtype=np.float64);z,m=project(LIB,x,u);ql,qh=projection_interval(z,m,u)
    return x,u,z,m,ql,qh


def check_retention(x,u,radius):
    x,u,z,m,lo,hi=fixture(x,u);a2=gram_proof(u)['operator_norm_squared_upper']
    blo=lo.min(axis=0)[None,:];bhi=hi.max(axis=0)[None,:]
    for qi in range(len(x)):
        # A block contains its query and must always be retained.
        assert keep(lo[qi],hi[qi],blo,bhi,radius,x.shape[1],a2)[0]


class Tests(unittest.TestCase):
    def test_query_inside(self):
        z=np.zeros(4);lo=np.full((1,4),-1.);hi=np.ones((1,4));self.assertEqual(lower2(z,z,lo,hi)[0],0)
    def test_endpoint(self):
        z=np.ones(4);lo=np.zeros((1,4));hi=np.ones((1,4));self.assertTrue(keep(z,z,lo,hi,0.,4,1.)[0])
    def test_exact_radius_boundary(self):
        q=np.zeros(4);lo=np.array([[1.,0,0,0]]);self.assertTrue(keep(q,q,lo,lo,1.,4,1.)[0])
    def test_duplicates(self):check_retention(np.array([[.1,.2,.3,.4]]*4),None,0.)
    def test_zero_vector(self):check_retention(np.zeros((2,4)),None,0.)
    def test_constant_block(self):check_retention(np.full((5,12),.25),None,0.)
    def test_extreme_finite_fp32(self):
        m=np.finfo(np.float32).max;x=np.array([[m,-m,m,-m],[-m,m,-m,m]],dtype=np.float32);check_retention(x,None,0.);self.exact_dots(x,np.eye(4))
    def test_subnormal(self):
        t=np.nextafter(np.float32(0),np.float32(1));x=np.array([[t,-t,0,0],[0,0,0,0]],dtype=np.float32);u=np.eye(4);u[0,0]=np.nextafter(0.,1.);self.exact_dots(x,u);check_retention(x,u,0.)
    def test_cancellation(self):
        x=np.array([[1e20,1.,-1e20,2.,1.,-1.]],dtype=np.float32);u=np.full((6,4),.125);self.exact_dots(x,u)
    def test_nextafter_boundary(self):
        q=np.zeros(4);lo=np.array([[np.nextafter(np.float32(1),np.float32(2)),0,0,0]],dtype=np.float64)
        self.assertFalse(keep(q,q,lo,lo,1.,4,1.)[0]);lo[0,0]=np.nextafter(np.float32(1),np.float32(0));self.assertTrue(keep(q,q,lo,lo,1.,4,1.)[0])
    def test_final_partial_block(self):
        x=np.zeros((258,4),dtype=np.float32);x[-2:,0]=2;_,u,z,m,lo,hi=fixture(x)
        starts=np.array([0,256]);bl=np.minimum.reduceat(lo,starts);bh=np.maximum.reduceat(hi,starts)
        self.assertEqual(bl.shape,(2,4));self.assertFalse(keep(lo[0],hi[0],bl,bh,1.,4,1.)[1]);self.assertTrue(keep(lo[-1],hi[-1],bl,bh,0.,4,1.)[1])
    def test_malformed_nan_inf(self):
        for v in (np.nan,np.inf,-np.inf):
            with self.assertRaises(AssertionError):fixture([[v,0,0,0]])
            with self.assertRaises(AssertionError):fixture(np.zeros((2,4)),np.full((4,4),v))
        with self.assertRaises(AssertionError):project(LIB,np.zeros((0,4),np.float32),np.eye(4))
        with self.assertRaises(AssertionError):fixture(np.zeros((2,4)),np.full((4,4),2.))
        with self.assertRaises(AssertionError):lower2(np.zeros(4),np.zeros(4),np.ones((1,4)),np.zeros((1,4)))
        with self.assertRaises(AssertionError):threshold(.1,4,1.)
    def test_ordered_vector_scalar_and_exact_envelopes(self):
        rng=np.random.default_rng(20261011)
        for d in (4,32,960,4096):
            x=rng.standard_normal((3,d)).astype(np.float32);u=np.ascontiguousarray(rng.standard_normal((d,4))/d)
            self.exact_dots(x,u)
            a,m=project(LIB,x,u);b,n=project(LIB,x,u,True)
            np.testing.assert_array_equal(a.view(np.uint64),b.view(np.uint64));np.testing.assert_array_equal(m,n)
    def test_represented_gram_spectral_repair(self):
        u=np.zeros((5,4));u[0,0]=.6;u[1,0]=.8;u[2,1]=u[3,2]=u[4,3]=1.
        proof=gram_proof(u);a2=proof['operator_norm_squared_upper'];self.assertGreater(a2,1.)
        exact=Fraction(proof['operator_norm_squared_exact_row_sum']);self.assertGreaterEqual(Fraction.from_float(a2),exact)
    def test_PCA_sign_and_degeneracy(self):
        c=np.diag([5.,4.,3.,2.,1.]);v,u,p=select_directions(c);self.assertTrue(np.all(u[p['sign_coordinates'],np.arange(4)]>0))
        with self.assertRaises(AssertionError):select_directions(np.eye(5))
    def test_lower_bound_not_above_real_distance(self):
        rng=np.random.default_rng(23);x=rng.standard_normal((8,12)).astype(np.float32);u=np.ascontiguousarray(np.linalg.qr(rng.standard_normal((12,4)))[0]);x,u,z,m,lo,hi=fixture(x,u)
        a2=gram_proof(u)['operator_norm_squared_upper']
        for i in range(8):
            for j in range(8):
                lb=lower2(lo[i],hi[i],lo[j:j+1],hi[j:j+1])[0]
                exact=sum((Fraction.from_float(float(a))-Fraction.from_float(float(b)))**2 for a,b in zip(x[i],x[j]))
                self.assertLessEqual(Fraction.from_float(float(lb))/Fraction.from_float(a2),exact)
    def test_gate_joint_gain_tail_and_gray(self):
        def gate(m,t,g):
            ss=[dict(snapshot=n,statistics={'projected_box_false_prune':{'max':0},'projected_box_survival_fraction':{'mean':a,'p90':b},'global4_survival_fraction':{'mean':c}}) for n,a,b,c in zip(('initial','first_rebuilt'),m,t,g)]
            return decision(ss)
        self.assertTrue(gate([.3,.3],[.5,.5],[.7,.7])['strong_GO'])
        self.assertFalse(gate([.3,.3],[.8,.5],[.7,.7])['strong_GO'])
        self.assertEqual(gate([.4,.4],[.6,.6],[.5,.5])['reason'],'uncovered_interval')
        self.assertFalse(gate([.4,.4],[.6,.6],[.5,.5])['K8_admissible'])
        self.assertTrue(gate([.51,.52],[.9,.9],[.7,.7])['K8_admissible'])
        self.assertEqual(gate([.66,.5],[.9,.9],[.7,.7])['decision'],'NO_GO_PROJECTED_BOX')
        self.assertEqual(gate([.7,.5],[.9,.9],[.95,.52])['reason'],'uncovered_interval')
    def exact_dots(self,x,u):
        x,u,z,m,lo,hi=fixture(x,u)
        with localcontext() as c:
            c.prec=1200
            for i in range(len(x)):
                for j in range(4):
                    exact=sum((Decimal.from_float(float(x[i,k]))*Decimal.from_float(float(u[k,j])) for k in range(x.shape[1])),Decimal(0))
                    self.assertLessEqual(Decimal.from_float(float(lo[i,j])),exact);self.assertGreaterEqual(Decimal.from_float(float(hi[i,j])),exact)


if __name__=='__main__':
    p=argparse.ArgumentParser(add_help=False);p.add_argument('--library',required=True);a,rest=p.parse_known_args();LIB=library(a.library);unittest.main(argv=[sys.argv[0]]+rest)
