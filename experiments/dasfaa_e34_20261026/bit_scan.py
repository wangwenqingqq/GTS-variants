"""Custom exhaustive 2048-bit CUDA popcount scan with CuPy top-k selection."""
import csv
import datetime
import hashlib
import json
import os
from pathlib import Path
import sys
import time

import numpy as np
from audit_bits import load

CUDA = r'''
extern "C" __global__ void bit_distance(int n, int b,
    const unsigned long long* x, const unsigned long long* q, double* out) {
    unsigned long long index = (unsigned long long)blockIdx.x * blockDim.x + threadIdx.x;
    if (index >= (unsigned long long)n * b) return;
    int qi = index / n, id = index % n;
    const unsigned long long* a = x + (unsigned long long)id * 32;
    const unsigned long long* z = q + (unsigned long long)qi * 32;
    int intersection = 0, combined = 0;
    for (int word = 0; word < 32; ++word) {
        intersection += __popcll(a[word] & z[word]);
        combined += __popcll(a[word] | z[word]);
    }
    out[index] = combined ? 1.0 - (double)intersection / (double)combined : 0.0;
}
'''


def main(base, query, n, q, reps, warm, out, k='8'):
    n, q, reps, warm, k = map(int, (n, q, reps, warm, k))
    if not (10 <= n <= np.iinfo(np.int32).max and q > 0 and reps >= 0 and warm >= 0 and k == 8):
        raise ValueError('invalid E3 packed-bit workload')
    out = Path(out)
    for suffix in ('.pid', '.csv', '.ids', '.dist', '.json'):
        if Path(str(out) + suffix).exists():
            raise FileExistsError('preserve existing output: ' + str(out) + suffix)
    with Path(str(out) + '.pid').open('x') as f:
        f.write(str(os.getpid()) + '\n')
    t = time.perf_counter()
    x, queries = load(base, n), load(query)
    nq = len(queries)
    data_loading_ms = (time.perf_counter() - t) * 1000
    import cupy as cp
    t = time.perf_counter()
    dx = cp.asarray(x)
    kernel = cp.RawKernel(CUDA, 'bit_distance', options=('--std=c++17',))
    kernel.compile()
    cp.cuda.runtime.deviceSynchronize()
    build_ms = (time.perf_counter() - t) * 1000

    def call(start, b):
        # Both complete host outputs are materialized before this call returns.
        host = np.array(queries[start:start + b], dtype='<u8', order='C', copy=True)
        got_ids, got_dist = [], []
        for s in range(0, b, 32):
            bb = min(32, b - s)
            dq = cp.asarray(host[s:s + bb])
            distances = cp.empty((bb, n), dtype=cp.float64)
            kernel(((bb * n + 127) // 128,), (128,),
                   (np.int32(n), np.int32(bb), dx, dq, distances))
            ii = cp.argpartition(distances, k - 1, axis=1)[:, :k]
            dd = cp.take_along_axis(distances, ii, axis=1)
            order = cp.argsort(dd, axis=1)
            got_ids.append(cp.asnumpy(cp.take_along_axis(ii, order, axis=1)).astype('<i4'))
            got_dist.append(cp.asnumpy(cp.take_along_axis(dd, order, axis=1)).astype('<f8'))
        return np.concatenate(got_ids), np.concatenate(got_dist)

    print(datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'custom bit-popcount scan', 'N=', n, 'queries=', nq, 'Q=', q,
          'k=', k, 'scope=host-ready IDs+FP64 distances', flush=True)
    warm_ms = 0.0
    with Path(str(out) + '.csv').open('x') as f:
        writer = csv.writer(f)
        writer.writerow(['iteration', 'start', 'batch', 'batch_ms'])
        for iteration in range(-1, reps):
            all_ids, all_dist = [], []
            for start in range(0, nq, q):
                b = min(q, nq - start)
                t = time.perf_counter()
                ids, dd = call(start, b)
                elapsed = (time.perf_counter() - t) * 1000
                writer.writerow([iteration, start, b, elapsed])
                f.flush()
                if iteration == -1:
                    all_ids.append(ids); all_dist.append(dd)
            if iteration == -1:
                with Path(str(out) + '.ids').open('xb') as target:
                    np.concatenate(all_ids).tofile(target)
                with Path(str(out) + '.dist').open('xb') as target:
                    np.concatenate(all_dist).tofile(target)
                t = time.perf_counter()
                for _ in range(warm):
                    call(0, min(q, nq))
                warm_ms = (time.perf_counter() - t) * 1000
    metadata = {
        'implementation': 'custom CUDA uint64 popcount scan + CuPy argpartition/argsort top-k',
        'metric': 'FP64 Tanimoto distance 1-intersection/union',
        'empty_union_distance': 0, 'packed_bits': 2048,
        'N': n, 'queries': nq, 'Q': q, 'k': k, 'reps': reps, 'warmup_batches': warm,
        'data_loading_ms': data_loading_ms, 'build_ms': build_ms, 'warmup_ms': warm_ms,
        'cupy': cp.__version__, 'internal_query_tile': 32,
        'kernel_sha256': hashlib.sha256(CUDA.encode()).hexdigest(),
        'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'timing_scope': 'host-query copy, H2D, exhaustive GPU bit scan+topk, complete IDs+FP64 distances D2H, host assembly',
        'logical_scan_bytes_per_full_batch': q * n * 256,
        'logical_scan_bytes_per_complete_query_pass': nq * n * 256,
        'logical_bytes_are_not_measured_DRAM_traffic': True,
        'index_queries': False,
    }
    with Path(str(out) + '.json').open('x') as f:
        json.dump(metadata, f, indent=2); f.write('\n')


if __name__ == '__main__':
    main(*sys.argv[1:])
