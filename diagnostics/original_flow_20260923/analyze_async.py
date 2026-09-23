#!/usr/bin/env python3
"""Read-only small-kernel and host-serialization analysis of admitted NSYS traces."""
import argparse
from bisect import bisect_right
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import sqlite3
from analyze import admitted, clipped, length, quantiles, union


def overlap(a, b):
    a, b = union(a), union(b)
    i = j = total = 0
    while i < len(a) and j < len(b):
        total += max(0, min(a[i][1], b[j][1]) - max(a[i][0], b[j][0]))
        if a[i][1] <= b[j][1]: i += 1
        else: j += 1
    return total


def category(name):
    if name.startswith('cudaLaunch'): return 'launch'
    if name.startswith(('cudaMalloc', 'cudaFree')): return 'allocation_free'
    if name.startswith(('cudaDeviceSynchronize', 'cudaStreamSynchronize')): return 'synchronize'
    if name.startswith('cudaMemcpy'): return 'copy_api'
    return 'other'


def analyze(path, kind):
    with sqlite3.connect(f'file:{path}?mode=ro', uri=True) as db:
        db.row_factory = sqlite3.Row
        names = dict(db.execute('select id,value from StringIds'))
        kernels = list(db.execute('select * from CUPTI_ACTIVITY_KIND_KERNEL order by start'))
        api = list(db.execute('select * from CUPTI_ACTIVITY_KIND_RUNTIME order by start'))
        copies = list(db.execute('select * from CUPTI_ACTIVITY_KIND_MEMCPY order by start'))
        sets = list(db.execute('select * from CUPTI_ACTIVITY_KIND_MEMSET order by start'))
    first, last = ('initQnode', 'mergeTotalResult') if kind == 'update' else ('initPListKnn', 'mergeResKnn')
    lo = min(r['start'] for r in kernels if names[r['shortName']] == first)
    hi = max(r['end'] for r in kernels if names[r['shortName']] == last)
    kernels = [r for r in kernels if lo <= r['start'] < hi]
    launches = {r['correlationId']: r for r in api if names[r['nameId']].startswith('cudaLaunchKernel')}
    assert all(r['correlationId'] in launches for r in kernels)
    duration = [(r['end'] - r['start']) / 1000 for r in kernels]
    busy = union(clipped(kernels + copies + sets, lo, hi))
    gaps = [(b, c) for (_, b), (c, _) in zip(busy, busy[1:]) if c > b]
    by_api = defaultdict(list)
    cuda = [r for r in api if names[r['nameId']].startswith('cuda')]
    for r in cuda:
        if r['start'] < hi and r['end'] > lo:
            by_api[category(names[r['nameId']])].append((max(lo,r['start']), min(hi,r['end'])))
    gap_overlap = {k: overlap(gaps, v) / 1e6 for k, v in by_api.items()}
    cuda_overlap = overlap(gaps, [v for xs in by_api.values() for v in xs]) / 1e6
    # API categories are a partition only when their intervals do not overlap.
    assert abs(sum(gap_overlap.values()) - cuda_overlap) < 1e-6
    transitions = [launches[b['correlationId']]['start'] >= a['end'] for a,b in zip(kernels,kernels[1:])]
    durations = defaultdict(list)
    for r in kernels: durations[names[r['shortName']]].append((r['end']-r['start'])/1000)
    scoped_api = [r for r in cuda if lo <= r['start'] < hi]
    copy_followed_sync = sum(names[a['nameId']].startswith('cudaMemcpyAsync') and
                             names[b['nameId']].startswith('cudaStreamSynchronize')
                             for a,b in zip(scoped_api,scoped_api[1:]))
    result = {
        'sqlite_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'kernel_count':len(kernels), 'kernel_us':quantiles(duration),
        'kernel_duration_le_us':{str(t):sum(x<=t for x in duration) for t in [2,5,10]},
        'kernel_stream_ids':sorted({r['streamId'] for r in kernels}),
        'kernel_sum_minus_union_us':(sum(r['end']-r['start'] for r in kernels)-length(clipped(kernels,lo,hi)))/1000,
        'next_launch_api_starts_after_previous_kernel_end':sum(transitions),
        'adjacent_kernel_pairs':len(transitions),
        'query_span_ms':(hi-lo)/1e6, 'gpu_work_ms':length(busy)/1e6,
        'gpu_gap_ms':length(gaps)/1e6, 'gap_overlapping_cuda_api_ms':gap_overlap,
        'gap_outside_recorded_cuda_api_ms':length(gaps)/1e6-cuda_overlap,
        'async_copy_immediately_followed_by_stream_sync':copy_followed_sync,
        'd2h_bytes_histogram':dict(Counter(str(r['bytes']) for r in copies if lo<=r['start']<hi and r['copyKind']==2)),
        'by_kernel':{n:{'calls':len(v),'us':quantiles(v)} for n,v in durations.items()},
    }
    if kind == 'update':
        starts = [i for i,r in enumerate(kernels) if names[r['shortName']] == first]
        ends = starts[1:] + [len(kernels)]
        patterns = Counter(tuple(names[r['shortName']] for r in kernels[a:b]) for a,b in zip(starts,ends))
        assert len(patterns)==1, 'Report variable query patterns rather than assuming fixed positions'
        pattern,count = next(iter(patterns.items()))
        boundaries = [launches[kernels[i]['correlationId']]['start'] for i in starts]
        cycles = [Counter() for _ in range(len(boundaries)-1)]
        for r in cuda:
            i = bisect_right(boundaries,r['start'])-1
            if 0 <= i < len(cycles): cycles[i][names[r['nameId']]] += 1
        result['query_count'] = count
        result['complete_init_to_next_init_cycles'] = len(cycles)
        result['cycle_api_counts'] = {name:dict(Counter(str(c[name]) for c in cycles)) for name in sorted(set().union(*cycles))}
        result['kernel_positions'] = [{'position':j+1,'name':name,
                                      'us':quantiles([(kernels[i+j]['end']-kernels[i+j]['start'])/1000 for i in starts])}
                                     for j,name in enumerate(pattern)]
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('raw_root',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    out={'parent_experiment':'gts_20260923_original_flow_words',
         'scope':'Diagnostic reanalysis only; same first/last-query-kernel spans; no new GPU run or clean latency.',
         'caveats':['API/GPU temporal overlap is not CPU arithmetic or removable overhead.',
                    'Launch start is a host submission proxy, not a hardware queue-depth counter.',
                    'Init-to-next-init cycles contain previous cleanup and next setup; omit the last incomplete cycle.',
                    'One stream is not inherently wrong; device ordering and host synchronization are distinct.'],
         'traces':{}}
    for path in sorted((a.raw_root/'runs').glob('nsys*/trace.sqlite')):
        receipt=json.loads((path.parent/'receipt.json').read_text())
        if admitted(receipt):out['traces'][path.parent.name]=analyze(path,receipt['kind'])
    a.output.write_text(json.dumps(out,indent=2)+'\n')
    print('Analyzed',len(out['traces']),'accepted traces; raw files unchanged')


if __name__=='__main__':main()
