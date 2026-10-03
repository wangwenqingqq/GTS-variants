#!/usr/bin/env python3
"""Query-range attribution only; API durations overlap GPU work, not CPU compute."""
import argparse
from collections import defaultdict
import csv
import hashlib
import json
from pathlib import Path
import sqlite3


def union_length(intervals):
    merged = []
    for lo, hi in sorted(intervals):
        if lo >= hi: continue
        if merged and lo <= merged[-1][1]: merged[-1] = (merged[-1][0], max(hi, merged[-1][1]))
        else: merged.append((lo, hi))
    return sum(hi-lo for lo, hi in merged)


def trace(path):
    with sqlite3.connect(path) as db:
        db.row_factory = sqlite3.Row
        tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        names = dict(db.execute('SELECT id,value FROM StringIds'))
        def rows(table): return list(db.execute('SELECT * FROM '+table)) if table in tables else []
        nvtx = [r for r in rows('NVTX_EVENTS') if (r['text'] or names.get(r['textId'])) == 'formal.query_pass']
        assert len(nvtx) == 1 and nvtx[0]['end'] is not None, 'Missing complete query NVTX range'
        lo, hi = nvtx[0]['start'], nvtx[0]['end']
        def clipped(events): return [(max(lo,r['start']),min(hi,r['end'])) for r in events if r['start'] < hi and r['end'] > lo]
        kernels = [r for r in rows('CUPTI_ACTIVITY_KIND_KERNEL') if lo <= r['start'] < hi]
        copies = [r for r in rows('CUPTI_ACTIVITY_KIND_MEMCPY') if lo <= r['start'] < hi]
        sets = [r for r in rows('CUPTI_ACTIVITY_KIND_MEMSET') if lo <= r['start'] < hi]
        apis = [r for r in rows('CUPTI_ACTIVITY_KIND_RUNTIME') if lo <= r['start'] < hi]
        assert kernels and apis and all(r['returnValue'] == 0 for r in apis)
        def grouped(events, key):
            result = defaultdict(lambda: {'calls': 0, 'inclusive_ms': 0.})
            for r in events:
                value = result[key(r)]; value['calls'] += 1
                value['inclusive_ms'] += (min(hi,r['end'])-max(lo,r['start']))/1e6
            return dict(sorted(result.items(),key=lambda p:-p[1]['inclusive_ms']))
        kernel_totals = grouped(kernels, lambda r:names[r['demangledName']])
        api_totals = grouped(apis, lambda r:names[r['nameId']])
        memory = grouped(copies, lambda r:str(r['copyKind']))
        labels = {str(r['id']):r['label'] for r in rows('ENUM_CUDA_MEMCPY_OPER')}
        for kind, value in memory.items():
            value['bytes'] = sum(r['bytes'] for r in copies if str(r['copyKind']) == kind)
            value['label'] = labels.get(kind,'unknown')
        span = (hi-lo)/1e6
        gpu_union = union_length(clipped(kernels+copies+sets))/1e6
        api_union = union_length(clipped(apis))/1e6
        return {'scope': 'Complete formal.query_pass NVTX interval; first32 final GIST queries, K8; diagnostic only',
                'range_ms': span, 'gpu_work_union_ms': gpu_union, 'gpu_work_coverage': gpu_union/span,
                'runtime_api_union_ms': api_union, 'runtime_api_coverage': api_union/span,
                'no_recorded_gpu_work_ms': span-gpu_union, 'kernel_calls': len(kernels),
                'kernels': kernel_totals, 'cuda_api': api_totals, 'copy_kind_activity': memory,
                'sqlite_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                'warning': 'Temporal GPU coverage is not SM utilization. Inclusive CUDA API duration overlaps GPU work and may contain CPU spinning, driver work or blocking; it is not measured CPU computation. No coalescing counters or causal optimization control collected.'}


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('root',type=Path)
    root = p.parse_args().root
    result = {}
    for method in ('gts','ivf'):
        for b in (1,32):
            label = f'profile_{method}_GIST_k8_b{b}_v2'
            receipt = json.loads((root/'runs'/label/'receipt.json').read_text())
            assert receipt['runtime_valid'] and receipt['stop_reason'] is None
            result[label] = trace(root/f'{label}.sqlite')
            for kind in ('kernels','cuda_api'):
                with (root/f'{label}_{kind}.csv').open('w') as f:
                    writer = csv.writer(f); writer.writerow(['name','calls','inclusive_ms'])
                    writer.writerows((name,v['calls'],v['inclusive_ms']) for name,v in result[label][kind].items())
    (root/'TRACE_SUMMARY.json').write_text(json.dumps(result,indent=2)+'\n')
    print('PASS query-scoped trace inventory; TRACE_SUMMARY.json written')


if __name__ == '__main__': main()
