#!/usr/bin/env python3
"""Correlate diagnostic GPU launches to Host NVTX ranges, never sum overlapping scopes."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sqlite3


def analyze(path):
    db = sqlite3.connect(path); db.row_factory = sqlite3.Row
    strings = dict(db.execute('SELECT id,value FROM StringIds'))
    ranges = [dict(r) for r in db.execute('SELECT * FROM NVTX_EVENTS')]
    for r in ranges: r['label'] = r['text'] or strings.get(r['textId'], '')
    ranges = [r for r in ranges if r['end'] is not None and (r['label'].startswith('rb.') or r['label'].startswith('rebuild.'))]
    outer = [r for r in ranges if r['label'] == 'rb.event48']; assert len(outer) == 1
    low, high = outer[0]['start'], outer[0]['end']
    runtimes = [dict(r) for r in db.execute('SELECT * FROM CUPTI_ACTIVITY_KIND_RUNTIME') if low <= r['start'] <= high]
    runtime_by_id = {r['correlationId']: r for r in runtimes}
    kernels = [dict(r) for r in db.execute('SELECT * FROM CUPTI_ACTIVITY_KIND_KERNEL') if low <= r['start'] <= high]
    rows = []
    for r in sorted(ranges, key=lambda r:r['start']):
        if not low <= r['start'] <= r['end'] <= high: continue
        launched = [k for k in kernels if k['correlationId'] in runtime_by_id and
            r['start'] <= runtime_by_id[k['correlationId']]['start'] <= r['end'] and
            runtime_by_id[k['correlationId']]['globalTid'] == r['globalTid']]
        calls = [x for x in runtimes if r['start'] <= x['start'] <= r['end'] and x['globalTid'] == r['globalTid']]
        rows.append(dict(stage=r['label'],inclusive_host_ms=(r['end']-r['start'])/1e6,
            attributed_GPU_kernel_sum_ms=sum(k['end']-k['start'] for k in launched)/1e6, kernel_launches=len(launched),
            attributed_runtime_calls=Counter(strings[x['nameId']] for x in calls),
            kernels=[dict(name=strings[k['shortName']],ms=(k['end']-k['start'])/1e6,
                grid=[k['gridX'],k['gridY'],k['gridZ']],block=[k['blockX'],k['blockY'],k['blockZ']],
                registers_per_thread=k['registersPerThread'],static_shared_bytes=k['staticSharedMemory'],local_bytes_per_thread=k['localMemoryPerThread']) for k in launched]))
    api = {}
    for x in runtimes:
        d=api.setdefault(strings[x['nameId']],dict(calls=0,inclusive_host_ms=0.));d['calls']+=1;d['inclusive_host_ms']+=(x['end']-x['start'])/1e6
    leaf = list(db.execute('SELECT k.module,count(*) AS n FROM SAMPLING_CALLCHAINS k JOIN COMPOSITE_EVENTS c ON k.id=c.id WHERE stackDepth=0 AND c.start BETWEEN ? AND ? GROUP BY k.module',(low,high)))
    leaf_modules = Counter()
    for module,n in leaf: leaf_modules[Path(strings[module]).name]+=n
    copies = [dict(r) for r in db.execute('SELECT * FROM CUPTI_ACTIVITY_KIND_MEMCPY') if low <= r['start'] <= high]
    copy_summary = {}
    for x in copies:
        key=f"copyKind={x['copyKind']};migrationCause={x['migrationCause']}"
        d=copy_summary.setdefault(key,dict(events=0,bytes=0,summed_event_ms=0.));d['events']+=1;d['bytes']+=x['bytes'];d['summed_event_ms']+=(x['end']-x['start'])/1e6
    gpu_faults = db.execute('SELECT count(*),coalesce(sum(numberOfPageFaults),0),coalesce(sum(end-start),0)/1e6 FROM CUDA_UM_GPU_PAGE_FAULT_EVENTS WHERE start BETWEEN ? AND ?',(low,high)).fetchone()
    cpu_faults = db.execute('SELECT count(*) FROM CUDA_UM_CPU_PAGE_FAULT_EVENTS WHERE start BETWEEN ? AND ?',(low,high)).fetchone()[0]
    assert len([r for r in rows if r['stage'].startswith('rb.pivot[')])==5
    assert len(kernels)==sum(len(r['kernels']) for r in rows if r['stage']=='rb.event48'), 'missing launch correlation'
    return dict(sqlite_sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest(),captured_event=48,captured_host_ms=(high-low)/1e6,
        stages=rows,runtime=api,leaf_CPU_module_samples=dict(leaf_modules),CPU_sample_total=sum(leaf_modules.values()),
        copy_summary=copy_summary,CPU_UM_fault_events=cpu_faults,GPU_UM_fault_events=gpu_faults[0],GPU_UM_fault_count=gpu_faults[1],GPU_UM_fault_summed_event_ms=gpu_faults[2],
        interpretation='Host NVTX inclusive boundaries and correlated GPU-duration sums overlap. UM fault/event durations also overlap; do not add them to kernel or Host time. CPU leaf-module samples are not effective CPU numerical-work counts. Diagnostic-only, not paired speed evidence.')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('sqlite',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    assert not a.output.exists(); a.output.write_text(json.dumps(analyze(a.sqlite),indent=2)+'\n')
