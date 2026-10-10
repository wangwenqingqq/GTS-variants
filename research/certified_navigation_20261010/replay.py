#!/usr/bin/env python3
"""CPU frontier model of pinned V2 policy; diagnostic-only, no leaf answers/timing claims."""
import argparse
import csv
import json
from pathlib import Path
import numpy as np
from audit import load_index, sha, save


def qids(path):
    x=[int(v) for v in Path(path).read_text().split()]
    if not x or x[0]!=len(x)-1 or len(set(x[1:]))!=x[0]: raise ValueError('query file')
    return x[1:]


def score(data, query, rows):
    # Separate ufuncs enforce ordered FP64 subtract/multiply/add without FMA.
    values=data[np.asarray(rows,dtype=np.int64)].astype(np.float64)
    result=np.zeros(len(rows),dtype=np.float64)
    for j in range(data.shape[1]):
        delta=values[:,j]-float(query[j]); result=result+delta*delta
    return result


def replay(data,index,query_ids,k):
    n,d,h,ids,nodes,flags=load_index(index)
    if data.shape!=(n,d) or len(query_ids)!=32 or k!=8: raise ValueError('bounded replay contract')
    rows=[];traces=[]
    for mode in ('G0_MODEL','G1_MODEL','G2_MODEL','G3_MODEL','G2_G0_U_REPLAY'):
        for qid in query_ids:
            if not 0<=qid<n: raise ValueError('query ID out of range')
            active={0};memo={};known={};seen_pivot=set();calls=hits=repeats=0;bound_tests=0;visited=0
            threshold=float('inf');start=1;leaf_ids=[];timeline=[]
            reuse=mode in ('G1_MODEL','G3_MODEL');candidate=mode in ('G2_MODEL','G3_MODEL','G2_G0_U_REPLAY')
            for level in range(1,h):
                width=10**level;groups=[];eligible=[]
                for nid in range(start,start+width,10):
                    if (nid-1)//10 in active and not flags[nid]:
                        groups.append(nid);eligible.append(nodes[nid][0])
                distances=[]
                if level>=3:
                    missing=list(dict.fromkeys(p for p in eligible if not (reuse and p in memo))) if reuse else eligible
                    computed=score(data,data[qid],missing)
                    values=iter(computed); pending=dict(zip(missing,computed)) if reuse else {}
                    for p in eligible:
                        repeats+=p in seen_pivot;seen_pivot.add(p)
                        if reuse and p in memo: s=memo[p];hits+=1
                        else:
                            s=float(pending[p] if reuse else next(values));calls+=1
                            if reuse: memo[p]=s
                        distances.append(float(np.sqrt(s)))
                        if candidate:known[p]=s
                    if len(distances)>=k:threshold=min(threshold,sorted(distances)[k-1])
                    if candidate and len(known)>=k:
                        threshold=min(threshold,float(np.sqrt(sorted(known.values())[k-1])))
                    if mode=='G2_G0_U_REPLAY':threshold=g0_timeline[qid][level-1]
                next_active=set()
                for nid,dis in zip(groups, distances if level>=3 else [0.]*len(groups)):
                    for child in range(nid,nid+10):
                        if flags[child]:continue
                        if level<=2:keep=True
                        else:
                            # Raw stored FP32 splits, as in upstream. NOT certified geometric intervals.
                            lb=max(0.,float(nodes[child][1])-dis)
                            if child%10:lb=max(lb,dis-float(nodes[child+1][1]))
                            keep=lb<=threshold;bound_tests+=1
                        visited+=1
                        if keep:next_active.add(child)
                active=next_active;timeline.append(threshold)
                traces.append(dict(mode=mode,query_id=qid,level=level,U=threshold,
                    active_regions=len(active),active_sha256=__import__("hashlib").sha256(np.asarray(sorted(active),dtype="<i4").tobytes()).hexdigest(),
                    known_distinct_candidates=len(known),pivot_calls=calls))
                start+=width
            for nid in active:
                if not nodes[nid][4]:raise ValueError('nonterminal frontier')
                leaf_ids.extend(ids[nodes[nid][3]:nodes[nid][3]+nodes[nid][2]])
            leaf_set=set(leaf_ids)
            if len(leaf_ids)!=len(leaf_set):raise ValueError('duplicate frontier ownership')
            pivot_leaf=len(seen_pivot&leaf_set)
            rows.append(dict(mode=mode,query_id=qid,pivot_distance_computations=calls,
                distinct_pivot_rows=len(seen_pivot),repeat_pivot_to_pivot=repeats,
                modeled_leaf_instances=len(leaf_ids),modeled_leaf_regions=len(active),
                modeled_pivot_to_leaf_hits=pivot_leaf if reuse else 0,
                pivot_to_leaf_reuse_opportunity=pivot_leaf,pivot_cache_hits=hits,
                bound_tests=bound_tests,considered_nodes=visited,final_U=threshold,
                modeled_distance_computations=calls+len(leaf_ids)-(pivot_leaf if reuse else 0)))
            if mode=='G0_MODEL':
                if 'g0_timeline' not in locals():g0_timeline={}
                g0_timeline[qid]=timeline
    return rows,traces


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('data','index','queries','manifest','out'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();reg=json.loads(a.manifest.read_text())
    if sha(a.data)!=reg['data_sha256'] or sha(a.index)!=reg['tree_sha256'] or sha(a.queries)!=reg['development_sha256']:
        raise ValueError('frozen input drift')
    header=np.fromfile(a.data,dtype='<i4',count=3)
    if list(header)!=[960,1000000,2] or a.data.stat().st_size!=12+4*960*1000000:
        raise ValueError('data identity')
    data=np.memmap(a.data,dtype='<f4',mode='r',offset=12,shape=(1000000,960))
    rows,traces=replay(data,a.index,qids(a.queries),8)
    a.out.mkdir(parents=True,exist_ok=False)
    for name,values in (('query_work_model.csv',rows),('threshold_model.csv',traces)):
        with (a.out/name).open('x',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(values[0]));w.writeheader();w.writerows(values)
    pairs={x['mode']:{r['query_id']:r for r in rows if r['mode']==x['mode']} for x in rows}
    for left,right in (('G0_MODEL','G1_MODEL'),('G2_MODEL','G3_MODEL'),('G0_MODEL','G2_G0_U_REPLAY')):
        for qid in qids(a.queries):
            for field in ('modeled_leaf_instances','modeled_leaf_regions','final_U'):
                if pairs[left][qid][field]!=pairs[right][qid][field]: raise ValueError('causal model invariant')
    save(a.out/'MODEL_RECEIPT.json',dict(kind='CPU model, not CUDA runtime evidence',
        query_count=32,modes=list(pairs),leaf_distances_computed=False,full_knn_correctness_verified=False,
        geometry_certified=False,G0_U_counterfactual_pass=True,
        data_sha256=reg['data_sha256'],tree_sha256=reg['tree_sha256'],query_sha256=sha(a.queries),
        sources={p.name:sha(p) for p in (Path(__file__),Path(__file__).with_name('audit.py'))}))
    print('PASS 32-query CPU frontier model; leaf answers, CUDA traces and timings NOT measured')


if __name__=='__main__':main()
