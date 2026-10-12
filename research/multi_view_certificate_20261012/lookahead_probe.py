#!/usr/bin/env python3
"""Small frozen two-level oracle; never an upper bound on global coordination."""
import argparse, json, os, sys, time
from fractions import Fraction
from pathlib import Path
import numpy as np
from views import HERE, sha, save
from evaluate_multi_view import csv_write
sys.path.insert(0,str(HERE.parent/'certificate_effectiveness_split_20261012'))
from splits import candidates, score_proposals
from independent import enumerate_scores

def main():
    p=argparse.ArgumentParser()
    for k in ['old-projected','scores','prior-run','out']:p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);started=time.monotonic()
    im=json.loads((HERE/'evidence/INPUT_IDENTITY.json').read_text());samples=json.loads((HERE/'evidence/LOOKAHEAD_SAMPLES.json').read_text())['samples']
    assert sha(HERE/'CONTRACT.json')==im['contract_sha256']
    assert os.environ.get('CUDA_VISIBLE_DEVICES')=='' and len(os.sched_getaffinity(0))==1
    assert all(os.environ.get(k)=='1' for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS']) and os.getpriority(os.PRIO_PROCESS,0)>=10
    assert sha(a.old_projected)==im['projected_sha256'] and sha(a.scores)==im['scores_sha256'] and sha(a.prior_run/'PCA_BALANCED.i32')==im['P2_permutation_sha256']
    z=np.memmap(a.old_projected,dtype='<f8',mode='r',shape=(1000000,16))[:,8:16]
    scores=np.memmap(a.scores,dtype='<f8',offset=16,mode='r',shape=(8,1000000));perm=np.fromfile(a.prior_run/'PCA_BALANCED.i32',dtype='<i4')
    queries=z[im['queries']];u=np.sqrt([float.fromhex(t) for t in im['U_star_squared_hex']]);rows=[];proposals=[];checks=[];bound_checks=0
    for sn,sample in enumerate(samples):
        d=sample['parent_depth'];pi=sample['parent_index'];size=sample['object_count'];ids=perm[pi*size:(pi+1)*size]
        first=candidates(z,ids,d);immediate,_=score_proposals(z,first,queries,u,scores);bound_checks+=8*120
        greedy=int(np.argmax(immediate[:,2:].sum(1)));horizon=np.zeros((12,8),dtype=np.int64);seconds=[]
        independently_check=sn in (0,8)
        if independently_check:
            ref,reforders=enumerate_scores(z,ids,d,queries,u)
            assert np.array_equal(ref,immediate) and all(np.array_equal(r,f) for r,f in zip(reforders,first)), 'first independent enumeration'
        for fi,ordering in enumerate(first):
            selected=[]
            for ci,child in enumerate(ordering.reshape(10,-1)):
                second=candidates(z,child,d+1);counts,_=score_proposals(z,second,queries,u,scores);bound_checks+=8*120
                chosen=int(np.argmax(counts[:,2:].sum(1)));selected.append(chosen);horizon[fi]+=counts[chosen]
                if independently_check:
                    ref,reforders=enumerate_scores(z,child,d+1,queries,u)
                    assert np.array_equal(ref,counts) and all(np.array_equal(r,f) for r,f in zip(reforders,second)), 'second independent all proposals'
            seconds.append(selected)
            proposals.append(dict(parent_depth=d,parent_index=pi,first_proposal=fi,immediate_hard_pruned=int(immediate[fi,2:].sum()),grandchildren_hard_pruned=int(horizon[fi,2:].sum()),second_proposals=';'.join(map(str,selected))))
        selected=int(np.argmax(horizon[:,2:].sum(1)));g=int(horizon[greedy,2:].sum());h=int(horizon[selected,2:].sum());assert h>=g
        rows.append(dict(parent_depth=d,parent_index=pi,parent_objects=size,grandchild_objects=size//100,greedy_first_proposal=greedy,lookahead_first_proposal=selected,
            greedy_horizon_pruned=g,lookahead_horizon_pruned=h,gain_pruned_objects=h-g,denominator=6*size,gain_fullscan_fraction=float(Fraction(h-g,6*size)),
            parent_membership_sha256=__import__('hashlib').sha256(np.sort(ids).astype('<i4').tobytes()).hexdigest()))
        if independently_check:checks.append(dict(parent_depth=d,parent_index=pi,first_and_all120_second_parents_all12_proposals_independently_equal=True))
        print(f'Lookahead parent {sn+1}/16 depth={d} index={pi}: gain={h-g}/{6*size}',flush=True)
    def summary(rs):
        gain=sum(r['gain_pruned_objects'] for r in rs);den=sum(r['denominator'] for r in rs)
        return dict(gain_objects=gain,denominator=den,gain_fullscan_fraction=gain/den,parents=len(rs))
    pooled=summary(rows);bydepth={str(d):summary([r for r in rows if r['parent_depth']==d]) for d in (2,3)}
    points=[pooled,*bydepth.values()];closed=all(Fraction(r['gain_objects'],r['denominator'])<Fraction(1,10) for r in points);opened=any(Fraction(r['gain_objects'],r['denominator'])>=Fraction(15,100) for r in points)
    verdict='LOOKAHEAD_CLOSED' if closed else 'LOOKAHEAD_SIGNAL' if opened else 'INSUFFICIENT_LOOKAHEAD'
    csv_write(a.out/'lookahead_parents.csv',rows);csv_write(a.out/'lookahead_first_proposals.csv',proposals)
    save(a.out/'LOOKAHEAD_SUMMARY.json',dict(decision=verdict,pooled=pooled,by_parent_depth=bydepth,safety_bound_checks=bound_checks,bound_above_truth=0,false_topK_prunes=0,
        independent_checks=checks,source_hashes={k:sha(HERE.parent/'certificate_effectiveness_split_20261012'/k) for k in ['splits.py','independent.py']},
        samples_sha256=sha(HERE/'evidence/LOOKAHEAD_SAMPLES.json'),scope='same grandchildren horizon, 16 fixed parents, 12 first proposals and 12 child proposals; NOT global upper bound',
        sort_calls=16*12+16*12*10*12,sort_object_occurrences=sum(12*12*r['parent_objects']+12*r['parent_objects'] for r in rows),
        GPU_used=False,no_latency_measured=True,elapsed_resource_seconds=time.monotonic()-started,CPU_affinity_count=1))
    print(verdict,json.dumps(pooled),flush=True)

if __name__=='__main__':main()
