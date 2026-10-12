#!/usr/bin/env python3
"""Curate empirical CDF ranks and region statistics without publishing vectors."""
import argparse
import csv
import gzip
import json
from pathlib import Path
import numpy as np
from shape_math import NAMES,HERE,sha,save
from evaluate_shapes import csv_write


def main():
    p=argparse.ArgumentParser();p.add_argument('--eval',type=Path,required=True);p.add_argument('--stats',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();raw=np.load(a.eval/'full_query_region_bounds.npz');cdf=[]
    for si,shape in enumerate(NAMES):
        gaps=(raw['LB_truth_4']-raw['LB_4'][si])[2:].reshape(-1);ordered=np.sort(gaps)
        ranks=np.unique(np.linspace(0,len(ordered)-1,4097,dtype=int))
        for rank in ranks:
            cdf.append(dict(shape=shape,level=4,scope='hard6',query_region_pairs=len(gaps),rank=int(rank+1),
                dead_gap=float(ordered[rank]),empirical_cdf=(int(rank)+1)/len(gaps)))
    csv_write(a.out/'dead_gap_cdf.csv',cdf)
    with gzip.open(a.stats,'rt',newline='') as f:rows=list(csv.DictReader(f))
    assert len(rows)==111000 and {l:sum(int(r['level'])==l for r in rows) for l in (3,4,5)}=={3:1000,4:10000,5:100000}
    stats=[]
    for l in (3,4,5):
        subset=[r for r in rows if int(r['level'])==l]
        for key in rows[0]:
            if key in ['level','region_index','objects']:continue
            v=np.array([float(r[key]) for r in subset])
            stats.append(dict(level=l,statistic=key,regions=len(v),minimum=float(v.min()),median=float(np.median(v)),
                p90=float(np.quantile(v,.9)),p99=float(np.quantile(v,.99)),maximum=float(v.max()),
                certified_optimization_ratio=False))
    csv_write(a.out/'region_shape_stats.csv',stats)
    summary=json.loads((a.out/'aggregate_summary.json').read_text());cost=[]
    for r in summary['rows']:
        cost.append(dict(shape=r['shape'],level=r['level'],regions=10**r['level'],aligned_bytes=r['aligned_bytes'],
            total_metadata_bytes=10**r['level']*r['aligned_bytes'],matched_budget=r['aligned_bytes']<=64,
            hard_alignment_per_byte=r['alignment_per_aligned_byte'],query_cost='offline diagnostic; no latency measured'))
    csv_write(a.out/'cost_accounting.csv',cost)
    save(a.out/'ANALYSIS_RECEIPT.json',dict(status='PASS',worker_sha256=sha(Path(__file__)),
        raw_bounds_sha256=sha(a.eval/'full_query_region_bounds.npz'),full_region_stats_sha256=sha(a.stats),
        full_region_stats_rows=111000,CDF_source='hard6 L4, all 60000 query-region pairs per shape',
        CDF_display='4097 frozen equally spaced order-statistic ranks per shape; no synthetic uncertainty',
        count_is_not_latency=True))


if __name__=='__main__':main()
