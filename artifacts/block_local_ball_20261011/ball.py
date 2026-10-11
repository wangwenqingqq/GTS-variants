#!/usr/bin/env python3
"""One fixed local-ball summary; pure geometry is separate from oracle evaluation."""
import ctypes
import json
import sys
from pathlib import Path
import numpy as np

HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'block_certificate_headroom_20261010'
PART=HERE.parent/'certificate_aware_partition_20261010'
sys.path.insert(0,str(PART))
from partition import validate_partition
from run import sha,save,outside_repo,raw,interval,radius_upper,stats,rejected
if not __debug__:raise RuntimeError('Assertions are required')


def library(path):
    lib=ctypes.CDLL(str(Path(path).resolve()))
    lib.pair_distances.argtypes=[ctypes.POINTER(ctypes.c_float),ctypes.c_int64,ctypes.c_int,
        ctypes.POINTER(ctypes.c_int64),ctypes.POINTER(ctypes.c_int64),ctypes.c_int64,ctypes.POINTER(ctypes.c_double)]
    lib.pair_distances.restype=ctypes.c_int
    return lib


def pair_scores(lib,x,left,right):
    assert x.dtype==np.float32 and x.ndim==2 and x.flags.c_contiguous and 0<x.shape[1]<=4096
    left=np.asarray(left);right=np.asarray(right)
    assert left.dtype==right.dtype==np.int64 and left.ndim==right.ndim==1 and left.shape==right.shape and len(left)>0
    assert np.all((left>=0)&(left<len(x))) and np.all((right>=0)&(right<len(x)))
    left=np.ascontiguousarray(left);right=np.ascontiguousarray(right);out=np.empty(len(left),dtype=np.float64)
    rc=lib.pair_distances(x.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),len(x),x.shape[1],
        left.ctypes.data_as(ctypes.POINTER(ctypes.c_int64)),right.ctypes.data_as(ctypes.POINTER(ctypes.c_int64)),
        len(left),out.ctypes.data_as(ctypes.POINTER(ctypes.c_double)))
    assert rc==0 and np.isfinite(out).all() and np.all(out>=0),'invalid pair distance input/output'
    return out


def centers(scores,occ,perm,starts):
    assert scores.shape==(4,len(occ)) and np.isfinite(scores).all() and np.all(scores>=0)
    assert len(np.unique(occ))==len(occ)
    validate_partition(perm,starts,len(occ),256)
    norms=np.sqrt(scores);selected=[];means=[];ends=np.r_[starts[1:],len(perm)]
    for start,end in zip(starts,ends):
        ids=perm[start:end];signature=norms[:,ids]
        mu=np.cumsum(signature,axis=1)[:,-1]/len(ids)
        delta=signature-mu[:,None];cost=delta[0]*delta[0]
        for j in (1,2,3):cost=cost+delta[j]*delta[j]
        tied=ids[cost==cost.min()];chosen=int(tied[np.argmin(occ[tied])])
        selected.append(chosen);means.append(mu)
    return np.array(selected,dtype=np.int64),np.array(means)


def ball_keep(query_scores,cover,d,radius):
    assert np.isfinite(radius) and radius>=0 and float(np.float32(radius))==radius
    assert np.isfinite(cover).all() and np.all(cover>=0)
    lower,_=interval(query_scores,d)
    return lower<=np.nextafter(cover+radius_upper(radius,d),np.inf)


