"""Small independent arithmetic oracle and strict-boundary fixtures; no GPU."""
if not __debug__:
    raise SystemExit('Optimized Python disables mandatory checks; run without -O/PYTHONOPTIMIZE.')
import os
import unittest
from fractions import Fraction
from pathlib import Path
import numpy as np
from run import functions, pair_call, global_call, order_from_sums, guard_threshold


def reference(x, q, threshold, order):
    values, dims = [], []
    for row in x:
        differences = [float(v) - float(w) for v, w in zip(row, q)]
        terms = [delta * delta for delta in differences]
        total = 0.0
        for value in terms:
            total = total + value
        values.append(total)
        if total <= threshold:
            dims.append(len(q))
            continue
        ordered = sorted(terms, reverse=True) if order is None else [terms[j] for j in order]
        prefix, first = 0.0, len(q)
        for j, value in enumerate(ordered):
            prefix = prefix + value
            if prefix > threshold:
                first = j + 1
                break
        dims.append(first)
    return np.asarray(values, '<f8'), np.asarray(dims, '<u2')


class Oracles(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib = functions(Path(os.environ['ORACLES_LIBRARY']))

    def check(self, x, q, threshold):
        full, orig, pair, safe, sums, audit = pair_call(self.lib, x, q, threshold)
        ref, expected = reference(x, q, threshold, None)
        self.assertTrue(np.array_equal(full.view('<u8'), ref.view('<u8')))
        self.assertTrue(np.array_equal(pair, expected))
        self.assertTrue((safe >= pair).all())
        _, expected_orig = reference(x, q, threshold, list(range(len(q))))
        self.assertTrue(np.array_equal(orig, expected_orig))
        order, means = order_from_sums(sums, int((full > threshold).sum()))
        global_dims, global_safe, _ = global_call(self.lib, x, q, full, threshold, order)
        _, expected_global = reference(x, q, threshold, order)
        self.assertTrue(np.array_equal(global_dims, expected_global))
        self.assertTrue((global_safe >= global_dims).all())
        self.assertEqual(int(audit[0]), 0)
        return order, means

    def test_equality_hits_ties_and_last_coordinate(self):
        x = np.asarray([[0, 0, 0, 0], [1, 0, 0, 0], [1, 1, 0, 0], [0, 0, 0, 2]], '<f4')
        self.check(x, np.zeros(4, '<f4'), 1.0)
        order, _ = order_from_sums(np.asarray([5, 5, 1, 5], '<f8'), 2)
        self.assertEqual(order.tolist(), [0, 1, 3, 2])

    def test_high_entropy_960(self):
        rng = np.random.default_rng(20261014)
        x = rng.normal(size=(47, 960)).astype('<f4')
        q = np.ascontiguousarray(x[3])
        self.check(x, q, 500.0)

    def test_guard_is_outward(self):
        for d in (1, 4, 960):
            t = float.fromhex('0x1.fddb427319000p-2')
            exact = Fraction.from_float(t) / (1 - Fraction(2 * d, 2**53))
            self.assertGreater(Fraction.from_float(guard_threshold(t, d)), exact)

    def test_bad_inputs_fail(self):
        x = np.ones((1, 4), '<f4')
        x[0, 0] = np.nan
        with self.assertRaises(AssertionError):
            pair_call(self.lib, x, np.zeros(4, '<f4'), 1.0)
        x[:] = 1
        with self.assertRaises(AssertionError):
            global_call(self.lib, x, np.zeros(4, '<f4'), np.asarray([4.0], '<f8'), 1.0, np.zeros(4, '<i4'))


if __name__ == '__main__':
    unittest.main()
