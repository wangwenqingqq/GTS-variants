"""Small CPU-only contract checks; GPU membership/sanitizer gates remain separate."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from campaign import jobs, verify_stage, vector

HERE=Path(__file__).resolve().parent
C=json.loads((HERE/'CONTRACT.json').read_text())

class Contract(unittest.TestCase):
    def test_exact_schedule_and_budget(self):
        self.assertEqual([len(jobs(s)) for s in ('qualification','keeper','primary','ncu')],[13,6,48,8])
        self.assertEqual(sum(C['budget'].values())-C['budget']['max_top_level_starts'],80)
        primary=jobs('primary')
        for r in range(1,7):
            self.assertEqual([j['B'] for j in primary if j['round']==r],C['workload']['B'][::1 if r%2 else -1])

    def test_original_epilogue_and_device_kernels_unchanged(self):
        src=(HERE/'batch.cu').read_text();old=(HERE.parent/'external_closure/range_service.cu').read_text()
        self.assertNotIn('__global__',src)
        start='        flags_kernel<<<';end='        ck(cudaStreamSynchronize(stream));'
        epilogue=old[old.index(start):old.index(end,old.index(start))+len(end)]
        self.assertIn(epilogue,src)
        self.assertIn('range(q,radius,answers[0].ids,answers[0].dist,answers[0].raw)',src)
        self.assertIn('qs[2]={batch,d}',src)

    def test_pool_schedule_does_not_duplicate_queries_in_one_batch(self):
        for B in C['workload']['B']:
            pool=list(range(32 if B<=32 else 128))
            for i in range(40):
                start=(i if i<8 else i-8)*B%len(pool)
                batch=pool[start:start+B]
                self.assertEqual(len(batch),B);self.assertEqual(len(set(batch)),B)

    def test_missing_prior_job_cannot_unlock_later_stage(self):
        with patch('campaign.read',side_effect=[dict(jobs=jobs('qualification')),dict(complete=True,registration_sha256='wrong',rows=[])]),patch('campaign.sha',return_value='real'):
            with self.assertRaises(AssertionError):verify_stage(Path('/unused'),'qualification','private',0)

    def test_truncated_binary_payload_is_rejected(self):
        with tempfile.TemporaryDirectory() as name:
            prefix=Path(name)/'out';Path(str(prefix)+'.ids.i32').write_bytes(b'1')
            with self.assertRaises(AssertionError):vector(prefix,'.ids.i32','<i4')

    def test_original_traffic_gate_is_not_silently_removed(self):
        self.assertIn('decoupled',C['gates']['CONFIRM_PADDING'])
        self.assertIn('database reuse',C['gates']['PARTIAL_PADDING'])
        self.assertEqual(C['models']['M1_tiles'],[64,16,32,128])

if __name__=='__main__':unittest.main()
