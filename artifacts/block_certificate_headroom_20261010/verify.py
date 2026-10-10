#!/usr/bin/env python3
"""Strict CPU reconciliation from frozen inputs, scores and freshly compiled source."""
import argparse,json,subprocess,os
from pathlib import Path
import numpy as np
from run import HERE,sha,save,outside_repo,raw,layouts,blocks,interval,radius_upper,rejected,choose_s0,load_library,distance,NODE
if not __debug__:raise RuntimeError('Assertions required')

def main(a):
    out=outside_repo(a.output);out.mkdir(exist_ok=False);root=outside_repo(a.run)
    proof=json.loads((root/'PROOF.json').read_text());registered=json.loads((root/'REGISTERED.json').read_text());build=json.loads((root/'BUILD.json').read_text());contract=json.loads((HERE/'CONTRACT.json').read_text())
    assert proof['passed'] and proof['contract_sha256']==sha(HERE/'CONTRACT.json')
    source_files=[a.executed_code/'run.py',a.executed_code/'distance.cpp',a.executed_code/'CONTRACT.json',a.executed_code/'NUMERICS.md',a.executed_code/'test_certificate.py',HERE.parent/'external_closure/pruning_value/build.py',HERE.parent/'external_closure/pruning_value/analyze.py']
    assert {p.name:sha(p) for p in source_files}==proof['source_hashes']==registered['source_hashes']==build['source_hashes']
    assert sha(root/'distance.so')==proof['library_sha256']==build['library_sha256']
    assert {p.name:sha(p) for p in root.iterdir() if p.is_file() and p.name!='PROOF.json'}==proof['raw_files'],'full raw inventory'
    assert sha(a.inputs)==registered['input_manifest_sha256']
    cmd=['g++','-std=c++17','-O3','-fno-fast-math','-ffp-contract=off','-fopenmp','-shared','-fPIC',str(HERE/'distance.cpp'),'-o',str(out/'distance.so')];subprocess.run(cmd,check=True);lib=load_library(out/'distance.so')
    for library in (root/'distance.so',out/'distance.so'):
        subprocess.run(['python3',str(a.executed_code/'test_certificate.py'),'--library',str(library),'-v'],env={**os.environ,'PYTHONPATH':str(HERE.parent/'external_closure/pruning_value')},check=True)
    inputs=json.loads(a.inputs.read_text())['records'];l=json.loads((root/'LAYOUT_RESULTS.json').read_text());o=json.loads((root/'ORACLE_BLOCK_RESULTS.json').read_text());c=json.loads((root/'CERT_SWEEP.json').read_text())
    assert [len(l['rows']),len(o['rows']),len(c['rows'])]==[256,768,9216]
    lr={(r['snapshot'],r['layout'],r['query']):r for r in l['rows']};orr={(r['snapshot'],r['layout'],r['block_size'],r['query']):r for r in o['rows']};cr={(r['snapshot'],r['layout'],r['strategy'],r['pivot_count'],r['block_size'],r['query']):r for r in c['rows']};assert [len(lr),len(orr),len(cr)]==[256,768,9216]
    qpin=float(np.array([0x3f34a3d8],dtype=np.uint32).view(np.float32)[0]);r2=qpin*qpin;comparisons=0
    for name in contract['snapshots']:
        rec=inputs[name];qids=rec['qids'];assert qids==contract['inputs'][name]['qids']==proof['bindings'][name]['queries']
        cap=a.prior_campaign/(name+'_capture');cache=a.prior_campaign/(name+'_cache');refdir=a.references/name
        files={'data':Path(rec['data']),'reference':refdir/'REFERENCE.json','masks':cache/'masks','nodes':cap/'nodes','empty':cap/'empty','order':cap/'order'}
        hashes={k:sha(p) for k,p in files.items()};assert hashes==proof['bindings'][name]['input_hashes']=={k:contract['inputs'][name][k+'_sha256'] for k in files}
        x=np.memmap(files['data'],dtype='<f4',offset=12,mode='r',shape=(1000000,960));n,d=x.shape
        nodes=raw(cap/'nodes',NODE,((cap/'nodes').stat().st_size//NODE.itemsize,));empty=raw(cap/'empty','<i4',(len(nodes),));order=raw(cap/'order','<i4',(n,));perms=layouts(nodes,empty,order);masks=raw(cache/'masks','u1',(32,n));assert np.all(masks<=1)
        refs=np.stack([raw(refdir/(str(q)+'.f64'),'<f8',(n,)) for q in qids]);truth=refs<=r2;assert np.all(masks[truth]==1)
        assert {str(q):sha(refdir/(str(q)+'.f64')) for q in qids}==proof['bindings'][name]['reference_file_hashes']
        pivots=proof['bindings'][name]['pivots'];assert pivots==c['pivots'][name];assert pivots['S0']==choose_s0(nodes,empty);assert pivots['S2']==list(map(int,np.random.Generator(np.random.PCG64(20261010)).choice(n,8,replace=False)))
        pool={};nearest=np.full(n,np.inf);selected=[]
        for p in pivots['S1']:
            assert p==(0 if not selected else int(np.argmax(nearest)))
            score=distance(lib,x,p);pool[p]=score;selected.append(p);nearest=np.minimum(nearest,score);nearest[selected]=-1;comparisons+=n
        for s in ('S0','S1','S2'):
            scores=np.load(root/(name+'_'+s+'_scores.npy'));assert scores.shape==(8,n)
            for i,p in enumerate(pivots[s]):
                if p not in pool:pool[p]=distance(lib,x,p);comparisons+=n
                assert np.array_equal(scores[i].view(np.uint64),pool[p].view(np.uint64)),('fresh distance',name,s,p)
                assert np.array_equal(scores[i,qids].view(np.uint64),refs[:,p].view(np.uint64))
            low,high=interval(scores,d);qlo,qhi=interval(scores[:,qids],d);r=radius_upper(qpin,d)
            for label,perm in perms.items():
                assert np.array_equal(perm,np.load(root/(name+'_'+label+'.npy')))
                for size in (256,32,512):
                    starts=np.arange(0,n,size);lo=np.minimum.reduceat(low[:,perm],starts,axis=1);hi=np.maximum.reduceat(high[:,perm],starts,axis=1);lengths=np.minimum(size,n-starts);nt=len(starts)
                    with np.load(root/(name+'_'+label+'_'+s+'_'+str(size)+'_bounds.npz')) as b:assert np.array_equal(lo,b['lo']) and np.array_equal(hi,b['hi'])
                    for qi,q in enumerate(qids):
                        req=blocks(truth[qi],perm,size);reach=blocks(masks[qi],perm,size);nr=int(req.sum());hits=int(truth[qi].sum());rj=rejected(lo,hi,qlo[:,qi,None],qhi[:,qi,None],r)
                        row=lr[name,label,qi];assert row['qid']==q and row['candidate_count']==int(masks[qi].sum()) and row['candidate_fraction']==float(masks[qi].mean()) and row['touched_'+str(size)+'_blocks']==int(reach.sum()) and row['reach_'+str(size)+'_fraction']==float(reach.mean())
                        expected_o=dict(snapshot=name,layout=label,block_size=size,query=qi,qid=q,total_blocks=nt,current_tree_reached_blocks=int(reach.sum()),oracle_required_blocks=nr,oracle_fraction=nr/nt,empty_but_currently_reached_blocks=int(np.count_nonzero(reach&~req)),true_hits=hits,hits_per_required_block=hits/nr if nr else None,block_amplification=int(reach.sum())/nr if nr else None,empty_result=not bool(nr));assert orr[name,label,size,qi]==expected_o
                        for p in (1,2,4,8):
                            keep=~np.any(rj[:p],axis=0);nk=int(keep.sum());false=int(np.count_nonzero(req&~keep));assert false==0
                            expected_c=dict(snapshot=name,layout=label,strategy=s,pivot_count=p,block_size=size,query=qi,qid=q,query_pivot_distance_count=p,certificate_scalar_reads=2*p*nt,certificate_pairs_checked=p*nt,certificate_metadata_bytes=16*p*nt,rejected_blocks=nt-nk,surviving_blocks=nk,total_blocks=nt,surviving_block_fraction=nk/nt,surviving_object_count=int(lengths[keep].sum()),oracle_required_blocks=nr,oracle_gap_blocks=nk-nr,false_keep_blocks=int(np.count_nonzero(keep&~req)),false_prune_blocks=false,certificate_efficiency=(nt-nk)/p,oracle_ratio=nk/nr if nr else None,non_tiny_oracle=nr/nt>=.01);assert cr[name,label,s,p,size,qi]==expected_c
        print(name,'strict reconstruction complete',flush=True)
    from run import summarize
    for result,keys in [(l,['snapshot','layout']),(o,['snapshot','layout','block_size']),(c,['snapshot','layout','strategy','pivot_count','block_size'])]:
        metrics=list(result['summary'][0]['statistics']);assert result['summary']==summarize(result['rows'],keys,metrics)
    best={name:min(r['statistics']['surviving_block_fraction']['mean'] for r in c['summary'] if r['snapshot']==name and r['block_size']==256 and r['pivot_count']==8) for name in contract['snapshots']}
    assert best==proof['best_P8_mean_surviving_256'];decision=json.loads((root/'DECISION.json').read_text());assert decision['best_P8_mean_surviving_256']==best
    assert not any(v>.8 for v in best.values()) and decision['decision']=='CONDITIONAL' and not decision['D_admitted']
    update=json.loads((root/'UPDATE_LOCALITY.json').read_text());assert update['status']=='not_run' and not update['admitted_candidates']
    save(out/'VERIFY.json',dict(passed=True,proof_sha256=sha(root/'PROOF.json'),verification_source_sha256=sha(HERE/'verify.py'),fresh_library_sha256=sha(out/'distance.so'),fresh_compiler_command=cmd,all_rows_reconstructed=True,all_summaries_reconstructed=True,original_and_fresh_library_passed_tests=True,fresh_distance_pairs_recomputed=comparisons,actual_false_prune_blocks=0,decision='CONDITIONAL',delivered_driver_sha256=sha(HERE/'run.py'),result_hashes={p:sha(root/p) for p in ['LAYOUT_RESULTS.json','ORACLE_BLOCK_RESULTS.json','CERT_SWEEP.json','UPDATE_LOCALITY.json','DECISION.json']}))
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('run','inputs','prior-campaign','references','output','executed-code'):p.add_argument('--'+k,type=Path,required=True)
    main(p.parse_args())
