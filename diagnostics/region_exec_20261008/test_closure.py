#!/usr/bin/env python3
"""CPU checks for multiset replay and exact diagnostic work-set admission."""
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from audit_closure import integer_oracle
from finish_closure import compare_work


class ClosureTests(unittest.TestCase):
    def test_duplicate_occurrences_base_and_buffer_delete(self):
        ops = [[2, 0], [0, 0], [2, 0], [1, 0], [2, 0], [1, 2], [2, 0]]
        queries, states, rebuilt = integer_oracle(np.array([[0], [1], [0]], dtype=np.int64), ops, 0)
        self.assertEqual([set(x[4]) for x in queries], [{0, 2}, {0, 2, 3}, {1, 2}, {1}])
        self.assertEqual(states[-1][:4], (3, 0, 3, 0))
        self.assertEqual(rebuilt, 0)
        self.assertTrue(all(v == bytes(np.float32(0)) for q in queries for v in q[4].values()))

    def test_actual_occupancy_rebuild(self):
        queries, states, rebuilt = integer_oracle(np.array([[0], [1], [0]], dtype=np.int64),
                                                 [[0, 0]] * 10 + [[2, 12]], 0)
        self.assertEqual(rebuilt, 1)
        self.assertEqual(states[9], (3, 9, 13, 0, True))
        self.assertEqual(len(queries[0][4]), 12)

    def test_exact_work_sets_and_rejections(self):
        with tempfile.TemporaryDirectory() as directory:
            files = [Path(directory) / str(i) for i in range(3)]
            record = dict(epoch=1, nodes=[1], pivots=[1], leaves=[1], objects=[1, 0])
            for path in files:
                path.write_text('REGION_WORK ' + json.dumps(record) + '\n')
            self.assertEqual(compare_work(files, 1)['totals']['objects'], 1)
            with self.assertRaises(AssertionError):
                compare_work(files, 2)
            record['objects'] = [0, 1]
            files[2].write_text('REGION_WORK ' + json.dumps(record) + '\n')
            with self.assertRaises(AssertionError):
                compare_work(files, 1)


if __name__ == '__main__':
    unittest.main()
