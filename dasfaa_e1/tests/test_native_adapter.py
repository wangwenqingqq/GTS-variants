"""Local static smoke checks; these are not GPU correctness or sanitizer gates."""
import hashlib
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from prepare_native import SEARCH_PINS, adapt, add_tanimoto, apply_exact_patch, patch_static_search, function_body


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

    def test_native_knn_outputs_and_route(self):
        text=(ROOT/'dynamic.cu').read_text()
        self.assertIn('store.qx,knn_ids,1,last_native_k',text)
        self.assertIn('qid,knn_ids,1,last_native_k',text)
        self.assertIn('last_native_k=std::min(n,c.k+deleted_tree)',text)
        self.assertIn('mapping[id]',text)
        self.assertIn('distance.data(),res_dis',text)
        self.assertIn('store.last_distances[j]',text)
        query=text[text.index(' std::vector<int>query('):text.index('\n};\n#endif')]
        self.assertNotIn('cpu_distance',query)
        self.assertNotIn('searchIndexRnnUpdate',query)
        self.assertIn('std::vector<int>range_tree(',text)
        self.assertIn('N exceeds frozen 10M resource cap',text)
        self.assertIn('native int32 row-dimension indexing overflow',text)
        self.assertIn('pid<<getpid()',text)
        for arm in ('g','p'):
            code=(ROOT/f'native_{arm}/search_v2.cuh').read_text()
            self.assertIn('mergeResKnnIds<<<',code)
            self.assertIn('qnum * k * sizeof(float)',code)
            self.assertIn('res_ids[qid * k + jj]',code)
            self.assertIn('res_dis[qid * k + jj]',code)
            self.assertIn('data_info[2] == 8',code)
        self.assertNotIn('rp_predict(', (ROOT/'native_p/search_v2.cuh').read_text().replace('// New inference: rp_predict(dis_lb, disk_val, cur_level) -- 4 FLOPs vs ~40 FLOPs',''))

    def test_g_pruning_and_distance_preserved(self):
        original=(ROOT/'source_g/include/search_v2.cuh').read_text()
        patch=(ROOT/'patches/gts_original_search_v2_fixes.patch').read_text()
        fixed=add_tanimoto(apply_exact_patch(original,patch))
        adapted=(ROOT/'native_g/search_v2.cuh').read_text()
        for marker in ('__global__ void nodeProcessKnn(', '__global__ void getDisPQ(', '__global__ void updateDisK('):
            a,_,b=function_body(fixed,marker);x,_,y=function_body(adapted,marker)
            self.assertEqual(fixed[a:b],adapted[x:y])
        a,_,b=function_body(fixed,'__global__ void dataProcessKnn(')
        x,_,y=function_body(adapted,'__global__ void dataProcessKnn(')
        expected=fixed[a:b].replace('double result = INFI_DIS;', 'double result = INFI_DIS;\n\t\tint data_id = -1;').replace('int data_id = id_list[node.lid + did];','data_id = id_list[node.lid + did];').replace('= bid * MAX_SIZE + did;','= (double)data_id;')
        self.assertEqual(expected,adapted[x:y])

    def test_tombstone_overfetch_preserves_live_topk(self):
        # Exhaust all deletion patterns on an already distance-sorted tree.
        # No native bounds are changed; k+d ranks contain all remaining top k.
        for n in range(1,10):
            for mask in range(1<<n):
                dead={i for i in range(n) if mask>>i&1}
                live=[i for i in range(n) if i not in dead]
                for k in range(1,n+1):
                    count=min(n,k+len(dead))
                    actual=[i for i in range(count) if i not in dead][:k]
                    self.assertEqual(actual,live[:k])


if __name__=='__main__':
    unittest.main()
