"""Independent fixed-zone and ordered-FP64 boundary fixtures; no dataset or GPU."""
if not __debug__:
    raise SystemExit('Optimized Python disables mandatory checks; run without -O/PYTHONOPTIMIZE.')
import os
import unittest
from pathlib import Path
import numpy as np
from run import library, order_call, old


class PDX(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib = library(Path(os.environ['PDX_LIBRARY']))

    def test_official_score_three_groups_full_last_zone(self):
        q = np.repeat(np.arange(1, 31, dtype='<f4'), 32)
        q[-1] = 1000
        order, zones, ranks, tie = order_call(self.lib, q, np.zeros(960, '<f4'))
        self.assertEqual(zones.tolist(), [27, 28, 29]+list(range(27)))
        self.assertEqual(order[:96].tolist(), list(range(864, 960)))
        self.assertEqual(float(ranks[-1]), (31*30+1000)/32)
        self.assertEqual(tie, 0)

    def test_abs_fp32_not_squared_moment(self):
        q, means = np.zeros(960, '<f4'), np.zeros(960, '<f4')
        q[:32] = -3
        means[32:64] = 2
        _, _, ranks, _ = order_call(self.lib, q, means)
        self.assertEqual(ranks[:2].tolist(), [3, 2])
        q[8] = np.nan
        with self.assertRaises(AssertionError):
            order_call(self.lib, q, means)

    def test_ties_permutation_and_two_sorted_groups(self):
        order, zones, ranks, tie = order_call(self.lib, np.zeros(960, '<f4'), np.zeros(960, '<f4'))
        self.assertEqual(tie, 27)
        self.assertEqual(zones[:3].tolist(), sorted(zones[:3].tolist()))
        self.assertEqual(zones[3:].tolist(), sorted(zones[3:].tolist()))
        self.assertEqual(sorted(order.tolist()), list(range(960)))

    def test_ordered_authority_guard_and_equality(self):
        rng = np.random.default_rng(20261015)
        x = rng.normal(size=(17, 960)).astype('<f4')
        q = np.ascontiguousarray(x[0])
        full = np.empty(len(x), '<f8')
        for i, row in enumerate(x):
            total = 0.0
            for a, b in zip(row, q):
                delta = float(a)-float(b)
                total = total + delta*delta
            full[i] = total
        mismatch = np.zeros(1, '<u8')
        rc = self.lib.validate_ordered_scores(x.ctypes.data, q.ctypes.data, full.ctypes.data, len(x), mismatch.ctypes.data)
        self.assertEqual(rc, 0)
        order, _, _, _ = order_call(self.lib, q, x.mean(axis=0, dtype=np.float32))
        for threshold in (0.0, float(full[2]), 700.0):
            nominal, safe, audit = old.global_call(self.lib, x, q, full, threshold, order)
            self.assertTrue((safe >= nominal).all())
            self.assertTrue((safe[full <= threshold] == 960).all())
        broken = full.copy()
        broken[3] = np.nextafter(broken[3], np.inf)
        self.assertEqual(self.lib.validate_ordered_scores(x.ctypes.data, q.ctypes.data, broken.ctypes.data,
                                                        len(x), mismatch.ctypes.data), 3)
        self.assertEqual(int(mismatch[0]), 1)


if __name__ == '__main__':
    unittest.main()
