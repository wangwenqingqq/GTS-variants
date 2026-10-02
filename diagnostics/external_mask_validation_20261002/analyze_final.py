#!/usr/bin/env python3
"""Summarize paired six-round Host-ready results without mixing old query sets."""
import csv
import itertools
import json
from pathlib import Path
import statistics

ROOT=Path(__file__).resolve().parent
source=ROOT/'latency_final.csv'
rows=list(csv.DictReader(source.open()))
assert len(rows)==288,len(rows)
by_key={}
for row in rows:
    key=(row['dataset'],row['radius'],int(row['B']),row['mode'])
    round_no=int(row['round'])
    by_key.setdefault(key,{})[round_no]=row
assert len(by_key)==48
assert all(set(v)==set(range(1,7)) for v in by_key.values())


def median_ci(values):
    samples=sorted(statistics.median(sample) for sample in
                   itertools.product(values,repeat=len(values)))
    return samples[int(0.025*(len(samples)-1))],samples[int(0.975*(len(samples)-1))]


summary=[]
for (dataset,radius,b,mode),rounds in sorted(by_key.items()):
    values=[float(rounds[i]['host_total_ms']) for i in range(1,7)]
    batch_p50=[float(rounds[i]['batch_p50_ms']) for i in range(1,7)]
    batch_p95=[float(rounds[i]['batch_p95_ms']) for i in range(1,7)]
    counts=[int(rounds[i]['hits']) for i in range(1,7)]
    assert len(set(counts))==1
    summary.append({'dataset':dataset,'radius':radius,'B':b,'mode':mode,
        'host_median_ms':statistics.median(values),'host_min_ms':min(values),
        'host_max_ms':max(values),'six_round_ms':values,
        'batch_p50_median_ms':statistics.median(batch_p50),
        'batch_p95_median_ms':statistics.median(batch_p95),
        'amortized_ms_per_query':statistics.median(values)/1024,
        'qps':1024000/statistics.median(values),'hits':counts[0],
        'd2h_bytes':int(rounds[1]['d2h_bytes']),
        'count_mismatch_queries':int(rounds[1]['count_mismatch_queries']),
        'hash_mismatch_queries':int(rounds[1]['hash_mismatch_queries'])})

comparisons=(('SCAN_E','C_MASK_E'),('SCAN_L','C_MASK_E'),
             ('LIB64_U','C_MASK_E'),('LIB64_X','C_MASK_E'),
             ('C_MASK_E','LIB32_U'))
paired=[]
for dataset,radius,b in sorted({(x[0],x[1],x[2]) for x in by_key}):
    for reference,candidate in comparisons:
        a=by_key[dataset,radius,b,reference]
        c=by_key[dataset,radius,b,candidate]
        ratios=[float(a[i]['host_total_ms'])/float(c[i]['host_total_ms'])
                for i in range(1,7)]
        lo,hi=median_ci(ratios)
        paired.append({'dataset':dataset,'radius':radius,'B':b,
            'reference':reference,'candidate':candidate,
            'median_ratio':statistics.median(ratios),'min_ratio':min(ratios),
            'max_ratio':max(ratios),'six_round_ratios':ratios,
            'wins':sum(x>1 for x in ratios),
            'paired_round_bootstrap_95_low':lo,'paired_round_bootstrap_95_high':hi})

(ROOT/'summary_final.json').write_text(json.dumps({
    'source':'latency_final.csv','rounds':6,'per_process_queries':1024,
    'bootstrap':'exact enumeration of 6^6 resamples of paired round ratios; fixed queries',
    'conditions':summary,'comparisons':paired},indent=2)+'\n')
with (ROOT/'paired_final.csv').open('w') as f:
    writer=csv.DictWriter(f,fieldnames=[k for k in paired[0] if k!='six_round_ratios']+
                          [f'ratio_r{i}' for i in range(1,7)])
    writer.writeheader()
    for row in paired:
        d={k:v for k,v in row.items() if k!='six_round_ratios'}
        d.update({f'ratio_r{i}':v for i,v in enumerate(row['six_round_ratios'],1)})
        writer.writerow(d)
print('PASS',len(summary),'conditions',len(paired),'paired comparisons')
