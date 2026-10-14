"""Exact gate boundaries, conditional models and population quantiles."""
if not __debug__:
    raise SystemExit('Optimized Python disables mandatory checks; run without -O/PYTHONOPTIMIZE.')
import unittest
from fractions import Fraction
from pathlib import Path
from analyze import gate, load, model_b2, model_b3, rational


class Models(unittest.TestCase):
    def test_gate_boundaries(self):
        self.assertEqual(gate(100, 70, 80), ('B1_SATURATED', False))
        self.assertEqual(gate(100, 40, 80), ('MODERATE_HEADROOM', False))
        self.assertEqual(gate(100, 39, 80), ('LARGE_HEADROOM', True))
        self.assertEqual(gate(100, 70, 60), ('B1_SATURATED', False))
        self.assertEqual(gate(100, 70, 59), ('B1_SATURATED', True))

    def test_metadata_break_even_exact(self):
        c = load(Path(__file__).with_name('CONTRACT.json'))
        result = model_b2(c)
        self.assertEqual(result['state'], 'B2_BARRIER_NOT_SUPPORTED')
        for row in result['rows']:
            r = row['break_even_rejection_fraction']
            f = Fraction(r['numerator'], r['denominator'])
            self.assertEqual(row['metadata_bytes'] + (1 - f) * 3840000000, 1014828776)
            self.assertLess(f, Fraction(9, 10))
        self.assertEqual(result['rows'][-1]['bytes_per_vector'], 256)

    def test_online_surface_denominator(self):
        c = load(Path(__file__).with_name('CONTRACT.json'))
        surface, examples = model_b3(c)
        self.assertEqual(surface['state'], 'B3_FROZEN_REGION_BARRIER')
        value = surface['gate_best_corner']['bytes']
        self.assertEqual(Fraction(value['numerator'], value['denominator']), Fraction(3840000000, 1) / Fraction(7, 2))
        self.assertEqual(len(surface['lambda_qps']), 100)
        self.assertEqual(len(surface['window_us']), 40)
        threshold = surface['break_even_lambda_times_W_seconds']
        product = Fraction(threshold['numerator'], threshold['denominator'])
        self.assertEqual(Fraction(3840000000, 1) / (1 + product), 1014828776)
        self.assertGreater(product, Fraction(5, 2))
        self.assertEqual(rational(product * 2000), examples['break_even_qps_at_500us'])


if __name__ == '__main__':
    unittest.main()
