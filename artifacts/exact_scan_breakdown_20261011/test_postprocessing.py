"""CPU-only regression checks for the delivered interpretation helpers."""
import csv
import json
import tempfile
import unittest
from pathlib import Path

from forensic import selected
from l2_finalize import finalize, sha


class Postprocessing(unittest.TestCase):
    def test_ASLR_only_normalization_preserves_real_changes(self):
        def source(base):
            rows = []
            for i in range(128):
                instruction = 'FFMA R0, R1, R2, R3'
                if i == 2:
                    instruction = f'@P0 BRA {base + 64:#x}'
                rows.append(f'{base + 16*i:#x} {instruction}')
            return 'Kernel Name pairwise_matrix_kernel\n' + '\n'.join(rows)
        a, b = source(0x100000), source(0x200000)
        self.assertEqual(selected(a)[1]['normalized_sha256'],
                         selected(b)[1]['normalized_sha256'])
        for changed in (a.replace('FFMA', 'FMUL', 1),
                        a.replace('@P0', '@P1', 1),
                        a.replace('R3', 'R4', 1)):
            self.assertNotEqual(selected(a)[1]['normalized_sha256'],
                                selected(changed)[1]['normalized_sha256'])

    def fixture(self, root, total=20):
        out = root / 'l2_supplement'
        (out / 'guard').mkdir(parents=True)
        (out / 'guard/receipt.json').write_text('{"runtime_valid": true}')
        (out / 'CHECKED.json').write_text('{"passed": true, "output_hashes": {}}')
        (out / 'REGISTERED.json').write_text('{"binary_sha256": "fixture"}')
        (out / 'report.ncu-rep').write_bytes(b'CPU-only fixture, not a real report')
        keys = ['Kernel Name', 'lts__t_sectors.sum', 'lts__t_sectors_op_read.sum',
                'lts__t_sectors_op_write.sum', 'lts__t_bytes.sum',
                'dram__bytes.sum', 'gpu__time_duration.avg']
        with (out / 'report_base.csv').open('w') as f:
            csv.writer(f).writerows([keys, ['', 'sector', 'sector', 'sector', 'byte', 'byte', 'ns'],
                                    ['pairwise_matrix_kernel', total, 12, 5, total*32, 400, 100]])
        return out

    def test_other_bucket_retains_capture_and_rejects_automatic_rewrite(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            out = self.fixture(root)
            before = sha(out / 'report.ncu-rep')
            result = finalize(root)
            self.assertEqual(result['other_L2_bytes'], 3*32)
            self.assertEqual(result['total_L2_bytes'],
                             sum(result[k] for k in ('read_L2_bytes', 'write_L2_bytes', 'other_L2_bytes')))
            self.assertEqual(before, sha(out / 'report.ncu-rep'))
            self.assertTrue(json.loads((out / 'POSTPROCESSING_R1_REJECTED.json').read_text())['GPU_runtime_valid'])
            with self.assertRaises(AssertionError):
                finalize(root)

    def test_negative_other_is_not_silently_clipped(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            self.fixture(root, total=16)
            with self.assertRaises(AssertionError):
                finalize(root)
            self.assertFalse((root / 'L2_SUPPLEMENT.json').exists())


if __name__ == '__main__':
    unittest.main()
