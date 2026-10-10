#!/usr/bin/env python3
"""Frozen CPU-only block layout/oracle/global-pivot certificate diagnostic."""
import argparse, ctypes, json, sys, subprocess
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'external_closure/pruning_value'))
from build import sha,save,outside_repo
from analyze import NODE
if not __debug__: raise RuntimeError('Assertions required')

def raw(p,dtype,shape):
    assert p.stat().st_size==np.prod(shape)*np.dtype(dtype).itemsize,('payload size',p.name)
    return np.memmap(p,dtype=dtype,mode='r',shape=shape)

def interval(scores,d):
    assert 0<d<=4096 and np.isfinite(scores).all() and np.all(scores>=0)
    e=(4*d+16)*2.0**-52
    lo=np.maximum(0,np.nextafter(np.sqrt(np.maximum(0,np.nextafter(scores/(1+e),-np.inf))),-np.inf))
    hi=np.nextafter(np.sqrt(np.nextafter(scores/(1-e),np.inf)),np.inf)
    return lo,hi

def radius_upper(radius,d):
    return float(interval(np.array([radius*radius]),d)[1][0])

def rejected(lo,hi,qlo,qhi,r):
    assert np.isfinite(lo).all() and np.isfinite(hi).all() and np.all(lo<=hi)
    return (qlo>np.nextafter(hi+r,np.inf)) | (lo>np.nextafter(qhi+r,np.inf))

def layouts(nodes,empty,order):
    n=len(order);nn=len(nodes);live=(empty==0)&(nodes['size']>0)
    assert np.array_equal(np.sort(order),np.arange(n))
    depth=np.zeros(nn,dtype=np.int32)
    for i in range(1,nn):depth[i]=depth[(i-1)//10]+1
    def group(ids,sort_inside):
        members=[order[int(nodes[i]['lid']):int(nodes[i]['lid']+nodes[i]['size'])] for i in ids]
        a=np.concatenate([np.sort(m) if sort_inside else m for m in members])
        assert np.array_equal(np.sort(a),np.arange(n)), 'complete occurrence partition'
        return a
    leaves=np.flatnonzero(live&(nodes['leaf']!=0))
    subtree=np.flatnonzero(live&(depth==3))
    dfs=[]
    def visit(i):
        if not live[i]:return
        if nodes[i]['leaf']:dfs.append(i)
        else:
            for j in range(i*10+1,min(i*10+11,nn)):visit(j)
    visit(0)
    result=dict(L0=np.arange(n,dtype=np.int32),L1=group(leaves,True),L2=group(subtree,True),L3=group(dfs,False))
    assert np.array_equal(result['L3'],order),'qualified order must match DFS'
    return result

def blocks(flags,permutation,size):
    return np.maximum.reduceat(np.asarray(flags)[permutation],np.arange(0,len(permutation),size)).astype(bool)

def stats(values):
    a=np.asarray(values,dtype=np.float64);assert len(a)>0 and np.isfinite(a).all()
    return dict(mean=float(a.mean()),median=float(np.median(a)),p10=float(np.quantile(a,.1)),p90=float(np.quantile(a,.9)),min=float(a.min()),max=float(a.max()))

def summarize(rows,keys,metrics):
    groups={}
    for r in rows:groups.setdefault(tuple(r[k] for k in keys),[]).append(r)
    return [dict(**dict(zip(keys,k)),queries=len(rs),statistics={m:stats([r[m] for r in rs if r[m] is not None]) for m in metrics if any(r[m] is not None for r in rs)}) for k,rs in groups.items()]

def admitted_D(certificate_summary,oracle_summary):
    result=[]
    for label in ('L0','L1','L2','L3'):
        oracle=[r for r in oracle_summary if r['layout']==label and r['block_size']==256]
        if len(oracle)!=2 or not all(r['statistics']['oracle_fraction']['mean']<=.30 for r in oracle):continue
        for strategy in ('S0','S1','S2'):
            for p in (1,2,4,8):
                rows=[r for r in certificate_summary if r['layout']==label and r['strategy']==strategy and r['pivot_count']==p and r['block_size']==256]
                if len(rows)==2 and all(r['statistics']['surviving_block_fraction']['mean']<=.70 for r in rows):result.append([label,strategy,p])
    return result

def distance(lib,x,p):
    out=np.empty(len(x),dtype=np.float64)
    rc=lib.distances(x.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),len(x),x.shape[1],int(p),out.ctypes.data_as(ctypes.POINTER(ctypes.c_double)))
    assert rc==0 and np.isfinite(out).all() and np.all(out>=0)
    return out

