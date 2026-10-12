#!/usr/bin/env python3
"""Adversarial deterministic proposals, scalar enumeration and decision checks."""
import inspect, unittest
import numpy as np
from splits import candidates, score_proposals, decision, PARTITIONS
from independent import enumerate_scores, proposals as independent_proposals


class Checks(unittest.TestCase):
    def test_proposals_ties_and_balance(self):
        for z in [np.zeros((100, 8)), np.random.default_rng(3).integers(-2, 3, (100, 8)).astype(float),
                  np.random.default_rng(8).normal(size=(100, 8))]:
            ids = np.random.default_rng(4).permutation(100).astype(np.int32)
            for depth in [0, 3, 8]:
                got = candidates(z, ids, depth); reference = independent_proposals(z, ids, depth)
                self.assertEqual(got.shape, (12, 100))
                self.assertTrue(np.array_equal(got, np.array(reference)))
                self.assertTrue(np.array_equal(np.sort(got, axis=1), np.tile(np.arange(100), (12, 1))))
                self.assertTrue(np.array_equal(got[9], got[depth % 8 + 1]))
                self.assertTrue(np.array_equal(candidates(z, ids[::-1], depth), got))
        self.assertEqual(list(inspect.signature(candidates).parameters), ['z', 'ids', 'depth'])

    def test_radial_cancellation_sequential_fold(self):
        # Python >=3.12 builtin sum is compensated, not the frozen ordered fold.
        z = np.zeros((100, 8)); z[:5, 0] = [1., 1e-16, -1., -1e-18, 1e-18]
        ids = np.arange(100, dtype=np.int32)
        self.assertTrue(np.array_equal(candidates(z, ids, 4)[11], independent_proposals(z, ids, 4)[11]))

    def test_bound_and_argmax_reference(self):
        z = np.random.default_rng(7).normal(size=(100, 8)) * .1
        qs = z[[1, 4, 8, 12, 15, 16, 31, 37]]; u = np.array([.15, .25, .12, .07, .08, .11, .14, .03])
        ids = np.arange(100, dtype=np.int32); pp = candidates(z, ids, 2)
        fast, _ = score_proposals(z, pp, qs, u)
        slow, _ = enumerate_scores(z, ids, 2, qs, u)
        self.assertTrue(np.array_equal(fast, slow))
        for selected in [fast.sum(1), fast[:, 2:].sum(1)]:
            self.assertEqual(int(np.argmax(selected)), list(selected).index(max(selected)))
        zeros, _ = score_proposals(z, pp, qs, np.full(8, 100.))
        self.assertEqual(int(np.argmax(zeros.sum(1))), 0)

    def test_nested_small_construction(self):
        z = np.random.default_rng(13).normal(size=(1000, 8)); perm = np.arange(1000, dtype=np.int32)
        qs = z[:8]; u = np.ones(8)
        for depth in range(2):
            size = 1000 // 10 ** depth
            for start in range(0, 1000, size):
                parent = perm[start:start + size].copy(); pp = candidates(z, parent, depth)
                count, _ = score_proposals(z, pp, qs, u)
                perm[start:start + size] = pp[np.argmax(count[:, 2:].sum(1))]
            self.assertTrue(np.array_equal(np.sort(perm), np.arange(1000)))
            self.assertEqual(perm.reshape(10 ** (depth + 1), -1).shape[1], size // 10)

    def test_decision_thresholds(self):
        def rows(p2=.30, p4=.35, p3=.45):
            return [dict(partition=p, level=l, hard_alignment=p4 if p == 'ORACLE_HARD6' else p2,
                         alignment=p3 if p == 'ORACLE_ALL8' else .4) for p in PARTITIONS for l in [3, 4, 5]]
        self.assertEqual(decision(rows())['decision'], 'LINEAR_SPLIT_OBJECTIVE_HEADROOM_LOW')
        self.assertEqual(decision(rows(p3=.60))['decision'], 'EASY_QUERY_ONLY')
        self.assertEqual(decision(rows(p4=.40))['decision'], 'INSUFFICIENT_EVIDENCE')
        self.assertEqual(decision(rows(p2=.35, p4=.60))['decision'], 'SPLIT_OBJECTIVE_HEADROOM_HIGH')
        self.assertEqual(decision(rows(p2=.45, p4=.70, p3=.60))['decision'], 'CERTIFICATE_EFFECTIVENESS_CONSTRUCTION_SUPPORTED')
        self.assertEqual(decision(rows(p2=.60, p4=.70, p3=.60))['decision'], 'INSUFFICIENT_EVIDENCE')


if __name__ == '__main__': unittest.main()
