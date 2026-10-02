#!/usr/bin/env python3
"""Collect paired P4 rounds; raw receipts remain authoritative."""
import argparse
import csv
import json
from pathlib import Path
import random
import statistics


ROOT = Path(__file__).resolve().parent
MODES = ('SCAN_L', 'C_ID_L', 'C_MASK_L', 'C_TASK_L',
         'SCAN_E', 'C_ID_E', 'C_MASK_E', 'C_TASK_E')


def read(path):
    with path.open() as stream:
        return list(csv.DictReader(stream))


def read_gpu(path):
    with path.open() as stream:
        return [int(row[1].strip()) for row in csv.reader(stream)
                if len(row) > 1 and row[1].strip().isdigit()]


def percentile(values, p):
    ordered = sorted(values)
    return ordered[min(len(ordered)-1, int(p*(len(ordered)-1)))]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('radius', choices=('half', 'normal', 'all'))
    args = parser.parse_args()
    sizes = (8, 32) if args.radius == 'half' else (32,)
    details = []
    totals = {}
    for round_no in range(1, 7):
        for batch in sizes:
            for mode in MODES:
                folder = ROOT/'runs'/f'final_formal_gist_{args.radius}_r{round_no}_b{batch}_{mode}'
                receipt = json.loads((folder/'receipt.json').read_text())
                assert receipt['runtime_valid']
                rows = read(folder/'result.csv')
                assert len(rows) == 1024//batch
                host = [float(row['host_ms']) for row in rows]
                gpu = [float(row['gpu_ms']) for row in rows]
                samples = read_gpu(folder/'gpu.csv')
                totals[batch, mode, round_no] = {'host_ms': sum(host), 'gpu_ms': sum(gpu),
                    'batch_p50_ms': statistics.median(host), 'batch_p95_ms': percentile(host, .95),
                    'amortized_ms_per_query': sum(host)/1024, 'qps': 1024000/sum(host),
                    'max_gpu_memory_MiB': max(samples) if samples else None}
                for row in rows:
                    details.append(('GIST', args.radius, batch, 2, round_no, mode,
                        row['batch_id'], row['query_ids_hash'], row['host_ms'], row['gpu_ms'],
                        row['result_count_total'], row['d2h_bytes'], row['ordered_hash']))
    output = ROOT/f'latency_gist_{args.radius}.csv'
    with output.open('w', newline='') as stream:
        writer = csv.writer(stream, lineterminator='\n')
        writer.writerow(('dataset','radius','B','Q_T','round','mode','batch_id',
                         'query_ids_hash','host_ready_ms','gpu_ready_ms',
                         'result_count_total','d2h_bytes','correctness_hash'))
        writer.writerows(details)
    rng = random.Random(20261002)
    comparisons = []
    for batch in sizes:
        for suffix in ('L', 'E'):
            base = 'SCAN_'+suffix
            for path in ('C_ID', 'C_MASK', 'C_TASK'):
                mode = path+'_'+suffix
                ratios = [totals[batch,base,r]['host_ms']/totals[batch,mode,r]['host_ms']
                          for r in range(1,7)]
                bootstrap = [statistics.median(ratios[rng.randrange(6)] for _ in range(6))
                             for _ in range(10000)]
                comparisons.append({'B':batch,'base':base,'candidate':mode,
                    'round_ratios':ratios,'median':statistics.median(ratios),
                    'range':[min(ratios),max(ratios)],
                    'bootstrap_median_95':[percentile(bootstrap,.025),
                                           percentile(bootstrap,.975)]})
    summary = {'dataset':'GIST','radius':args.radius,'query_count':1024,
        'processes':len(totals),'batch_rows':len(details),
        'round_totals':[{'B':b,'mode':m,'round':r,**value}
                        for (b,m,r),value in sorted(totals.items())],
        'paired':comparisons}
    (ROOT/f'summary_gist_{args.radius}.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps({'processes':len(totals),'batch_rows':len(details),
                      'paired':comparisons},indent=2))


if __name__ == '__main__':
    main()
