"""Query-blind balanced partitions and separately evaluated safe-ball diagnostics."""
if not __debug__:
    raise SystemExit('Assertions are mandatory.')
import argparse
import ctypes
import json
import os
from pathlib import Path
import sys
import time
import subprocess
import numpy as np

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent.parent
sys.path.insert(0,str(HERE.parent/'block_local_ball_20261011'))
from ball import library, pair_scores, ball_keep, interval, radius_upper, sha, save, stats, outside_repo as parent_outside_repo


def load(path):
    return json.loads(Path(path).read_text())


def outside_repo(path):
    path=parent_outside_repo(path)
    if path.is_relative_to(ROOT.resolve()):raise ValueError('Raw output must also be outside the execution source tree.')
    return path


def source_ids():
    paths=[HERE/n for n in ('CONTRACT.json','geometry.cpp','tree_study.py','run_study.py','test_study.py','verify_study.py')]
    paths += [HERE.parent/'block_local_ball_20261011'/n for n in ('pairs.cpp','ball.py')]
    paths += [HERE.parent/'certificate_aware_partition_20261010/partition.py',
              HERE.parent/'block_certificate_headroom_20261010/run.py']
    paths += [HERE.parent/'external_closure/pruning_value'/n for n in ('build.py','analyze.py')]
    return {str(p.relative_to(ROOT)):sha(p) for p in paths}


def runtime_identity():
    np.dot(np.ones((4,4)),np.ones((4,4)))
    paths={line.split()[-1] for line in Path('/proc/self/maps').read_text().splitlines()
           if any(word in line.lower() for word in ('openblas','libblas','mkl_rt')) and '/' in line}
    assert paths,'Actual BLAS object must be identifiable.'
    omp=Path(subprocess.check_output(['g++','-print-file-name=libgomp.so'],text=True).strip()).resolve()
    omphash=sha(omp)
    for line in Path('/proc/self/maps').read_text().splitlines():
        if 'libgomp' in line and '/' in line:assert sha(Path(line.split()[-1]))==omphash
    return dict(NumPy=np.__version__,blas_objects={p:sha(Path(p)) for p in sorted(paths)},
                configured_OpenMP_object={str(omp):omphash},
                thread_environment={k:os.environ.get(k) for k in ('OMP_NUM_THREADS','OMP_THREAD_LIMIT','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS')})


def bind(data, references):
    c=load(HERE/'CONTRACT.json');pin=c['input_identity'];t=c['task']
    assert data.stat().st_size==pin['data_file_bytes'] and sha(data)==pin['data_sha256']
    assert tuple(np.fromfile(data,'<i4',count=3))==(t['D'],t['N'],2)
    parent=HERE.parent/'pdx_bond_gpu_realizability_gate4_20261015_recovery_01/evidence/INPUT_IDENTITY.json'
    old=HERE.parent/'fixed_batch_dag_gate0_20261019/CONTRACT.json'
    assert sha(parent)==pin['parent_identity_sha256'] and sha(old)==pin['old_query_contract_sha256']
    assert load(parent)['qids']==load(old)['qids']==t['qids']
    for name,h in pin['reference_sha256'].items():
        p=references/name
        assert p.stat().st_size==t['N']*8 and sha(p)==h,name
    x=np.memmap(data,'<f4','r',offset=12,shape=(t['N'],t['D']))
    refs=np.stack([np.fromfile(references/(str(q)+'.f64'),'<f8') for q in t['qids']])
    assert np.isfinite(refs).all() and np.all(refs>=0)
    assert np.all(refs[np.arange(32),t['qids']]==0)
    return c,x,refs


def native(path):
    lib=library(path)
    lib.node_center.argtypes=[ctypes.POINTER(ctypes.c_float),ctypes.c_int64,ctypes.c_int,
        ctypes.POINTER(ctypes.c_int64),ctypes.c_int64,ctypes.POINTER(ctypes.c_double),
        ctypes.POINTER(ctypes.c_double),ctypes.POINTER(ctypes.c_int64)]
    lib.node_center.restype=ctypes.c_int
    return lib


