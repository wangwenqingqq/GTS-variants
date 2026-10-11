#!/usr/bin/env python3
"""Frozen 64-query offline local-ball diagnostic. No GPU or update operations."""
import argparse
import json
import platform
import subprocess
import sys
from pathlib import Path
import numpy as np
from ball import HERE,sha,save,outside_repo,raw,interval,stats,library,pair_scores,centers,ball_keep,summarize,decision,sources,bind


def main(a):
    out=outside_repo(a.output);out.mkdir(exist_ok=False)
    source=sources();flags=['-std=c++17','-O3','-fno-fast-math','-ffp-contract=off','-fopenmp','-shared','-fPIC']
    save(out/'REGISTERED.json',dict(source_hashes=source,contract_sha256=sha(HERE/'CONTRACT.json'),compiler_flags=flags,
                                  Python=platform.python_version(),NumPy=np.__version__,CPU_threads_max=4,priority_nice=15,GPU_processes=0))
    subprocess.run(['g++',*flags,str(HERE/'pairs.cpp'),'-o',str(out/'pairs.so')],check=True)
    subprocess.run([sys.executable,str(HERE/'test_ball.py'),'--library',str(out/'pairs.so'),'-v'],check=True)
    save(out/'BUILD.json',dict(library_sha256=sha(out/'pairs.so'),compiler=subprocess.check_output(['g++','--version'],text=True).splitlines()[0],
                             compiler_flags=flags,numerical_tests_passed=11,pairs_source_sha256=sha(HERE/'pairs.cpp')))
    c,prior,inputs,files=bind(a);lib=library(out/'pairs.so')
    global_rows=json.loads((a.partition/'BLOCK_SELECTIVITY.json').read_text())['rows']
    radius=float(np.array([0x3f34a3d8],dtype=np.uint32).view(np.float32)[0])
    result=[];block_rows=[];bindings={}
    for name in c['snapshots']:
        data=Path(inputs[name]['data']);header=np.fromfile(data,dtype='<i4',count=3)
        assert tuple(header)==(960,1000000,2) and data.stat().st_size==12+1000000*960*4
        n,d=1000000,960;x=np.memmap(data,dtype='<f4',mode='r',offset=12,shape=(n,d));assert np.isfinite(x).all()
        occ=np.load(a.maintenance/(name+'.occurrence.npy'));scores=np.load(a.prior/(name+'_S1_scores.npy'))[:4]
        with np.load(a.partition/(name+'_S1_P2.npz')) as f:perm=f['permutation'];starts=f['starts']
        sizes=np.diff(np.r_[starts,n]);nb=len(starts);assert nb==4096 and set(sizes)=={244,245}
        center,mu=centers(scores,occ,perm,starts)
        member_scores=pair_scores(lib,x,perm,np.repeat(center,sizes))
        cover=np.maximum.reduceat(interval(member_scores,d)[1],starts)
        qids=c['inputs'][name]['qids']
        qs=pair_scores(lib,x,np.repeat(np.array(qids,dtype=np.int64),nb),np.tile(center,len(qids))).reshape(32,nb)
        np.savez(out/(name+'_certificate.npz'),center_rows=center,center_occurrences=occ[center],signature_means=mu,
                 member_scores=member_scores,cover_upper=cover,query_scores=qs)
        # The certificate is complete before oracle loading/evaluation.
        save(out/(name+'_CERTIFICATE_READY.json'),dict(certificate_sha256=sha(out/(name+'_certificate.npz')),
                                                     construction_has_no_query_oracle_input=True,centers=nb,member_distances=n))
        refs=np.stack([raw(a.references/name/(str(q)+'.f64'),'<f8',(n,)) for q in qids])
        assert np.array_equal(qs.view(np.uint64),refs[:,center].view(np.uint64)),'fresh query-center/reference mismatch'
        gr=[r for r in global_rows if (r['snapshot'],r['strategy'],r['partition'],r['pivot_count'])==(name,'S1','P2',4)]
        assert len(gr)==32 and [r['qid'] for r in gr]==qids
        for b,size in enumerate(sizes):
            block_rows.append(dict(snapshot=name,block=b,size=int(size),center_row=int(center[b]),center_occurrence=int(occ[center[b]]),
                                   cover_radius_upper=float(cover[b]),max_member_squared_score=float(member_scores[starts[b]:starts[b]+size].max())))
        for qi,q in enumerate(qids):
            hits=refs[qi]<=radius*radius;required=np.maximum.reduceat(hits[perm],starts)
            keep=ball_keep(qs[qi],cover,d,radius);false=int(np.count_nonzero(required&~keep));assert false==0,('false prune',name,qi)
            nk,nr=int(keep.sum()),int(required.sum());survive=int(sizes[keep].sum());g=gr[qi]
            assert g['total_blocks']==nb and g['oracle_required_blocks']==nr
            result.append(dict(snapshot=name,query=qi,qid=q,total_blocks=nb,global4_surviving_blocks=g['surviving_blocks'],
                               local_ball_surviving_blocks=nk,oracle_required_blocks=nr,
                               global4_survival_fraction=g['surviving_block_fraction'],local_ball_survival_fraction=nk/nb,oracle_fraction=nr/nb,
                               local_ball_false_prune=false,local_ball_false_keep=int(np.count_nonzero(keep&~required)),local_ball_oracle_gap=nk-nr,
                               true_hit_count=int(hits.sum()),surviving_objects=survive,global4_surviving_objects=g['candidate_objects_in_surviving_blocks'],
                               center_distance_evals=nb,summary_bytes=8*nb,center_id_bytes=8*nb,center_coordinate_bytes=nb*d*4,
                               modeled_total_distance_evals=nb+survive,modeled_total_coordinate_bytes=(nb+survive)*d*4))
        bindings[name]=dict(data_sha256=sha(data),partition_sha256=sha(a.partition/(name+'_S1_P2.npz')),
                            score_sha256=sha(a.prior/(name+'_S1_scores.npy')),occurrence_sha256=sha(a.maintenance/(name+'.occurrence.npy')),
                            reference_sha256=sha(a.references/name/'REFERENCE.json'),queries=qids,
                            query_center_matches_reference_bitwise=True)
        print(name,'local mean',np.mean([r['local_ball_survival_fraction'] for r in result if r['snapshot']==name]),flush=True)
    assert len(result)==64 and len(block_rows)==8192
    summary=summarize(result)
    save(out/'LOCAL_BALL_STATS.json',dict(rows=block_rows,summary=[dict(snapshot=n,blocks=4096,
        covering_radius=stats([r['cover_radius_upper'] for r in block_rows if r['snapshot']==n])) for n in c['snapshots']]))
    save(out/'SUMMARY_COMPARISON.json',dict(rows=result,summary=summary))
    save(out/'DECISION.json',decision(summary))
    assert sources()==source
    for p,h in files.items():assert sha(p)==h,('input mutation',p.name)
    save(out/'PROOF.json',dict(passed=True,source_hashes=source,bindings=bindings,
                             partition_proof_sha256=sha(a.partition/'PROOF.json'),partition_verification_sha256=sha(a.partition_verify),
                             prior_score_proof_sha256=sha(a.prior/'PROOF.json'),prior_score_verification_sha256=sha(a.prior_verify),
                             raw_files={p.name:sha(p) for p in sorted(out.iterdir()) if p.is_file()},
                             center_member_distance_pairs=2000000,query_center_distance_pairs=262144,query_rows=64,false_prune=0,GPU_processes=0))
    print(json.dumps(decision(summary)),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('partition','partition-verify','prior','prior-verify','inputs','maintenance','references','output'):p.add_argument('--'+k,type=Path,required=True)
    main(p.parse_args())
