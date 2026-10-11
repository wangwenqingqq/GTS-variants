"""Small regression checks for classification, route precedence, and ancestor replay."""
import math
import struct
import unittest
import numpy as np
from analyze_region_truth import classify, decode_bits, route, scalar_score, bounds_and_replay


def encode_bits(bits):
    return ''.join(format(sum(int(v) << j for j, v in enumerate(bits[i:i+4])), 'x')
                   for i in range(0, len(bits), 4))


class DiagnosisTests(unittest.TestCase):
    def test_three_classes_and_threshold_tie(self):
        lb, truth, labels = classify(np.array([2., 0., 0., 1.+1e-6]), np.array([9.,4.,1.,4.]), 1.)
        self.assertEqual(labels.tolist(), [0,1,2,1])
        self.assertLessEqual(lb[-1], 1.)

    def test_zero_radius_and_duplicate_truth(self):
        _, _, labels = classify(np.array([0.,0.,1.]), np.array([0.,0.,4.]), 0.)
        self.assertEqual(labels.tolist(), [2,2,0])

    def test_unsafe_bound_rejected(self):
        with self.assertRaisesRegex(ValueError, 'unsafe current prune'):
            classify(np.array([2.]), np.array([0.]), 1.)

    def test_bound_above_truth_rejected_even_without_false_topk_prune(self):
        with self.assertRaisesRegex(ValueError, 'bound exceeds'):
            classify(np.array([5.]), np.array([9.]), 1.)

    def test_route_precedence_and_conflict(self):
        self.assertEqual(route(.85,.0001,.0001), 'CERTIFICATE_ROUTE')
        self.assertEqual(route(.1,.7,.7), 'PARTITION_ROUTE')
        self.assertEqual(route(.3,.3,.1), 'MIXED_ROUTE')
        self.assertEqual(route(.17,.0001,.0001), 'INSUFFICIENT_EVIDENCE')
        self.assertEqual(route(.6,.2,.6), 'INSUFFICIENT_EVIDENCE')
        self.assertEqual(route(.5,.25,.01), 'CERTIFICATE_ROUTE')

    def test_little_nibble_bit_order_and_padding(self):
        self.assertEqual(decode_bits('12', 8).tolist(), [True,False,False,False,False,True,False,False])
        with self.assertRaisesRegex(ValueError, 'padding'):
            decode_bits('f', 2)

    def test_ordered_scalar_not_vector_reduction(self):
        x = np.array([1.,2**-27,2**-27,2**-27,2**-27], dtype=np.float32)
        value = scalar_score(np.zeros(5,dtype=np.float32), x)
        self.assertEqual(struct.pack('<d',value), struct.pack('<d',1.))
        self.assertGreater(math.fsum(float(v)**2 for v in x), value)

    def test_ancestor_pruning_and_bit_mismatch_fail_closed(self):
        nodes = [(0,0.,1,0,0) for _ in range(11111)]
        nodes[111] = (0,5.,1,0,0)
        expected = np.ones(11111,dtype=bool)
        expected[111] = False
        expected[1111:1121] = False
        traces = []
        start = 1
        for level in range(1,5):
            bits = expected[start:start+10**level]
            traces.append(dict(level=level,upper=None if level<3 else 2.,
                               visited=int(bits.sum()),visit_bits_hex=encode_bits(bits)))
            start += 10**level
        raw,path,source,_,_ = bounds_and_replay(nodes, np.array([1.]), traces)
        self.assertLess(raw[1111],2.)
        self.assertGreater(path[1111],2.)
        self.assertEqual(source[1111],111)
        traces[-1]['visit_bits_hex'] = 'f' + traces[-1]['visit_bits_hex'][1:]
        with self.assertRaisesRegex(ValueError,'native replay differs'):
            bounds_and_replay(nodes,np.array([1.]),traces)


if __name__ == '__main__':
    unittest.main()
