#!/usr/bin/env python3
"""Check portable receipts, exact-source bindings, counts, plots and delivery hashes."""
import argparse
import csv
import json
from pathlib import Path
import numpy as np
from ball import HERE,sha,save,sources,stats,summarize,decision


def load(p):return json.loads(p.read_text())


def main(seal=False):
    root=HERE;c=load(root/'CONTRACT.json');p=load(root/'evidence/PROOF.json');v=load(root/'evidence/VERIFY.json')
    reg=load(root/'evidence/REGISTERED.json');build=load(root/'evidence/BUILD.json')
    assert p['passed'] and v['passed'] and p['source_hashes']==v['source_hashes']==reg['source_hashes']==sources()
    assert reg['contract_sha256']==sha(root/'CONTRACT.json') and v['proof_sha256']==sha(root/'evidence/PROOF.json')
    assert v['verification_source_sha256']==sha(root/'verify_ball.py') and build['pairs_source_sha256']==sha(root/'pairs.cpp')
    assert build['library_sha256']==p['raw_files']['pairs.so']
    assert v['scalar_centers_checked']==8192 and v['center_member_pairs_recomputed']==2000000 and v['query_center_pairs_recomputed']==262144
    assert v['all_rows_and_summaries_reconstructed'] and v['global4_counts_reconstructed'] and v['all_query_center_scores_match_reference']
    assert v['numerical_tests_passed']==build['numerical_tests_passed']==11 and v['false_prune']==p['false_prune']==0
    assert p['partition_proof_sha256']==c['partition_proof_sha256']==sha(root.parent/'certificate_aware_partition_20261010/evidence/STATIC_PROOF.json')
    assert p['partition_verification_sha256']==c['partition_verification_sha256']==sha(root.parent/'certificate_aware_partition_20261010/evidence/STATIC_VERIFY.json')
    assert p['prior_score_proof_sha256']==c['prior_score_proof_sha256'] and p['prior_score_verification_sha256']==c['prior_score_verification_sha256']
    curated=load(root/'evidence/CURATION.json');assert curated['passed']
    for r in curated['files']:assert sha(root/r['published_file'])==r['sha256'] and r['transform']=='byte-identical'
    for original,published in [('LOCAL_BALL_STATS.json','summary/LOCAL_BALL_STATS.json'),('SUMMARY_COMPARISON.json','query/SUMMARY_COMPARISON.json')]+[(n,'evidence/'+n) for n in ('REGISTERED.json','BUILD.json','DECISION.json','initial_CERTIFICATE_READY.json','first_rebuilt_CERTIFICATE_READY.json')]:
        assert sha(root/published)==p['raw_files'][original]
    query=load(root/'query/SUMMARY_COMPARISON.json');b=load(root/'summary/LOCAL_BALL_STATS.json');rows=query['rows']
    assert len(rows)==64 and len(b['rows'])==8192 and summarize(rows)==query['summary']
    assert decision(query['summary'])==load(root/'evidence/DECISION.json') and v['decision']==decision(query['summary'])['decision']
    baseline=load(root.parent/'certificate_aware_partition_20261010/query/BLOCK_SELECTIVITY.json')
    assert sha(root.parent/'certificate_aware_partition_20261010/query/BLOCK_SELECTIVITY.json')==c['global4_result_sha256']
    for name in c['snapshots']:
        rr=[r for r in rows if r['snapshot']==name];bb=[r for r in b['rows'] if r['snapshot']==name]
        gg=[r for r in baseline['rows'] if (r['snapshot'],r['strategy'],r['partition'],r['pivot_count'])==(name,'S1','P2',4)]
        assert len(rr)==32 and [r['query'] for r in rr]==list(range(32)) and [r['qid'] for r in rr]==c['inputs'][name]['qids']
        assert p['bindings'][name]['queries']==c['inputs'][name]['qids'] and p['bindings'][name]['data_sha256']==c['inputs'][name]['data_sha256']
        assert len(bb)==4096 and [r['block'] for r in bb]==list(range(4096)) and sum(r['size'] for r in bb)==1000000
        assert set(r['size'] for r in bb)=={244,245} and len({r['center_occurrence'] for r in bb})==4096
        assert next(s['covering_radius'] for s in b['summary'] if s['snapshot']==name)==stats([r['cover_radius_upper'] for r in bb])
        assert load(root/'evidence'/(name+'_CERTIFICATE_READY.json'))['certificate_sha256']==p['raw_files'][name+'_certificate.npz']
        for r,g in zip(rr,gg):
            assert r['qid']==g['qid'] and r['total_blocks']==4096 and r['global4_surviving_blocks']==g['surviving_blocks']
            assert r['global4_surviving_objects']==g['candidate_objects_in_surviving_blocks'] and r['oracle_required_blocks']==g['oracle_required_blocks']
            assert 0<=r['oracle_required_blocks']<=r['local_ball_surviving_blocks']<=4096 and r['local_ball_false_prune']==0
            assert r['local_ball_oracle_gap']==r['local_ball_false_keep']==r['local_ball_surviving_blocks']-r['oracle_required_blocks']
            for count,fraction in [('global4_surviving_blocks','global4_survival_fraction'),('local_ball_surviving_blocks','local_ball_survival_fraction'),('oracle_required_blocks','oracle_fraction')]:assert r[fraction]==r[count]/4096
            assert r['center_distance_evals']==4096 and r['summary_bytes']==r['center_id_bytes']==32768 and r['center_coordinate_bytes']==15728640
            assert r['modeled_total_distance_evals']==4096+r['surviving_objects'] and r['modeled_total_coordinate_bytes']==r['modeled_total_distance_evals']*960*4
    assert sum(r['local_ball_surviving_blocks']>r['global4_surviving_blocks'] for r in rows)==63
    with (root/'figures/summary_survival.csv').open() as f:plot=list(csv.DictReader(f))
    assert len(plot)==6
    for r in plot:
        s=next(s['statistics'] for s in query['summary'] if s['snapshot']==r['snapshot'])
        k={'GLOBAL4':'global4_survival_fraction','LOCAL_BALL':'local_ball_survival_fraction','ORACLE':'oracle_fraction'}[r['summary']]
        assert float(r['surviving_percent'])==100*s[k]['mean'] and float(r['oracle_gap_blocks'])==(s[k]['mean']-s['oracle_fraction']['mean'])*4096
    for filename in ('local_vs_global','oracle_gap'):
        with (root/'figures'/(filename+'.csv')).open() as f:plot=list(csv.DictReader(f))
        assert len(plot)==64
        for r,q in zip(plot,rows):
            assert (r['snapshot'],int(r['query']),int(r['qid']))==(q['snapshot'],q['query'],q['qid'])
            if filename=='oracle_gap':assert int(r['oracle_gap_blocks'])==q['local_ball_oracle_gap']
            else:assert float(r['global4_percent'])==100*q['global4_survival_fraction'] and float(r['local_ball_percent'])==100*q['local_ball_survival_fraction']
    inventory={str(f.relative_to(root)):sha(f) for f in sorted(root.rglob('*')) if f.is_file() and '__pycache__' not in f.parts and f.name!='DELIVERY_MANIFEST.json'}
    if seal:(root/'DELIVERY_MANIFEST.json').write_text(json.dumps(dict(files=inventory),indent=2)+'\n')
    else:assert inventory==load(root/'DELIVERY_MANIFEST.json')['files']
    print(json.dumps(dict(passed=True,query_rows=64,block_rows=8192,false_prune=0,decision=v['decision'],files=len(inventory)+1)))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--seal',action='store_true');main(p.parse_args().seal)