def decision(summary):
    assert len(summary)==2 and {r['snapshot'] for r in summary}=={'initial','first_rebuilt'}
    for r in summary:assert r['statistics']['local_ball_false_prune']['max']==0
    m=[r['statistics']['local_ball_survival_fraction']['mean'] for r in summary]
    tail=[r['statistics']['local_ball_survival_fraction']['p90'] for r in summary]
    g=[r['statistics']['global4_survival_fraction']['mean'] for r in summary]
    gain=[a-b for a,b in zip(g,m)]
    go=all(v<=.5 for v in m) and all(v<=.7 for v in tail)
    no_go=any(v>.65 and improvement<.1 for v,improvement in zip(m,gain))
    conditional=not go and not no_go and max(m)>.5 and max(m)<=.65 and min(gain)>=.15
    label='GO_LOCAL' if go else 'NO_GO_LOCAL_BALL' if no_go else 'CONDITIONAL_LOCAL'
    return dict(decision=label,reason='joint_mean_and_tail_pass' if go else 'same_snapshot_high_survival_and_small_gain' if no_go else
                'specified_conditional_band' if conditional else 'uncovered_interval',strong_GO=go and max(m)<=.35,
                snapshots=[r['snapshot'] for r in summary],local_mean=m,local_p90=tail,global4_mean=g,
                improvement_percentage_points=[100*v for v in gain],GPU_admitted_this_round=False,
                scope='Only fixed S1/P2, C0 signature-nearest-member center, one safe ball, these two snapshots and original queries; not all local summaries')


METRICS=['global4_surviving_blocks','local_ball_surviving_blocks','oracle_required_blocks','global4_survival_fraction',
         'local_ball_survival_fraction','oracle_fraction','local_ball_false_prune','local_ball_false_keep',
         'local_ball_oracle_gap','true_hit_count','surviving_objects','global4_surviving_objects',
         'center_distance_evals','summary_bytes','center_coordinate_bytes','modeled_total_distance_evals',
         'modeled_total_coordinate_bytes']


def summarize(rows):
    return [dict(snapshot=name,queries=32,statistics={key:stats([r[key] for r in rows if r['snapshot']==name]) for key in METRICS})
            for name in ('initial','first_rebuilt')]


def sources():
    files=[HERE/x for x in ('CONTRACT.json','NUMERICS.md','ball.py','pairs.cpp','experiment.py','test_ball.py')]
    files += [PART/'partition.py',BASE/'run.py',HERE.parent/'external_closure/pruning_value/build.py',HERE.parent/'external_closure/pruning_value/analyze.py']
    return {str(p.relative_to(HERE.parent)):sha(p) for p in files}


def bind(a):
    c=json.loads((HERE/'CONTRACT.json').read_text());files={}
    def check(path,digest):
        assert sha(path)==digest,('input identity mismatch',path.name);files[path]=digest
    check(a.partition/'PROOF.json',c['partition_proof_sha256']);check(a.partition_verify,c['partition_verification_sha256'])
    pp=json.loads((a.partition/'PROOF.json').read_text());pv=json.loads(a.partition_verify.read_text())
    assert pp['passed'] and pv['passed'] and pv['static_proof_sha256']==sha(a.partition/'PROOF.json')
    check(a.partition/'BLOCK_SELECTIVITY.json',c['global4_result_sha256'])
    check(a.prior/'PROOF.json',c['prior_score_proof_sha256']);check(a.prior_verify,c['prior_score_verification_sha256'])
    prior=json.loads((a.prior/'PROOF.json').read_text());v=json.loads(a.prior_verify.read_text())
    assert prior['passed'] and v['passed'] and v['proof_sha256']==sha(a.prior/'PROOF.json')
    inputs=json.loads(a.inputs.read_text())['records']
    for name in c['snapshots']:
        check(a.partition/(name+'_S1_P2.npz'),c['partition_sha256'][name])
        check(a.prior/(name+'_S1_scores.npy'),prior['raw_files'][name+'_S1_scores.npy'])
        check(a.maintenance/(name+'.occurrence.npy'),c['occurrence_sha256'][name])
        check(Path(inputs[name]['data']),c['inputs'][name]['data_sha256'])
        check(a.references/name/'REFERENCE.json',c['inputs'][name]['reference_sha256'])
        assert inputs[name]['qids']==c['inputs'][name]['qids']==prior['bindings'][name]['queries']
        for q,digest in prior['bindings'][name]['reference_file_hashes'].items():check(a.references/name/(q+'.f64'),digest)
    return c,prior,inputs,files
