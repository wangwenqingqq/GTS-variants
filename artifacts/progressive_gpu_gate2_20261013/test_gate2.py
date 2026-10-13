"""Dependency-light numerical-envelope, accounting and boundary regression checks."""
import unittest
import tempfile
from pathlib import Path
import numpy as np
from copy import deepcopy
from analyze import classify,summarize
from campaign import validate_job_rows,validate_static_record,checked_identity,checkpoint_ids,jobs
from prepare import generate,sources,GUARD_DEPENDENCIES
from static_evidence import opcodes
class GateTests(unittest.TestCase):
    def test_decision_boundaries(self):
        self.assertEqual(classify(1.6e9,.8,.899,.1),'GO_PROGRESSIVE_GPU')
        self.assertEqual(classify(1.6e9,.8,.9,.1),'UNCLASSIFIED')
        self.assertEqual(classify(1.6e9,.90,.89,.1),'UNCLASSIFIED')
        self.assertEqual(classify(1.6e9,.901,.89,.1),'BYTE_SAVING_BUT_CONTROL_BOUND')
        self.assertEqual(classify(1.3e9,1,.99,.20),'NO_GO_PROGRESSIVE_GPU')
        self.assertEqual(classify(1.3e9,1,.99,.201),'BYTE_SAVING_BUT_CONTROL_BOUND')
        self.assertEqual(classify(2.21e9,.65,.8,.5),'NO_GO_PROGRESSIVE_GPU')
        self.assertEqual(classify(1.8e9,.7,.8,.2),'UNCLASSIFIED')
        self.assertEqual(classify(float('nan'),.7,.8,.2),'UNCLASSIFIED')
        self.assertEqual(classify(1.2e9,.7,.8,.2,False),'UNCLASSIFIED')
    def test_paired_unit(self):
        x=summarize([{'B0':2.,'B1':3.+i,'P1':(3.+i)*.75} for i in range(6)])
        self.assertAlmostEqual(x['latency_ratio'],.75)
        self.assertAlmostEqual(x['paired_geometric_ratio'],.75)
        self.assertEqual(x['wins'],6)
        self.assertAlmostEqual(x['paired_95_CI'][1],.75)
    def test_envelope_margin(self):
        u=2**-24;gamma=32*u/(1-32*u)
        reference_gamma=960*2**-53/(1-960*2**-53)
        self.assertLess(4*(gamma/(1-gamma)+reference_gamma),2**-16)
        self.assertLess(960*32*2**-149,2**-130)
    def test_exact_qualification_set(self):
        expected=jobs('qualification',None);rows=[dict(**j,status='passed') for j in expected]
        validate_job_rows(rows,expected)
        bad=[deepcopy(rows[0]) for _ in rows]
        with self.assertRaises(AssertionError):validate_job_rows(bad,expected)
        bad=deepcopy(rows);bad[-1]=deepcopy(rows[-2])
        with self.assertRaises(AssertionError):validate_job_rows(bad,expected)
        bad=deepcopy(rows);bad[1],bad[2]=bad[2],bad[1]
        with self.assertRaises(AssertionError):validate_job_rows(bad,expected)
    def test_static_identity_binding(self):
        binaries=dict(keeper='a',keeper_diagnostic='b',candidate='c')
        record=dict(passed=True,no_GPU_starts=True,registration_sha256='r',static_tool_sha256='s',records={k:dict(container_sha256=v) for k,v in binaries.items()})
        validate_static_record(record,'r',binaries,'s')
        for field in ('registration_sha256','static_tool_sha256'):
            bad=deepcopy(record);bad[field]='wrong'
            with self.assertRaises(AssertionError):validate_static_record(bad,'r',binaries,'s')
        bad=deepcopy(record);bad['records']['candidate']['container_sha256']='wrong'
        with self.assertRaises(AssertionError):validate_static_record(bad,'r',binaries,'s')
    def test_predicated_opcode(self):
        counts=opcodes('@P0 LDL R0, [R1];\n@!P1 STL [R2], R3;\nFFMA R1, R2, R3, R4;')
        self.assertEqual(dict(counts),dict(LDL=1,STL=1,FFMA=1))
    def test_actual_p1_metadata_and_dependency_closure(self):
        _,candidate=generate()
        self.assertIn(r'\"squared_bytes\":0',candidate)
        self.assertIn(r'\"state_buffer_bytes\":',candidate)
        self.assertIn(r'\"diagnostic_mode\":',candidate)
        frozen=sources();self.assertTrue(all(k in frozen for k in GUARD_DEPENDENCIES))
        self.assertIn('artifacts/progressive_gpu_gate2_20261013/static_evidence.py',frozen)
    def test_fixture_workload_identity(self):
        job=jobs('qualification',None)[0]
        checked=dict(passed=True,job=job,iterations=100,stream_slots=2,empty_answers=2,exact_boundary_pairs=1,stage_rejects=[1]*4,subnormal_cases=True)
        checked_identity(checked,job)
        bad=deepcopy(checked);bad['job']=jobs('qualification',None)[1]
        with self.assertRaises(AssertionError):checked_identity(bad,job)
        bad=deepcopy(checked);bad['stage_rejects'][3]=0
        with self.assertRaises(AssertionError):checked_identity(bad,job)
    def test_checkpoint_tail_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'ids.i32';want=np.array([2,5,7],dtype='<i4');path.write_bytes(want.tobytes())
            checkpoint_ids(path,want)
            for size in (1,2,3):
                path.write_bytes(want.tobytes()+b'\0'*size)
                with self.assertRaises(AssertionError):checkpoint_ids(path,want)
if __name__=='__main__':unittest.main()
