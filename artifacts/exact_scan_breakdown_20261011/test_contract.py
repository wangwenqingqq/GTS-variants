#!/usr/bin/env python3
"""Small controls for calibration, statistics and exact scope before GPU work."""
import unittest,json
from pathlib import Path
import numpy as np
C=json.loads((Path(__file__).parent/'CONTRACT.json').read_text())
class Tests(unittest.TestCase):
    def test_fixed_work(self):
        self.assertEqual(C['workload']['radius_bits'],'0x3f34a3d8');self.assertEqual(C['roofline']['logical_bytes'],1000000*960*4);self.assertEqual(C['roofline']['approx_ops'],1000000*(3*960-1))
    def test_sum_budget(self):
        b=C['budget'];self.assertEqual(sum(v for k,v in b.items() if k!='max_GPU_processes'),b['max_GPU_processes'])
    def test_native_scope(self):
        s=(Path(__file__).parent/'probe.cu').read_text();self.assertIn('else s.range(query,radius',s);self.assertIn('thrust::make_transform_iterator',s);self.assertNotIn('cublas',s)
    def test_counts_not_traffic(self):
        self.assertIn('logical payload always distinct',C['roofline']['traffic']);self.assertIn('inconclusive',C['gates']['confidence']);self.assertIn('no automatic replacement',C['stop'])

class RejectedEvidence(unittest.TestCase):
    def test_metadata_and_payload_negative_cases(self):
        import tempfile
        from campaign import metadata,vector,check_copy
        from unittest.mock import patch
        root=Path(__file__).parent
        with tempfile.TemporaryDirectory(prefix='check_',dir=root) as name:
            prefix=Path(name)/'out';job=dict(kind='probe',N=1000000,D=960,mode='THRESHOLD_COUNT',diagnostic=0)
            rows=[dict(ack_ms='1') for _ in range(40)]
            valid=dict(N=1000000,D=960,mode='THRESHOLD_COUNT',diagnostic=False,build_ms=1,warmup_ms=8,release_ms=1,context_ms=1,measured_pass_ms=32)
            meta=Path(str(prefix)+'.meta.json');meta.write_text(json.dumps(valid));metadata(prefix,job,rows)
            meta.write_text(json.dumps({**valid,'diagnostic':True}));metadata(prefix,{**job,'diagnostic':1},rows)
            with self.assertRaises(AssertionError):metadata(prefix,job,rows)
            for delta in (dict(N=999),dict(D=128),dict(mode='READ_ONLY'),dict(diagnostic=True),dict(measured_pass_ms=float('inf')),dict(measured_pass_ms=31)):
                meta.write_text(json.dumps({**valid,**delta}))
                with self.assertRaises(AssertionError):metadata(prefix,job,rows)
            Path(str(prefix)+'.ids.i32').write_bytes(b'\x00')
            with self.assertRaises(AssertionError):vector(prefix,'.ids.i32','<i4')
            qids=list(range(32));copyjob={**job,'mode':'COPY'}
            copyrows=[dict(query=str(i),qid=str(i if i<8 else i-8),warmup=str(int(i<8)),count='0',offset='0',ack_ms='1',p0='0.5',**{'p'+str(k):'-1' for k in range(1,7)}) for i in range(40)]
            meta.write_text(json.dumps({**valid,'mode':'COPY'}))
            for suffix in ('.ids.i32','.dist.f32','.native_squared.f64'):Path(str(prefix)+suffix).write_bytes(b'')
            with patch('campaign.table',return_value=copyrows):check_copy(prefix,copyjob,qids)
            for bad in (copyrows[:-1],[{**r,'p0':'inf'} for r in copyrows],[{**r,'warmup':'0'} for r in copyrows]):
                with patch('campaign.table',return_value=bad),self.assertRaises(AssertionError):check_copy(prefix,copyjob,qids)

    def test_deleted_pass_job_cannot_unlock_next_stage(self):
        from campaign import verify_stage,jobs
        from unittest.mock import patch
        root=Path('/unused');cal={'960':{'mid':{'radius':1.0}}};expected=jobs(cal,'qualification')
        records={'RESULTS.json':dict(complete=True,registration_sha256='h',rows=[]),'REGISTERED.json':dict(prepared_sha256='h',ready_sha256='h',contract_sha256='h',jobs=expected,binaries={},gpu='private-device',numa=0,source_hashes={'compiled-source':'h'}), 'READY.json':dict(contract_sha256='h',calibration=cal),'BUILD.json':dict(binaries={})}
        with patch('campaign.read',side_effect=lambda p:records[p.name]),patch('campaign.sha',return_value='h'),patch('campaign.sources',return_value={'compiled-source':'h'}),self.assertRaises(AssertionError):verify_stage(root,'qualification',root/'READY.json','private-device',0)

if __name__=='__main__':unittest.main()
