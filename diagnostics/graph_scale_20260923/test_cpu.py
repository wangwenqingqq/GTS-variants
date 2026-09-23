#!/usr/bin/env python3
"""CPU-only oracle and generation regression tests; no device calls."""
import importlib.util,random,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
import prepare
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('fixture',HERE.parent/'original_tree_profile/make_fixture.py')
fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)

class Checks(unittest.TestCase):
    def test_inventory(self):
        from analyze import required
        self.assertEqual(len(required(2000,1)),42)
        self.assertEqual(len(required(611756,1)),46)
        self.assertEqual(len(required(611756,8)),34)
        self.assertEqual(len(required(611756,32)),36)

    def test_generation(self):
        s=prepare.transform((HERE.parent/'graph_query_20260923/graph_bench.cu').read_text())
        self.assertIn('const int nodes, slots, bundle',s)
        self.assertIn('cudaMemcpyAsync(hd+size_t(j)*slots,outdis',s)
        self.assertIn('for(int j=0;j<bundle;++j)enqueue(radius,j)',s)
        self.assertNotIn('nodes=111',s)
        compile(prepare.runner((HERE.parent/'graph_query_20260923/run.py').read_text()),'run_scale.py','exec')
        with self.assertRaises(AssertionError):prepare.transform('wrong source')
        # Existing helper modules alter sys.path; keep standalone CLI imports valid.
        subprocess.run([sys.executable,str(HERE/'analyze.py'),'--help'],check=True,stdout=subprocess.DEVNULL)

    def test_cpu_oracle(self):
        compiler=shutil.which('c++');self.assertIsNotNone(compiler)
        (HERE/'local').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=HERE/'local') as tmp:
            p=Path(tmp);rng=random.Random(932);rows=[b'',b'kitten',b'sitting',b'\xff']
            rows += [bytes(rng.choice([97,98,255]) for _ in range(rng.randrange(14))) for _ in range(16)]
            (p/'data').write_bytes(f'14 {len(rows)} 6\n'.encode()+b'\n'.join(rows)+b'\n')
            (p/'qids').write_text(str(len(rows))+'\n'+'\n'.join(map(str,range(len(rows))))+'\n')
            subprocess.run([compiler,'-std=c++17','-O2',str(HERE/'oracle.cpp'),'-o',str(p/'oracle')],check=True)
            subprocess.run([str(p/'oracle'),str(p/'data'),str(p/'qids'),str(p/'out')],check=True,stdout=subprocess.DEVNULL)
            self.assertEqual((p/'out').read_bytes(),bytes(fixture.distance(a,b) for a in rows for b in rows))

if __name__=='__main__':unittest.main()
