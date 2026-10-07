#!/usr/bin/env python3
"""CPU regressions of recovery policy and frozen K10 comparison admission."""
import importlib.util
import copy
import hashlib
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

class K10Statistics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root=Path(__file__).resolve().parent
        spec=importlib.util.spec_from_file_location('k10_statistics',root/'summarize_k10.py')
        cls.s=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.s)
        evidence=root/'evidence/recovery'
        cls.rows=json.loads((evidence/'K10_FORMAL_ROWS.json').read_text())['rows']
        cls.contract=json.loads((evidence/'K10_EXECUTION_CONTRACT.json').read_text())
        cls.policy=json.loads((root/'ADMISSION_POLICY.json').read_text())
        cls.controls={r['case']:r for r in json.loads((evidence/'HOOK_CONTROL_COMPLETE.json').read_text())['summary']}
        cls.group=next(g for g in cls.s.group_rows(cls.rows).values() if g[0]['method']=='O_MASK')

    def test_duplicate_labels_and_missing_round_are_fatal(self):
        with self.assertRaisesRegex(ValueError,'重复逻辑标签'):
            self.s.group_rows(self.group+[copy.deepcopy(self.group[0])])
        with self.assertRaisesRegex(ValueError,'缺轮或重复轮'):
            self.s.group_rows(self.group[:-1])

    def test_one_bad_round_keeps_all_six_and_blocks_group(self):
        gates={r['label']:self.s.row_gates(r,self.policy,self.controls) for r in self.group}
        bad=gates[self.group[0]['label']];bad['strict_quality']=False;bad['reasons']=['strict_quality_failed']
        stats=self.s.describe(self.group,gates)
        self.assertFalse(stats['complete_quality_and_timer_comparable'])
        self.assertEqual(len(stats['round_pass_ms']),6)

    def test_unreachable_target_remains_diagnostic_after_full_quality(self):
        row=copy.deepcopy(self.group[0]);row['anchors']=[1.];row['development_unreachable']=[1.]
        self.assertEqual(self.s.target_status(row),{'1.0':'diagnostic_only'})

    def test_field_only_and_member_failures_are_separate(self):
        row=copy.deepcopy(self.group[0]);row['quality'].update(output_contract_pass=False,
            distance_tolerance_pass=False,complete_gate_pass=False)
        row['admission']['strict_quality_admitted']=False
        gates=self.s.row_gates(row,self.policy,self.controls)
        self.assertIn('fields_only_failed',gates['reasons']);self.assertNotIn('members_incomplete',gates['reasons'])

    def test_large_call_missing_window_is_not_passing(self):
        row=next(r for r in self.rows if 'throughput_decline_over_10pct' not in r['stability'])
        gates=self.s.row_gates(row,self.policy,self.controls)
        self.assertFalse(gates['throughput_observable']);self.assertIsNone(gates['throughput_declined'])

    def test_observer_hash_and_cost_failure_have_distinct_reasons(self):
        hashed=next(r for r in self.rows if r['observer'].get('cases')==[17])
        cost=next(r for r in self.rows if r['observer'].get('cases')==[11])
        a=self.s.row_gates(hashed,self.policy,self.controls);b=self.s.row_gates(cost,self.policy,self.controls)
        self.assertIn('observer_hash_mismatch',a['reasons']);self.assertNotIn('observer_upper_unproven',a['reasons'])
        self.assertIn('observer_upper_unproven',b['reasons']);self.assertNotIn('observer_hash_mismatch',b['reasons'])

    def test_matched_B_mismatch_blocks_pair(self):
        left=copy.deepcopy(self.group);right=copy.deepcopy(self.group)
        for i,(a,b) in enumerate(zip(left,right)):
            a['method']='GTS_ORIG';a['B']=1;b['B']=32
            a['position']=0 if i%2 else 2;b['position']=1
        stats={'complete_quality_and_timer_comparable':True,'reason_counts':{}}
        p=self.s.compare(left,right,stats,stats,self.contract)
        self.assertFalse(p['comparable']);self.assertIn('matched_B_mismatch',p['reasons'])

    def test_different_bulk_chunks_compare_whole_pass(self):
        left=copy.deepcopy(self.group);right=copy.deepcopy(self.group)
        for i,(a,b) in enumerate(zip(left,right)):
            a.update(method='FAISS_FLAT',protocol='bulk',B=10000,position=0 if i%2 else 2)
            b.update(protocol='bulk',B=32,position=1)
        stats={'complete_quality_and_timer_comparable':True,'reason_counts':{}}
        p=self.s.compare(left,right,stats,stats,self.contract)
        self.assertTrue(p['comparable']);self.assertFalse(p['same_B']);self.assertEqual(p['protocol'],'bulk_whole_pass')

    def test_input_hash_drift_is_fatal(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);e=root/'evidence/recovery';e.mkdir(parents=True)
            source=Path(__file__).resolve().parent/'evidence/recovery'
            (e/'PUBLICATION.json').write_bytes((source/'PUBLICATION.json').read_bytes())
            (e/'K10_FORMAL_ROWS.json').write_text('changed input')
            with self.assertRaisesRegex(ValueError,'公开输入SHA改变'):
                self.s.analyze(root)

    def test_registered_replacement_cannot_use_another_process(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);e=root/'evidence/recovery';e.mkdir(parents=True)
            source=Path(__file__).resolve().parent
            for name in ['K10_FORMAL_ROWS.json','K10_COMPLETION.json','K10_EXECUTION_CONTRACT.json',
                         'MATCHED_POLICY.json','BULK_POLICY.json','HOOK_CONTROL_COMPLETE.json','PUBLICATION.json']:
                (e/name).write_bytes((source/'evidence/recovery'/name).read_bytes())
            (root/'ADMISSION_POLICY.json').write_bytes((source/'ADMISSION_POLICY.json').read_bytes())
            data=json.loads((e/'K10_FORMAL_ROWS.json').read_text())
            row=next(r for r in data['rows'] if 'contamination_replacement' in r)
            other=next(r for r in data['rows'] if r['method']==row['method'] and 'contamination_replacement' not in r)
            row['measurement_label']=other['measurement_label']
            (e/'K10_FORMAL_ROWS.json').write_text(json.dumps(data))
            pub=json.loads((e/'PUBLICATION.json').read_text())
            pub['K10_FORMAL_ROWS.json']['public_sha256']=hashlib.sha256((e/'K10_FORMAL_ROWS.json').read_bytes()).hexdigest()
            (e/'PUBLICATION.json').write_text(json.dumps(pub))
            with self.assertRaisesRegex(ValueError,'污染替代轮来源改变'):
                self.s.analyze(root)

if __name__=='__main__':unittest.main()
