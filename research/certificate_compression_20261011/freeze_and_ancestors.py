#!/usr/bin/env python3
"""Stage A plus query-independent pivot-pool freeze; reuse all original truth scores."""
import argparse,gzip,json,math,sys
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
PRIOR=HERE.parent/'region_truth_diagnosis_20261011'
BASE=HERE.parent/'certified_navigation_20261010'
sys.path.insert(0,str(PRIOR));sys.path.insert(0,str(BASE))
from audit import load_index,sha,save
from analyze_region_truth import bounds_and_replay,classify,read_oracle,require


def main():
    p=argparse.ArgumentParser();p.add_argument('--index',type=Path,required=True)
    p.add_argument('--scores',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    m=json.loads((PRIOR/'evidence/QUERY_MANIFEST.json').read_text())
    raw=json.loads((PRIOR/'evidence/RAW_MANIFEST.json').read_text())
    require(sha(a.index)==m['tree_sha256'],'tree identity')
    require(sha(a.scores)==raw['local/run1/all_scores.bin']['sha256'],'prior score identity')
    n,d,h,ids,nodes,flags=load_index(a.index)
    require((n,d,h)==(1000000,960,6),'tree shape')
    scores=np.memmap(a.scores,mode='r',dtype='<f8',offset=16,shape=(8,n))
    _,os=read_oracle(PRIOR/'evidence/oracle8.bin')
    traces=json.loads(gzip.decompress((PRIOR/'evidence/G0_trace8.json.gz').read_bytes()))
    native=[];visited=[]
    for q in range(8):
        _,path,_,active,_=bounds_and_replay(nodes,scores[q],traces[q]['levels'])
        native.append(path);visited.append(active)
    native=np.array(native);visited=np.array(visited)
    perm=np.array(ids);storage={};reports=[]
    for level,size in [(3,1000),(4,100),(5,10)]:
        start=(10**level-1)//9;regions=np.arange(start,start+10**level)
        require(all(nodes[i][2]==size and nodes[i][3]==j*size for j,i in enumerate(regions)),'partition extents')
        values=scores[:,perm].reshape(8,10**level,size).min(axis=2)
        lbs=[];labels=[]
        for q in range(8):
            lb,truth,lab=classify(native[q,regions],values[q],float(os[q,-1]));lbs.append(lb);labels.append(lab)
        lbs=np.array(lbs);labels=np.array(labels);active=visited[:,regions]
        truth_res=int((labels==2).sum())*size
        current_res=int((labels!=0).sum())*size
        require(not np.any((labels!=0)&~active),'counterfactual survivor missing from G0')
        storage.update({f'truth_sq_{level}':values,f'native_lb_{level}':lbs,f'visited_{level}':active})
        reports.append(dict(level=level,regions=10**level,objects_per_region=size,
            current_GTS_residual_fraction=current_res/(8*n),truth_residual_fraction=truth_res/(8*n),
            certificate_headroom_fraction=(current_res-truth_res)/(8*n),
            current_residual_objects=current_res,truth_residual_objects=truth_res,
            G0_visited_objects=int(active.sum())*size,
            per_query_truth_objects=((labels==2).sum(axis=1)*size).tolist(),
            per_query_current_objects=((labels!=0).sum(axis=1)*size).tolist()))
    require(reports[-1]['current_residual_objects']==6101720,'C0 bridge')
    require(reports[-1]['truth_residual_objects']==600,'truth bridge')
    proceed=reports[0]['truth_residual_fraction']<.5
    queried=sorted({nodes[i][0] for level in [3,4,5] for i in range((10**level-1)//9,(10**level-1)//9+10**level,10)})
    rng=np.random.default_rng(20261011)
    pool=sorted(map(int,rng.choice(queried,64,replace=False)))
    sample_rng=np.random.default_rng(2026101102)
    samples=[]
    for pair in sorted(map(int,sample_rng.choice(64*100000,128,replace=False))):
        pi,ri=divmod(pair,100000)
        samples.append(dict(pivot_index=pi,pivot_id=pool[pi],region_id=11111+ri,
                            object_ids=ids[ri*10:ri*10+10]))
    save(a.out/'INTERVAL_SAMPLE_MANIFEST.json',dict(seed=2026101102,pair_count=128,samples=samples))
    (a.out/'pivot_pool64.ids').write_text('64\n'+''.join(str(i)+'\n' for i in pool))
    storage['query_pivot_scores']=scores[:,pool].copy();storage['U_star_squared']=os[:,-1]
    np.savez_compressed(a.out/'ancestors.npz',**storage)
    save(a.out/'ANCESTOR_TRUTH.json',dict(levels=reports,leaf_alias=5,
        decision='CONTINUE_STAGE_B' if proceed else 'PARTITION_LIMITED',
        replayed_node_bits=888880,C0_bridge=True,truth_bridge=True))
    save(a.out/'INPUT_IDENTITY.json',dict(base_commit='1f4d4ab05c66b4cc2411b7532a86517b823d53f9',
        queries=m['queries'],data_sha256=m['data_sha256'],tree_sha256=m['tree_sha256'],
        prior_scores_sha256=sha(a.scores),prior_manifest_sha256=sha(PRIOR/'PUBLISH_MANIFEST.json'),
        score_contract='unchanged ordered RN FP64 squared L2; FMA disabled',GPU_used=False))
    save(a.out/'PIVOT_MANIFEST.json',dict(seed=20261011,pool=pool,pool_size=64,
        source_unique_original_queried_pivot_rows=len(queried),pool_sha256=sha(a.out/'pivot_pool64.ids'),
        interval_sample_manifest_sha256=sha(a.out/'INTERVAL_SAMPLE_MANIFEST.json'),
        selection='query-independent uniform distinct sample, then sorted; GLOBAL farthest-first seed=min ID',
        ancestors_sha256=sha(a.out/'ancestors.npz'),contract_sha256=sha(HERE/'CONTRACT.yaml')))
    print(json.dumps(reports,indent=2));print('Stage B admitted:',proceed)

if __name__=='__main__':main()
