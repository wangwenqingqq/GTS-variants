"""Local static smoke checks; these are not GPU correctness or sanitizer gates."""
import hashlib
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from prepare_native import SEARCH_PINS, adapt, apply_exact_patch, patch_static_search


def worst_leaf(n, height):
    for _ in range(height-1):
        if n <= 20:
            break
        n -= 9*(n//10)
    return n


class NativeAdapterTests(unittest.TestCase):
    def test_exact_mandated_patches(self):
        for arm,(source_pin,patch_name,patch_pin) in SEARCH_PINS.items():
            source=(ROOT/f'source_{arm}/include/search_v2.cuh').read_bytes()
            patch=(ROOT/'patches'/patch_name).read_bytes()
            self.assertEqual(hashlib.sha256(source).hexdigest(),source_pin)
            self.assertEqual(hashlib.sha256(patch).hexdigest(),patch_pin)
            fixed=apply_exact_patch(source.decode(),patch.decode())
            self.assertNotIn('int le = qe + 1',fixed)
            self.assertIn('update_disk = false; // FIX1',fixed)
            self.assertIn('// FIX2:',fixed)
            self.assertIn('FAILFAST:',fixed)
            with self.assertRaises(AssertionError):
                apply_exact_patch(source.decode().replace('cout << "Searching..." << endl;', '// changed context'),patch.decode())

    def test_derivation_is_deterministic_and_preserves_archive(self):
        for arm in ('g','p'):
            original={p.name:p.read_bytes() for p in (ROOT/f'source_{arm}/include').iterdir() if p.is_file()}
            patch_static_search(arm); first=adapt(arm)
            patch_static_search(arm); self.assertEqual(first,adapt(arm))
            self.assertEqual(original,{p.name:p.read_bytes() for p in (ROOT/f'source_{arm}/include').iterdir() if p.is_file()})
            update=(ROOT/f'native_{arm}/update.cuh').read_text()
            self.assertIn('is_delete[e1_stable_ids[data_id]]',update)
            self.assertNotIn('void updateIndexRnn(',update)
            for filename in ('tree.cuh','search.cuh','update.cuh'):
                self.assertIn('data_info[2] == 8',(ROOT/f'native_{arm}'/filename).read_text())

    def test_tree_height_covers_residual_last_child(self):
        # Native split uses nine floor(N/10) children and one residual child.
        for n in (8,20,21,100,10001,100000,900000,1000000,9999999,10000000):
            h=1; worst=n
            while worst>20:
                worst-=9*(worst//10);h+=1
            self.assertLessEqual(worst_leaf(n,h),20)
        # The old ideal log10 recipe can leave an oversized residual leaf.
        self.assertGreater(worst_leaf(19999,4),20)

    def test_candidate_radius_uses_only_live_objects(self):
        text=(ROOT/'dynamic.cu').read_text()
        self.assertIn('if(!store.hdead[i]){bound=std::max(bound,cpu_distance(c,i,src));++seeds;}',text)
        self.assertIn('last_tree_ids=out;last_radius=radius;',text)
        self.assertIn('range_tree_consolidated_before_slot',text)
        self.assertIn('N exceeds frozen 10M resource cap',text)
        self.assertIn('native int32 row-dimension indexing overflow',text)
        self.assertIn('pid<<getpid()',text)


if __name__=='__main__':
    unittest.main()
