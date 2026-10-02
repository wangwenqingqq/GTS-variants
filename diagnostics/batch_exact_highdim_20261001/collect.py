#!/usr/bin/env python3
"""Collect the six frozen GIST P1 rounds without changing raw receipts."""
import csv
import json
from pathlib import Path
import random
import statistics


ROOT = Path('/home/data/wangxuran/tmp/gts_batch_exact_highdim_20261001/runs')
MODES = ('SEQ_L', 'GRID_L', 'TILE_L', 'SEQ_E', 'GRID_E', 'TILE_E')
BATCHES = (1, 8, 32, 128)
OUT = Path(__file__).resolve().parent


def read(path):
    with path.open() as f:
        return list(csv.DictReader(f))


def percentile(items, p):
    values = sorted(items)
    return values[min(len(values)-1, max(0, int(p*(len(values)-1))))]


def main():
    columns = ('dataset','phase','split','radius_bits','mode','B','Q_T','round',
               'batch_id','query_ids_hash','host_ready_ms','gpu_ready_ms',
               'result_count_total','d2h_bytes','correctness_hash','valid','invalid_reason')
    round_totals = {}
    rows = []
    memory_peaks = {}
    for round_no in range(1, 7):
        for batch in BATCHES:
            modes = ('SEQ_L', 'SEQ_E') if batch == 1 else MODES
            for mode in modes:
                path = ROOT/f'formal_gist_normal_r{round_no}_b{batch}_{mode}'
                receipt = json.loads((path/'receipt.json').read_text())
                assert receipt['runtime_valid'] and receipt['mode'] == mode
                timing = read(path/'result.csv')
                assert len(timing) == 1024//batch
                total_host = total_gpu = 0.0
                for item in timing:
                    host = float(item['host_ms'])
                    gpu = float(item['gpu_ms'])
                    total_host += host
                    total_gpu += gpu
                    rows.append(('GIST','P1','final1024','0x3fb4a3d8',mode,batch,2,
                                 round_no,int(item['batch_id']),item['query_ids_hash'],
                                 host,gpu,int(item['result_count_total']),
                                 int(item['d2h_bytes']),item['ordered_hash'],True,''))
                round_totals[batch,mode,round_no] = (total_host,total_gpu)
                with (path/'gpu.csv').open() as f:
                    samples = list(csv.reader(f))
                mem = [int(s[1].strip()) for s in samples
                       if len(s)>1 and s[1].strip().isdigit()]
                memory_peaks[batch,mode,round_no] = max(mem) if mem else None
    with (OUT/'latency.csv').open('w') as f:
        writer = csv.writer(f)
        writer.writerow(columns)
        writer.writerows(rows)
    comparisons = (('GRID_L','TILE_L'),('GRID_E','TILE_E'),
                   ('SEQ_L','GRID_L'),('SEQ_E','GRID_E'),
                   ('SEQ_L','TILE_L'),('SEQ_E','TILE_E'),
                   ('TILE_L','TILE_E'))
    paired = []
    rng = random.Random(20261001)
    for batch in BATCHES:
        for base, candidate in comparisons:
            if (batch,base,1) not in round_totals or (batch,candidate,1) not in round_totals:
                continue
            ratios = [round_totals[batch,base,r][0]/round_totals[batch,candidate,r][0]
                      for r in range(1,7)]
            medians = [statistics.median(ratios[rng.randrange(6)] for _ in range(6))
                       for _ in range(10000)]
            paired.append({'B':batch,'base':base,'candidate':candidate,
                           'round_ratios':ratios,'median_speedup':statistics.median(ratios),
                           'min_speedup':min(ratios),'max_speedup':max(ratios),
                           'bootstrap_median_95':(percentile(medians,.025),
                                                  percentile(medians,.975))})
    summary = {'rows':len(rows),'round_totals_ms':[
        {'B':b,'mode':m,'round':r,'host_ms':v[0],'gpu_ms':v[1],
         'amortized_ms_per_query':v[0]/1024,'qps':1024000/v[0],
         'max_gpu_memory_MiB':memory_peaks[b,m,r]}
        for (b,m,r),v in sorted(round_totals.items())],
        'paired':paired}
    (OUT/'p1_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print('COLLECTED',len(rows),'batches',len(round_totals),'independent processes')


if __name__ == '__main__':
    main()
