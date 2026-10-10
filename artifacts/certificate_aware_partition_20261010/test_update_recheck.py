#!/usr/bin/env python3
import unittest
import numpy as np
from partition import make_partition
from update_recheck import VariableOwnership


class UpdateTests(unittest.TestCase):
    def test_variable_boundaries_holes_duplicate_and_full_state(self):
        n=1001;occ=np.arange(n);line=occ.copy();x=np.arange(n,dtype=float)
        scores=(x[None,:]-np.array([0,1000,250,750])[:,None])**2
        perm,starts=make_partition(np.sqrt(scores),occ,occ,'P2',240,True)
        model=VariableOwnership(occ,perm,starts,scores,n+1)
        self.assertEqual(len(starts),5)
        qids=[0,400];refs=(x[None,:]-x[qids,None])**2;r=1.
        before=model.query(refs,qids,r);model.check_full(occ,line,line,refs,qids,r,before)
        b=int(model.owner[400]);slot=int(model.slot[400])
        model.apply(dict(action='delete',occurrence=400,step=0),400)
        self.assertEqual(model.slots(b)[slot],-1)
        model.apply(dict(action='insert',occurrence=n,step=1),400)
        target=np.r_[occ[occ!=400],n];target_line=np.r_[line[line!=400],400]
        after=model.query(refs,qids,r);model.check_full(target,target_line,line,refs,qids,r,after)
        self.assertEqual(len(model.moved),0);self.assertEqual(model.splits,0)
        bad=target_line.copy();bad[-1]=401
        with self.assertRaises(AssertionError):model.check_full(target,bad,line,refs,qids,r,after)

    def test_full_block_local_split(self):
        n=240;occ=np.arange(n);scores=np.zeros((4,n));perm=occ.copy();starts=np.array([0])
        model=VariableOwnership(occ,perm,starts,scores,260)
        for i in range(n,257):model.apply(dict(action='insert',occurrence=i,step=i),0)
        self.assertEqual(model.splits,1);self.assertEqual(model.nb,2)
        self.assertEqual(int(model.count[:2].sum()),257)
        self.assertEqual(len(model.moved),112)
        ids=np.concatenate([model.slots(b)[model.slots(b)>=0] for b in range(2)])
        np.testing.assert_array_equal(np.sort(ids),np.arange(257))


if __name__=='__main__':unittest.main()
