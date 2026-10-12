"""Small arithmetic, layout, budget, max-safety, and exact gate regressions."""
import unittest
import numpy as np
from views import bounds, scalar_bound, configurations, endpoints, decision
from projection_math import prefix_bounds

class Tests(unittest.TestCase):
    def test_scalar_and_old_bridge(self):
        rng=np.random.default_rng(13);z=rng.normal(size=(100,8));lo,hi=endpoints(z-0.1,z+0.1);q=rng.normal(size=8)
        self.assertTrue(np.array_equal(bounds(lo,hi,q),prefix_bounds(lo,hi,q)[8]))
        for k in (1,2,4,8):
            actual=bounds(lo[:,:k],hi[:,:k],q[:k]);ref=[scalar_bound(a,b,q[:k]) for a,b in zip(lo[:,:k],hi[:,:k])]
            self.assertTrue(np.array_equal(actual,ref))
    def test_layout_budget_domination(self):
        configs,aliases=configurations();self.assertEqual(len(configs),12);self.assertEqual(len(aliases),4)
        rng=np.random.default_rng(15);z=rng.normal(size=(128,40));lo,hi=endpoints(z-.2,z+.2);q=rng.normal(size=40)
        values={c['config']:np.array([bounds(lo[:,g],hi[:,g],q[g]) for g in c['groups']]).max(0) for c in configs}
        for c in configs:
            self.assertEqual(sum(map(len,c['groups'])),8)
            self.assertEqual(np.stack([lo[:,np.concatenate(c['groups'])],hi[:,np.concatenate(c['groups'])]],axis=-1).nbytes,128*64)
        for name in ('BLOCKS_2x4','BLOCKS_4x2','BLOCKS_8x1','INTERLEAVED_2x4','INTERLEAVED_4x2'):
            self.assertTrue(np.all(values[name]<=values['PCA8']))
    def test_complementary_max_not_energy_sum(self):
        # Two identical 1D projections can be contractive separately, not jointly.
        a=bounds(*endpoints(np.array([[0.]]),np.array([[0.]])),np.array([1.]))[0]
        self.assertLessEqual(max(a,a),1.);self.assertGreater(np.sqrt(a*a+a*a),1.)
    def test_exact_gate_boundary(self):
        def row(name,l,h,w):return dict(config=name,level=l,hard_pruned_objects=h,hard_truth_prunable_objects=100,pruned_objects=h,truth_prunable_objects=100,hard_query_pruned=[w]*6,hard_query_truth_prunable=[100]*6)
        rows=[row('PCA8',l,40,10) for l in (3,4,5)]+[row('X',l,55,25) for l in (3,4,5)]
        self.assertEqual(decision(rows)['decision'],'MULTI_VIEW_SIGNAL')
        rows[-3]['hard_pruned_objects']=54;rows[-2]['hard_pruned_objects']=54
        self.assertNotEqual(decision(rows)['decision'],'MULTI_VIEW_SIGNAL')

if __name__=='__main__':unittest.main()
