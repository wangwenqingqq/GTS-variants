#!/usr/bin/env python3
"""Four small, locked diagnostic profiles after the immutable primary campaign."""
import argparse
import collections
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys

import run_region as r


def analyze(path):
    with sqlite3.connect(path) as db:
        db.row_factory = sqlite3.Row
        names = dict(db.execute('select id,value from StringIds'))
        ranges = list(db.execute('select * from NVTX_EVENTS'))
        name = lambda row: row['text'] or names.get(row['textId'])
        full = [x for x in ranges if name(x) == 'native.trace' and x['end']]
        assert len(full) == 1
        start, end = full[0]['start'], full[0]['end']
        trees = [x for x in ranges if name(x) == 'query.tree' and x['end']]
        assert len(trees) == 19
        inside_tree = lambda x: any(t['start'] <= x['start'] and x['end'] <= t['end'] for t in trees)
        kernels = list(db.execute('select * from CUPTI_ACTIVITY_KIND_KERNEL where start>=? and end<=?', (start, end)))
        grouped = collections.Counter()
        duration = collections.Counter()
        resources = {}
        for x in kernels:
            signature = names[x['demangledName']]
            grid = tuple(x[k] for k in ('gridX', 'gridY', 'gridZ'))
            block = tuple(x[k] for k in ('blockX', 'blockY', 'blockZ'))
            key = (signature, grid, block, x['registersPerThread'],
                   x['staticSharedMemory'], x['dynamicSharedMemory'], x['localMemoryPerThread'])
            grouped[key] += 1
            duration[key] += (x['end'] - x['start']) / 1e6
            resources[key] = dict(signature=signature, grid=grid, block=block,
                                  registers_per_thread=key[3], static_shared_bytes=key[4],
                                  dynamic_shared_bytes=key[5], local_memory_per_thread=key[6])
        apis, tree_apis, copies = collections.Counter(), collections.Counter(), collections.Counter()
        for x in db.execute('select * from CUPTI_ACTIVITY_KIND_RUNTIME where start>=? and end<=?', (start, end)):
            apis[names[x['nameId']]] += 1
            if inside_tree(x):
                tree_apis[names[x['nameId']]] += 1
        for x in db.execute('select * from CUPTI_ACTIVITY_KIND_MEMCPY where start>=? and end<=?', (start, end)):
            copies[str(x['copyKind'])] += x['bytes']
    return dict(sqlite_sha256=r.sha(path), diagnostic_only=True,
                scope='57 events, 19 queries, 2 rebuilds; native.trace',
                kernel_launches=len(kernels), query_tree_launches=sum(map(inside_tree, kernels)),
                cuda_api_counts=dict(apis), query_tree_api_counts=dict(tree_apis),
                copy_bytes_by_kind=dict(copies),
                kernel_shapes=[dict(**resources[k], calls=v, diagnostic_sum_ms=duration[k])
                               for k, v in sorted(grouped.items())],
                observed_occupancy='NOT_MEASURED; grid and resources are not achieved occupancy')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ('dest', 'raw', 'helpers'):
        p.add_argument('--' + key, type=Path, required=True)
    p.add_argument('--gpu', required=True)
    a = p.parse_args()
    assert r.read(a.dest / 'COMPLETE.json')['state'] == 'completed'
    binary = a.dest / 'native_timed/region_exec'
    assert r.sha(binary) == r.read(a.dest / 'SOURCE.json')['binary_sha256']
    launcher = Path(shutil.which('nsys')).resolve()
    assert launcher.is_file(), 'absolute profiler path required by frozen guard'
    registration = a.dest / 'CLOSURE_PROFILE_REGISTERED.json'
    assert not registration.exists()
    r.save(registration, dict(binary_sha256=r.sha(binary), launcher_sha256=r.sha(launcher),
                            controller_sha256=r.sha(__file__),
                            scope='4 diagnostic profiles; no primary timing replacement',
                            retained_old_failure='profile_NATIVE: post-run relative launcher hash lookup failed'))
    sys.path.insert(0, str(a.helpers))
    from u_life_bridge import check_small
    case = a.dest / 'boundaries/0'
    profiles = a.dest / 'closure_profiles'
    profiles.mkdir(exist_ok=False)
    rows = []
    for mode in r.MODES:
        label = 'closure_profile_' + mode
        target = a.dest / 'native_timed' / label
        run_dir = a.dest / 'runs' / label
        cmd = [str(launcher), 'profile', '--trace=cuda,nvtx', '--sample=none', '--cpuctxsw=none',
               '--cuda-memory-usage=true', '--export=sqlite', '--force-overwrite=false',
               '--output=' + str(profiles / mode), str(binary), str(case / 'data.txt'),
               str(case / 'events.txt'), '2', '0', str(target)]
        subprocess.run([sys.executable, str(a.raw / 'run_locked.py'), '--gpu', a.gpu,
                        '--output', str(run_dir), '--timeout-seconds', '1200', '--', *cmd],
                       env={**os.environ, 'REGION_MODE': mode, 'U10_OBSERVE': '1', 'U10_TREE_AUDIT': '0'},
                       check=True, stdout=subprocess.DEVNULL)
        assert r.read(run_dir / 'receipt.json')['runtime_valid']
        result = analyze(profiles / (mode + '.sqlite'))
        result.update(mode=mode, correctness=check_small(a, case, target, run_dir, False),
                      receipt_sha256=r.sha(run_dir / 'receipt.json'),
                      report_sha256=r.sha(profiles / (mode + '.nsys-rep')))
        rows.append(result)
        r.save(a.dest / 'CLOSURE_PROFILE_ROWS.json', rows)
        print(mode, 'PROFILE PASS', result['query_tree_launches'], flush=True)


if __name__ == '__main__':
    main()