def center(lib,x,ids):
    ids=np.ascontiguousarray(np.sort(ids),dtype=np.int64)
    mean=np.empty(x.shape[1],np.float64);span=np.empty_like(mean);chosen=ctypes.c_int64()
    rc=lib.node_center(x.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),len(x),x.shape[1],
        ids.ctypes.data_as(ctypes.POINTER(ctypes.c_int64)),len(ids),
        mean.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),span.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),ctypes.byref(chosen))
    assert rc==0 and np.isfinite(mean).all() and np.isfinite(span).all() and np.all(span>=0)
    return int(chosen.value),mean,span


def build(x,lib,kind,depth=12,seed=2026102007,sample=512,iterations=8):
    """No query/radius/reference argument exists at this construction boundary."""
    assert x.dtype==np.float32 and x.flags.c_contiguous and np.isfinite(x).all()
    assert kind in ('RANDOM_BALANCED','KD_MAXSPAN_MEDIAN','SAMPLED_PCA_MEDIAN') and len(x)>=2**depth
    n,d=x.shape;nn=2**(depth+1)-1;leaf=2**depth-1
    random_order=np.random.Generator(np.random.PCG64(seed)).permutation(n)
    rank=np.empty(n,np.int64);rank[random_order]=np.arange(n)
    centers=np.empty(nn,np.int64);radii=np.empty(nn,np.float64)
    starts=np.empty(nn,np.int64);sizes=np.empty(nn,np.int64);split=np.full(nn,-1,np.int32)
    leaves=[];cursor=0
    def visit(ids,node):
        nonlocal cursor
        ids=np.sort(ids).astype(np.int64,copy=False)
        centers[node],mu,span=center(lib,x,ids)
        scores=pair_scores(lib,x,ids,np.full(len(ids),centers[node],np.int64))
        radii[node]=float(interval(scores,d)[1].max())
        starts[node]=cursor;sizes[node]=len(ids)
        if node>=leaf:
            leaves.append(ids);cursor+=len(ids);return
        if kind=='RANDOM_BALANCED':
            ordered=ids[np.argsort(rank[ids])]
        elif kind=='KD_MAXSPAN_MEDIAN':
            j=int(np.argmax(span));split[node]=j
            ordered=ids[np.lexsort((ids,np.asarray(x[ids,j],np.float64)))]
        else:
            count=min(sample,len(ids))
            selected=ids if count==len(ids) else np.sort(ids[np.argpartition(rank[ids],count-1)[:count]])
            y=np.asarray(x[selected],np.float64)-mu
            variance=np.sum(y*y,axis=0);j=int(np.argmax(variance));split[node]=j
            v=np.zeros(d,np.float64);v[j]=1
            for _ in range(iterations):
                w=y.T@(y@v);norm=float(np.sqrt(np.dot(w,w)))
                if norm>0:v=w/norm
            projection=np.empty(len(ids),np.float64)
            for begin in range(0,len(ids),4096):
                part=ids[begin:begin+4096]
                projection[begin:begin+len(part)]=(np.asarray(x[part],np.float64)-mu)@v
            assert np.isfinite(projection).all()
            ordered=ids[np.lexsort((ids,projection))]
        cut=len(ids)//2
        visit(ordered[:cut],2*node+1);visit(ordered[cut:],2*node+2)
        assert sizes[node]==sizes[2*node+1]+sizes[2*node+2]
    visit(np.arange(n,dtype=np.int64),0)
    result=dict(perm=np.concatenate(leaves),centers=centers,radii=radii,starts=starts,sizes=sizes,split=split)
    validate(result,n,depth)
    return result


