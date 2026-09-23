#!/usr/bin/env python3
"""Curate admitted NCU results without host identities or profiler speedup guesses."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
from analyze import admitted

DETAILS = {'Grid Size','Block Size','# SMs','Registers Per Thread','Duration',
           'Compute (SM) Throughput','DRAM Throughput','Memory Throughput',
           'L1/TEX Cache Throughput','L2 Cache Throughput','Theoretical Occupancy',
           'Achieved Occupancy','Achieved Active Warps Per SM','No Eligible',
           'Eligible Warps Per Scheduler','Issued Warp Per Scheduler',
           'Avg. Active Threads Per Warp','Avg. Not Predicated Off Threads Per Warp'}
RAW = ['profiler__replayer_passes','profiler__replayer_passes_type_warmup',
       'gpu__time_duration.sum','sm__throughput.avg.pct_of_peak_sustained_elapsed',
       'sm__warps_active.avg.pct_of_peak_sustained_active',
       'smsp__thread_inst_executed_per_inst_executed.ratio',
       'smsp__average_warp_latency_per_inst_issued.ratio',
       'smsp__average_warps_issue_stalled_long_scoreboard_per_issue_active.ratio',
       'smsp__average_warps_issue_stalled_barrier_per_issue_active.ratio']


def summarize(root):
    result = {'experiment':'gts_20260923_ncu_privileged_original',
              'parent':'gts_20260923_original_flow_words',
              'state':'Four successful privileged selected-kernel profiles; no driver change or optimization.',
              'caveat':'First matching launch, kernel replay, clocks/cache uncontrolled; not clean latency or repeatability proof.',
              'runs':{}, 'raw_file_sha256':{}}
    for path in sorted((root/'runs').glob('ncu_sudo_*')):
        receipt = json.loads((path/'receipt.json').read_text())
        assert admitted(receipt), path.name
        with (path/'metrics.csv').open() as f: rows = list(csv.DictReader(f))
        kernels = {r['Kernel Name'] for r in rows if r['Metric Name']}
        assert len(kernels)==1
        details = {r['Metric Name']:{'value':r['Metric Value'],'unit':r['Metric Unit']}
                   for r in rows if r['Metric Name'] in DETAILS}
        assert set(details)==DETAILS
        with (path/'metrics_raw.csv').open() as f: raw = list(csv.reader(f))
        assert len(raw)==3, 'Expected header, units, exactly one kernel'
        units,values = (dict(zip(raw[0],row)) for row in raw[1:])
        metrics = {k:{'value':values[k],'unit':units[k]} for k in RAW}
        result['runs'][path.name] = {
            'kernel':next(iter(kernels)), 'kind':receipt['kind'],'long':receipt['long'],
            'binary_sha256':receipt['binary_sha256'],'input_sha256':receipt['input_sha256'],
            'runner_sha256':receipt['runner_sha256'],'validation':receipt['validation'],
            'exit_code':receipt['exit_code'],'stop_reason':receipt['stop_reason'],
            'post_gpu_clear':receipt['post_gpu_clear'],'detail_metrics':details,'raw_metrics':metrics}
    assert len(result['runs'])==4
    for path in sorted(root.rglob('*')):
        if path.is_file():result['raw_file_sha256'][str(path.relative_to(root))]=hashlib.sha256(path.read_bytes()).hexdigest()
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('raw_root',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    a.output.write_text(json.dumps(summarize(a.raw_root),indent=2)+'\n')
    print('Curated four admitted profiles; source, raw reports and machine records remain excluded')
