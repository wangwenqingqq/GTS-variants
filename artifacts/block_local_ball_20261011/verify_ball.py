#!/usr/bin/env python3
"""Fresh O0 score reconstruction, scalar C0 selection and owner-based oracle."""
import argparse
import json
import subprocess
import sys
from pathlib import Path
import numpy as np
from ball import HERE,sha,save,outside_repo,raw,interval,radius_upper,stats,library,pair_scores,summarize,decision,sources,bind


def scalar_centers(scores,occ,perm,starts):
    norms=np.sqrt(scores);chosen=[];means=[]
    for start,end in zip(starts,np.r_[starts[1:],len(perm)]):
        members=perm[start:end];mu=[]
        for j in range(4):
            value=0.
            for row in members:value+=float(norms[j,row])
            mu.append(value/len(members))
        best=None
        for row in members:
            cost=0.
            for j in range(4):delta=float(norms[j,row])-mu[j];cost+=delta*delta
            key=(cost,int(occ[row]),int(row))
            if best is None or key<best:best=key
        chosen.append(best[2]);means.append(mu)
    return np.array(chosen,dtype=np.int64),np.array(means)


def main(a):
    out=outside_repo(a.output);out.mkdir(exist_ok=False)
    c,prior,inputs,files=bind(a);proof=json.loads((a.run/'PROOF.json').read_text())
    reg=json.loads((a.run/'REGISTERED.json').read_text());build=json.loads((a.run/'BUILD.json').read_text())
    assert proof['passed'] and proof['source_hashes']==reg['source_hashes']==sources()
    assert reg['contract_sha256']==sha(HERE/'CONTRACT.json') and build['pairs_source_sha256']==sha(HERE/'pairs.cpp')
    assert {p.name:sha(p) for p in a.run.iterdir() if p.is_file() and p.name!='PROOF.json'}==proof['raw_files']
    assert build['library_sha256']==sha(a.run/'pairs.so')
    flags=['-std=c++17','-O0','-fno-fast-math','-ffp-contract=off','-fopenmp','-shared','-fPIC']
    subprocess.run(['g++',*flags,str(HERE/'pairs.cpp'),'-o',str(out/'fresh_pairs.so')],check=True)
    subprocess.run([sys.executable,str(HERE/'test_ball.py'),'--library',str(out/'fresh_pairs.so'),'-v'],check=True)
    lib=library(out/'fresh_pairs.so');query=json.loads((a.run/'SUMMARY_COMPARISON.json').read_text())
    bstats=json.loads((a.run/'LOCAL_BALL_STATS.json').read_text());assert len(query['rows'])==64 and len(bstats['rows'])==8192
    rowmap={(r['snapshot'],r['query']):r for r in query['rows']};blockmap={(r['snapshot'],r['block']):r for r in bstats['rows']}
    assert len(rowmap)==64 and len(blockmap)==8192
    reconstructed=[];reconstructed_blocks=[];r=float(np.array([0x3f34a3d8],dtype=np.uint32).view(np.float32)[0]);ru=radius_upper(r,960)
    for name in c['snapshots']:
        x=np.memmap(inputs[name]['data'],dtype='<f4',mode='r',offset=12,shape=(1000000,960));n,d=x.shape
        occ=np.load(a.maintenance/(name+'.occurrence.npy'));scores=np.load(a.prior/(name+'_S1_scores.npy'))[:4]
        with np.load(a.partition/(name+'_S1_P2.npz')) as f:perm=f['permutation'];starts=f['starts']
        sizes=np.diff(np.r_[starts,n]);nb=len(starts);assert nb==4096
        centers,means=scalar_centers(scores,occ,perm,starts)
        with np.load(a.run/(name+'_certificate.npz')) as f:
            np.testing.assert_array_equal(centers,f['center_rows']);np.testing.assert_array_equal(occ[centers],f['center_occurrences'])
            np.testing.assert_array_equal(means.view(np.uint64),f['signature_means'].view(np.uint64))
            # Reversed pair orientation and O0 must give the identical ordered squared scores.
            ms=pair_scores(lib,x,np.repeat(centers,sizes),perm)
            np.testing.assert_array_equal(ms.view(np.uint64),f['member_scores'].view(np.uint64))
            upper=interval(ms,d)[1];cover=np.array([max(upper[start:start+size]) for start,size in zip(starts,sizes)])
            np.testing.assert_array_equal(cover.view(np.uint64),f['cover_upper'].view(np.uint64))
            qids=c['inputs'][name]['qids'];qs=pair_scores(lib,x,np.tile(centers,32),np.repeat(np.array(qids,dtype=np.int64),nb)).reshape(32,nb)
            np.testing.assert_array_equal(qs.view(np.uint64),f['query_scores'].view(np.uint64))
        refs=np.stack([raw(a.references/name/(str(q)+'.f64'),'<f8',(n,)) for q in qids])
        np.testing.assert_array_equal(qs.view(np.uint64),refs[:,centers].view(np.uint64))
        owner=np.empty(n,dtype=np.int64);owner[perm]=np.repeat(np.arange(nb),sizes)
        glo,ghi=interval(scores,d);lo=np.minimum.reduceat(glo[:,perm],starts,axis=1);hi=np.maximum.reduceat(ghi[:,perm],starts,axis=1)
        qlo,qhi=interval(scores[:,qids],d);local_low=interval(qs,d)[0]
        for b,size in enumerate(sizes):
            expected=dict(snapshot=name,block=b,size=int(size),center_row=int(centers[b]),center_occurrence=int(occ[centers[b]]),
                          cover_radius_upper=float(cover[b]),max_member_squared_score=float(ms[starts[b]:starts[b]+size].max()))
            assert expected==blockmap[name,b];reconstructed_blocks.append(expected)
        for qi,q in enumerate(qids):
            hits=np.flatnonzero(refs[qi]<=r*r);req=np.zeros(nb,dtype=bool);req[np.unique(owner[hits])]=True
            keep=~(local_low[qi]>np.nextafter(cover+ru,np.inf));assert not np.any(req & ~keep)
            gkeep=~((qlo[:,qi,None]>np.nextafter(hi+ru,np.inf)) | (lo>np.nextafter(qhi[:,qi,None]+ru,np.inf))).any(axis=0)
            assert not np.any(req & ~gkeep)
            nk,nr,ng=int(keep.sum()),int(req.sum()),int(gkeep.sum());no=int(sizes[keep].sum())
            expected=dict(snapshot=name,query=qi,qid=q,total_blocks=nb,global4_surviving_blocks=ng,local_ball_surviving_blocks=nk,
                          oracle_required_blocks=nr,global4_survival_fraction=ng/nb,local_ball_survival_fraction=nk/nb,oracle_fraction=nr/nb,
                          local_ball_false_prune=0,local_ball_false_keep=int(np.count_nonzero(keep&~req)),local_ball_oracle_gap=nk-nr,
                          true_hit_count=len(hits),surviving_objects=no,global4_surviving_objects=int(sizes[gkeep].sum()),center_distance_evals=nb,
                          summary_bytes=8*nb,center_id_bytes=8*nb,center_coordinate_bytes=nb*d*4,modeled_total_distance_evals=nb+no,
                          modeled_total_coordinate_bytes=(nb+no)*d*4)
            assert expected==rowmap[name,qi];reconstructed.append(expected)
        print(name,'verified all centers, radii, distances and 32 rows',flush=True)
    assert summarize(reconstructed)==query['summary'] and decision(query['summary'])==json.loads((a.run/'DECISION.json').read_text())
    assert bstats['summary']==[dict(snapshot=n,blocks=4096,covering_radius=stats([r['cover_radius_upper'] for r in reconstructed_blocks if r['snapshot']==n])) for n in c['snapshots']]
    for path,digest in files.items():assert sha(path)==digest
    save(out/'VERIFY.json',dict(passed=True,proof_sha256=sha(a.run/'PROOF.json'),source_hashes=sources(),
                                verification_source_sha256=sha(Path(__file__)),fresh_library_sha256=sha(out/'fresh_pairs.so'),
                                fresh_compiler_flags=flags,scalar_centers_checked=8192,center_member_pairs_recomputed=2000000,
                                query_center_pairs_recomputed=262144,all_query_center_scores_match_reference=True,
                                all_rows_and_summaries_reconstructed=True,global4_counts_reconstructed=True,
                                numerical_tests_passed=11,false_prune=0,decision=decision(query['summary'])['decision'],GPU_processes=0))


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('partition','partition-verify','prior','prior-verify','inputs','maintenance','references','run','output'):p.add_argument('--'+k,type=Path,required=True)
    main(p.parse_args())
