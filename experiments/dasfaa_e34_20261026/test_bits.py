"""Local CPU-only checks; no CuPy import, CUDA, SSH, NVML or benchmark claims."""
from fractions import Fraction
import contextlib
import io
import hashlib
import importlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import types
from unittest.mock import patch
import unittest

import numpy as np
from audit_bits import audit, distance, feature_int, load

HERE = Path(__file__).resolve().parent


def pack(path, values):
    with Path(path).open('xb') as f:
        f.write(np.array([len(values), 2048], dtype='<i4').tobytes())
        for value in values:
            f.write(int(value).to_bytes(256, 'little'))


def exact(a, b):
    common, combined = (a & b).bit_count(), (a | b).bit_count()
    return Fraction(combined - common, combined) if combined else Fraction(0)


class BitChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='.test_bits_', dir=HERE)
        cls.folder = Path(cls.temp.name)
        cls.binary = cls.folder / 'bit_oracle'
        compiler = shutil.which('c++')
        if compiler is None:
            raise RuntimeError('a C++17 compiler is required for the CPU smoke check')
        subprocess.run([compiler, '-std=c++17', '-O2', '-Wall', '-Wextra',
                        str(HERE / 'bit_oracle.cpp'), '-o', str(cls.binary)],
                       check=True, capture_output=True, text=True)
        rng = np.random.default_rng(20261026)
        high_entropy = [int.from_bytes(rng.bytes(256), 'little') for _ in range(40)]
        cls.values = [0, 1, 1 << 63, 1 << 64, 1 << 127, 1 << 2047,
                      (1 << 2048) - 1, (1 << 63) | (1 << 64) | (1 << 2047),
                      1, 1, *high_entropy]
        cls.queries = [0, 1, (1 << 2048) - 1, (1 << 63) | (1 << 2047),
                       int.from_bytes(rng.bytes(256), 'little')]
        cls.base, cls.query = cls.folder / 'base.bits', cls.folder / 'query.bits'
        pack(cls.base, cls.values); pack(cls.query, cls.queries)
        cls.oracle = cls.folder / 'main.oracle'
        cls.run_oracle(cls.base, cls.query, len(cls.values), cls.oracle, check=True)
        cls.case = {'base': cls.base.name, 'query': cls.query.name,
                    'oracle': cls.oracle.name, 'N': len(cls.values)}
        cls.reference = [sorted(range(len(cls.values)), key=lambda i: (exact(cls.values[i], q), i))
                         for q in cls.queries]

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    @classmethod
    def run_oracle(cls, base, query, n, out, check=False):
        return subprocess.run([str(cls.binary), str(base), str(query), str(n), str(out)],
                              env={**os.environ, 'OMP_NUM_THREADS': '32'}, check=check,
                              capture_output=True, text=True)

    def results(self, label, ids=None, reported=None):
        prefix = self.folder / label
        ids = np.array([r[:8] for r in self.reference], dtype='<i4') if ids is None else np.asarray(ids, dtype='<i4')
        if reported is None:
            reported = np.array([[distance(self.values[int(i)], self.queries[row])
                                  if 0 <= int(i) < len(self.values) else 0.0
                                  for i in got] for row, got in enumerate(ids)], dtype='<f8')
        with Path(str(prefix) + '.ids').open('xb') as f: ids.tofile(f)
        with Path(str(prefix) + '.dist').open('xb') as f: np.asarray(reported, dtype='<f8').tofile(f)
        return prefix

    def test_cpu_oracle_matches_independent_rational_reference(self):
        nq = len(self.queries)
        raw = self.oracle.read_bytes()
        self.assertEqual(len(raw), nq * 10 * 12)
        ids = np.frombuffer(raw, dtype='<i4', count=nq * 10).reshape(nq, 10)
        dd = np.frombuffer(raw, dtype='<f8', offset=nq * 10 * 4).reshape(nq, 10)
        self.assertEqual(ids.tolist(), [row[:10] for row in self.reference])
        for row, query in enumerate(self.queries):
            np.testing.assert_allclose(dd[row], [float(exact(self.values[i], query)) for i in ids[row]], rtol=0, atol=1e-15)

    def test_zero_sparse_and_high_word_semantics(self):
        self.assertEqual(distance(0, 0), 0)
        self.assertEqual(distance(0, 1 << 2047), 1)
        self.assertEqual(distance(1 << 63, 1 << 64), 1)
        self.assertEqual(distance((1 << 63) | (1 << 64), 1 << 64), 0.5)
        rows = load(self.base)
        self.assertEqual(feature_int(rows[5]), 1 << 2047)
        self.assertEqual(int(rows[5, 31]), 1 << 63)
        self.assertEqual(int(rows[3, 1]), 1)
        self.assertEqual(len(load(self.base, 10)), 10)
        self.assertEqual(rows.dtype.str, '<u8')

    def test_complete_output_and_alternative_ties(self):
        ids = np.array([r[:8] for r in self.reference], dtype='<i4')
        # The empty query has distance1 to every nonempty fingerprint.
        ids[0] = [0, 12, 13, 14, 15, 16, 17, 18]
        got = audit(self.folder, self.case, self.results('valid_alternative_ties', ids))
        self.assertTrue(got['correct'])
        self.assertEqual(got['tie_aware_recall'], 1)

    def test_bad_rank_duplicate_and_invalid_ids(self):
        original = np.array([r[:8] for r in self.reference], dtype='<i4')
        bad = original.copy(); bad[2, 0] = 0  # empty versus all-ones query is farther than kth
        self.assertGreater(audit(self.folder, self.case, self.results('bad_rank', bad))['distance_failures'], 0)
        bad = original.copy(); bad[0, 0] = bad[0, 1]
        got = audit(self.folder, self.case, self.results('bad_duplicate', bad))
        self.assertFalse(got['correct']); self.assertEqual(got['duplicate_rows'], 1)
        for label, value in [('bad_negative', -1), ('bad_range', len(self.values))]:
            bad = original.copy(); bad[0, 0] = value
            got = audit(self.folder, self.case, self.results(label, bad))
            self.assertFalse(got['correct']); self.assertEqual(got['invalid_ids'], 1)

    def test_reported_distance_and_truncated_outputs(self):
        prefix = self.results('bad_distance')
        values = np.fromfile(str(prefix) + '.dist', dtype='<f8'); values[0] = np.nan
        values.tofile(str(prefix) + '.dist')
        got = audit(self.folder, self.case, prefix)
        self.assertFalse(got['correct']); self.assertEqual(got['reported_distance_mismatches'], 1)
        prefix = self.results('truncated_output')
        with Path(str(prefix) + '.ids').open('r+b') as f: f.truncate(4)
        with self.assertRaises(ValueError): audit(self.folder, self.case, prefix)
        with self.assertRaises(ValueError): audit(self.folder, self.case, prefix, expected_rows=1)

    def test_oracle_prefix_and_nonoverwrite(self):
        prefix_oracle = self.folder / 'prefix.oracle'
        self.run_oracle(self.base, self.query, 10, prefix_oracle, check=True)
        expected = [sorted(range(10), key=lambda i: (exact(self.values[i], q), i)) for q in self.queries]
        ids = np.fromfile(prefix_oracle, dtype='<i4', count=len(self.queries) * 10).reshape(-1, 10)
        self.assertEqual(ids.tolist(), expected)
        before = hashlib.sha256(self.oracle.read_bytes()).hexdigest()
        self.assertNotEqual(self.run_oracle(self.base, self.query, len(self.values), self.oracle).returncode, 0)
        self.assertEqual(hashlib.sha256(self.oracle.read_bytes()).hexdigest(), before)
        link = self.folder / 'dangling.oracle'; link.symlink_to('does_not_exist')
        self.assertNotEqual(self.run_oracle(self.base, self.query, 10, link).returncode, 0)
        self.assertTrue(link.is_symlink())
        self.assertFalse(list(self.folder.glob('*.partial.*')))

    def test_malformed_inputs_rejected_by_python_and_cpu(self):
        raw = self.base.read_bytes()
        variants = {
            'short_header': b'\0',
            'zero_rows': np.array([0, 2048], dtype='<i4').tobytes(),
            'negative_rows': np.array([-1, 2048], dtype='<i4').tobytes(),
            'wrong_bits': np.array([len(self.values), 2047], dtype='<i4').tobytes() + raw[8:],
            'short_payload': raw[:-1],
            'trailing_payload': raw + b'\0',
        }
        for label, content in variants.items():
            path = self.folder / (label + '.bits'); path.write_bytes(content)
            with self.subTest(label=label):
                with self.assertRaises(ValueError): load(path)
                result = self.run_oracle(path, self.query, 10, self.folder / (label + '.oracle'))
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse((self.folder / (label + '.oracle')).exists())
        for n in [0, -1, len(self.values) + 1, True]:
            with self.assertRaises(ValueError): load(self.base, n)
        for n in ['9', str(len(self.values) + 1), '2147483648', '10junk']:
            self.assertNotEqual(self.run_oracle(self.base, self.query, n, self.folder / ('invalid_n_' + n)).returncode, 0)

    def test_malformed_oracle(self):
        damaged = self.folder / 'bad.oracle'
        raw = bytearray(self.oracle.read_bytes())
        raw[:4] = np.array([-1], dtype='<i4').tobytes()
        damaged.write_bytes(raw)
        case = {**self.case, 'oracle': damaged.name}
        with self.assertRaises(ValueError): audit(self.folder, case, self.results('bad_oracle_result'))

    def test_scan_host_flow_with_numpy_mock_not_gpu_evidence(self):
        import bit_scan
        queries = [self.queries[i % len(self.queries)] for i in range(35)]
        query_path = self.folder / 'tiled_query.bits'; pack(query_path, queries)
        oracle = self.folder / 'tiled_query.oracle'
        self.run_oracle(self.base, query_path, len(self.values), oracle, check=True)
        case = {**self.case, 'query': query_path.name, 'oracle': oracle.name}
        launches = []
        class Kernel:
            def compile(self): pass
            def __call__(self, grid, block, args):
                n, b, base, query, out = args
                launches.append((int(n), int(b), grid, block))
                for qi in range(int(b)):
                    for obj in range(int(n)):
                        out[qi, obj] = distance(feature_int(base[obj]), feature_int(query[qi]))
        fake = types.ModuleType('cupy')
        fake.__version__ = 'CPU_TEST_MOCK_NOT_GPU_EVIDENCE'
        fake.asarray = np.asarray; fake.empty = np.empty; fake.float64 = np.float64
        fake.argpartition = np.argpartition; fake.take_along_axis = np.take_along_axis
        fake.argsort = np.argsort; fake.asnumpy = lambda x: np.array(x, copy=True)
        fake.RawKernel = lambda *args, **kwargs: Kernel()
        fake.cuda = types.SimpleNamespace(runtime=types.SimpleNamespace(deviceSynchronize=lambda: None))
        for q in (1, 32, 35):
            prefix = self.folder / ('cpu_mock_scan_q' + str(q))
            with patch.dict('sys.modules', {'cupy': fake}), contextlib.redirect_stdout(io.StringIO()):
                bit_scan.main(str(self.base), str(query_path), str(len(self.values)), str(q),
                              '1', '1', str(prefix))
            self.assertTrue(audit(self.folder, case, prefix)['correct'])
            # All required query rows, including the ragged final tile, survive.
            self.assertEqual(Path(str(prefix) + '.ids').stat().st_size, 35 * 8 * 4)
        self.assertTrue(any(b == 32 for _, b, _, _ in launches))
        self.assertTrue(any(b == 3 for _, b, _, _ in launches))
        self.assertTrue(all(b <= 32 for _, b, _, _ in launches))

    def test_scan_module_remains_cpu_importable(self):
        module = importlib.import_module('bit_scan')
        self.assertIn('__popcll(a[word] & z[word])', module.CUDA)
        self.assertIn('__popcll(a[word] | z[word])', module.CUDA)
        self.assertIn('double* out', module.CUDA)
        self.assertNotIn('fast_math', module.CUDA)


if __name__ == '__main__':
    unittest.main()
