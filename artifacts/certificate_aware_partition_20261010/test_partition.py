#!/usr/bin/env python3
"""Dependency-light boundary tests; no dataset or GPU needed."""
import unittest
import numpy as np
from partition import make_partition, validate_partition, block_stats, queries, decide


class PartitionTests(unittest.TestCase):
    def test_duplicates_ties_and_query_independence(self):
        norms=np.zeros((4,1025));occ=np.arange(1025)[::-1];tree=np.arange(1025)[::-1]
        for kind in ('P0','P1','P2','P3'):
            perm,starts=make_partition(norms,occ,tree,kind)
            self.assertTrue(np.array_equal(occ[perm],np.arange(1025)))
            self.assertEqual(len(starts),5)
            self.assertEqual(int(np.diff(np.r_[starts,1025]).min()),1 if kind in ('P0','P1') else 128)
            again=make_partition(norms,occ,tree,kind)
            for x,y in zip((perm,starts),again):np.testing.assert_array_equal(x,y)
        with self.assertRaises(AssertionError):make_partition(norms,np.zeros(1025),tree,'P1')
        with self.assertRaises(AssertionError):make_partition(norms+np.nan,occ,tree,'P2')
        with self.assertRaises(AssertionError):validate_partition(np.array([0,0]),np.array([0]),2,256)

    def test_lexicographic_and_normalization(self):
        norms=np.array([[2,1,1,1,1],[0,2,1,1,1],[0,0,2,1,1],[0,0,0,2,1]],dtype=float)
        occ=np.array([9,8,7,6,5]);tree=np.arange(5)
        p,_=make_partition(norms,occ,tree,'P1',2)
        np.testing.assert_array_equal(p,[4,3,2,1,0])
        rng=np.random.default_rng(19);norms=rng.random((4,257));norms[2]=0
        a=make_partition(norms, np.arange(257),np.arange(257),'P3',16)
        b=make_partition(norms*np.array([8,2,16,.5])[:,None],np.arange(257),np.arange(257),'P3',16)
        for x,y in zip(a,b):np.testing.assert_array_equal(x,y)

    def test_capacity_aware_not_flattened(self):
        rng=np.random.default_rng(1);n=1001;x=rng.random((4,n));occ=np.arange(n)
        for kind in ('P2','P3'):
            p,s=make_partition(x,occ,occ,kind,240,True)
            sizes=validate_partition(p,s,n,240)
            self.assertEqual(len(s),5)
            self.assertEqual(int(sizes.max()-sizes.min()),1)
            self.assertLessEqual(int(sizes.max()),240)
            a,b=make_partition(x,occ,occ,kind)
            self.assertEqual(len(b),4)
            self.assertFalse(np.array_equal(p,a))

    def test_safe_filter_and_p2_subset(self):
        x=np.arange(1025,dtype=float);pivots=np.array([0,1024,500,250])
        scores=(x[None,:]-pivots[:,None])**2;qids=[0,128,512,1024];r=8.
        truth=(x[None,:]-x[qids,None])**2<=r*r
        for kind in ('P0','P1','P2','P3'):
            perm,starts=make_partition(np.sqrt(scores),np.arange(len(x)),np.arange(len(x)),kind)
            lo,hi,_,_,_,_=block_stats(scores,perm,starts,d=1)
            a=queries(scores,perm,starts,lo,hi,truth,qids,4,r,d=1)
            b=queries(scores,perm,starts,lo,hi,truth,qids,2,r,d=1)
            self.assertTrue(all(u['false_prune_blocks']==0 for u in a+b))
            self.assertTrue(all(u['surviving_blocks']<=v['surviving_blocks'] for u,v in zip(a,b)))

    def test_joint_gates_and_uncovered_interval(self):
        def fixture(a,b):
            return [dict(snapshot=n,strategy=s,partition=p,pivot_count=4,
                         statistics={'surviving_block_fraction':{'mean':v},'oracle_fraction':{'mean':.01}})
                    for n,v in [('initial',a),('first_rebuilt',b)] for s in ('S0','S1') for p in ('P0','P1','P2','P3')]
        for a,b,label,reason in [(.5,.5,'GO','joint_GO'),(.6,.49,'CONDITIONAL','specified_conditional_band'),
                                 (.66,.68,'CONDITIONAL','uncovered_interval'),(.71,.51,'NO-GO_GLOBAL_PIVOT','optimistic_per_snapshot_envelope_failed'),
                                 (.8,.49,'CONDITIONAL','uncovered_interval')]:
            d=decide(fixture(a,b));self.assertEqual(d['decision'],label);self.assertEqual(d['reason'],reason)
        f=fixture(.8,.8)
        for r in f:
            if (r['snapshot']=='initial' and r['strategy']=='S0') or (r['snapshot']=='first_rebuilt' and r['strategy']=='S1'):
                r['statistics']['surviving_block_fraction']['mean']=.4
        self.assertEqual(decide(f)['GO'],[])
        self.assertEqual(decide(f)['decision'],'CONDITIONAL')


if __name__=='__main__':unittest.main()
