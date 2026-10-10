#!/usr/bin/env python3
"""Tiny ownership checks for exact duplicates, holes, split and no global movement."""
import unittest,json,tempfile
from pathlib import Path
import numpy as np
from update import Ownership,bind_static
from run import sha

class UpdateTest(unittest.TestCase):
    def test_proof_binding_and_checkpoint_tamper(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);checkpoint=root/'initial_AB_CHECKPOINT.json';checkpoint.write_text('{}')
            proof=root/'PROOF.json';proof.write_text(json.dumps({'raw_files':{checkpoint.name:sha(checkpoint)}}))
            v=dict(passed=True,proof_sha256=sha(proof),result_hashes={})
            bind_static(root,v)
            with self.assertRaises(AssertionError):bind_static(root,{**v,'proof_sha256':'wrong'})
            checkpoint.write_text('{"qids": [1]}')
            with self.assertRaises(AssertionError):bind_static(root,v)
    def test_holes_and_duplicate_occurrences(self):
        occ=np.arange(256,dtype=np.int64);scores=np.zeros((8,256));m=Ownership(occ,occ.astype(np.int32),scores,1,240,300)
        m.apply(dict(step=0,action='delete',occurrence=10),10)
        m.apply(dict(step=1,action='insert',occurrence=256),10)
        self.assertEqual(m.owner[256],0);self.assertEqual(m.slot[256],10);self.assertEqual(m.owner[10],-1);self.assertEqual(m.nb,2);self.assertEqual(m.splits,0);self.assertEqual(len(m.moved),0)
        for i in (0,1,11,239):self.assertEqual(m.slot[i],i)
    def test_split_preserves_retained_slots(self):
        occ=np.arange(256,dtype=np.int64);scores=np.tile(np.arange(256,dtype=np.float64)**2,(8,1));m=Ownership(occ,occ.astype(np.int32),scores,4,256,300)
        events=[dict(step=1,action='insert',occurrence=256,vector_original_row=0)]
        m.apply(events[0],0);self.assertEqual(m.nb,2);self.assertEqual(m.splits,1);self.assertEqual(m.count[:2].tolist(),[128,129]);self.assertEqual(len(m.moved),129)
        for i in range(127):self.assertEqual(m.owner[i],0);self.assertEqual(m.slot[i],i)
        self.assertEqual(m.slot[256],127)
        end_occ=np.r_[occ,256];end_line=np.r_[occ,0];m.validate_delta(events,end_occ,end_line,occ)
        refs=np.tile(scores[0],(32,1));qs=[0]*32;r=m.query(refs,qs,1);self.assertTrue(all(q['false_prune_blocks']==0 for q in r))
    def test_delete_buffer_insert_without_merging_duplicates(self):
        occ=np.arange(4,dtype=np.int64);scores=np.zeros((8,4));m=Ownership(occ,occ.astype(np.int32),scores,1,224,12)
        m.apply(dict(step=1,action='insert',occurrence=4),0);m.apply(dict(step=2,action='delete',occurrence=4),0)
        self.assertEqual(m.count[0],4);self.assertEqual(m.owner[0],0);self.assertEqual(m.owner[4],-1)
        with self.assertRaises(AssertionError):m.apply(dict(step=3,action='delete',occurrence=4),0)
if __name__=='__main__':unittest.main()
