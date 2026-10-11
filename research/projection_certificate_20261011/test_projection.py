#!/usr/bin/env python3
"""Small runnable regression for contraction, signed intervals, nesting and gates."""
import unittest
import numpy as np
from projection_math import certify,endpoints,prefix_bounds,serialize,decision,ETA

class Check(unittest.TestCase):
    def test_contraction(self):
        p=np.zeros((8,960));p[np.arange(8),np.arange(8)]=1
        p,c=certify(p);self.assertTrue(c['certified_contractive']);self.assertLess(c['bound_display'],1)
    def test_signed_cover(self):
        x=np.array([[-4.,-1.,0.,1.,2.,3.,4.,5.]])
        lo,hi=endpoints(x,x)
        self.assertTrue(np.all(lo.astype(float)<=x-ETA));self.assertTrue(np.all(hi.astype(float)>=x+ETA))
        self.assertLess(lo[0,0],0)
        self.assertEqual(len(serialize(lo,hi,1)),16);self.assertEqual(len(serialize(lo,hi,8)),64)
    def test_joint_and_nesting(self):
        low=np.array([[1.,1.,0.,0.,0.,0.,0.,0.]],dtype=np.float32);high=low+1
        b=prefix_bounds(low,high,np.zeros(8));self.assertGreater(b[2][0],1.4)
        self.assertTrue(all(np.all(b[x]<=b[y]) for x,y in [(1,2),(2,4),(4,8)]))
        self.assertEqual(b[2][0],b[8][0])
    def test_decision_boundaries(self):
        rows=[dict(family='PCA',level=l,k=8,oracle_gap_coverage=.29,incremental_G0_pruning=.1,aligned_bytes_per_region=64) for l in [3,4,5]]
        self.assertEqual(decision(rows),'LINEAR_PROJECTION_CERTIFICATE_KILLED')
        rows[0]['oracle_gap_coverage']=.3;self.assertEqual(decision(rows),'INTERMEDIATE_NEEDS_DIRECTION_TEST')
        rows[0].update(oracle_gap_coverage=.5,incremental_G0_pruning=.3)
        self.assertEqual(decision(rows),'PROJECTION_CERTIFICATE_FEASIBLE')
        rows[0].update(oracle_gap_coverage=.1);rows[1]['oracle_gap_coverage']=.1;rows[2]['oracle_gap_coverage']=.5
        self.assertEqual(decision(rows),'LEAF_ONLY')
if __name__=='__main__':unittest.main()
