"""Descriptive costs from published process records; no new winner estimator."""
if not __debug__:
    raise SystemExit('Optimized Python disables mandatory checks; run without -O/PYTHONOPTIMIZE.')
import argparse
import csv
from pathlib import Path
import numpy as np
from common import HERE, MODES, load, save


def run(processes):
    rows = []
    for workload in range(3):
        for mode in MODES:
            runs = [r for r in processes if r['job']['workload'] == workload and r['job']['mode'] == mode]
            assert len(runs) == 6 and [r['job']['round'] for r in runs] == list(range(1, 7))
            values = []
            for r in runs:
                m = r['metadata']; ops = r['operation_summaries']; updates = m['point_updates']; ack = m['update_batches']
                assert ops['delete']['rows']+ops['insert']['rows'] == updates
                assert ops['delete']['ACKs']+ops['insert']['ACKs'] == ack
                for name in ('delete', 'insert', 'query'):
                    s = ops[name]; assert abs(s['ACK_total_ms']-r['operation_totals_ms'][name]) < 1e-7
                    q = list(s['ACK_quantiles_ms'].values()); assert 0 < q[0] <= q[1] <= q[2]
                values.append(dict(
                    service_ms=m['service_ms'], query_ms=m['query_ms'], update_ms=m['update_ms_including_statistics'],
                    delete_ACK_total_ms=ops['delete']['ACK_total_ms'], insert_ACK_total_ms=ops['insert']['ACK_total_ms'],
                    delete_batch_ACK_mean_us=ops['delete']['ACK_total_ms']*1000/ops['delete']['ACKs'],
                    insert_batch_ACK_mean_us=ops['insert']['ACK_total_ms']*1000/ops['insert']['ACKs'],
                    update_amortized_us_per_point=m['update_ms_including_statistics']*1000/updates,
                    point_updates_per_service_s=updates*1000/m['service_ms'],
                    batch_ACKs_plus_queries_per_service_s=(ack+160)*1000/m['service_ms'],
                    point_operations_plus_queries_per_service_s=(updates+160)*1000/m['service_ms'],
                    queries_per_service_s=160*1000/m['service_ms'],
                    update_fraction_of_service=m['update_ms_including_statistics']/m['service_ms'],
                    query_fraction_of_service=m['query_ms']/m['service_ms'],
                    insert_H2D_request_bytes=m['insert_H2D_request_bytes'], swap_D2D_request_bytes=m['swap_D2D_request_bytes'],
                    copy_request_bytes_per_point_update=(m['insert_H2D_request_bytes']+m['swap_D2D_request_bytes'])/updates,
                    statistics_submit_nested_ms=sum(s['statistics_submit_total_ms'] for s in ops.values()),
                    statistics_tail_nested_ms=sum(s['statistics_tail_inclusive_total_ms'] for s in ops.values()),
                    device_owned_peak_bytes=m['device_owned_peak_bytes'], device_observed_built_bytes=m['device_observed_built_bytes'],
                    process_RSS_peak_KiB_including_client=m['process_peak_RSS_KiB_including_client_inputs'],
                    CPU_events_user_plus_system_s=m['cpu_events_user_s']+m['cpu_events_system_s'],
                    query_p50_ms=ops['query']['ACK_quantiles_ms']['p50'],
                    query_p95_ms=ops['query']['ACK_quantiles_ms']['p95'], query_p99_ms=ops['query']['ACK_quantiles_ms']['p99']))
            rows.append(dict(workload='W'+str(workload), mode=mode, formal_queries=160,
                point_updates=updates, batch_ACKs=ack, updates_per_query=updates/160,
                metrics={key: dict(median=float(np.median([v[key] for v in values])), process_values=[v[key] for v in values]) for key in values[0]}))
    return dict(scope='Descriptive medians of six per-process values;not new promotion criteria',
        caveats=['Update ACK includes statistics;nested submit/tail must not be added',
            'Batch mean and amortized point cost are not individual point latency',
            'Copy request bytes exclude stats traffic and are not measured DRAM',
            'Finite repeated-query p50/p95/p99 within each process,not population or SLA',
            'Device-owned peak excludes external library/driver allocations;RSS includes client inputs',
            'All rates use segmented events+release,not throughput under concurrency'], cells=rows)


def main():
    p = argparse.ArgumentParser(); p.add_argument('--data', type=Path, default=HERE); p.add_argument('--out', type=Path, required=True)
    a = p.parse_args(); a.out.mkdir(parents=True, exist_ok=False)
    result = run(load(a.data/'evidence/PRIMARY_PROCESSES.json')); save(a.out/'SUMMARY.json', result)
    with (a.out/'SUMMARY.csv').open('x', newline='') as f:
        writer = csv.writer(f, lineterminator='\n'); writer.writerow(['workload', 'mode', 'metric', 'median', 'unit_in_metric_name'])
        for cell in result['cells']:
            for name, record in cell['metrics'].items(): writer.writerow([cell['workload'], cell['mode'], name, record['median'], 'see METRICS.md'])
    print('12 descriptive cost/memory/finite-tail cells;0 GPU starts')


if __name__ == '__main__': main()
