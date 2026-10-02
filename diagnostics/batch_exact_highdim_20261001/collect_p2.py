#!/usr/bin/env python3
"""Collect the matched GIST half/all P2 rounds."""
import csv
import json
from pathlib import Path
import random
import statistics

from collect import ROOT, OUT, read, percentile


RADII={'half':'0x3f34a3d8','all':'0x41cb7260'}
BATCHES=(1,32,128)
MODES=('GRID_L','TILE_L','GRID_E','TILE_E')


def main():
    columns=('dataset','phase','split','radius_bits','mode','B','Q_T','round',
             'batch_id','query_ids_hash','host_ready_ms','gpu_ready_ms',
             'result_count_total','d2h_bytes','correctness_hash','valid','invalid_reason')
    records=[]
    totals={}
    for kind,bits in RADII.items():
        for round_no in range(1,7):
            for batch in BATCHES:
                modes=('GRID_L','GRID_E') if batch==1 else MODES
                for mode in modes:
                    path=ROOT/f'formal_gist_{kind}_r{round_no}_b{batch}_{mode}'
                    receipt=json.loads((path/'receipt.json').read_text())
                    assert receipt['runtime_valid'] and receipt['mode']==mode
                    timing=read(path/'result.csv')
                    assert len(timing)==1024//batch
                    host=gpu=0.0
                    for row in timing:
                        t=float(row['host_ms']);g=float(row['gpu_ms'])
                        host+=t;gpu+=g
                        records.append(('GIST','P2','final1024',bits,mode,batch,2,round_no,
                                        int(row['batch_id']),row['query_ids_hash'],t,g,
                                        int(row['result_count_total']),int(row['d2h_bytes']),
                                        row['ordered_hash'],True,''))
                    totals[kind,batch,mode,round_no]=(host,gpu)
    with (OUT/'p2_latency.csv').open('w') as f:
        w=csv.writer(f);w.writerow(columns);w.writerows(records)
    rng=random.Random(20261001)
    pairs=[]
    for kind in RADII:
        for batch in BATCHES:
            for base,candidate in (('GRID_L','TILE_L'),('GRID_E','TILE_E'),
                                   ('GRID_L','GRID_E'),('TILE_L','TILE_E')):
                if (kind,batch,base,1) not in totals or (kind,batch,candidate,1) not in totals:
                    continue
                ratios=[totals[kind,batch,base,r][0]/totals[kind,batch,candidate,r][0]
                        for r in range(1,7)]
                boot=[statistics.median(ratios[rng.randrange(6)] for _ in range(6))
                      for _ in range(10000)]
                pairs.append({'radius':kind,'B':batch,'base':base,'candidate':candidate,
                              'round_ratios':ratios,'median_speedup':statistics.median(ratios),
                              'range':(min(ratios),max(ratios)),
                              'bootstrap_median_95':(percentile(boot,.025),percentile(boot,.975))})
    report={'rows':len(records),'processes':len(totals),'round_totals_ms':[
        {'radius':k,'B':b,'mode':m,'round':r,'host_ms':v[0],'gpu_ms':v[1],
         'amortized_ms_per_query':v[0]/1024,'qps':1024000/v[0]}
        for (k,b,m,r),v in sorted(totals.items())],
        'paired':pairs}
    (OUT/'p2_summary.json').write_text(json.dumps(report,indent=2)+'\n')
    print('COLLECTED',len(records),'batches',len(totals),'independent processes')


if __name__=='__main__':main()
