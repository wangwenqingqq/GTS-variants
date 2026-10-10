#!/usr/bin/env python3
"""Independent stable-sort partitions, direct block reductions and owner-based oracle."""
import argparse
import csv
import json
from pathlib import Path
import numpy as np
from partition import (HERE, sha, save, outside_repo, raw, interval, radius_upper,
                       stats, query_summary, decide, bind_inputs, source_hashes)


def independent_partition(norms,occ,tree,kind,capacity=256,balanced=False):
    n=len(occ)
    def order(ids,j):
        ids=ids[np.argsort(occ[ids],kind='stable')]
        return ids[np.argsort(norms[j,ids],kind='stable')]
    if kind=='P0':return tree.astype(np.int64),np.arange(0,n,capacity)
    if kind=='P1':
        ids=np.argsort(occ,kind='stable')
        for j in (3,2,1,0):ids=ids[np.argsort(norms[j,ids],kind='stable')]
        return ids,np.arange(0,n,capacity)
    scale=norms.max(axis=1)-norms.min(axis=1)
    stack=[(np.arange(n),(n+capacity-1)//capacity if balanced else None)]
    leaves=[]
    while stack:
        ids,budget=stack.pop()
        if (budget==1) if balanced else (len(ids)<=capacity):
            leaves.append(ids);continue
        span=np.array([norms[j,ids].max()-norms[j,ids].min() for j in range(4)])
        if kind=='P3':span=np.array([span[j]/scale[j] if scale[j] else 0 for j in range(4)])
        j=max(range(4),key=lambda j:(span[j],-j));ids=order(ids,j)
        left=budget//2 if balanced else None
        cut=len(ids)*left//budget if balanced else len(ids)//2
        stack.append((ids[cut:],budget-left if balanced else None));stack.append((ids[:cut],left))
    return np.concatenate(leaves),np.r_[0,np.cumsum([len(x) for x in leaves])[:-1]]


def main(a):
    out=outside_repo(a.output);out.mkdir(exist_ok=False)
    c,prior,files=bind_inputs(a.prior,a.verification,a.maintenance,a.references)
    proof=json.loads((a.run/'PROOF.json').read_text())
    assert proof['passed'] and proof['source_hashes']==source_hashes()
    registered=json.loads((a.run/'REGISTERED.json').read_text())
    assert registered['source_hashes']==proof['source_hashes'] and registered['contract_sha256']==sha(HERE/'CONTRACT.json')
    assert {p.name:sha(p) for p in a.run.iterdir() if p.is_file() and p.name!='PROOF.json'}==proof['raw_files']
    pr=json.loads((a.run/'PARTITION_STATS.json').read_text())['rows']
    qr=json.loads((a.run/'BLOCK_SELECTIVITY.json').read_text())
    assert len(pr)==16 and len(qr['rows'])==1024 and len(qr['summary'])==32
    index={(r['snapshot'],r['strategy'],r['partition'],r['pivot_count'],r['query']):r for r in qr['rows']}
    assert len(index)==1024
    radius=float(np.array([0x3f34a3d8],dtype=np.uint32).view(np.float32)[0]);rup=radius_upper(radius,960)
    count=0;all_summaries=[]
    with (a.run/'BLOCK_STATS.csv').open(newline='') as f:
        csv_rows=iter(csv.DictReader(f))
        for name in c['snapshots']:
            occ=np.load(a.maintenance/(name+'.occurrence.npy'));n=len(occ);tree=np.load(a.prior/(name+'_L3.npy'))
            qids=prior['bindings'][name]['queries']
            refs=np.stack([raw(a.references/name/(str(q)+'.f64'),'<f8',(n,)) for q in qids])
            for strategy in c['strategies']:
                scores=np.load(a.prior/(name+'_'+strategy+'_scores.npy'))[:4];norms=np.sqrt(scores)
                lower,upper=interval(scores,960);qlo,qhi=interval(scores[:,qids],960)
                for kind in c['partitions']:
                    perm,starts=independent_partition(norms,occ,tree,kind)
                    with np.load(a.run/(name+'_'+strategy+'_'+kind+'.npz')) as packed:
                        np.testing.assert_array_equal(perm,packed['permutation']);np.testing.assert_array_equal(starts,packed['starts'])
                    nb=len(starts);ends=np.r_[starts[1:],n];sizes=ends-starts
                    owner=np.empty(n,dtype=np.int64);width=np.empty((4,nb));lo=width.copy();hi=width.copy()
                    span=norms.max(axis=1)-norms.min(axis=1)
                    for b,(start,end) in enumerate(zip(starts,ends)):
                        members=perm[start:end];owner[members]=b
                        width[:,b]=norms[:,members].max(axis=1)-norms[:,members].min(axis=1)
                        lo[:,b]=lower[:,members].min(axis=1);hi[:,b]=upper[:,members].max(axis=1)
                    nw=np.divide(width,span[:,None],out=np.zeros_like(width),where=span[:,None]>0)
                    for b in range(nb):
                        row=next(csv_rows);assert [row[k] for k in ('snapshot','strategy','partition')]==[name,strategy,kind]
                        assert (int(row['block']),int(row['size']))==(b,int(sizes[b]))
                        assert [float(row['width_p'+str(j+1)]) for j in range(4)]==list(width[:,b])
                        assert [float(row['normalized_width_p'+str(j+1)]) for j in range(4)]==list(nw[:,b]);count+=1
                    expected=dict(snapshot=name,strategy=strategy,partition=kind,total_blocks=nb,size=stats(sizes),
                                  imbalance=float(sizes.max()/sizes.mean()),physical_occupancy=float(n/(256*nb)),
                                  mean_normalized_width=stats(nw.mean(axis=0)),width_by_pivot=[stats(w) for w in width],
                                  normalized_width_by_pivot=[stats(w) for w in nw],global_span=span.tolist())
                    assert expected==next(r for r in pr if (r['snapshot'],r['strategy'],r['partition'])==(name,strategy,kind))
                    for p in (4,2):
                        rows=[]
                        for qi,q in enumerate(qids):
                            req=np.zeros(nb,dtype=bool);req[np.unique(owner[np.flatnonzero(refs[qi]<=radius*radius)])]=True
                            reject=(qlo[:p,qi,None]>np.nextafter(hi[:p]+rup,np.inf)) | (lo[:p]>np.nextafter(qhi[:p,qi,None]+rup,np.inf))
                            keep=~reject.any(axis=0);nk=int(keep.sum());nr=int(req.sum());assert not np.any(req & ~keep)
                            row=dict(snapshot=name,strategy=strategy,partition=kind,query=qi,qid=q,pivot_count=p,query_pivot_distance_count=p,
                                     total_blocks=nb,surviving_blocks=nk,rejected_blocks=nb-nk,surviving_block_fraction=nk/nb,false_prune_blocks=0,
                                     oracle_required_blocks=nr,oracle_fraction=nr/nb,oracle_gap_blocks=nk-nr,
                                     candidate_objects_in_surviving_blocks=int(sizes[keep].sum()),surviving_object_fraction=float(sizes[keep].sum()/n),
                                     surviving_physical_slots=256*nk,certificate_scalar_reads=2*p*nb,certificate_metadata_bytes=16*p*nb)
                            assert row==index[name,strategy,kind,p,qi];rows.append(row)
                        all_summaries.append(dict(snapshot=name,strategy=strategy,partition=kind,pivot_count=p,queries=32,statistics=query_summary(rows)))
                    print('verified',name,strategy,kind,flush=True)
        assert next(csv_rows,None) is None
    assert all_summaries==qr['summary']
    assert decide(all_summaries)==json.loads((a.run/'DECISION.json').read_text())
    for path,digest in files.items():assert sha(path)==digest
    save(out/'VERIFY.json',dict(passed=True,static_proof_sha256=sha(a.run/'PROOF.json'),verification_source_sha256=sha(Path(__file__)),
                                independent_stable_sort_partitions=16,direct_block_stats_rows=count,owner_based_query_rows=1024,
                                all_summaries_and_decision_reconstructed=True,false_prune_blocks=0,GPU_processes=0))


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for key in ('prior','verification','maintenance','references','run','output'):p.add_argument('--'+key,type=Path,required=True)
    main(p.parse_args())
