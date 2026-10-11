#!/usr/bin/env python3
"""Freeze eight development queries and independent validation samples before truth scan."""
import argparse,csv,gzip,hashlib,json,math,struct,sys
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'certified_navigation_20261010'
sys.path.insert(0,str(BASE))
from audit import load_index,sha,save,tree_audit
from verify import traces,result


def main():
    p=argparse.ArgumentParser();p.add_argument('--index',type=Path,required=True);p.add_argument('--trace',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);(a.out/'evidence').mkdir()
    m=json.loads((BASE/'QUERY_MANIFEST.json').read_text())
    if sha(a.index)!=m['tree_sha256']:raise ValueError('tree drift')
    raw=json.loads((BASE/'evidence/e1_v7/RAW_MANIFEST.json').read_text())
    if sha(a.trace)!=raw['G0/stdout.log']:raise ValueError('original exact-visit trace drift')
    n,d,h,ids,nodes,flags=load_index(a.index)
    leaf=[i for i,x in enumerate(nodes) if not flags[i] and x[4]]
    if len(leaf)!=100000 or any(nodes[i][2]!=10 for i in leaf):raise ValueError('frozen terminal partition')
    with (BASE/'evidence/e1_v7/G0_raw_work.csv').open() as f:work=list(csv.DictReader(f))
    oracle,shape=result(BASE/'evidence/e1_v7/oracle_result.bin');N,D,Q,K=shape
    oi=np.frombuffer(oracle,dtype='<i4',count=Q*K,offset=16).reshape(Q,K)
    os=np.frombuffer(oracle,dtype='<f8',count=Q*K,offset=16+Q*K*4).reshape(Q,K)
    rows=traces(a.trace);assert len(rows)==Q*5
    info={int(w['qid']):dict(qid=int(w['qid']),original_index=i,leaf_calls=int(w['leaf_calls']),
          U_final=rows[i*5+4]['upper'],U_star=math.sqrt(os[i,-1])) for i,w in enumerate(work)}
    for v in info.values():v['upper_ratio']=v['U_final']/v['U_star'] if v['U_star'] else None
    ordered=sorted(info,key=lambda q:(info[q]['leaf_calls'],q));selected=[];selection=[]
    groups=[('low_visits',ordered[:2]),('median_visits',ordered[15:17]),('high_visits',ordered[-2:])]
    for name,qs in groups:
        for q in qs:selected.append(q);selection.append(dict(stratum=name,**info[q]))
    gaps=sorted((q for q in info if q not in selected),key=lambda q:(-info[q]['upper_ratio'],q))[:2]
    for q in gaps:selected.append(q);selection.append(dict(stratum='largest_remaining_upper_gap',**info[q]))
    assert len(set(selected))==8
    (a.out/'region_truth8.qid').write_text('8\n'+''.join(str(q)+'\n' for q in selected))
    outids=oi[[info[q]['original_index'] for q in selected]].astype('<i4').tobytes()
    outs=os[[info[q]['original_index'] for q in selected]].astype('<f8').tobytes()
    (a.out/'evidence/oracle8.bin').write_bytes(struct.pack('<4i',N,D,8,K)+outids+outs)
    selected_trace=[dict(query_id=q,levels=rows[info[q]['original_index']*5:info[q]['original_index']*5+5]) for q in selected]
    (a.out/'evidence/G0_trace8.json.gz').write_bytes(gzip.compress(json.dumps(selected_trace,separators=(',',':')).encode(),mtime=0))
    rng=np.random.default_rng(202610110801);pairs=sorted(map(int,rng.choice(8*len(leaf),128,replace=False)))
    samples=[]
    for pair in pairs:
        qi,li=divmod(pair,len(leaf));nid=leaf[li];node=nodes[nid]
        samples.append(dict(query_index=qi,query_id=selected[qi],region_id=nid,object_ids=list(ids[node[3]:node[3]+node[2]])))
    save(a.out/'evidence/SAMPLE_MANIFEST.json',dict(seed=202610110801,sample_count=128,selection='uniform distinct query-terminal-region pairs, frozen before truth scan',samples=samples))
    save(a.out/'evidence/TREE_IDENTITY.json',tree_audit(a.index))
    save(a.out/'evidence/QUERY_MANIFEST.json',dict(base_commit='b800019240a42fe5409e2643816368730a1161f3',
        data_sha256=m['data_sha256'],tree_sha256=m['tree_sha256'],queries=selected,
        selection_rule='low ranks 0/1, middle ranks 15/16, high ranks 30/31 by (leaf_calls,qid); largest remaining Ufinal/Ustar ranks 0/1, ties by qid',
        selection=selection,query_sha256=sha(a.out/'region_truth8.qid'),prior_G0_trace_sha256=sha(a.trace),
        prior_oracle_sha256=sha(BASE/'evidence/e1_v7/oracle_result.bin'),oracle8_sha256=sha(a.out/'evidence/oracle8.bin'),
        stratified_diagnostic_not_population_estimate=True))
    print(json.dumps(selection,indent=2))

if __name__=='__main__':main()
