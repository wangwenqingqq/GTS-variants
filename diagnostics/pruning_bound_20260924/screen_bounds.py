#!/usr/bin/env python3
"""Screen exact leaf-level metric lower bounds on actual candidate leaves."""
import json
from pathlib import Path
import numpy as np
from analyze_tree import ROOT,SEED,LEAVES_PER_QUERY,read_tree,read_candidates

def main():
    output={'seed':SEED,'candidate_leaves_per_query':LEAVES_PER_QUERY,
            'bounds':['existing radial shell','centroid ball','axis-aligned box'],
            'datasets':{}}
    rng=np.random.default_rng(SEED)
    for ds in ('GIST','Deep'):
        base=ROOT/'data'/ds/'1000000'
        run=base/'runs/prune_dump_Q'
        n,d,tree,empty,ids=read_tree(run/'result.tree.bin')
        fixture=base/'fixtures'
        r=json.loads((fixture/'oracle.json').read_text())['radii']['normal']
        data=np.memmap(fixture/'data.f32bin',mode='r',dtype='<f4',offset=12,shape=(n,d))
        per=[]
        for q,candidates in read_candidates(run/'result.candidates.bin'):
            sampled=rng.choice(candidates,size=LEAVES_PER_QUERY,replace=False)
            qv=np.asarray(data[q],dtype=np.float64)
            stats=[]
            for node_ids in np.array_split(sampled,4):
                sizes=tree['size'][node_ids]
                assert np.all(sizes==10)
                pos=tree['lid'][node_ids,None]+np.arange(10)[None,:]
                pointids=ids[pos]
                points=np.asarray(data[pointids],dtype=np.float64)
                true=np.sqrt(np.sum((points-qv)**2,axis=2)).min(axis=1)
                lo=points.min(axis=1);hi=points.max(axis=1)
                delta=np.maximum(np.maximum(lo-qv,qv-hi),0)
                box=np.sqrt(np.sum(delta*delta,axis=1))
                centroid=points.mean(axis=1)
                rad=np.sqrt(np.sum((points-centroid[:,None,:])**2,axis=2)).max(axis=1)
                ball=np.maximum(0,np.sqrt(np.sum((centroid-qv)**2,axis=1))-rad)
                pivotids=tree['pid'][node_ids]
                piv=np.asarray(data[pivotids],dtype=np.float64)
                dqp=np.sqrt(np.sum((piv-qv)**2,axis=1))
                radial=np.maximum(0,tree['min_dis'][node_ids]-dqp)
                upper=(node_ids%10)!=0
                radial[upper]=np.maximum(radial[upper],dqp[upper]-tree['min_dis'][node_ids[upper]+1])
                assert np.all(box<=true+1e-10) and np.all(ball<=true+1e-10)
                stats.append(np.column_stack((true,radial,ball,box)))
            a=np.concatenate(stats)
            miss=a[:,0]>r
            per.append({'qid':int(q),'sampled':len(a),'empty_leaves':int(miss.sum()),
                        'pruned_by_existing_radial':int(np.sum(a[:,1]>r)),
                        'pruned_by_centroid_ball':int(np.sum(a[:,2]>r)),
                        'pruned_by_axis_box':int(np.sum(a[:,3]>r)),
                        'bound_medians':{'radial':float(np.median(a[:,1])),
                                         'ball':float(np.median(a[:,2])),
                                         'box':float(np.median(a[:,3])),
                                         'true_min':float(np.median(a[:,0]))}})
        totals={k:sum(x[k] for x in per) for k in
                ('sampled','empty_leaves','pruned_by_existing_radial',
                 'pruned_by_centroid_ball','pruned_by_axis_box')}
        output['datasets'][ds]={'radius':r,'totals':totals,'queries':per,
                                'axis_box_index_bytes_estimate':int(100000*2*d*4)}
    path=Path(__file__).resolve().parent/'BOUND_SCREEN.json'
    path.write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps({ds:x['totals'] for ds,x in output['datasets'].items()},indent=2))

if __name__=='__main__':main()