def load_library(path):
    lib=ctypes.CDLL(str(path.resolve()));lib.distances.argtypes=[ctypes.POINTER(ctypes.c_float),ctypes.c_int64,ctypes.c_int,ctypes.c_int64,ctypes.POINTER(ctypes.c_double)];lib.distances.restype=ctypes.c_int
    return lib

def choose_s0(nodes,empty):
    chosen=[]
    for i in np.flatnonzero((empty==0)&(nodes['size']>0)):
        p=int(nodes[i]['pid'])
        if p>=0 and p not in chosen:chosen.append(p)
        if len(chosen)==8:break
    assert len(chosen)==8;return chosen

def main(a):
    root=outside_repo(a.output);root.mkdir(exist_ok=False)
    contract=json.loads((HERE/'CONTRACT.json').read_text());inputs=json.loads(a.inputs.read_text())['records']
    assert contract['ownership'].startswith('Global shared')
    command=['g++','-std=c++17','-O3','-fno-fast-math','-ffp-contract=off','-fopenmp','-shared','-fPIC',str(HERE/'distance.cpp'),'-o',str(root/'distance.so')]
    source_files=[HERE/'run.py',HERE/'distance.cpp',HERE/'CONTRACT.json',HERE/'NUMERICS.md',HERE/'test_certificate.py',HERE.parent/'external_closure/pruning_value/build.py',HERE.parent/'external_closure/pruning_value/analyze.py']
    source={p.name:sha(p) for p in source_files}
    save(root/'REGISTERED.json',dict(source_hashes=source,input_manifest_sha256=sha(a.inputs),command=command,thread_count=4,GPU_processes=0,baseline=contract['baseline_commit']))
    subprocess.run(command,check=True)
    lib=load_library(root/'distance.so');save(root/'BUILD.json',dict(library_sha256=sha(root/'distance.so'),compiler=subprocess.check_output(['g++','--version'],text=True).splitlines()[0],source_hashes=source))
    lrows=[];orows=[];crows=[];bindings={};best8={};pivot_records={}
    radius=float(np.array([0x3f34a3d8],dtype=np.uint32).view(np.float32)[0]);r2=radius*radius
    for name in contract['snapshots']:
        record=inputs[name];pin=contract['inputs'][name];data=Path(record['data']);cap=a.prior_campaign/(name+'_capture');cache=a.prior_campaign/(name+'_cache');refdir=a.references/name
        files={'data':data,'reference':refdir/'REFERENCE.json','masks':cache/'masks','nodes':cap/'nodes','empty':cap/'empty','order':cap/'order'}
        hashes={k:sha(p) for k,p in files.items()}
        assert hashes=={k:pin[k+'_sha256'] for k in files},'input pin mismatch'
        header=np.fromfile(data,'<i4',count=3);d,n,metric=map(int,header);assert (n,d,metric)==(1000000,960,2) and data.stat().st_size==12+n*d*4
        x=np.memmap(data,dtype='<f4',mode='r',offset=12,shape=(n,d));assert np.isfinite(x).all()
        assert (cap/'nodes').stat().st_size%NODE.itemsize==0
        nodes=raw(cap/'nodes',NODE,((cap/'nodes').stat().st_size//NODE.itemsize,));empty=raw(cap/'empty','<i4',(len(nodes),));order=raw(cap/'order','<i4',(n,));masks=raw(cache/'masks','u1',(32,n));assert np.all(masks<=1)
        qids=record['qids'];assert qids==pin['qids'];assert len(qids)==len(set(qids))==32 and all(0<=q<n for q in qids)
        reference=json.loads((refdir/'REFERENCE.json').read_text());assert (reference['N'],reference['D'],reference['data_sha256'])==(n,d,hashes['data'])
        refs=np.empty((32,n),dtype=np.float64);rh={}
        for qi,q in enumerate(qids):
            rp=refdir/(str(q)+'.f64');rh[str(q)]=sha(rp);assert rh[str(q)]==reference['files'][str(q)];refs[qi]=raw(rp,'<f8',(n,));assert np.isfinite(refs[qi]).all() and np.all(refs[qi]>=0)
        truth=refs<=r2;assert np.all(masks[truth]==1),'tree lost a true hit'
        permutations=layouts(nodes,empty,order);permutation_hashes={}
        for label,perm in permutations.items():
            np.save(root/(name+'_'+label+'.npy'),perm);permutation_hashes[label]=sha(root/(name+'_'+label+'.npy'))
            for qi,q in enumerate(qids):
                lr=dict(snapshot=name,layout=label,query=qi,qid=q,candidate_count=int(masks[qi].sum()),candidate_fraction=float(masks[qi].mean()))
                for size in (32,256,512):
                    reached=blocks(masks[qi],perm,size);required=blocks(truth[qi],perm,size)
                    assert np.all(reached[required]);lr['touched_'+str(size)+'_blocks']=int(reached.sum());lr['reach_'+str(size)+'_fraction']=float(reached.mean())
                    hits=int(truth[qi].sum());nr=int(required.sum());nt=len(reached)
                    orows.append(dict(snapshot=name,layout=label,block_size=size,query=qi,qid=q,total_blocks=nt,current_tree_reached_blocks=int(reached.sum()),oracle_required_blocks=nr,oracle_fraction=nr/nt,empty_but_currently_reached_blocks=int(np.count_nonzero(reached&~required)),true_hits=hits,hits_per_required_block=hits/nr if nr else None,block_amplification=int(reached.sum())/nr if nr else None,empty_result=not bool(nr)))
                lrows.append(lr)
        save(root/(name+'_AB_CHECKPOINT.json'),dict(input_hashes=hashes,reference_file_hashes=rh,layout_hashes=permutation_hashes,queries=qids));print(name,'A/B complete',flush=True)
        # No oracle or query coordinates influence pivot selection; the evaluator is separate.
        strategies={'S0':choose_s0(nodes,empty),'S2':list(map(int,np.random.Generator(np.random.PCG64(20261010)).choice(n,8,replace=False)))}
        pool={};nearest=np.full(n,np.inf);selected=[];p=0
        for _ in range(8):
            selected.append(int(p));score=distance(lib,x,p);pool[int(p)]=score;nearest=np.minimum(nearest,score);nearest[selected]=-1;p=int(np.argmax(nearest))
        strategies['S1']=selected
        for s,pivots in sorted(strategies.items()):
            for p in pivots:
                if p not in pool:pool[p]=distance(lib,x,p)
                assert np.array_equal(pool[p][qids].view(np.uint64),refs[:,p].view(np.uint64)),('ordered distance mismatch',name,s,p)
            scores=np.stack([pool[p] for p in pivots]);np.save(root/(name+'_'+s+'_scores.npy'),scores)
            low,high=interval(scores,d);qlo,qhi=interval(scores[:,qids],d);rupper=radius_upper(radius,d)
            for label,perm in permutations.items():
                for size in (256,32,512):
                    starts=np.arange(0,n,size);lo=np.minimum.reduceat(low[:,perm],starts,axis=1);hi=np.maximum.reduceat(high[:,perm],starts,axis=1);lengths=np.minimum(size,n-starts);nt=len(starts)
                    np.savez(root/(name+'_'+label+'_'+s+'_'+str(size)+'_bounds.npz'),lo=lo,hi=hi)
                    for qi,q in enumerate(qids):
                        req=blocks(truth[qi],perm,size)
                        rej=rejected(lo,hi,qlo[:,qi,None],qhi[:,qi,None],rupper)
                        for count in (1,2,4,8):
                            keep=~np.any(rej[:count],axis=0);false=int(np.count_nonzero(req&~keep));assert false==0,('false prune',name,label,s,count,qi,size)
                            nk=int(keep.sum());nr=int(req.sum())
                            crows.append(dict(snapshot=name,layout=label,strategy=s,pivot_count=count,block_size=size,query=qi,qid=q,query_pivot_distance_count=count,certificate_scalar_reads=2*count*nt,certificate_pairs_checked=count*nt,certificate_metadata_bytes=16*count*nt,rejected_blocks=nt-nk,surviving_blocks=nk,total_blocks=nt,surviving_block_fraction=nk/nt,surviving_object_count=int(lengths[keep].sum()),oracle_required_blocks=nr,oracle_gap_blocks=nk-nr,false_keep_blocks=int(np.count_nonzero(keep&~req)),false_prune_blocks=false,certificate_efficiency=(nt-nk)/count,oracle_ratio=nk/nr if nr else None,non_tiny_oracle=nr/nt>=.01))
            print(name,s,pivots,'sweep complete',flush=True)
        pivot_records[name]=strategies;bindings[name]=dict(input_hashes=hashes,reference_file_hashes=rh,layout_hashes=permutation_hashes,queries=qids,pivots=strategies)
        assert {k:sha(p) for k,p in files.items()}==hashes,'input mutation'
        assert {str(q):sha(refdir/(str(q)+'.f64')) for q in qids}==rh,'reference mutation'
    lm=['candidate_count','candidate_fraction']+[k for size in (32,256,512) for k in ('touched_'+str(size)+'_blocks','reach_'+str(size)+'_fraction')]
    om=['current_tree_reached_blocks','oracle_required_blocks','oracle_fraction','empty_but_currently_reached_blocks','true_hits','hits_per_required_block','block_amplification']
    cm=['query_pivot_distance_count','certificate_scalar_reads','rejected_blocks','surviving_blocks','surviving_block_fraction','surviving_object_count','oracle_gap_blocks','false_keep_blocks','false_prune_blocks','certificate_efficiency']
    ls=summarize(lrows,['snapshot','layout'],lm);os=summarize(orows,['snapshot','layout','block_size'],om);cs=summarize(crows,['snapshot','layout','strategy','pivot_count','block_size'],cm)
    for name in contract['snapshots']:best8[name]=min(r['statistics']['surviving_block_fraction']['mean'] for r in cs if r['snapshot']==name and r['block_size']==256 and r['pivot_count']==8)
    nogo=any(v>.80 for v in best8.values());admitted=admitted_D(cs,os)
    save(root/'LAYOUT_RESULTS.json',dict(rows=lrows,summary=ls))
    save(root/'ORACLE_BLOCK_RESULTS.json',dict(rows=orows,summary=os))
    save(root/'CERT_SWEEP.json',dict(rows=crows,summary=cs,pivots=pivot_records,configurations_per_snapshot=48,sensitivity_evaluations_per_snapshot=96))
    save(root/'UPDATE_LOCALITY.json',dict(status='not_run',reason='Predeclared query NO-GO; no qualifying certificate. Stop before D.' if nogo else 'D requires a separate admitted deterministic insertion/split rule before execution.',admitted_candidates=admitted,not_evidence_of_update_failure=True))
    save(root/'DECISION.json',dict(decision='NO-GO' if nogo else 'CONDITIONAL',best_P8_mean_surviving_256=best8,D_admitted=bool(admitted) and not nogo,scope='Only these global interval certificates/layouts, snapshots and queries; not all possible metric summaries or GPU trees',next='Stop this certificate design; no GPU prototype or P>8' if nogo else 'No automatic GPU promotion; evaluate admitted D candidates under a frozen local update rule'))
    assert {p.name:sha(p) for p in source_files}==source,'source mutation'
    save(root/'PROOF.json',dict(passed=True,contract_sha256=sha(HERE/'CONTRACT.json'),source_hashes=source,library_sha256=sha(root/'distance.so'),bindings=bindings,all_false_prune_blocks=sum(r['false_prune_blocks'] for r in crows),counts=dict(layout_rows=len(lrows),oracle_rows=len(orows),certificate_rows=len(crows)),best_P8_mean_surviving_256=best8,source_and_inputs_unchanged=True,GPU_processes=0,raw_files={p.name:sha(p) for p in sorted(root.iterdir()) if p.is_file()}))
    print('Decision', 'NO-GO' if nogo else 'CONDITIONAL',best8,flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for key in ('inputs','prior-campaign','references','output'):p.add_argument('--'+key,type=Path,required=True)
    main(p.parse_args())
