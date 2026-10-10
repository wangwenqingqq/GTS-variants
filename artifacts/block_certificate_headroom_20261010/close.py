#!/usr/bin/env python3
"""Close historical execution bindings without rewriting original registrations."""
import argparse,json
from pathlib import Path
from run import HERE,sha,save,outside_repo
from update import bind_static

def main(a):
    out=outside_repo(a.output);out.mkdir(exist_ok=False);sv=json.loads(a.verification.read_text());sp=bind_static(a.run,sv)
    ur=json.loads((a.update/'REGISTERED.json').read_text());up=json.loads((a.update/'PROOF.json').read_text());u=json.loads((a.update/'UPDATE_LOCALITY.json').read_text());dc=json.loads((HERE/'D_CONTRACT.json').read_text())
    assert up['passed'] and sha(a.update/'REGISTERED.json')==up['registered_sha256'] and sha(a.update/'UPDATE_LOCALITY.json')==up['update_results_sha256']
    assert ur['static_proof_sha256']==sha(a.run/'PROOF.json')==sv['proof_sha256'] and ur['static_verification_sha256']==sha(a.verification)
    assert ur['contract_sha256']==sha(HERE/'D_CONTRACT.json')==sha(a.executed_D/'D_CONTRACT.json')
    assert {name:sha(a.executed_D/name) for name in up['source_hashes']}==up['source_hashes']==ur['source_hashes']
    assert {name:sha(a.maintenance/name) for name in up['input_hashes']}==up['input_hashes']
    assert len(u['rows'])==288 and len({(r['snapshot'],r['layout'],r['strategy'],r['pivot_count'],r['active_capacity']) for r in u['rows']})==288
    for name,b in u['bindings'].items():
        cp=json.loads((a.run/(name+'_AB_CHECKPOINT.json')).read_text());assert cp['queries']==json.loads((HERE/'CONTRACT.json').read_text())['inputs'][name]['qids']
        assert {str(q):sha(a.references/name/(str(q)+'.f64')) for q in cp['queries']}==sp['bindings'][name]['reference_file_hashes']
        expected=[e for e in json.loads((a.maintenance/'PREPARED.json').read_text())['updates'] if (-1 if name=='initial' else 48)<e['step']<=(48 if name=='initial' else 216)];assert b['events']==expected
    for r in u['rows']:
        ni,nd=(10,10) if r['snapshot']=='initial' else (20,20);events=r['events'];assert r['actual_inserts']==ni and r['actual_deletes']==nd and len(events)==ni+nd
        assert [e['step'] for e in events]==[e['step'] for e in u['bindings'][r['snapshot']]['events']]
        assert [(e['action'],e['occurrence']) for e in events]==[(e['action'],e['occurrence']) for e in u['bindings'][r['snapshot']]['events']]
        changed=set(b for e in events for b in e['affected_blocks']);assert len(changed)==r['changed_blocks']==r['changed_certificates']
        assert r['moved_existing_events']==sum(e['existing_move_events'] for e in events) and r['moved_existing_objects']<=r['moved_existing_events']<=r['all_vector_move_events']
        assert r['block_splits']==r['final_total_blocks']-r['initial_total_blocks'] and r['block_merges']==r['global_repartition_events']==0
        assert r['changed_block_fraction']==r['invalidated_block_fraction']==len(changed)/r['initial_total_blocks']
        assert r['bytes_moved']==r['coordinate_payload_model_bytes']==(ni+r['all_vector_move_events'])*960*4
        assert r['certificate_write_model_bytes']==16*r['pivot_count']*r['certificate_refresh_calls']
        live=1000000
        for e in events:live+=1 if e['action']=='insert' else -1;assert live==e['live_objects']
        assert live==r['final_live_objects']==1000000
        for phase in ('initial','post_update'):
            qs=r[phase+'_queries'];assert len(qs)==32 and [q['qid'] for q in qs]==sp['bindings'][r['snapshot']]['queries']
            for q in qs:assert q['false_prune_blocks']==0 and q['surviving_block_fraction']==q['surviving_blocks']/q['total_blocks'] and q['oracle_required_blocks']<=q['surviving_blocks']
            assert r[phase+'_query_survival_mean']==sum(q['surviving_block_fraction'] for q in qs)/32 or abs(r[phase+'_query_survival_mean']-sum(q['surviving_block_fraction'] for q in qs)/32)<1e-15
    original={k:sha(a.executed_D/k) for k in up['source_hashes']};delivered={k:sha(HERE/k) for k in up['source_hashes']}
    save(out/'CLOSURE.json',dict(passed=True,scope='CPU-only historical execution/provenance and full count reconciliation; not GPU or end-to-end',static_proof_sha256=sha(a.run/'PROOF.json'),static_verification_raw_sha256=sha(a.verification),update_proof_sha256=sha(a.update/'PROOF.json'),update_results_raw_sha256=sha(a.update/'UPDATE_LOCALITY.json'),closure_source_sha256=sha(HERE/'close.py'),historical_D_source_hashes=original,delivered_D_source_hashes=delivered,static_raw_inventory_verified=True,D_actual_static_inputs_bound=True,D_288_records_reconciled=True,all_9216_post_update_queries_false_prune_zero=True,scope_corrections=['Affected slots checked after each update; untouched slots preserved by construction','Independent interval initializations, not sustained maintenance','Insert matching scans all summaries, despite local writes'],decision='CONDITIONAL',source_hardening='Historical D driver lacked explicit verification-to-proof/checkpoint pin; closure checked actual exact input bindings. Delivered entry now enforces it; original source identity retained'))
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('run','update','verification','executed-D','maintenance','references','output'):p.add_argument('--'+k,type=Path,required=True)
    main(p.parse_args())
