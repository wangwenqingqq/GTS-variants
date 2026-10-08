#!/usr/bin/env python3
"""CPU gates for paired ordering and exact region/object work attribution."""
import itertools
import json
from pathlib import Path
import tempfile
import unittest

from leaf_distribution import distribution
from run_warp import ORDERS
from curate_warp import curate,RESULTS


class WarpTests(unittest.TestCase):
    def test_missing_optional_publication_rebuild(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);raw=root/'raw';raw.mkdir()
            source=dict(build=['/tmp/campaign/controllers/group/run/native_timed/region_exec'],
                        test_warp_build=['/tmp/code/diagnostics/region_warp_20261008/test_warp.cu'])
            (raw/'SOURCE.json').write_text(json.dumps(source))
            for name in RESULTS:(raw/name).write_text('{}')
            curate(raw,root/'out','results')
            receipt=json.loads((root/'out/PUBLICATION_RESULTS.json').read_text())
            self.assertEqual(receipt['missing_optional_receipts'],['ARTIFACT_CHECK.json'])
            self.assertNotIn('ARTIFACT_CHECK.json',receipt['files'])

    def test_direction_balance(self):
        self.assertEqual(len(ORDERS),6)
        for order in ORDERS:self.assertEqual(sorted(order),list(range(5)))
        for i,j in itertools.combinations(range(5),2):
            self.assertEqual(sum(o.index(i)<o.index(j) for o in ORDERS),3)

    def test_region_work_and_missing_mapping(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'stdout'
            plan=dict(epoch=1,n=4,regions=[dict(root=0,leaves=[1,2]),dict(root=3,leaves=[4])],
                      leaf_objects=[[1,[0,1]],[2,[2]],[4,[3]]])
            work=dict(epoch=1,n=4,qid=0,leaves=[0,1,1,0,0],objects=[0,1,1,0])
            path.write_text('REGION_PLAN '+json.dumps(plan)+'\nREGION_WORK '+json.dumps(work)+'\n')
            got=distribution(path)
            self.assertEqual(got['buckets']['2-8'],dict(query_regions=1,candidate_objects=3,distance_evaluations=2))
            self.assertEqual(got['buckets']['0']['query_regions'],1)
            work['objects'][3]=1
            path.write_text('REGION_PLAN '+json.dumps(plan)+'\nREGION_WORK '+json.dumps(work)+'\n')
            with self.assertRaises(AssertionError):distribution(path)
            path.write_text('REGION_WORK '+json.dumps(work)+'\n')
            with self.assertRaises(KeyError):distribution(path)


if __name__=='__main__':unittest.main()
