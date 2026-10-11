#!/usr/bin/env python3
"""Five independently constructed capacities; fixed pivot/query/reference chain."""
import argparse
import csv
import os
import platform
import subprocess
import sys
from pathlib import Path
import numpy as np
from tiles import HERE,SIZES,SNAPS,load,sha,save,outside_repo,raw,stats,make_tiles,bounds,evaluate,summarize,decide,costs,source_hashes,bind


def main(a):
    out=outside_repo(a.output);out.mkdir(exist_ok=False);source=source_hashes()
    assert all(os.environ.get(k)=='4' for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'))
    assert os.getpriority(os.PRIO_PROCESS,0)==15
    save(out/'REGISTERED.json',dict(source_hashes=source,contract_sha256=sha(HERE/'CONTRACT.json'),python=platform.python_version(),numpy=np.__version__,CPU_threads_max=4,nice_actual=15,GPU_processes=0,scope='Structural counts only, no query/GPU/E2E time'))
    subprocess.run([sys.executable,str(HERE/'test_tiles.py'),'-v'],check=True)
    c,prior,files=bind(a);anchor=load(a.partition/'BLOCK_SELECTIVITY.json')['rows'];rows=[];layout=[];bindings={}
    radius=float(np.array([0x3f34a3d8],dtype=np.uint32).view(np.float32)[0])
    with (out/'TILE_STATS.csv').open('x',newline='') as f:
        writer=csv.writer(f,lineterminator='\n');writer.writerow(['snapshot','tile_size','tile','objects'])
        for name in SNAPS:
            occ=np.load(a.maintenance/(name+'.occurrence.npy'));n=len(occ);assert n==1000000
            scores=np.load(a.prior/(name+'_S1_scores.npy'),mmap_mode='r')[:4];norms=np.sqrt(scores)
            qids=c['inputs'][name]['qids'];pivots=prior['bindings'][name]['pivots']['S1'][:4]
            refs=np.stack([raw(a.references/name/(str(q)+'.f64'),'<f8',(n,)) for q in qids]);truth=refs<=radius*radius
            assert np.array_equal(scores[:,qids].T.view(np.uint64),refs[:,pivots].view(np.uint64))
            packed={}
            for target in SIZES:
                perm,starts=make_tiles(norms,occ,target);lo,hi=bounds(scores,perm,starts);sizes=np.diff(np.r_[starts,n]);nb=len(starts)
                if target==256:
                    with np.load(a.partition/(name+'_S1_P2.npz')) as old:
                        np.testing.assert_array_equal(perm,old['permutation']);np.testing.assert_array_equal(starts,old['starts'])
                np.savez(out/(name+'_T'+str(target)+'.npz'),permutation=perm,starts=starts,lo=lo,hi=hi)
                packed[target]=(perm,starts,lo,hi)
                layout.append(dict(snapshot=name,tile_size=target,total_tiles=nb,objects=n,occupancy=stats(sizes),physical_slots=nb*target,physical_occupancy=n/(nb*target),metadata_bytes=nb*64,endpoint_reads=nb*8))
                writer.writerows([name,target,b,int(size)] for b,size in enumerate(sizes))
            for target in SIZES:
                perm,starts,lo,hi=packed[target];rr=evaluate(name,target,scores,perm,starts,lo,hi,truth,qids,radius)
                if target==256:
                    old=[r for r in anchor if (r['snapshot'],r['strategy'],r['partition'],r['pivot_count'])==(name,'S1','P2',4)]
                    assert len(old)==32
                    for r,o in zip(rr,old):
                        for k,v in [('qid','qid'),('surviving_tiles','surviving_blocks'),('surviving_objects','candidate_objects_in_surviving_blocks'),('surviving_object_fraction','surviving_object_fraction'),('oracle_required_tiles','oracle_required_blocks'),('oracle_gap_tiles','oracle_gap_blocks')]:assert r[k]==o[v],('anchor',name,r['query'],k)
                rows.extend(rr);print(name,target,'tiles',len(starts),'mean objects',np.mean([r['surviving_object_fraction'] for r in rr]),flush=True)
            for coarse,fine in zip(SIZES,SIZES[1:]):
                cp,cs,*_=packed[coarse];fp,fs,*_=packed[fine];owner=np.empty(n,dtype=np.int32);owner[cp]=np.repeat(np.arange(len(cs)),np.diff(np.r_[cs,n]))
                assert np.array_equal(np.minimum.reduceat(owner[fp],fs),np.maximum.reduceat(owner[fp],fs)),'non-nested membership'
                cr=[r for r in rows if r['snapshot']==name and r['tile_size']==coarse];fr=[r for r in rows if r['snapshot']==name and r['tile_size']==fine]
                assert all(b['surviving_objects']<=a['surviving_objects'] and b['true_hit_count']==a['true_hit_count'] for a,b in zip(cr,fr))
            bindings[name]=dict(pivots=pivots,queries=qids,S1_score_sha256=prior['raw_files'][name+'_S1_scores.npy'],occurrence_sha256=c['occurrence_sha256'][name],partition256_sha256=c['partition_sha256'][name],data_sha256=c['inputs'][name]['data_sha256'],reference_hashes=prior['bindings'][name]['reference_file_hashes'],anchor_exact=True,nested_member_sets_verified=True)
    assert len(rows)==320 and len(layout)==10
    summary=summarize(rows);save(out/'GRANULARITY_RESULTS.json',dict(rows=rows,summary=summary,layouts=layout))
    save(out/'ORACLE_BY_TILE.json',dict(rows=[{k:r[k] for k in ('snapshot','tile_size','query','qid','total_tiles','oracle_required_tiles','oracle_tile_fraction','oracle_objects_in_required_tiles','empty_but_surviving_tiles','oracle_gap_tiles','true_hit_count','false_prune_tiles')} for r in rows]))
    save(out/'COST_PROXY.json',costs(rows));save(out/'DECISION.json',decide(summary))
    assert source_hashes()==source
    for p,h in files.items():assert sha(p)==h,('input mutation',p.name)
    save(out/'PROOF.json',dict(passed=True,source_hashes=source,input_file_count=len(files),bindings=bindings,raw_files={p.name:sha(p) for p in out.iterdir() if p.is_file()},query_rows=320,independent_partition_builds=10,anchor256_exact=True,nested_member_sets=True,false_prune_tiles=0,numerical_tests_passed=8,GPU_processes=0))
    print(decide(summary),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('prior','prior-verify','partition','partition-verify','maintenance','references','output'):p.add_argument('--'+k,type=Path,required=True)
    main(p.parse_args())
