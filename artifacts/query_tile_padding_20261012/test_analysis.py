"""CPU-only regression tests for the predeclared causal classifier."""
import copy
import json
from pathlib import Path
import unittest
import subprocess
import sys
from analyze import fit, distribution

C=json.loads((Path(__file__).parent/'CONTRACT.json').read_text())
U=C['workload']['useful_ops_per_query']

def rows(traffic='reuse',constant=False):
    result={}
    for b in C['workload']['B']:
        tiles=max(1,b//64)
        result[str(b)]={
            'executed_FP32_proxy':64*U*(b if constant else tiles),
            'DRAM_bytes':4e9*(b if traffic=='decoupled' else tiles),
            'geometry':dict(normalized_sha256='fixed',block=[256,1,1],grid=[376,tiles,1]),
        }
    return result

class Analysis(unittest.TestCase):
    def test_analysis_import_cannot_shadow_campaign_with_legacy_module(self):
        subprocess.run([sys.executable,'-c','import analyze, campaign; from pathlib import Path; assert Path(campaign.__file__).parent == Path.cwd(); assert len(campaign.jobs("ncu"))==8'],cwd=Path(__file__).parent,check=True)

    def test_perfect_compute_scaling_with_reuse_is_partial(self):
        r=fit(rows(),C)
        self.assertEqual(r['decision'],'PARTIAL_PADDING')
        self.assertEqual(r['models']['T64']['median_relative_error'],0)
        self.assertTrue(r['geometry_support']['passed'])
        self.assertFalse(r['traffic']['passed_decoupling_gate'])

    def test_confirmation_requires_traffic_and_independent_geometry(self):
        data=rows('decoupled')
        self.assertEqual(fit(data,C)['decision'],'CONFIRM_PADDING')
        data['128']['geometry']['normalized_sha256']='switch'
        self.assertEqual(fit(data,C)['decision'],'PARTIAL_PADDING')

    def test_constant_inflation_is_rejected(self):
        self.assertEqual(fit(rows(constant=True),C)['decision'],'REJECT_PADDING')

    def test_only_frozen_models_and_fit_points(self):
        data=rows();result=fit(data,C)
        self.assertEqual(set(result['models']),{'T64','T16','T32','T128','M0'})
        changed=copy.deepcopy(data);changed['128']['executed_FP32_proxy']*=7
        self.assertEqual(fit(changed,C)['models'],result['models'])

    def test_six_positive_processes_are_required(self):
        with self.assertRaises(AssertionError):distribution([1]*5)
        with self.assertRaises(AssertionError):distribution([1]*5+[float('nan')])
        self.assertEqual(distribution([1,2,3,4,5,6])['median'],3.5)

if __name__=='__main__':unittest.main()
