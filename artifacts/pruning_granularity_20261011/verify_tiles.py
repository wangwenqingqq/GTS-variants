#!/usr/bin/env python3
"""Fresh stable-sort partitions, direct endpoints and owner-array oracle counts."""
import argparse
import csv
import subprocess
import sys
from pathlib import Path
import numpy as np
from tiles import HERE,SIZES,SNAPS,load,sha,save,outside_repo,raw,stats,interval,radius_upper,independent_partition,row,summarize,decide,costs,source_hashes,bind


def main(a):
    out=outside_repo(a.output);out.mkdir(exist_ok=False);c,prior,files=bind(a);proof=load(a.run/'PROOF.json')
    assert proof['passed'] and proof['source_hashes']==source_hashes()
    assert {p.name:sha(p) for p in a.run.iterdir() if p.is_file() and p.name!='PROOF.json'}==proof['raw_files']
    subprocess.run([sys.executable,str(HERE/'test_tiles.py'),'-v'],check=True)
    q=load(a.run/'GRANULARITY_RESULTS.json');observed={(r['snapshot'],r['tile_size'],r['query']):r for r in q['rows']};rows=[];layouts=[];count=0
    assert len(observed)==320
    r=float(np.array([0x3f34a3d8],dtype=np.uint32).view(np.float32)[0]);rup=radius_upper(r,960)
    with (a.run/'TILE_STATS.csv').open() as f:
        csvrows=iter(csv.DictReader(f))
        for name in SNAPS:
            occ=np.load(a.maintenance/(name+'.occurrence.npy'));n=len(occ);scores=np.load(a.prior/(name+'_S1_scores.npy'),mmap_mode='r')[:4]
            norms=np.sqrt(scores);low,high=interval(scores,960);qids=c['inputs'][name]['qids'];ql,qh=interval(scores[:,qids],960)
            for target in SIZES:
                perm,starts=independent_partition(norms,occ,np.arange(n),'P2',target);ends=np.r_[starts[1:],n];sizes=ends-starts;nb=len(starts)
                lo=np.empty((4,nb));hi=lo.copy();owner=np.empty(n,dtype=np.int32)
                for b,(start,end) in enumerate(zip(starts,ends)):
                    ids=perm[start:end];owner[ids]=b;lo[:,b]=low[:,ids].min(axis=1);hi[:,b]=high[:,ids].max(axis=1)
                    line=next(csvrows);assert line==dict(snapshot=name,tile_size=str(target),tile=str(b),objects=str(end-start));count+=1
                with np.load(a.run/(name+'_T'+str(target)+'.npz')) as packed:
                    for key,val in [('permutation',perm),('starts',starts),('lo',lo),('hi',hi)]:np.testing.assert_array_equal(packed[key],val)
                layouts.append(dict(snapshot=name,tile_size=target,total_tiles=nb,objects=n,occupancy=stats(sizes),physical_slots=nb*target,physical_occupancy=n/(nb*target),metadata_bytes=nb*64,endpoint_reads=nb*8))
                for qi,qid in enumerate(qids):
                    ref=raw(a.references/name/(str(qid)+'.f64'),'<f8',(n,));hits=ref<=r*r;required=np.zeros(nb,dtype=bool);required[np.unique(owner[hits])]=True
                    keep=np.ones(nb,dtype=bool)
                    for j in range(4):keep&=(ql[j,qi]<=np.nextafter(hi[j]+rup,np.inf))&(lo[j]<=np.nextafter(qh[j,qi]+rup,np.inf))
                    assert not np.any(required&~keep),'false prune'
                    no=int(np.count_nonzero(keep[owner]));oracle_objects=int(np.count_nonzero(required[owner]))
                    expected=row(name,target,qi,qid,n,nb,int(keep.sum()),no,int(required.sum()),int(hits.sum()),oracle_objects)
                    assert expected==observed[name,target,qi];rows.append(expected)
                print('verified',name,target,flush=True)
        assert next(csvrows,None) is None
    assert layouts==q['layouts'] and summarize(rows)==q['summary'] and costs(rows)==load(a.run/'COST_PROXY.json')
    assert decide(q['summary'])==load(a.run/'DECISION.json')
    oracle=[{k:r[k] for k in ('snapshot','tile_size','query','qid','total_tiles','oracle_required_tiles','oracle_tile_fraction','oracle_objects_in_required_tiles','empty_but_surviving_tiles','oracle_gap_tiles','true_hit_count','false_prune_tiles')} for r in rows]
    assert oracle==load(a.run/'ORACLE_BY_TILE.json')['rows']
    for p,h in files.items():assert sha(p)==h
    save(out/'VERIFY.json',dict(passed=True,proof_sha256=sha(a.run/'PROOF.json'),source_hashes=source_hashes(),verification_source_sha256=sha(Path(__file__)),independent_stable_sort_partitions=10,direct_tile_rows=count,owner_based_query_rows=320,all_layouts_summaries_costs_and_decision_reconstructed=True,false_prune_tiles=0,numerical_tests_passed=8,GPU_processes=0))


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('prior','prior-verify','partition','partition-verify','maintenance','references','run','output'):p.add_argument('--'+k,type=Path,required=True)
    main(p.parse_args())
