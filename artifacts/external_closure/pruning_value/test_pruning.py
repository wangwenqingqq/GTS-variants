#!/usr/bin/env python3
"""Small deterministic checks for occurrence identity and early-leaf accounting."""
import json,tempfile,unittest
from pathlib import Path
import numpy as np
from analyze import NODE,min_truth,check_answers
from build import sha

class PruningTests(unittest.TestCase):
    def test_bottom_up_with_early_leaf_and_duplicate_vectors(self):
        nodes=np.zeros(23,NODE);live=np.zeros(23,bool)
        for nid,lid,size,leaf in [(0,0,5,0),(1,0,3,1),(2,3,2,0),(21,3,1,1),(22,4,1,1)]:
            nodes[nid]['lid']=lid;nodes[nid]['size']=size;nodes[nid]['leaf']=leaf;live[nid]=True
        order=np.array([4,2,0,1,3]);ref=np.array([9.,1.,9.,0.,9.])
        truth=min_truth(nodes,live,order,ref)
        self.assertEqual(truth[0],0);self.assertEqual(truth[1],9);self.assertEqual(truth[2],0)
        self.assertEqual(truth[21],1);self.assertEqual(truth[22],0)
        # Early leaf remains unresolved when an internal descendant is rejected.
        unresolved=5-int(nodes[21]['size']);self.assertEqual(unresolved,4)
        self.assertEqual(len(order),5)  # Equal vector scores are not deduplicated instances.

    def test_full_output_gate_rejects_dropped_duplicate_instance(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);ref=root/'reference';ref.mkdir()
            scores=np.array([0.,0.,1.],'<f8');scores.tofile(ref/'0.f64')
            (ref/'REFERENCE.json').write_text(json.dumps(dict(N=3,D=128,files={'0':sha(ref/'0.f64')})))
            (root/'META.json').write_text(json.dumps(dict(N=3,D=128)))
            (root/'queries.csv').write_text('qid,query,count,offset\n0,0,2,0\n')
            np.array([1,0],'<i4').tofile(root/'ids');np.zeros(2,'<f4').tofile(root/'fields')
            self.assertEqual(len(check_answers(root,ref,[0])[0]),1)
            (root/'queries.csv').write_text('qid,query,count,offset\n0,0,1,0\n')
            np.array([0],'<i4').tofile(root/'ids');np.zeros(1,'<f4').tofile(root/'fields')
            with self.assertRaises(AssertionError):check_answers(root,ref,[0])

    def test_reject_partial_payload_and_invalid_time(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);ref=root/'reference';ref.mkdir()
            np.zeros(1,'<f8').tofile(ref/'0.f64')
            (ref/'REFERENCE.json').write_text(json.dumps(dict(N=1,D=128,files={'0':sha(ref/'0.f64')})))
            (root/'META.json').write_text(json.dumps(dict(N=1,D=128)))
            for bad in ('nan','-1','inf'):
                (root/'queries.csv').write_text('qid,query,count,offset,host_ms\n0,0,1,0,'+bad+'\n')
                np.zeros(1,'<i4').tofile(root/'ids');np.zeros(1,'<f4').tofile(root/'fields')
                with self.assertRaises(AssertionError):check_answers(root,ref,[0])
            (root/'queries.csv').write_text('qid,query,count,offset,host_ms\n0,0,1,0,1\n')
            for which in ('ids','fields'):
                np.zeros(1,'<i4').tofile(root/'ids');np.zeros(1,'<f4').tofile(root/'fields')
                with (root/which).open('ab') as f:f.write(b'x')
                with self.assertRaises(AssertionError):check_answers(root,ref,[0])

if __name__=='__main__':unittest.main()