def validate(tree,n,depth):
    nn=2**(depth+1)-1;leaf=2**depth-1
    assert set(tree)=={'perm','centers','radii','starts','sizes','split'}
    for name in ('perm','centers','starts','sizes'):assert tree[name].dtype==np.int64
    assert tree['radii'].dtype==np.float64 and tree['split'].dtype==np.int32
    assert np.array_equal(np.sort(tree['perm']),np.arange(n))
    assert all(tree[k].shape==(nn,) for k in tree if k!='perm')
    assert np.all((tree['centers']>=0)&(tree['centers']<n))
    assert np.isfinite(tree['radii']).all() and np.all(tree['radii']>=0)
    assert tree['starts'][0]==0 and tree['sizes'][0]==n
    assert np.array_equal(np.sort(tree['starts'][leaf:]),np.r_[0,np.cumsum(tree['sizes'][leaf:])[:-1]])
    for i in range(nn):
        begin=int(tree['starts'][i]);end=begin+int(tree['sizes'][i])
        assert 0<=begin<end<=n and tree['centers'][i] in tree['perm'][begin:end]
        if i<leaf:
            assert tree['starts'][2*i+1]==begin and tree['sizes'][2*i+1]==tree['sizes'][i]//2
            assert tree['starts'][2*i+2]==begin+tree['sizes'][2*i+1]
            assert tree['sizes'][2*i+1]+tree['sizes'][2*i+2]==tree['sizes'][i]


def walk(reject,tree):
    nn=len(reject);leaf=(nn-1)//2;todo=[0];visited=[];kept=[];pruned=[]
    while todo:
        i=todo.pop();visited.append(i)
        if reject[i]:pruned.append(i)
        elif i>=leaf:kept.append(i)
        else:todo.extend((2*i+2,2*i+1))
    retained=sum(int(tree['sizes'][i]) for i in kept)
    assert retained+sum(int(tree['sizes'][i]) for i in pruned)==len(tree['perm'])
    return visited,kept,retained


def evaluate(tree,refs,qids,radius,depth=12,d=960):
    n=refs.shape[1];nn=len(tree['centers']);leaf=(nn-1)//2
    threshold=radius*radius
    minima=np.empty((len(refs),nn),np.float64)
    minima[:,leaf:]=np.minimum.reduceat(refs[:,tree['perm']],tree['starts'][leaf:],axis=1)
    for i in range(leaf-1,-1,-1):minima[:,i]=np.minimum(minima[:,2*i+1],minima[:,2*i+2])
    center_scores=refs[:,tree['centers']]
    keep=ball_keep(center_scores,tree['radii'],d,radius)
    oracle=minima>threshold;reject=~keep
    assert not np.any(reject&~oracle),'False prune:node contains a reference hit'
    sizes=tree['sizes'];rows=[];levels=[]
    for qi,q in enumerate(qids):
        visited,kept,retained=walk(reject[qi],tree)
        _,_,oracle_points=walk(oracle[qi],tree)
        bits=np.zeros(n,bool)
        for node in kept:
            start=int(tree['starts'][node]);bits[tree['perm'][start:start+sizes[node]]]=True
        truth=refs[qi]<=threshold
        assert np.all(bits[truth])
        leaf_oracle_mass=int(sizes[leaf:][oracle[qi,leaf:]].sum())
        leaf_cert_mass=int(sizes[leaf:][reject[qi,leaf:]].sum())
        p10,p50,p90=np.quantile(np.sqrt(refs[qi]),(.1,.5,.9))
        rows.append(dict(query=qi,qid=int(q),true_hits=int(truth.sum()),visited_nodes=len(visited),
            retained_points=retained,retained_fraction=retained/n,oracle_retained_points=oracle_points,
            oracle_prunable_fraction=1-oracle_points/n,flat_leaf_oracle_prunable_fraction=leaf_oracle_mass/n,
            flat_leaf_certificate_prunable_fraction=leaf_cert_mass/n,
            flat_leaf_certificate_capture=leaf_cert_mass/leaf_oracle_mass if leaf_oracle_mass else None,
            flat_leaf_missed_prunable_points=leaf_oracle_mass-leaf_cert_mass,
            coordinate_proxy_bytes=(len(visited)+retained)*d*4+d*4,
            node_metadata_read_proxy_bytes=len(visited)*32,
            full_scan_coordinate_bytes=n*d*4+d*4,
            distance_p10=float(p10),distance_p50=float(p50),distance_p90=float(p90),
            distance_contrast=float((p90-p10)/p50) if p50 else None,false_prune_nodes=0))
        for dep in range(depth+1):
            lo=2**dep-1;hi=2**(dep+1)-1
            omass=int(sizes[lo:hi][oracle[qi,lo:hi]].sum())
            cmass=int(sizes[lo:hi][reject[qi,lo:hi]].sum())
            assert cmass<=omass and int(sizes[lo:hi].sum())==n
            levels.append(dict(query=qi,qid=int(q),depth=dep,nodes=hi-lo,
                oracle_rejected_nodes=int(oracle[qi,lo:hi].sum()),certificate_rejected_nodes=int(reject[qi,lo:hi].sum()),
                oracle_prunable_points=omass,certificate_pruned_points=cmass,
                oracle_prunable_fraction=omass/n,certificate_pruned_fraction=cmass/n,
                certificate_capture=cmass/omass if omass else None,
                radius_mean=float(tree['radii'][lo:hi].mean()),radius_p90=float(np.quantile(tree['radii'][lo:hi],.9))))
    return rows,levels,dict(minima=minima,center_scores=center_scores,reject=reject.astype(np.uint8))


