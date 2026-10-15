"""Small CPU-only schedule/replay regression; never starts CUDA."""
if not __debug__:
    raise SystemExit('Optimized Python disables mandatory checks; run without -O/PYTHONOPTIMIZE.')
import argparse
import ctypes
import subprocess
from pathlib import Path
import numpy as np
from common import HERE, expected_jobs, batches, ends, requests
from analyze import check


def main():
    p = argparse.ArgumentParser(); p.add_argument('--out', type=Path, required=True); a = p.parse_args(); a.out.mkdir(parents=True, exist_ok=False)
    subprocess.run(['g++', '-std=c++17', '-O2', '-shared', '-fPIC', str(HERE/'oracle.cpp'), '-o', str(a.out/'replay.so')], check=True)
    f = ctypes.CDLL(str(a.out/'replay.so')).check_mutations
    f.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
    f.restype = ctypes.c_int
    for workload in range(3):
        n = 4096; total = ends(workload, n)[-1]; victims = np.random.default_rng(2026101501).permutation(n)[:total].astype('<i4')
        forward = list(range(n)); reverse = list(range(n))+[-1]*total; records = []; next_id = n
        for batch in batches(workload, n):
            for id in victims[batch['begin']:batch['begin']+batch['count']]:
                id = int(id); size = len(forward); row = reverse[id]; last = size-1; moved = forward[-1] if row != last else -1
                records.append([0, id, size, row, last, moved, next_id, size-1])
                if row != last: forward[row] = moved; reverse[moved] = row
                forward.pop(); reverse[id] = -1
            for _ in range(batch['count']):
                size = len(forward); records.append([1, next_id, size, size, -1, -1, next_id+1, size+1])
                forward.append(next_id); reverse[next_id] = size; next_id += 1
        record = np.array(records, '<i4'); physical = np.array(forward, '<i4'); positions = np.array(reverse, '<i4'); swaps = np.zeros(1, '<u8')
        call = lambda: f(n, victims.ctypes.data, total, workload, record.ctypes.data, total*2, physical.ctypes.data, positions.ctypes.data, swaps.ctypes.data)
        assert call() == 0; record[0, 1] = -1; assert call() != 0
        assert len(requests(workload, n)) == 168
    assert [len(expected_jobs(s)) for s in ('qualification', 'primary', 'query_ncu', 'maintenance_ncu')] == [32, 72, 12, 1]
    check(); print('PASS:all workloads,actual-owner replay,negative witness test;0 CUDA starts')


if __name__ == '__main__': main()
