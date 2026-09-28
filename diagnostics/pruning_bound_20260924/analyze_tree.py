#!/usr/bin/env python3
"""Reconstruct actual-tree radial pruning and compare with exact leaf distances."""
import csv
import hashlib
import json
from pathlib import Path
import numpy as np

ROOT=Path('/home/data/wangxuran/tmp/gts_20260922_cpu_io/leaf_early_l2_20260924')
TN=np.dtype([('pid','<i4'),('min_dis','<f4'),('size','<i4'),
             ('lid','<i4'),('is_leaf','<i4')])
SEED=240925
LEAVES_PER_QUERY=1024

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for part in iter(lambda:f.read(8*1024*1024),b''):h.update(part)
    return h.hexdigest()

def read_tree(path):
    with path.open('rb') as f:
        n,d,nodes,height,size=np.fromfile(f,dtype='<i4',count=5)
        tree=np.fromfile(f,dtype=TN,count=nodes)
        empty=np.fromfile(f,dtype='<i4',count=nodes)
        ids=np.fromfile(f,dtype='<i4',count=n)
        assert not f.read(1)
    assert len(tree)==nodes and len(empty)==nodes and len(ids)==n
    assert height==6 and size==20 and np.sum((empty==0)&(tree['is_leaf']==1))==100000
    return int(n),int(d),tree,empty,ids

def read_candidates(path):
    result=[]
    with path.open('rb') as f:
        records=int(np.fromfile(f,dtype='<i4',count=1)[0])
        for _ in range(records):
            q,nc=map(int,np.fromfile(f,dtype='<i4',count=2))
            ids=np.fromfile(f,dtype='<i4',count=nc)
            assert len(ids)==nc
            result.append((int(q),ids))
        assert not f.read(1)
    return result

def exact_leaf_min(data,qv,tree,id_list,node_ids):
    values=[]
    for block in np.array_split(node_ids,max(1,(len(node_ids)+255)//256)):
        lid=tree['lid'][block];size=tree['size'][block]
        slots=lid[:,None]+np.arange(int(max(size)))[None,:]
        valid=np.arange(slots.shape[1])[None,:]<size[:,None]
        pointids=id_list[slots[valid]]
        points=np.asarray(data[pointids],dtype=np.float64)
        dist=np.sqrt(np.sum((points-qv)**2,axis=1))
        offsets=np.r_[0,np.cumsum(size)]
        values.extend(float(np.min(dist[offsets[i]:offsets[i+1]]))
                      for i in range(len(block)))
    return np.asarray(values)

def main():
    rng=np.random.default_rng(SEED)
    report={'seed':SEED,'sampled_candidate_leaves_per_query':LEAVES_PER_QUERY,
            'datasets':{}}
    for ds in ('GIST','Deep'):
        base=ROOT/'data'/ds/'1000000'
        run=base/'runs/prune_dump_Q'
        n,d,tree,empty,id_list=read_tree(run/'result.tree.bin')
        fixture=base/'fixtures'
        radius=json.loads((fixture/'oracle.json').read_text())['radii']['normal']
        data=np.memmap(fixture/'data.f32bin',mode='r',dtype='<f4',offset=12,shape=(n,d))
        candidates=read_candidates(run/'result.candidates.bin')
        work=list(csv.DictReader((run/'result.work.csv').open()))
        assert [int(x['qid']) for x in work]==[q for q,_ in candidates]
        pivots=np.unique(tree['pid'][(empty==0)&(tree['pid']>=0)])
        pivot_pos=np.searchsorted(pivots,np.maximum(tree['pid'],0))
        per=[]
        for (q,gpu_cands),row in zip(candidates,work):
            qv=np.asarray(data[q],dtype=np.float64)
            pivot_data=np.asarray(data[pivots],dtype=np.float64)
            dp=np.sqrt(np.sum((pivot_data-qv)**2,axis=1))
            active=np.zeros(len(tree),dtype=bool);active[0]=True
            levels=[];leaf_lb=np.full(len(tree),np.nan)
            start,num=1,10
            for depth in range(1,6):
                ids=np.arange(start,start+num,dtype=np.int32)
                eligible=ids[active[(ids-1)//10] & (empty[ids]==0)]
                dist=dp[pivot_pos[eligible]]
                lb=np.maximum(0,tree['min_dis'][eligible].astype(np.float64)-dist)
                has_upper=(eligible%10)!=0
                ub=np.full(len(eligible),-np.inf)
                ub[has_upper]=dist[has_upper]-tree['min_dis'][eligible[has_upper]+1]
                lb=np.maximum(lb,ub)
                passing=eligible[lb<=radius]
                active[passing]=True
                levels.append({'depth':depth,'eligible':int(len(eligible)),
                               'passed':int(len(passing)),
                               'zero_bound_fraction':float(np.mean(lb<1e-7)),
                               'median_bound':float(np.median(lb)),
                               'p90_bound':float(np.quantile(lb,.9))})
                if depth==5:leaf_lb[eligible]=lb
                start+=num;num*=10
            predicted=np.flatnonzero(active & (tree['is_leaf']==1))
            missing=np.setdiff1d(gpu_cands,predicted,assume_unique=False)
            extra=np.setdiff1d(predicted,gpu_cands,assume_unique=False)
            sampled=rng.choice(gpu_cands,size=min(LEAVES_PER_QUERY,len(gpu_cands)),replace=False)
            true_min=exact_leaf_min(data,qv,tree,id_list,sampled)
            bound=leaf_lb[sampled]
            assert np.all(np.isfinite(bound))
            per.append({'qid':q,'levels':levels,
                        'gpu_candidates':int(len(gpu_cands)),
                        'hit_leaves':int(row['hit_leaves']),
                        'cpu_predicted_candidates':int(len(predicted)),
                        'cpu_gpu_candidate_symmetric_difference':int(len(missing)+len(extra)),
                        'sampled_leaf_true_min_median':float(np.median(true_min)),
                        'sampled_leaf_bound_median':float(np.median(bound)),
                        'sampled_leaf_bound_over_true_median':float(np.median(bound/true_min)),
                        'sampled_leaf_empty_fraction':float(np.mean(true_min>radius))})
        report['datasets'][ds]={'radius':radius,'n':n,'dimensions':d,
            'tree_sha256':sha(run/'result.tree.bin'),
            'candidates_sha256':sha(run/'result.candidates.bin'),
            'receipt_sha256':sha(run/'receipt.json'),
            'nonempty_pivot_count':int(len(pivots)),'queries':per}
    output=Path(__file__).resolve().parent/'TREE_EVIDENCE.json'
    output.write_text(json.dumps(report,indent=2)+'\n')
    for ds,x in report['datasets'].items():
        q=x['queries']
        print(ds,'candidate_diff',sum(v['cpu_gpu_candidate_symmetric_difference'] for v in q),
              'leaf_lb_median',np.median([v['sampled_leaf_bound_median'] for v in q]),
              'leaf_true_min_median',np.median([v['sampled_leaf_true_min_median'] for v in q]),
              'hit_leaf_range',min(v['hit_leaves'] for v in q),max(v['hit_leaves'] for v in q))

if __name__=='__main__':main()
