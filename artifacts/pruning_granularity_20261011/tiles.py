#!/usr/bin/env python3
"""One frozen GLOBAL4 rule; vary only recursive leaf stopping capacity."""
import json
import sys
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
PART=HERE.parent/'certificate_aware_partition_20261010'
sys.path.insert(0,str(PART))
import partition
from partition import sha,save,outside_repo,raw,interval,radius_upper,rejected,stats,validate_partition
from verify_partition import independent_partition
if not __debug__:raise RuntimeError('Assertions required')
SIZES=[512,256,128,64,32]
SNAPS=['initial','first_rebuilt']
LAMBDAS=[.01,.05,.10]


def load(p):return json.loads(Path(p).read_text())


def make_tiles(norms,occ,capacity):
    assert norms.shape==(4,len(occ)) and len(occ)>0 and np.isfinite(norms).all() and np.all(norms>=0)
    assert occ.dtype.kind in 'iu' and len(np.unique(occ))==len(occ) and 0<capacity<=512
    if capacity<=256:return partition.make_partition(norms,occ,np.arange(len(occ)),'P2',capacity)
    # The immutable helper caps capacity at256; extend the identical rule only for512.
    leaves=[]
    def visit(ids):
        if len(ids)<=capacity:leaves.append(ids);return
        j=int(np.argmax(np.ptp(norms[:,ids],axis=1)))
        ids=ids[np.lexsort((occ[ids],norms[j,ids]))];cut=len(ids)//2
        visit(ids[:cut]);visit(ids[cut:])
    visit(np.arange(len(occ)));p=np.concatenate(leaves);s=np.r_[0,np.cumsum([len(x) for x in leaves])[:-1]]
    validate_partition(p,s,len(occ),capacity);return p,s


def bounds(scores,perm,starts,d=960):
    assert scores.shape==(4,len(perm)) and np.isfinite(scores).all() and np.all(scores>=0)
    low,high=interval(scores,d)
    return np.minimum.reduceat(low[:,perm],starts,axis=1),np.maximum.reduceat(high[:,perm],starts,axis=1)


def row(name,size,qi,qid,n,nb,nk,no,nr,hits,oracle_objects):
    return dict(snapshot=name,tile_size=size,query=qi,qid=qid,total_tiles=nb,surviving_tiles=nk,surviving_tile_fraction=nk/nb,
                surviving_objects=no,surviving_object_fraction=no/n,oracle_required_tiles=nr,oracle_tile_fraction=nr/nb,
                oracle_objects_in_required_tiles=oracle_objects,empty_but_surviving_tiles=nk-nr,oracle_gap_tiles=nk-nr,
                false_prune_tiles=0,true_hit_count=hits,query_pivot_distances=4,endpoint_reads=8*nb,certificate_scalar_reads=8*nb,
                certificate_checks=nb,pivot_interval_checks=4*nb,metadata_bytes=64*nb,modeled_fullD_distances=4+no)


def evaluate(name,size,scores,perm,starts,lo,hi,truth,qids,radius,d=960):
    sizes=np.diff(np.r_[starts,len(perm)]);rows=[]
    old=partition.queries(scores,perm,starts,lo,hi,truth,qids,4,radius,d)
    for qi,r in enumerate(old):
        req=np.maximum.reduceat(truth[qi,perm],starts)
        rows.append(row(name,size,qi,r['qid'],len(perm),len(starts),r['surviving_blocks'],r['candidate_objects_in_surviving_blocks'],
                        r['oracle_required_blocks'],int(truth[qi].sum()),int(sizes[req].sum())))
    return rows


METRICS=['surviving_tiles','surviving_tile_fraction','surviving_objects','surviving_object_fraction','oracle_required_tiles',
         'oracle_tile_fraction','oracle_objects_in_required_tiles','oracle_gap_tiles','false_prune_tiles','true_hit_count']
def summarize(rows):
    return [dict(snapshot=n,tile_size=t,queries=32,total_tiles=next(r['total_tiles'] for r in rows if r['snapshot']==n and r['tile_size']==t),
                 statistics={k:stats([r[k] for r in rows if r['snapshot']==n and r['tile_size']==t]) for k in METRICS}) for n in SNAPS for t in SIZES]


