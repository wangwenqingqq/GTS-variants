#!/usr/bin/env python3
"""Standard-library regression of recovery policy using mocked GPU evidence."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

stub=types.ModuleType('qualification');stub.BASE=Path('/nonexistent-recovery-fixture')
stub.native_ivf=None;stub.check_output=None;sys.modules['qualification']=stub
spec=importlib.util.spec_from_file_location('campaign_policy',Path(__file__).with_name('campaign10k.py'))
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)

def row(method,correct=True,growth=0,anchors=(),unreachable=()):
    q={'output_contract_pass':True,'recall_tie_aware':1. if correct else .98,'minimum_query_recall':1. if correct else .875,'complete_gate_pass':correct}
    r={'method':method,'label':method,'quality':q,'actual_Q':10000,
       'stability':{'memory_growth_gate_pass':growth<=64*(1<<20)},
       'anchors':list(anchors),'development_unreachable':list(unreachable),'receipt':{'runtime_valid':True}}
    r['admission']=c.admission(r,True);return r

class RecoveryPolicy(unittest.TestCase):
    def test_native_rejection_is_local_and_other_method_schedulable(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);(root/'outputs').mkdir();(root/'fixtures').mkdir()
            (root/'fixtures/GIST_dev1024.qid').write_text('1\n7\n')
            (root/'oracle_GIST_dev1024.json').write_text(json.dumps({'Q':1,'records':[{'qid':7}]}))
            for method in ('FAISS_FLAT','CAGRA'):
                prefix=root/'outputs'/method
                Path(str(prefix)+'.bin').write_bytes(method.encode())
                Path(str(prefix)+'.json').write_text(json.dumps({'Q':1,'pass_ms':1.}))
                Path(str(prefix)+'.windows.csv').write_text('processed,wall_s,cpu_s,device_used_bytes,rss_bytes\n0,0,0,1,1\n1,1,1,1,1\n')
                Path(str(prefix)+'.cpu.json').write_text('{}')
            native=types.SimpleNamespace(read_qids=lambda p:types.SimpleNamespace(tolist=lambda:[7]),load_data=lambda p:'mock-data')
            qualities=[row('FAISS_FLAT',False)['quality'],row('CAGRA')['quality']]
            retained=[]
            with patch.object(c,'ROOT',root),patch.object(c,'native_ivf',native),patch.object(c,'check_output',side_effect=qualities),\
                 patch.object(c,'commands',return_value=[sys.executable]),patch.object(c,'invoke',return_value={'binary_sha256':'mock','wall_s':1,'runtime_valid':True,'exit_code':0,'stop_reason':None}):
                for method in ('FAISS_FLAT','CAGRA'):
                    r={'label':method,'dataset':'GIST','method':method,'K':8,'B':32,'config':{},'anchors':[.99] if method=='CAGRA' else []}
                    retained.append(c.collect(types.SimpleNamespace(data_root=root),r,'dev1024'))
            saved=json.loads((root/'outputs/FAISS_FLAT.audit.json').read_text())
            self.assertFalse(saved['admission']['strict_quality_admitted'])
            self.assertEqual(retained[1]['admission']['target_admission']['0.99'],'admitted')
            self.assertTrue((root/'outputs/CAGRA.audit.json').exists())
    def test_wrong_candidate_cannot_promote(self):
        d=row('O_MASK',False)['admission']
        self.assertTrue(d['candidate_promotion_blocked']);self.assertFalse(d['candidate_stable'])
    def test_missed_ann_target_is_ineligible(self):
        self.assertEqual(row('CAGRA',False,anchors=(.99,))['admission']['target_admission']['0.99'],'missed_target')
    def test_unreachable_100_is_diagnostic_even_after_empirical_pass(self):
        self.assertEqual(row('CAGRA',anchors=(1.,),unreachable=(1.,))['admission']['target_admission']['1.0'],'diagnostic_only')
    def test_retained_growth_rejects_stability(self):
        d=row('O_MASK',growth=65*(1<<20))['admission']
        self.assertFalse(d['stability_admitted']);self.assertFalse(d['candidate_stable'])
    def test_changed_script_invalidates_cached_admission(self):
        with tempfile.TemporaryDirectory() as t:
            original=c.ROOT;c.ROOT=Path(t)
            try:
                script=c.ROOT/'measure.py';script.write_text('initial')
                a=types.SimpleNamespace(gpu='mock-gpu');cmd=[sys.executable,script]
                before=c.run_identity(a,cmd);script.write_text('changed')
                self.assertFalse(c.cached_admission_valid(before,c.run_identity(a,cmd)))
            finally:c.ROOT=original
    def test_changed_observer_mode_invalidates_cached_admission(self):
        with tempfile.TemporaryDirectory() as t,patch.object(c,'ROOT',Path(t)):
            a=types.SimpleNamespace(gpu='mock-gpu');cmd=[sys.executable]
            saved=c.run_identity(a,cmd,{'U10_OBSERVE':'1','U10_TREE_AUDIT':'0'})
            self.assertFalse(c.cached_admission_valid(saved,c.run_identity(a,cmd,{'U10_OBSERVE':'0','U10_TREE_AUDIT':'0'})))
            self.assertFalse(c.cached_admission_valid(saved,c.run_identity(a,cmd,{'U10_OBSERVE':'1','U10_TREE_AUDIT':'1'})))
    def test_missing_required_row_cannot_accept_comparison(self):
        rows=[row(m) for m in c.COMPLETE]
        decision=c.matrix_decision(rows,[r['label'] for r in rows]+['CAGRA'])
        self.assertFalse(decision['collection_complete']);self.assertFalse(decision['comparison_admitted'])
    def test_collected_rejected_flat_is_not_a_strict_pass(self):
        rows=[row(m,m!='FAISS_FLAT') for m in c.COMPLETE]+[row('CAGRA',anchors=(.99,))]
        decision=c.matrix_decision(rows,[r['label'] for r in rows])
        self.assertTrue(decision['collection_complete']);self.assertIn('FAISS_FLAT',decision['strict_rejected_rows'])
    def test_collected_unqualified_timer_cannot_accept_comparison(self):
        rows=[row(m) for m in c.COMPLETE]+[row('CAGRA',anchors=(.99,))]
        rows[-1]['admission']=c.admission(rows[-1],False)
        decision=c.matrix_decision(rows,[r['label'] for r in rows])
        self.assertTrue(decision['collection_complete']);self.assertFalse(decision['comparison_admitted'])
        self.assertEqual(decision['unqualified_timer_rows'],['CAGRA'])
    def test_observer_failure_does_not_poison_another_method(self):
        with tempfile.TemporaryDirectory() as t,patch.object(c,'ROOT',Path(t)):
            for name in ('HOOK_CONTROL.json','HOOK_CONTROL_REGISTERED.json'):(c.ROOT/name).write_text('{}')
            for n in ('opt_knn_bench','opt_knn_bench.cu','query_trace.hpp','knn_cutoff.cuh','knn_select.cuh','knn_verify.cuh'):(c.ROOT/n).write_text(n)
            identity=c.ROOT/'runs/hook_c0_r1_on/identity.json';identity.parent.mkdir(parents=True)
            c.save(identity,{'files':{str(p.resolve()):c.sha(p) for p in c.ROOT.iterdir() if p.is_file()}})
            c.save(c.ROOT/'HOOK_CONTROL_COMPLETE.json',{'state':'collection_complete',
                'rows_sha256':c.sha(c.ROOT/'HOOK_CONTROL.json'),'registration_sha256':c.sha(c.ROOT/'HOOK_CONTROL_REGISTERED.json'),
                'summary':[{'case':0,'dataset':'Deep','method':'O_MASK','B':32,'timer_admitted':True},
                           {'case':1,'dataset':'Deep','method':'CAGRA','B':32,'timer_admitted':False}]})
            self.assertTrue(c.observer_decision({'dataset':'GIST','method':'O_MASK','B':32,'config':{}})['qualified'])
            self.assertFalse(c.observer_decision({'dataset':'Deep','method':'CAGRA','B':32,'config':{'itopk_size':1024,'search_width':4}})['qualified'])
            self.assertFalse(c.observer_decision({'dataset':'Deep','method':'IVF_APPROX','B':32,'config':{'nlist':1024,'nprobe':16}})['qualified'])
            # A declared move with the old path kept as an alias preserves the
            # exact entry/observer hashes; changing bytes must still reject.
            alias=c.ROOT/'old_location';alias.symlink_to(c.ROOT,target_is_directory=True)
            c.save(identity,{'files':{str(alias/p.name):c.sha(p) for p in c.ROOT.iterdir() if p.is_file()}})
            self.assertTrue(c.observer_decision({'dataset':'GIST','method':'O_MASK','B':32,'config':{}})['qualified'])
            (c.ROOT/'query_trace.hpp').write_text('changed observer')
            self.assertFalse(c.observer_decision({'dataset':'GIST','method':'O_MASK','B':32,'config':{}})['qualified'])
    def test_drift_in_query_or_oracle_cannot_reuse_receipt(self):
        saved={'command':['mock'],'files':{'script':'s','query':'q','oracle':'o'}}
        self.assertFalse(c.cached_admission_valid(saved,{**saved,'files':{**saved['files'],'oracle':'new'}}))

if __name__=='__main__':unittest.main()
