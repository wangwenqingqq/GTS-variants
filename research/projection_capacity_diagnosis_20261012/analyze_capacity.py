#!/usr/bin/env python3
"""Exact integer gates and bounded projected-point capacity, never latency."""
import argparse
import json
from fractions import Fraction
from pathlib import Path
import numpy as np
from common import HERE,KS,SIZES,sha,save,csv_write,inputs,freeze_check,envelope,level_decision

def analyze(raw,spectrum,out):
    im=inputs();queries=im['queries'];u=raw['U_star_squared'];perquery=[];rows=[];loss=[];thresholds=[];crossings=[];variance={r['k']:r['ratio'] for r in spectrum['explained_variance']}
    for l,size in SIZES.items():
        truth=raw[f'truth_sq_{l}'];truthmask=truth>u[:,None];truthcounts=truthmask.sum(1)*size;d=raw[f'D_{l}'];low,high=envelope(d)
        safe=low>np.sqrt(u)[None,:,None];possible=(high>np.sqrt(u)[None,:,None]) & truthmask[None]
        assert not np.any(safe & ~truthmask[None]);safe_counts=safe.sum(2)*size;possible_counts=possible.sum(2)*size
        central=(d>np.sqrt(u)[None,:,None]) & truthmask[None];central_counts=central.sum(2)*size
        for ki,k in enumerate(KS):
            for qi,q in enumerate(queries):
                truepairs=int(truthmask[qi].sum());false_survivors=int(np.count_nonzero(truthmask[qi] & ~safe[ki,qi]))
                certain_survivors=int(np.count_nonzero(truthmask[qi] & ~(high[ki,qi]>np.sqrt(u[qi]))))
                perquery.append(dict(k=k,level=l,query_id=q,hard=qi>=2,truth_objects=int(truthcounts[qi]),safe_objects=int(safe_counts[ki,qi]),possible_objects=int(possible_counts[ki,qi]),central_proxy_objects=int(central_counts[ki,qi]),
                    safe_alignment=float(Fraction(int(safe_counts[ki,qi]),int(truthcounts[qi]))),possible_alignment=float(Fraction(int(possible_counts[ki,qi]),int(truthcounts[qi]))),
                    central_proxy_false_prune_pairs=int(np.count_nonzero((d[ki,qi]>np.sqrt(u[qi])) & ~truthmask[qi])),
                    central_proxy_false_survivor_pairs=int(np.count_nonzero(truthmask[qi] & ~(d[ki,qi]>np.sqrt(u[qi])))),
                    original_truth_prunable_pairs=truepairs,projection_false_survivor_pairs=false_survivors,
                    false_survivor_fraction_guaranteed_bound=false_survivors/truepairs,certain_projection_false_survivor_pairs=certain_survivors,
                    arithmetic_ambiguous_true_pairs=int(np.count_nonzero(possible[ki,qi] & ~safe[ki,qi])),full_query_region_pairs=10**l))
            row=dict(k=k,level=l,truth_objects=int(truthcounts.sum()),safe_objects=int(safe_counts[ki].sum()),possible_objects=int(possible_counts[ki].sum()),
                all_alignment=float(Fraction(int(safe_counts[ki].sum()),int(truthcounts.sum()))),all_possible_alignment=float(Fraction(int(possible_counts[ki].sum()),int(truthcounts.sum()))),
                hard_truth_objects=int(truthcounts[2:].sum()),hard_safe_objects=int(safe_counts[ki,2:].sum()),hard_possible_objects=int(possible_counts[ki,2:].sum()),
                hard_alignment=float(Fraction(int(safe_counts[ki,2:].sum()),int(truthcounts[2:].sum()))),hard_possible_alignment=float(Fraction(int(possible_counts[ki,2:].sum()),int(truthcounts[2:].sum()))),
                worst_hard_alignment=float(min(Fraction(int(n),int(t)) for n,t in zip(safe_counts[ki,2:],truthcounts[2:]))),
                canary_alignment=float(Fraction(int(safe_counts[ki,2]),int(truthcounts[2]))),canary_possible_alignment=float(Fraction(int(possible_counts[ki,2]),int(truthcounts[2]))),
                explained_variance_ratio=variance[k],hard_safe_counts=safe_counts[ki,2:].tolist(),hard_possible_counts=possible_counts[ki,2:].tolist(),hard_truth_counts=truthcounts[2:].tolist())
            rows.append(row)
            gap=np.sqrt(truth)-d[ki]
            for scope,values in [('all8',gap),('hard6',gap[2:])]:
                loss.append(dict(k=k,level=l,scope=scope,query_region_pairs=values.size,median=float(np.median(values)),p90=float(np.quantile(values,.9)),p99=float(np.quantile(values,.99)),
                    signed_sum=float(np.sum(values,dtype=np.float64)),negative_central_gaps=int(np.count_nonzero(values<0)),
                    sum_using_upper_distance_envelope=float(np.sum(np.nextafter(values-(high[ki]-d[ki])[(slice(None) if scope=='all8' else slice(2,None))],-np.inf))),
                    sum_using_lower_distance_envelope=float(np.sum(np.nextafter(values+(d[ki]-low[ki])[(slice(None) if scope=='all8' else slice(2,None))],np.inf)))))
        for qi,q in enumerate(queries):
            tr=dict(level=l,query_id=q,hard=qi>=2,threshold_scope='first tested k, not minimum over untested dimensions')
            for percent in [30,50,70,90]:
                for label,count in [('guaranteed',safe_counts),('possible',possible_counts)]:
                    tr[f'k_{percent}_{label}']=next((k for i,k in enumerate(KS) if Fraction(int(count[i,qi]),int(truthcounts[qi]))>=Fraction(percent,100)),None)
            thresholds.append(tr)
        for ki in range(1,len(KS)):
            a=rows[-8+ki-1];b=rows[-8+ki];delta=b['hard_alignment']-a['hard_alignment']
            crossings.append(dict(level=l,k_from=KS[ki-1],k_to=KS[ki],added_dimensions=KS[ki]-KS[ki-1],hard_alignment_gain=delta,gain_per_added_dimension=delta/(KS[ki]-KS[ki-1]),
                hard_new_safe_objects=b['hard_safe_objects']-a['hard_safe_objects'],all_new_safe_objects=b['safe_objects']-a['safe_objects']))
    decisions={str(l):level_decision([r for r in rows if r['level']==l]) for l in SIZES}
    hardthreshold=[]
    for l in SIZES:
        lr=[r for r in rows if r['level']==l];entry=dict(level=l)
        for percent in [50,70,90]:
            for label,key in [('guaranteed','hard_safe_objects'),('possible','hard_possible_objects')]:entry[f'K{percent}_hard_{label}']=next((r['k'] for r in lr if Fraction(r[key],r['hard_truth_objects'])>=Fraction(percent,100)),None)
        hardthreshold.append(entry)
    flat=[{k:v for k,v in r.items() if not isinstance(v,list)} for r in rows]
    for name,table in [('per_query_capacity.csv',perquery),('per_level_capacity.csv',flat),('per_query_dimension_thresholds.csv',thresholds),('hard_dimension_thresholds.csv',hardthreshold),('projection_loss_summary.csv',loss),('threshold_crossings.csv',crossings)]:csv_write(out/name,table)
    summary=dict(base_commit='5dea0d5bfb2f0e58e022b7733a54f9f1e07522e4',partition='PCA_BALANCED',dimensions=list(KS),levels=list(SIZES),
        primary_level=4,decision=decisions['4']['decision'],per_level_decisions=decisions,hard_dimension_thresholds=hardthreshold,rows=rows,
        decision_scope='protocol buckets on fixed projected point sets; not proof of compressibility, better alternative directions or intrinsic dimensionality',
        grid_thresholds_only=True,possible_alignment_counts_intersect_original_truth=True,uncertainty='directed arithmetic envelope only; no population CI or timing claim')
    save(out/'aggregate_summary.json',summary)
    return summary

def main():
    p=argparse.ArgumentParser();p.add_argument('--oracle',type=Path,required=True);p.add_argument('--build',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();freeze_check();a.out.mkdir(parents=True,exist_ok=False)
    summary=analyze(np.load(a.oracle/'capacity_raw.npz'),json.loads((a.build/'PCA_SPECTRUM.json').read_text()),a.out)
    save(a.out/'ANALYSIS_RECEIPT.json',dict(status='PASS',source_sha256=sha(Path(__file__)),raw_sha256=sha(a.oracle/'capacity_raw.npz'),query_level_dimension_cells=192,decision=summary['decision']))
    print(json.dumps(dict(decision=summary['decision'],per_level_decisions=summary['per_level_decisions'])))

if __name__=='__main__':main()