def decide(summary):
    idx={(r['snapshot'],r['tile_size']):r for r in summary};assert len(idx)==10
    assert all(r['statistics']['false_prune_tiles']['max']==0 for r in summary)
    means=lambda t:[idx[n,t]['statistics']['surviving_object_fraction']['mean'] for n in SNAPS]
    ratios=lambda t:[idx[n,t]['total_tiles']/idx[n,256]['total_tiles'] for n in SNAPS]
    anchor=means(256);gain=lambda t:[a-b for a,b in zip(anchor,means(t))]
    go=[t for t in (128,64,32) if max(means(t))<=.5 and min(gain(t))>=.2 and max(ratios(t))<=8]
    strong=[t for t in go if max(means(t))<=.35 and max(ratios(t))<=4]
    no=not go and (min(means(32))>.6 or max(gain(32))<.1)
    conditional=[t for t in (128,64,32) if min(means(t))>.5 and max(means(t))<=.6 and min(gain(t))>=.15] if not go and not no else []
    positive=go or conditional
    return dict(decision='GO_GRANULARITY' if go else 'NO_GO_GRANULARITY' if no else 'CONDITIONAL_GRANULARITY',
                reason='joint_mean_gain_metadata_pass' if go else 'both_snapshots_32_high_survival_or_small_gain' if no else 'specified_conditional_band' if conditional else 'uncovered_interval',
                GO_sizes=go,strong_GO_sizes=strong,conditional_supported_sizes=conditional,selected_update_sizes=positive[:2],update_admitted=bool(positive),
                GPU_admitted_this_round=False,anchor_object_means=dict(zip(SNAPS,anchor)),tile32_object_means=dict(zip(SNAPS,means(32))),
                gain_percentage_points={str(t):dict(zip(SNAPS,[100*x for x in gain(t)])) for t in SIZES},scope='Only S1/P2 GLOBAL4, these target sizes/snapshots/queries; not all trees or exact pruning')


def costs(rows):
    out=[];meta=[];proxies=[]
    for n in SNAPS:
        anchor=next(r['total_tiles'] for r in rows if r['snapshot']==n and r['tile_size']==256)
        for t in SIZES:
            rr=[r for r in rows if r['snapshot']==n and r['tile_size']==t];nb=rr[0]['total_tiles'];ratio=nb/anchor
            meta.append(dict(snapshot=n,tile_size=t,total_tiles=nb,endpoint_reads=8*nb,metadata_bytes=64*nb,relative_to_256=ratio,query_pivot_distances=4,certificate_checks=nb,pivot_interval_checks=4*nb))
            for lam in LAMBDAS:
                vals=[]
                for r in rr:
                    val=r['surviving_object_fraction']+lam*ratio;vals.append(val)
                    proxies.append(dict(snapshot=n,tile_size=t,query=r['query'],qid=r['qid'],lambda_value=lam,normalized_proxy=val))
                out.append(dict(snapshot=n,tile_size=t,lambda_value=lam,statistics=stats(vals)))
    winners=[dict(snapshot=n,lambda_value=lam,best_size=min(SIZES,key=lambda t:(next(r['statistics']['mean'] for r in out if (r['snapshot'],r['tile_size'],r['lambda_value'])==(n,t,lam)),-t))) for n in SNAPS for lam in LAMBDAS]
    return dict(metadata=meta,proxy_rows=proxies,proxy_summary=out,best_by_snapshot_and_lambda=winners,scope='Sensitivity only; no conversion to GPU time or DRAM traffic; query-pivot count common and not varied')


def source_hashes():
    own=[HERE/f for f in ('CONTRACT.json','NUMERICS.md','tiles.py','experiment.py','test_tiles.py')]
    return {**partition.source_hashes(),str((PART/'verify_partition.py').relative_to(HERE.parent)):sha(PART/'verify_partition.py'),
            **{str(p.relative_to(HERE.parent)):sha(p) for p in own}}


def bind(a):
    c=load(HERE/'CONTRACT.json');pc,prior,files=partition.bind_inputs(a.prior,a.prior_verify,a.maintenance,a.references)
    for path,key in [(a.partition/'PROOF.json','partition_proof_sha256'),(a.partition_verify,'partition_verification_sha256'),(a.partition/'BLOCK_SELECTIVITY.json','global4_result_sha256')]:
        assert sha(path)==c[key];files[path]=c[key]
    pp=load(a.partition/'PROOF.json');pv=load(a.partition_verify)
    assert pp['passed'] and pv['passed'] and pv['static_proof_sha256']==sha(a.partition/'PROOF.json') and pp['source_hashes']==partition.source_hashes()
    assert c['inputs']==pc['inputs'] and c['occurrence_sha256']==pc['occurrence_sha256']
    for n in SNAPS:
        p=a.partition/(n+'_S1_P2.npz');assert sha(p)==c['partition_sha256'][n];files[p]=sha(p)
    return c,prior,files