def population(data,references,library_path,kind,out):
    assert os.getpriority(os.PRIO_PROCESS,0)==10
    out=outside_repo(out)
    c,x,refs=bind(data,references);out.mkdir();sources=source_ids()
    save(out/'REGISTERED.json',dict(before_build=True,kind=kind,sources=sources,contract_sha256=sha(HERE/'CONTRACT.json'),
         library_sha256=sha(library_path),nice=10,data=str(data),references=str(references),runtime=runtime_identity()))
    start=time.monotonic();tree=build(x,native(library_path),kind)
    elapsed=time.monotonic()-start
    for name,value in tree.items():np.save(out/(name+'.npy'),value,allow_pickle=False)
    radius=float(np.array([int(c['task']['radius_bits'],16)],np.uint32).view(np.float32)[0])
    rows,levels,raw=evaluate(tree,refs,c['task']['qids'],radius)
    for name,value in raw.items():np.save(out/(name+'.npy'),value,allow_pickle=False)
    save(out/'RESULTS.json',dict(passed=True,kind=kind,rows=rows,levels=levels,construction_wall_seconds=elapsed,
         construction_time_scope='One CPU build;resource diagnostic,not paired end-to-end timing',GPU_starts=0,heldout_query_evaluations=0))
    assert source_ids()==sources
    assert sha(data)==c['input_identity']['data_sha256']
    assert all(sha(references/n)==h for n,h in c['input_identity']['reference_sha256'].items())
    assert runtime_identity()==load(out/'REGISTERED.json')['runtime']
    save(out/'COMPLETE.json',dict(passed=True,files={p.name:sha(p) for p in sorted(out.iterdir()) if p.is_file()},GPU_starts=0))
    print('POPULATION_PASS',kind,'32 queries;8191 nodes;0 false prune;0 GPU',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--data',type=Path,required=True);p.add_argument('--references',type=Path,required=True)
    p.add_argument('--library',type=Path,required=True);p.add_argument('--kind',choices=load(HERE/'CONTRACT.json')['builders'],required=True)
    p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    population(a.data.resolve(),a.references.resolve(),a.library.resolve(),a.kind,a.out.resolve())
