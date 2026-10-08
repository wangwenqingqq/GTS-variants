"""Small CPU regression checks for the public recipe and evidence validator."""
import hashlib
import csv
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from fixtures import DATA_SHA, EVENT_SHA, boundary_operations, data_bytes, events_bytes, full_operations, generate, load_case
from reproduce import integer_oracle, select_gpu, validate_output, validate_guard, save, sha


def scalar_oracle(data, ops, radius):
    base = data.tolist(); alive = [True] * len(base); buffer = []; answers = []
    for step, (flag, index) in enumerate(ops):
        if flag == 0:
            buffer.append(base[index])
            if len(buffer) == 10:
                base = [v for v, keep in zip(base, alive) if keep] + buffer
                alive = [True] * len(base); buffer = []
        elif flag == 1:
            positions = [i for i, keep in enumerate(alive) if keep]
            if index < len(positions):
                alive[positions[index]] = False
            else:
                buffer.pop(index - len(positions))
        else:
            live = [v for v, keep in zip(base, alive) if keep] + buffer
            expected = {}
            for i, v in enumerate(live):
                sq = sum((a - b) ** 2 for a, b in zip(base[index], v))
                if sq <= radius ** 2:
                    expected[i] = bytes(np.float32(sq ** .5))
            answers.append((step, index, len(base), len(buffer), expected))
    return answers


class RecipeTests(unittest.TestCase):
    def test_exact_frozen_inputs_and_counts(self):
        self.assertEqual(hashlib.sha256(data_bytes()).hexdigest(), DATA_SHA)
        ops = full_operations()
        self.assertEqual(hashlib.sha256(events_bytes(ops)).hexdigest(), EVENT_SHA)
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'data.txt'; path.write_bytes(data_bytes())
            data = np.loadtxt(path, skiprows=1, dtype=np.int64)
        queries, states, rebuilds = integer_oracle(data, ops, 0)
        self.assertEqual((len(queries), len(states), rebuilds), (10000, 12000, 50))
        self.assertEqual(states[-1][:4], (1000, 0, 1000, 0))

    def test_duplicate_occurrences_physical_reference_and_live_rank(self):
        data = np.array([[0, 0], [3, 4], [0, 0]], dtype=np.int64)
        ops = [(2, 0), (0, 0), (2, 0), (1, 0), (2, 0), (1, 2), (2, 0)]
        got, _, _ = integer_oracle(data, ops, 0)
        self.assertEqual(got, scalar_oracle(data, ops, 0))
        self.assertEqual([set(q[4]) for q in got], [{0, 2}, {0, 2, 3}, {1, 2}, {1}])
        ops = [(0, 0)] * 10 + [(2, 12)]
        got, states, rebuilds = integer_oracle(data, ops, 0)
        self.assertEqual(got, scalar_oracle(data, ops, 0))
        self.assertEqual((states[9], rebuilds), ((3, 9, 13, 0, True), 1))

    def test_inclusive_radius_and_fp32(self):
        data = np.array([[0, 0], [3, 4], [3, 5]], dtype=np.int64)
        ops = [(2, 0), (0, 1), (2, 0), (1, 1), (2, 0)]
        got, _, _ = integer_oracle(data, ops, 5)
        self.assertEqual(got, scalar_oracle(data, ops, 5))
        self.assertEqual(got[0][4], {0: bytes(np.float32(0)), 1: bytes(np.float32(5))})

    def test_boundary_recipe_shape(self):
        ops = boundary_operations()
        self.assertEqual((len(ops), sum(f == 2 for f, _ in ops)), (57, 19))
        data = np.zeros((1000, 1), dtype=np.int64)
        _, _, rebuilt = integer_oracle(data, ops, 10000)
        self.assertEqual(rebuilt, 2)

    def test_occupied_or_unsupported_gpu_refused(self):
        devices = '7, GPU-example, example device, 00000000:01:00.0, 12.0\n'
        with patch('subprocess.check_output', side_effect=[devices, '1234\n']):
            with self.assertRaises(RuntimeError):
                select_gpu('7')
        with patch('subprocess.check_output', return_value=devices.replace('12.0', '9.0')):
            with self.assertRaises(RuntimeError):
                select_gpu('7')
        with patch('subprocess.check_output', return_value=devices):
            with self.assertRaises(RuntimeError):
                select_gpu('6')

    def test_full_output_validator_rejects_wrong_mode_and_trailing_bytes(self):
        with tempfile.TemporaryDirectory() as root:
            work = Path(root); generate(work / 'cases'); (work / 'outputs').mkdir()
            data, ops = load_case(work / 'cases/boundary0')
            queries, states, _ = integer_oracle(data, ops, 0)
            prefix = work / 'outputs/check'
            ids = []; distances = []; query_rows = []
            for step, qid, n, buf, expected in queries:
                query_rows.append((step, qid, n, buf, len(expected), len(ids)))
                ids += list(expected); distances += [np.frombuffer(v, dtype='<f4')[0] for v in expected.values()]
            np.asarray(ids, dtype='<i4').tofile(str(prefix) + '.ids.i32')
            np.asarray(distances, dtype='<f4').tofile(str(prefix) + '.dist.f32')
            with open(str(prefix) + '.queries.csv', 'w') as stream:
                writer = csv.writer(stream); writer.writerow(['step', 'qid', 'tree_size', 'buffer', 'count', 'offset'])
                writer.writerows(query_rows)
            with open(str(prefix) + '.ops.csv', 'w') as stream:
                writer = csv.writer(stream)
                writer.writerow(['step', 'flag', 'base_before', 'buffer_before', 'base_after', 'buffer_after', 'ack_ms', 'rebuild_ms'])
                writer.writerows((i, ops[i][0], *state[:4], 1, .5 if state[4] else 0) for i, state in enumerate(states))
            region = dict(mode=1, final_owned_bytes=0, refreshes=3)
            save(str(prefix) + '.region.json', region)
            save(str(prefix) + '.summary.json', dict(observe=True, tree_audit=False, results=len(ids), trace_ms=1))
            self.assertEqual(validate_output(work, 'check', 'boundary0', 0, 'PAR_STRONG')['queries_checked'], 19)
            region['mode'] = 0; save(str(prefix) + '.region.json', region)
            with self.assertRaises(AssertionError):
                validate_output(work, 'check', 'boundary0', 0, 'PAR_STRONG')
            region['mode'] = 1; save(str(prefix) + '.region.json', region)
            with open(str(prefix) + '.ids.i32', 'ab') as stream:
                stream.write(b'x')
            with self.assertRaises(AssertionError):
                validate_output(work, 'check', 'boundary0', 0, 'PAR_STRONG')

    def test_guard_rejects_false_receipt_or_foreign_process(self):
        with tempfile.TemporaryDirectory() as root:
            run = Path(root); executable = run / 'binary'; executable.write_bytes(b'test')
            receipt = dict(runtime_valid=True, exit_code=0, stop_reason=None, binary_sha256=sha(executable))
            save(run / 'receipt.json', receipt)
            for name in ('before', 'after'):
                save(run / (name + '.json'), dict(apps=''))
            save(run / 'checks.json', [dict(foreign=[])])
            validate_guard(run, executable)
            receipt['runtime_valid'] = False; save(run / 'receipt.json', receipt)
            with self.assertRaises(AssertionError):
                validate_guard(run, executable)
            receipt['runtime_valid'] = True; save(run / 'receipt.json', receipt)
            save(run / 'checks.json', [dict(foreign=['1234, foreign'])])
            with self.assertRaises(AssertionError):
                validate_guard(run, executable)


if __name__ == '__main__':
    unittest.main()
