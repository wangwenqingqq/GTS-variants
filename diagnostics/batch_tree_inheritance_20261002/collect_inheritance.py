#!/usr/bin/env python3
"""Collect the frozen Deep/Tloc paired rounds without changing raw receipts."""
import csv
import json
from pathlib import Path
import random
import statistics
import sys

from inheritance_pilot import ROOT,rows


def percentile(values,p):
    ordered=sorted(values)
    return ordered[min(len(ordered)-1,int(p*(len(ordered)-1)))]


def main(dataset):
    assert dataset in ('Deep','Tloc')
    path=json.loads((ROOT/f'pilot_{dataset.lower()}_summary.json').read_text())['selected_path']
    modes=('SCAN_L',path+'_L','SCAN_E',path+'_E')
    sizes=(32,) if dataset=='Deep' else (1,32)
    details=[];totals={}
    for round_no in range(1,7):
        for batch in sizes:
            for mode in modes:
                folder=ROOT/'runs'/f'final_formal_{dataset.lower()}_r{round_no}_b{batch}_{mode}'
                receipt=json.loads((folder/'receipt.json').read_text())
                assert receipt['runtime_valid']
                measured=rows(folder/'result.csv')
                assert len(measured)==1024//batch
                host=[float(r['host_ms']) for r in measured]
                gpu=[float(r['gpu_ms']) for r in measured]
                total=sum(host)
                totals[batch,mode,round_no]={'host_ms':total,'gpu_ms':sum(gpu),
                    'batch_p50_ms':statistics.median(host),'batch_p95_ms':percentile(host,.95),
                    'amortized_ms_per_query':total/1024,'qps':1024000/total}
                for r in measured:
                    details.append((dataset,batch,2,round_no,mode,r['batch_id'],
                        r['query_ids_hash'],r['host_ms'],r['gpu_ms'],
                        r['result_count_total'],r['d2h_bytes'],r['ordered_hash']))
    with (ROOT/f'latency_{dataset.lower()}.csv').open('w',newline='') as stream:
        writer=csv.writer(stream,lineterminator='\n')
        writer.writerow(('dataset','B','Q_T','round','mode','batch_id','query_ids_hash',
                         'host_ready_ms','gpu_ready_ms','result_count_total',
                         'd2h_bytes','correctness_hash'))
        writer.writerows(details)
    rng=random.Random(20261002)
    paired=[]
    for batch in sizes:
        for suffix in ('L','E'):
            base='SCAN_'+suffix;candidate=path+'_'+suffix
            ratios=[totals[batch,base,r]['host_ms']/totals[batch,candidate,r]['host_ms']
                    for r in range(1,7)]
            bootstrap=[statistics.median(ratios[rng.randrange(6)] for _ in range(6))
                       for _ in range(10000)]
            paired.append({'B':batch,'base':base,'candidate':candidate,
                'round_ratios':ratios,'median':statistics.median(ratios),
                'range':[min(ratios),max(ratios)],
                'bootstrap_median_95':[percentile(bootstrap,.025),
                                       percentile(bootstrap,.975)]})
    result={'dataset':dataset,'selected_path':path,'processes':len(totals),
            'batch_rows':len(details),'round_totals':[
                {'B':b,'mode':m,'round':r,**value}
                for (b,m,r),value in sorted(totals.items())],
            'paired':paired}
    (ROOT/f'summary_{dataset.lower()}.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'processes':len(totals),'paired':paired},indent=2))


if __name__=='__main__':main(sys.argv[1])
