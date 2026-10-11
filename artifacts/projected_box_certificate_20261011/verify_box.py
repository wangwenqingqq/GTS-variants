#!/usr/bin/env python3
"""O0 scalar-left-to-right projection and owner-based oracle reconstruction."""
import argparse
import json
import subprocess
import sys
from fractions import Fraction
from pathlib import Path
import numpy as np
from box import HERE,sha,save,outside_repo,raw,stats,library,project,projection_interval,select_directions,threshold,sources,bind,summarize,decision


def scalar_lower(ql,qh,lo,hi):
    total=0.
    for j in range(4):
        delta=max(0.,float(np.nextafter(float(lo[j])-float(qh[j]),-np.inf)),float(np.nextafter(float(ql[j])-float(hi[j]),-np.inf)))
        term=max(0.,float(np.nextafter(delta*delta,-np.inf)));total=max(0.,float(np.nextafter(total+term,-np.inf)))
    return total


def main(a):
    out=outside_repo(a.output);out.mkdir(exist_ok=False)
    c,prior,inputs,files=bind(a);p=json.loads((a.run/'PROOF.json').read_text());reg=json.loads((a.run/'REGISTERED.json').read_text())
    assert p['passed'] and p['source_hashes']==reg['source_hashes']==sources() and reg['contract_sha256']==sha(HERE/'CONTRACT.json')
    assert {f.name:sha(f) for f in a.run.iterdir() if f.is_file() and f.name!='PROOF.json'}==p['raw_files']
    flags=['-std=c++17','-O0','-fno-fast-math','-ffp-contract=off','-fopenmp','-shared','-fPIC']
    subprocess.run(['g++',*flags,str(HERE/'project.cpp'),'-o',str(out/'scalar_projection.so')],check=True)
    subprocess.run([sys.executable,str(HERE/'test_box.py'),'--library',str(out/'scalar_projection.so'),'-v'],check=True)
    lib=library(out/'scalar_projection.so');dproof=json.loads((a.run/'DIRECTION_PROOF.json').read_text());directions=json.loads((a.run/'PCA_DIRECTIONS.json').read_text())
    assert dproof['passed'] and dproof['direction_json_sha256']==sha(a.run/'PCA_DIRECTIONS.json') and p['direction_proof_sha256']==sha(a.run/'DIRECTION_PROOF.json')
    with np.load(a.run/'PCA_CONSTRUCTION.npz') as f:
        u=f['directions'];mean=f['mean'];cov=f['covariance'];values=f['eigenvalues'];v2,u2,qual=select_directions(cov)
        np.testing.assert_array_equal(u.view(np.uint64),u2.view(np.uint64));np.testing.assert_array_equal(values.view(np.uint64),v2.view(np.uint64))
        assert u.tolist()==directions['directions'] and mean.tolist()==directions['mean'] and values.tolist()==directions['eigenvalues']
        for k,value in qual.items():assert dproof[k]==value
        # Separate exact row/column Gram construction, independent of gram_proof loop shape.
        exact=[]
        for j in range(4):
            row=[]
            for k in range(4):
                s=Fraction(0)
                for i in range(960):s+=Fraction.from_float(float(u[i,j]))*Fraction.from_float(float(u[i,k]))
                row.append(s)
            exact.append(row)
        assert [[str(v) for v in row] for row in exact]==dproof['gram_exact']
        a2=dproof['operator_norm_squared_upper'];bound=max(sum(abs(v) for v in row) for row in exact)
        assert Fraction.from_float(a2)>=bound and Fraction.from_float(float(np.nextafter(a2,-np.inf)))<bound
    query=json.loads((a.run/'SUMMARY_COMPARISON.json').read_text());blocks=json.loads((a.run/'PROJECTED_BOX_STATS.json').read_text())
    qmap={(r['snapshot'],r['query']):r for r in query['rows']};bmap={(r['snapshot'],r['block']):r for r in blocks['rows']}
    assert len(qmap)==64 and len(bmap)==8192;ballrows=json.loads((a.ball/'SUMMARY_COMPARISON.json').read_text())['rows']
    reconstructed=[];blockrows=[];r=float(np.array([0x3f34a3d8],dtype=np.uint32).view(np.float32)[0]);thr=threshold(r,960,a2)
    for name in c['snapshots']:
        x=np.memmap(inputs[name]['data'],dtype='<f4',mode='r',offset=12,shape=(1000000,960))
        with np.load(a.partition/(name+'_S1_P2.npz')) as f:perm=f['permutation'];starts=f['starts']
        sizes=np.diff(np.r_[starts,1000000]);z,m=project(lib,x,u,True);lo,hi=projection_interval(z,m,u)
        blo=np.stack([lo[perm[first:first+size]].min(axis=0) for first,size in zip(starts,sizes)])
        bhi=np.stack([hi[perm[first:first+size]].max(axis=0) for first,size in zip(starts,sizes)])
        with np.load(a.run/(name+'_projections.npz')) as f:
            for k,val in [('z',z),('maxabs',m),('lo',lo),('hi',hi),('box_lo',blo),('box_hi',bhi)]:np.testing.assert_array_equal(val.view(np.uint64),f[k].view(np.uint64))
        for b,size in enumerate(sizes):
            expected=dict(snapshot=name,block=b,size=int(size),lo=blo[b].tolist(),hi=bhi[b].tolist(),width=(bhi[b]-blo[b]).tolist())
            assert expected==bmap[name,b];blockrows.append(expected)
        owner=np.empty(1000000,dtype=np.int32);owner[perm]=np.repeat(np.arange(4096),sizes)
        qids=c['inputs'][name]['qids'];qz,qm=project(lib,np.ascontiguousarray(x[qids]),u,True)
        np.testing.assert_array_equal(qz.view(np.uint64),z[qids].view(np.uint64));qlo,qhi=projection_interval(qz,qm,u)
        old=[b for b in ballrows if b['snapshot']==name]
        for qi,q in enumerate(qids):
            ref=raw(a.references/name/(str(q)+'.f64'),'<f8',(1000000,));hits=np.flatnonzero(ref<=r*r);req=np.zeros(4096,dtype=bool);req[np.unique(owner[hits])]=True
            k=np.array([scalar_lower(qlo[qi],qhi[qi],l,h)<=thr for l,h in zip(blo,bhi)]);assert not np.any(req&~k)
            nk,nr,no=int(k.sum()),int(req.sum()),int(sizes[k].sum());o=old[qi]
            expected=dict(snapshot=name,query=qi,qid=q,total_blocks=4096,global4_surviving_blocks=o['global4_surviving_blocks'],local_ball_surviving_blocks=o['local_ball_surviving_blocks'],projected_box_surviving_blocks=nk,oracle_required_blocks=nr,
                global4_survival_fraction=o['global4_survival_fraction'],local_ball_survival_fraction=o['local_ball_survival_fraction'],projected_box_survival_fraction=nk/4096,oracle_fraction=nr/4096,
                projected_box_false_prune=0,projected_box_oracle_gap=nk-nr,true_hits=len(hits),surviving_objects=no,global4_surviving_objects=o['global4_surviving_objects'],local_ball_surviving_objects=o['surviving_objects'],
                query_projection_ops=4,numeric_maxabs_reductions=1,summary_endpoint_reads=32768,summary_metadata_bytes=262144,direction_coordinate_bytes=30720,
                modeled_total_fullD_equivalent_work=5+no,modeled_dot_only_plus_verification=4+no,modeled_total_coordinate_bytes=30720+3840+no*3840)
            assert expected==qmap[name,qi];reconstructed.append(expected)
        print(name,'verified all scalar projections, boxes and 32 rows',flush=True)
    assert summarize(reconstructed)==query['summary'] and decision(query['summary'])==json.loads((a.run/'DECISION.json').read_text())
    assert blocks['summary']==[dict(snapshot=name,blocks=4096,width_by_direction=[stats([r['width'][j] for r in blockrows if r['snapshot']==name]) for j in range(4)]) for name in c['snapshots']]
    for path,h in files.items():assert sha(path)==h
    save(out/'VERIFY.json',dict(passed=True,proof_sha256=sha(a.run/'PROOF.json'),source_hashes=sources(),verification_source_sha256=sha(Path(__file__)),
        fresh_compiler_flags=flags,fresh_library_sha256=sha(out/'scalar_projection.so'),object_projections_recomputed=2000000,query_projections_recomputed=64,
        boxes_reconstructed=8192,all_rows_and_summaries_reconstructed=True,represented_gram_exact_reconstructed=True,PCA_from_frozen_covariance_reconstructed=True,
        numerical_tests_passed=17,false_prune=0,decision=decision(query['summary'])['decision'],GPU_processes=0))


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('partition','partition-verify','prior','prior-verify','inputs','maintenance','references','ball','run','output'):p.add_argument('--'+k,type=Path,required=True)
    main(p.parse_args())
