#!/usr/bin/env python3
"""Offline checks; the failure-path regression must not access a GPU."""
import contextlib,io,json,os,signal,subprocess,sys,tempfile,unittest
from pathlib import Path
import prepare
HERE=Path(__file__).resolve().parent
class Checks(unittest.TestCase):
    def setUp(self):(HERE/'local').mkdir(exist_ok=True)
    def test_generation(self):
        base=prepare.scale.transform((HERE.parent/'graph_query_20260923/graph_bench.cu').read_text())
        t=prepare.transform(base)
        a='        ck(cub::DeviceReduce::Sum(temp,tempbytes,hits,hit_count,slots,stream));'
        z='        projectBounded<<<(slots+511)/512,512,0,stream>>>(count,outids,outdis,ids,ds,is_delete_prefix);'
        self.assertIn(base[base.index(a):base.index(z)+len(z)],t)
        self.assertEqual(t.count('fusedResultSelect<<<1,512'),1)
        self.assertIn('mode=="D"||mode=="E"',t)
        self.assertIn('*candidates<=capacity && capacity<=111111',prepare.selector())
        with self.assertRaises(AssertionError):prepare.transform(base+'\n')
        original=(HERE.parent/'fused_result_20260923/fused_result.cuh').read_text()
        self.assertEqual(prepare.selector().replace('int capacity, ','').replace('*candidates<=capacity && capacity<=111111','*candidates<=111'),original)

    def test_telemetry_failure_reaps_owned_child(self):
        raw=prepare.scale.runner((HERE.parent/'graph_query_20260923/run.py').read_text())
        code=prepare.runner(raw);compile(code,'run_fusion.py','exec')
        with tempfile.TemporaryDirectory(dir=HERE/'local') as tmp:
            p=Path(tmp).resolve()
            for d in ['runs','fixtures','bin']:(p/d).mkdir()
            (p/'fixtures/data.txt').write_text('test\n');(p/'fixtures/queries.qid').write_text('1\n0\n')
            for name in ['graph_bench','nvidia-smi']:
                f=p/'bin'/name;f.write_text('#!/bin/sh\nexec sleep 60\n');f.chmod(0o755)
            file=p/'run_fusion.py';file.write_text(code);runner=prepare.module('mock_gpu_runner',file)
            calls=0
            def fake_snapshot(gpu):
                nonlocal calls
                calls+=1
                if calls==2:raise subprocess.TimeoutExpired('fake-nvml',15)
                return {'apps':'','gpu':'mock'}
            runner.snapshot=fake_snapshot
            old=os.environ['PATH'];os.environ['PATH']=str(p/'bin')+os.pathsep+old
            try:
                with contextlib.redirect_stdout(io.StringIO()):ok=runner.execute(p,'0','timeout_probe','B',4,1,0,'clean',False)
            finally:os.environ['PATH']=old
            self.assertFalse(ok);r=json.loads((p/'runs/timeout_probe/receipt.json').read_text())
            self.assertEqual(r['stop_reason'],'GPU telemetry failure');self.assertEqual(r['exit_code'],-signal.SIGTERM)
            with self.assertRaises(ProcessLookupError):os.kill(r['pid'],0)

            # An unexpected collector exception must also reap the owned process.
            calls=0
            def unexpected(gpu):
                nonlocal calls
                calls+=1
                if calls==2:raise RuntimeError('injected collector failure')
                return {'apps':'','gpu':'mock'}
            runner.snapshot=unexpected;os.environ['PATH']=str(p/'bin')+os.pathsep+old
            try:
                with self.assertRaises(RuntimeError):runner.execute(p,'0','unexpected','B',4,1,0,'clean',False)
                failure=json.loads((p/'runs/unexpected/collector_failure.json').read_text())
                with self.assertRaises(ProcessLookupError):os.kill(failure['owned_pid'],0)
                # Spawn failure happens before a benchmark PID exists; monitor cleanup still runs.
                calls=0;(p/'bin/graph_bench').unlink()
                with self.assertRaises(FileNotFoundError):runner.execute(p,'0','spawn_failure','B',4,1,0,'clean',False)
                self.assertIsNone(json.loads((p/'runs/spawn_failure/collector_failure.json').read_text())['owned_pid'])
            finally:os.environ['PATH']=old

    def test_missing_phase_blocks_timing(self):
        from unittest.mock import patch
        import types
        fake=types.SimpleNamespace(execute=None,snapshot=None)
        with patch.dict(sys.modules,{'run_fusion':fake,'check':types.SimpleNamespace(check=None)}):
            suite=prepare.module('fusion_suite_test',HERE/'suite.py')
        with tempfile.TemporaryDirectory(dir=HERE/'local') as tmp:
            p=Path(tmp);(p/'bin').mkdir();(p/'bin/graph_bench').write_bytes(b'not a GPU executable')
            case=p/'cases/n2000_k1';(case/'fixtures').mkdir(parents=True)
            (case/'fixtures/manifest.json').write_text('{"file_sha256":{}}')
            with self.assertRaises(FileNotFoundError):suite.admit(p,case,'timing')
            (case/'selector_complete.json').write_text('{"complete":true,"binary_sha256":"stale"}')
            with self.assertRaises(AssertionError):suite.admit(p,case,'timing')
if __name__=='__main__':unittest.main()
