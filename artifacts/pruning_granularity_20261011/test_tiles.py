#!/usr/bin/env python3
"""Small synthetic rule/anchor/boundary/gate tests, not extra direction variants."""
import unittest
from decimal import Decimal,localcontext
import numpy as np
from tiles import SIZES,SNAPS,make_tiles,bounds,evaluate,interval,radius_upper,rejected,independent_partition,decide,costs


class Tests(unittest.TestCase):
    def test_partition_stable_and512_extension(self):
        rng=np.random.default_rng(20261011);norms=rng.random((4,2049));occ=np.arange(2049)[::-1]
        for t in SIZES:
            p,s=make_tiles(norms,occ,t);q,z=independent_partition(norms,occ,occ,'P2',t)
            np.testing.assert_array_equal(p,q);np.testing.assert_array_equal(s,z)
            self.assertEqual(len(np.unique(p)),2049);self.assertLessEqual(np.diff(np.r_[s,2049]).max(),t)
    def test_tie_duplicates_constant_and_partial(self):
        x=np.zeros((4,1025));occ=np.arange(1025)[::-1]
        for t in SIZES:
            p,s=make_tiles(x,occ,t);np.testing.assert_array_equal(occ[p],np.arange(1025));self.assertLessEqual(np.diff(np.r_[s,1025]).max(),t)
        p,s=make_tiles(x,occ,32);self.assertEqual(len(s),33)
    def test_nested_and_surviving_objects(self):
        x=np.arange(1025,dtype=float);scores=(x[None,:]-np.array([0,1024,500,250])[:,None])**2;qids=[0,128,512,1024];truth=(x[None,:]-x[qids,None])**2<=64
        before=None
        for t in SIZES:
            p,s=make_tiles(np.sqrt(scores),np.arange(len(x)),t);lo,hi=bounds(scores,p,s,1);rr=evaluate('initial',t,scores,p,s,lo,hi,truth,qids,8.,1)
            self.assertTrue(all(r['false_prune_tiles']==0 for r in rr))
            if before:self.assertTrue(all(a['surviving_objects']>=b['surviving_objects'] for a,b in zip(before,rr)))
            before=rr
    def test_decimal_norm_envelope_extreme_subnormal(self):
        values=np.array([0,np.nextafter(np.float32(0),np.float32(1)),np.finfo(np.float32).max,-np.finfo(np.float32).max,1,-1],dtype=np.float32)
        with localcontext() as c:
            c.prec=220
            for x in (values,np.nextafter(values,np.float32(0))):
                s=0.;exact=Decimal(0)
                for a,b in zip(x,values):
                    delta=float(a)-float(b);s+=delta*delta;exact+=(Decimal.from_float(float(a))-Decimal.from_float(float(b)))**2
                lo,hi=interval(np.array([s]),len(x));self.assertLessEqual(Decimal.from_float(float(lo[0])),exact.sqrt());self.assertGreaterEqual(Decimal.from_float(float(hi[0])),exact.sqrt())
    def test_radius_equality_nextafter_and_duplicates(self):
        scores=np.array([0.,1.,1.,4.]);lo,hi=interval(scores,1);mask=rejected(lo,hi,lo[0],hi[0],radius_upper(1.,1));self.assertFalse(mask[1]);self.assertFalse(mask[2]);self.assertTrue(mask[3])
        scores=np.array([float(np.nextafter(np.float32(1),np.float32(2)))**2]);lo,hi=interval(scores,1);self.assertTrue(rejected(lo,hi,0.,0.,radius_upper(1.,1))[0])
    def test_malformed(self):
        for v in (np.nan,np.inf,-1.):
            with self.assertRaises(AssertionError):make_tiles(np.full((4,10),v),np.arange(10),32)
        with self.assertRaises(AssertionError):make_tiles(np.zeros((4,10)),np.zeros(10,dtype=int),32)
        with self.assertRaises(AssertionError):make_tiles(np.zeros((4,10)),np.arange(10),0)
    def test_joint_gates_strong_and_uncovered(self):
        def fixture(a,b,anchor=.7):
            return [dict(snapshot=n,tile_size=t,total_tiles=4096*256//t,statistics={'surviving_object_fraction':{'mean':anchor if t in (256,512) else x},'false_prune_tiles':{'max':0}}) for n,x in zip(SNAPS,[a,b]) for t in SIZES]
        self.assertEqual(decide(fixture(.45,.46))['decision'],'GO_GRANULARITY')
        self.assertEqual(decide(fixture(.34,.34))['strong_GO_sizes'],[128,64])
        self.assertEqual(decide(fixture(.52,.53))['reason'],'specified_conditional_band')
        self.assertFalse(decide(fixture(.49,.51))['update_admitted'])
        self.assertEqual(decide(fixture(.62,.63))['decision'],'NO_GO_GRANULARITY')
        self.assertFalse(decide(fixture(.45,.63))['update_admitted'])
    def test_cost_no_distance_conversion(self):
        rows=[dict(snapshot=n,tile_size=t,total_tiles=4096*256//t,query=qi,qid=qi,surviving_object_fraction=.5) for n in SNAPS for t in SIZES for qi in range(32)]
        c=costs(rows);self.assertEqual(len(c['proxy_rows']),960);self.assertEqual(len(c['metadata']),10)
        self.assertEqual(c['metadata'][1]['metadata_bytes'],262144);self.assertEqual(c['metadata'][4]['relative_to_256'],8)


if __name__=='__main__':unittest.main()
