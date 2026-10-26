"""Pure local checks: approved patch, no endpoint change, IDs and native height."""
import hashlib
from pathlib import Path
import re
import unittest
from adapt import apply_unified, corrected, instrument_p, ORIGINAL_SHA

HERE = Path(__file__).resolve().parent
A = HERE.parents[2]
CAMPAIGN = A.parents[1]


def height(n):
    h, capacity = 1, 20
    while capacity < n:
        capacity *= 10
        h += 1
    return h


class PatchedSources(unittest.TestCase):
    def setUp(self):
        self.headers = {
            'P': A / 'search_v2_original.cuh',
            'G': A / 'provenance/resume_20261026/source_g/include/search_v2.cuh',
        }
        self.patches = {
            'P': CAMPAIGN / 'tools/gtspp_search_v2_fixes.patch',
            'G': CAMPAIGN / 'tools/gts_original_search_v2_fixes.patch',
        }

    def test_strict_patch_rejects_context_drift(self):
        with self.assertRaises(AssertionError):
            apply_unified('wrong\n', '--- a\n+++ b\n@@ -1 +1 @@\n-old\n+new\n')

    def test_exact_sources_and_no_endpoint_repair(self):
        for arm in ('P', 'G'):
            original = self.headers[arm].read_bytes()
            self.assertEqual(hashlib.sha256(original).hexdigest(), ORIGINAL_SHA[arm])
            result = corrected(original, self.patches[arm].read_text(), arm, instrument=arm == 'P')
            self.assertNotIn('int le = qe + 1', result)
            self.assertIn('update_disk = false; // FIX1', result)
            self.assertIn('if (pnum_level < k || cur_level <= 2) // FIX2', result)
            self.assertIn('exit(3);', result)

    def test_p_instrumentation_is_work_only(self):
        pure = corrected(self.headers['P'].read_bytes(), self.patches['P'].read_text(), 'P')
        instrumented = instrument_p(pure)
        clean = re.sub(r'\bWORK\([012],1\);', '', instrumented)
        clean = clean.replace('if(tid==0) \n', '')
        # Ignore layout whitespace only; every non-WORK token remains identical.
        self.assertEqual(re.sub(r'\s+', '', pure), re.sub(r'\s+', '', clean))
        self.assertEqual(instrumented.count('WORK(1,1)'), 2)
        self.assertEqual(instrumented.count('WORK(0,1)'), 5)

    def test_g_output_observer_and_native_height(self):
        result = corrected(self.headers['G'].read_bytes(), self.patches['G'].read_text(), 'G')
        self.assertEqual(result.count('if (audit_result_ids) auditMergeKnnIds<<<'), 1)
        pure = apply_unified(self.headers['G'].read_text(), self.patches['G'].read_text())
        observer_start = result.index('// Output-only observer:')
        observer_end = result.index('void searchIndexKnnV2(short *data_d', observer_start)
        clean = result[:observer_start] + result[observer_end:]
        clean = re.sub(r'if \(audit_result_ids\) auditMergeKnnIds<<<[^;]+;', '', clean)
        self.assertEqual(re.sub(r'\s+', '', pure), re.sub(r'\s+', '', clean))
        for n, expected in [(2000, 3), (1000000, 6), (3000000, 7), (10000000, 7), (30000000, 8)]:
            self.assertEqual(height(n), expected)
        harness = (HERE / 'tree_bench.cu').read_text()
        self.assertIn('MAX_H=configured_height(n);', harness)
        self.assertIn('assert(coverage==n', harness)
        self.assertNotIn('std::ifstream in(cache', harness)
        self.assertIn('n>10000000', harness)

    def test_g_slot_mapping(self):
        # Native payload keeps slot indices through sorting, not original IDs.
        leaves = [{'lid': 0, 'size': 3}, {'lid': 3, 'size': 2}]
        permutation = [14, 8, 19, 3, 11]
        sorted_slots = [21, 0, 20, 2, 1]
        got = [permutation[leaves[slot // 20]['lid'] + slot % 20] for slot in sorted_slots]
        self.assertEqual(got, [11, 14, 3, 19, 8])


if __name__ == '__main__':
    unittest.main()
