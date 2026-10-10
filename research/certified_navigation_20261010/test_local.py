#!/usr/bin/env python3
"""CPU regression checks; never substitutes for device/E2 evidence."""
import importlib.util
import json
from pathlib import Path
import shutil
import struct
import tempfile
import unittest
from audit import HERE,load_index,source_audit,sha
from prepare import prepare,once
from prepare_guard import prepare as prepare_guard
from verify import result,verify

class Checks(unittest.TestCase):
    def test_probe_subset_scope(self):
        source=(HERE/'probe.py').read_text()
        self.assertNotIn('profiles_only',source)
        self.assertNotIn('--profiles-only',source)
        self.assertIn("('memcheck_G0',0,'memcheck')",source)
        self.assertIn("'API_gate_passed':not a.memory_only",source)

    def test_exact_visit_bitset_rejection(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);(root/'qids').write_text('1\n0\n')
            (root/'oracle.bin').write_bytes(struct.pack('<4iid',10,3,1,1,0,0.))
            rows=[dict(level=i,upper=None,visited=0,digest='0',visit_bits_hex='0'*((10**i+3)//4),candidates=[]) for i in range(1,6)]
            for mode in range(4):
                folder=root/('G'+str(mode));folder.mkdir()
                (folder/'receipt.json').write_text(json.dumps(dict(exit_code=0,runtime_valid=True)))
                (folder/'out.bin').write_bytes((root/'oracle.bin').read_bytes())
                (folder/'out.work.csv').write_text('qid,pivot_calls,leaf_calls,bound_tests\n0,0,0,0\n')
                (folder/'stdout.log').write_text(''.join('TRACE '+json.dumps(r)+'\n' for r in rows))
            verify(root,root/'oracle.bin',root/'qids',root/'good.json')
            self.assertTrue(json.loads((root/'good.json').read_text())['exact_visit_bitsets_checked'])
            bad=[dict(x) for x in rows];bad[0]['visit_bits_hex']='800'
            (root/'G1/stdout.log').write_text(''.join('TRACE '+json.dumps(r)+'\n' for r in bad))
            with self.assertRaises(ValueError):verify(root,root/'oracle.bin',root/'qids',root/'bad.json')
    def test_output_protocol_and_fail_closed(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'result.bin'
            def write(ids,scores):
                p.write_bytes(struct.pack('<4i',10,3,1,2)+struct.pack('<2i',*ids)+struct.pack('<2d',*scores))
            write([1,2],[0.,1.]);self.assertEqual(result(p)[1],(10,3,1,2))
            for ids,scores in [([1,1],[0.,1.]),([2,1],[1.,0.]),([2,1],[0.,0.]),([1,2],[0.,float('nan')]),([1,10],[0.,1.])]:
                write(ids,scores)
                with self.assertRaises(ValueError):result(p)
            p.write_bytes(b'bad')
            with self.assertRaises(ValueError):result(p)
    def test_frozen_queries(self):
        m=json.loads((HERE/'QUERY_MANIFEST.json').read_text())
        dev=list(map(int,(HERE/'dev32.qid').read_text().split()))
        formal=list(map(int,(HERE/'formal256.qid').read_text().split()))
        self.assertEqual(dev[0],32);self.assertEqual(formal[0],256)
        self.assertEqual(dev[1:],m['development_ids']);self.assertEqual(formal[1:],m['formal_ids'])
        self.assertFalse(set(dev[1:])&set(formal[1:]));self.assertEqual(len(set(dev[1:]+formal[1:])),288)
        self.assertEqual(sha(HERE/'dev32.qid'),m['development_sha256'])
        self.assertEqual(sha(HERE/'formal256.qid'),m['formal_sha256'])
    def test_anchor_drift(self):
        self.assertEqual(once('abc','b','d'),'adc')
        for text in ['ac','abcb']:
            with self.assertRaises(ValueError):once(text,'b','d')
    def test_guard_observer_reuse(self):
        with tempfile.TemporaryDirectory() as t:
            out=Path(t)/'guard';prepare_guard(out)
            spec=importlib.util.spec_from_file_location('test_guard',out/'guard.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
            self.assertIn('timeout=10',(out/'guard.py').read_text())
            app='21, worker, 10 MiB'
            self.assertEqual(g.classify_apps(app,{10:1,21:7},{10:1},{21:None})[0],[])
            self.assertEqual(g.classify_apps(app,{10:1},{10:1},{21:None})[0],[app])
            self.assertEqual(g.classify_apps(app,{21:7},{21:7},{21:8})[0],[app])
    def test_generator_optional_live_source(self):
        import os
        if 'GTS_UPSTREAM' not in os.environ:self.skipTest('set GTS_UPSTREAM to exercise pinned live source')
        source=Path(os.environ['GTS_UPSTREAM']);source_audit(source)
        with tempfile.TemporaryDirectory() as t:
            out=Path(t)/'generated';prepare(source,out)
            s=(out/'adapted/include/search_v2.cuh').read_text();nav=(out/'adapted/include/navigation.cuh').read_text()
            self.assertEqual(s.count('nav_begin();'),1);self.assertEqual(s.count('nav_end();'),1)
            self.assertEqual(s.count('nav_update<<<'),1);self.assertEqual(s.count('nav_keys<<<'),1)
            self.assertEqual(s.count('nav_replay_level(disk);'),1)
            self.assertIn('if(kth<INFI_DIS)disk[0]=fmin(disk[0],kth);return;',nav)
            self.assertIn('disk[i] = INFINITY;',s)
            self.assertIn('int reserved=0;',nav)
            self.assertIn('visit_bits_hex',nav)
            self.assertIn('size_t(qnum) * k * sizeof(int)',s)
            self.assertIn('uses_oracle\\\":false',(out/'bench.cu').read_text())
            changed=Path(t)/'changed';shutil.copytree(source,changed)
            with (changed/'include/config.cuh').open('a') as f:f.write('\n')
            with self.assertRaises(ValueError):source_audit(changed)
    def test_tree_ownership_optional_fixture(self):
        import os
        if 'GTS_INDEX' not in os.environ:self.skipTest('set GTS_INDEX for live ownership regression')
        p=Path(os.environ['GTS_INDEX']);n,d,h,ids,nodes,flags=load_index(p)
        self.assertEqual((n,d,h),(1000000,960,6))
        with tempfile.TemporaryDirectory() as t:
            bad=Path(t)/'bad.index';b=bytearray(p.read_bytes());struct.pack_into('<i',b,20,ids[0]);bad.write_bytes(b)
            with self.assertRaises(ValueError):load_index(bad)
            bad.write_bytes(b[:15])
            with self.assertRaises(ValueError):load_index(bad)

if __name__=='__main__':unittest.main()
