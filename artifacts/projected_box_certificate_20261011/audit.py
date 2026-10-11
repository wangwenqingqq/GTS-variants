#!/usr/bin/env python3
"""Audit the portable scalar artifact against its immutable execution receipts."""
import argparse
import csv
import json
from fractions import Fraction
from pathlib import Path
import numpy as np
from box import HERE,sha,sources,stats,gram_proof,summarize,decision


def load(p):return json.loads(p.read_text())


def main(seal=False):
    root=HERE;c=load(root/'CONTRACT.json');p=load(root/'evidence/PROOF.json');v=load(root/'evidence/VERIFY.json');reg=load(root/'evidence/REGISTERED.json');build=load(root/'evidence/BUILD.json')
    assert p['passed'] and v['passed'] and p['source_hashes']==v['source_hashes']==reg['source_hashes']==sources()
    assert reg['contract_sha256']==sha(root/'CONTRACT.json') and v['proof_sha256']==sha(root/'evidence/PROOF.json')
    assert v['verification_source_sha256']==sha(root/'verify_box.py') and build['library_sha256']==p['raw_files']['projection.so']
    assert v['object_projections_recomputed']==2000000 and v['query_projections_recomputed']==64 and v['boxes_reconstructed']==8192
    assert v['all_rows_and_summaries_reconstructed'] and v['represented_gram_exact_reconstructed'] and v['PCA_from_frozen_covariance_reconstructed']
    assert v['numerical_tests_passed']==build['numerical_tests_passed']==17 and v['false_prune']==p['false_prune']==0
    assert reg['nice_actual']==15 and reg['BLAS_backend']['threads_actual']==4 and len(reg['BLAS_backend']['native_objects'])==4
    curated=load(root/'evidence/CURATION.json');assert curated['passed']
    for r in curated['files']:assert sha(root/r['published_file'])==r['sha256'] and r['transform']=='byte-identical'
    targets={'PROJECTED_BOX_STATS.json':'summary/PROJECTED_BOX_STATS.json','SUMMARY_COMPARISON.json':'query/SUMMARY_COMPARISON.json'}
    targets.update({n:'directions/'+n for n in ('PCA_DIRECTIONS.json','DIRECTION_PROOF.json')})
    targets.update({n:'evidence/'+n for n in ('REGISTERED.json','BUILD.json','DECISION.json','initial_BOX_READY.json','first_rebuilt_BOX_READY.json')})
    for original,published in targets.items():assert sha(root/published)==p['raw_files'][original]
    dr=load(root/'directions/PCA_DIRECTIONS.json');dp=load(root/'directions/DIRECTION_PROOF.json')
    assert p['direction_proof_sha256']==sha(root/'directions/DIRECTION_PROOF.json') and dp['direction_json_sha256']==sha(root/'directions/PCA_DIRECTIONS.json')
    assert dp['construction_sha256']==p['raw_files']['PCA_CONSTRUCTION.npz'] and dp['source_hashes']==sources() and dp['eigh_repeated_bitwise'] and dp['initial_only']
    assert dr['training_snapshot']=='initial' and dr['training_data_sha256']==c['inputs']['initial']['data_sha256'] and dr['rows']==1000000 and dr['dimensions']==960 and dr['K']==4
    u=np.ascontiguousarray(dr['directions'],dtype=np.float64);assert u.shape==(960,4)
    gp=gram_proof(u)
    for k,val in gp.items():assert dp[k]==val
    assert [int(np.argmax(np.abs(u[:,j]))) for j in range(4)]==dr['sign_coordinates']==dp['sign_coordinates']
    assert all(u[i,j]>0 for j,i in enumerate(dr['sign_coordinates']))
    ev=np.array(dr['eigenvalues']);assert ev.shape==(960,) and np.isfinite(ev).all() and np.all(ev[:-1]>=ev[1:]) and np.all(ev[:4]-ev[1:5]>1e-10*max(1.,ev[0]))
    assert dp['eigen_residual_relative_fro']<=1e-10 and dp['gram_infinity_deviation_upper']<=1e-10 and dp['direction_matrix_bytes']==30720
    assert dp['explicit_chunk_live_array_bytes_peak']==8192*960*8+2*960*960*8+960*8 and dp['PCA_wall_seconds']>0 and dp['PCA_process_CPU_seconds']>0
    query=load(root/'query/SUMMARY_COMPARISON.json');blocks=load(root/'summary/PROJECTED_BOX_STATS.json');rows=query['rows'];assert len(rows)==64 and len(blocks['rows'])==8192
    assert summarize(rows)==query['summary'] and decision(query['summary'])==load(root/'evidence/DECISION.json') and v['decision']==decision(query['summary'])['decision']
    oldroot=root.parent/'block_local_ball_20261011'
    for path,key in [('evidence/PROOF.json','local_ball_proof_sha256'),('evidence/VERIFY.json','local_ball_verify_sha256'),('query/SUMMARY_COMPARISON.json','local_ball_result_sha256')]:assert sha(oldroot/path)==c[key]
    old=load(oldroot/'query/SUMMARY_COMPARISON.json')['rows']
    for name in c['snapshots']:
        rr=[r for r in rows if r['snapshot']==name];bb=[r for r in blocks['rows'] if r['snapshot']==name];oo=[r for r in old if r['snapshot']==name]
        assert len(rr)==32 and [r['query'] for r in rr]==list(range(32)) and [r['qid'] for r in rr]==c['inputs'][name]['qids']
        assert len(bb)==4096 and [r['block'] for r in bb]==list(range(4096)) and sum(r['size'] for r in bb)==1000000 and set(r['size'] for r in bb)=={244,245}
        for b in bb:assert len(b['lo'])==len(b['hi'])==len(b['width'])==4 and np.array_equal(np.array(b['hi'])-b['lo'],b['width']) and np.all(np.array(b['lo'])<=b['hi'])
        assert next(s['width_by_direction'] for s in blocks['summary'] if s['snapshot']==name)==[stats([b['width'][j] for b in bb]) for j in range(4)]
        assert load(root/'evidence'/(name+'_BOX_READY.json'))['projection_sha256']==p['raw_files'][name+'_projections.npz']
        assert p['bindings'][name]['data_sha256']==c['inputs'][name]['data_sha256'] and p['bindings'][name]['partition_sha256']==c['partition_sha256'][name]
        assert p['bindings'][name]['directions_json_sha256']==sha(root/'directions/PCA_DIRECTIONS.json')
        for r,o in zip(rr,oo):
            assert r['qid']==o['qid'] and r['true_hits']==o['true_hit_count'] and r['oracle_required_blocks']==o['oracle_required_blocks'] and r['total_blocks']==4096
            for field in ('global4_surviving_blocks','local_ball_surviving_blocks','global4_survival_fraction','local_ball_survival_fraction','global4_surviving_objects'):assert r[field]==o[field]
            assert r['local_ball_surviving_objects']==o['surviving_objects']
            assert 0<=r['oracle_required_blocks']<=r['projected_box_surviving_blocks']<=4096 and r['projected_box_false_prune']==0
            assert r['projected_box_survival_fraction']==r['projected_box_surviving_blocks']/4096 and r['oracle_fraction']==r['oracle_required_blocks']/4096 and r['projected_box_oracle_gap']==r['projected_box_surviving_blocks']-r['oracle_required_blocks']
            assert r['query_projection_ops']==4 and r['numeric_maxabs_reductions']==1 and r['summary_endpoint_reads']==32768 and r['summary_metadata_bytes']==262144 and r['direction_coordinate_bytes']==30720
            assert r['modeled_total_fullD_equivalent_work']==5+r['surviving_objects'] and r['modeled_dot_only_plus_verification']==4+r['surviving_objects'] and r['modeled_total_coordinate_bytes']==34560+r['surviving_objects']*3840
    assert sum(r['projected_box_surviving_blocks']<r['global4_surviving_blocks'] for r in rows)==10
    with (root/'figures/summary_survival.csv').open() as f:plot=list(csv.DictReader(f))
    assert len(plot)==8
    for r in plot:
        s=next(s['statistics'] for s in query['summary'] if s['snapshot']==r['snapshot']);key=dict(zip(['GLOBAL4','LOCAL_BALL','PROJECTED_BOX','ORACLE'],['global4_survival_fraction','local_ball_survival_fraction','projected_box_survival_fraction','oracle_fraction']))[r['summary']]
        assert float(r['surviving_percent'])==100*s[key]['mean'] and float(r['oracle_gap_blocks'])==(s[key]['mean']-s['oracle_fraction']['mean'])*4096
    for filename in ('projected_vs_global','oracle_gap'):
        with (root/'figures'/(filename+'.csv')).open() as f:plot=list(csv.DictReader(f))
        assert len(plot)==64
        for r,q in zip(plot,rows):
            assert (r['snapshot'],int(r['query']),int(r['qid']))==(q['snapshot'],q['query'],q['qid'])
            if filename=='oracle_gap':assert int(r['oracle_gap_blocks'])==q['projected_box_oracle_gap']
            else:assert float(r['global4_percent'])==100*q['global4_survival_fraction'] and float(r['projected_box_percent'])==100*q['projected_box_survival_fraction']
    inventory={str(f.relative_to(root)):sha(f) for f in sorted(root.rglob('*')) if f.is_file() and '__pycache__' not in f.parts and f.name!='DELIVERY_MANIFEST.json'}
    if seal:(root/'DELIVERY_MANIFEST.json').write_text(json.dumps(dict(files=inventory),indent=2)+'\n')
    else:assert inventory==load(root/'DELIVERY_MANIFEST.json')['files']
    print(json.dumps(dict(passed=True,query_rows=64,block_rows=8192,false_prune=0,decision=v['decision'],files=len(inventory)+1)))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--seal',action='store_true');main(p.parse_args().seal)
