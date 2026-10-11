"""Regression gates for arithmetic enclosure, layouts, selection and promotion."""
import struct,unittest
import numpy as np
from certificates import bound,endpoints,error_bound,metadata_size,serialize,RHO
from evaluate_certificates import greedy,farthest_first,promotion,decision


class CertificateTests(unittest.TestCase):
    def test_error_budget_and_zero(self):
        self.assertLess(error_bound(),RHO)
        low,high=endpoints(np.array([0.]),np.array([0.]))
        self.assertEqual(float(bound(low,high,np.array([0.]))[0]),0.)

    def test_outward_FP32(self):
        minimum=np.array([0.,.123456789,20.123456789]);maximum=minimum+1.
        lo,hi=endpoints(minimum,maximum)
        self.assertTrue(np.all(lo.astype('f8')<=np.maximum(0.,minimum-RHO)))
        self.assertTrue(np.all(hi.astype('f8')>=maximum+RHO))

    def test_interval_triangle_safety(self):
        points=np.array([0.,.1,1.,2.],dtype='f4').astype('f8')
        for pivot in points:
            low,high=endpoints(np.array([np.abs(points-pivot).min()]),np.array([np.abs(points-pivot).max()]))
            for query in [0.,.13,1.5,2.,3.]:
                self.assertLessEqual(float(bound(low,high,np.array([abs(query-pivot)]))[0]),np.abs(points-query).min())

    def test_actual_layout_and_packed_IDs(self):
        low=np.arange(2*64,dtype='f4').reshape(2,64);high=low+10
        chosen=np.array([[63,62,31,30,29,28,27,26],[0,1,2,3,4,5,6,7]],dtype='u1')
        for region in [False,True]:
            for k in [0,1,2,4,8]:
                logical,aligned=metadata_size(k,region);data=serialize(low,high,chosen[:,:k],region)
                self.assertEqual(len(data),2*aligned)
                for i in range(2):
                    record=data[i*aligned:(i+1)*aligned]
                    for j in range(k):
                        a,b=struct.unpack_from('<2f',record,j*8)
                        self.assertEqual((a,b),(low[i,chosen[i,j]],high[i,chosen[i,j]]))
                    if region and k:
                        packed=int.from_bytes(record[8*k:logical],'little')
                        self.assertEqual([(packed>>(6*j))&63 for j in range(k)],chosen[i,:k].tolist())
                    self.assertFalse(any(record[logical:]))
        self.assertEqual(metadata_size(8,True),(70,80))
        self.assertEqual(metadata_size(8,False),(64,64))

    def test_nested_greedy_covers_full_pool_in_eight(self):
        rng=np.random.default_rng(111)
        masks=rng.integers(0,256,size=(40,64),dtype='u1')
        chosen=greedy(masks)
        for i,row in enumerate(chosen):
            self.assertEqual(len(set(row)),8)
            covered=np.uint8(0)
            for pi in row:covered |= masks[i,pi]
            self.assertEqual(covered,np.bitwise_or.reduce(masks[i]))
        self.assertEqual(greedy(np.zeros((1,64),dtype='u1'))[0].tolist(),list(range(8)))

    def test_farthest_first_tie(self):
        matrix=np.ones((64,64));np.fill_diagonal(matrix,0)
        self.assertEqual(farthest_first(matrix,list(range(64))),list(range(8)))

    def test_budget_not_silent_payload(self):
        row=dict(level=3,pivot_count=8,oracle_gap_coverage=.8,incremental_G0_pruning=.6,aligned_bytes_per_region=80)
        self.assertFalse(promotion([row]))
        self.assertEqual(decision([], [row]),'METADATA_HEAVY')
        row['aligned_bytes_per_region']=64
        self.assertTrue(promotion([row]))
        self.assertEqual(decision([row],[]),'GLOBAL_CERTIFICATE_FEASIBLE')

    def test_pivot_kill_is_not_global_only_kill(self):
        row=dict(level=5,pivot_count=8,oracle_gap_coverage=.1,incremental_G0_pruning=.09,aligned_bytes_per_region=80)
        self.assertEqual(decision([], [row]),'PIVOT_CERTIFICATE_KILLED')


if __name__=='__main__':unittest.main()
