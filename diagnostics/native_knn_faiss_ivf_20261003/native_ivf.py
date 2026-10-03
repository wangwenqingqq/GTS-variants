#!/usr/bin/env python3
"""Independent FP64 top-K oracle and native GPU IVF Host-ready measurements."""
import argparse
import json
from pathlib import Path
import struct
import time

import cupy as cp
import numpy as np

HERE = Path(__file__).resolve().parent
KERNEL = r'''
extern "C" __global__ void distances(const float* x, double* ds, int n, int d, int q) {
    int id = blockIdx.x * blockDim.x + threadIdx.x;
    if (id >= n) return;
    double sum = 0;
    for (int j = 0; j < d; ++j) {
        double delta = __dsub_rn(double(x[(long long)j*n+id]), double(x[(long long)j*n+q]));
        sum = __dadd_rn(sum, __dmul_rn(delta, delta));
    }
    ds[id] = sum;
}
'''


def load_data(path):
    with Path(path).open('rb') as f:
        d, n, metric = struct.unpack('<iii', f.read(12))
    assert d in (96, 960) and 4097 <= n <= 1_000_000 and metric == 2
    assert Path(path).stat().st_size == 12 + n*d*4
    return np.memmap(path, dtype='<f4', mode='r', offset=12, shape=(n, d))


def read_qids(path):
    values = list(map(int, Path(path).read_text().split()))
    assert values[0] == len(values)-1 and len(set(values[1:])) == values[0]
    return np.array(values[1:], dtype=np.int32)


def make_oracle(data, qids, out):
    begin = time.perf_counter()
    soa = cp.asarray(data).T.copy()
    cp.cuda.Stream.null.synchronize()
    layout_s = time.perf_counter()-begin
    n, d = data.shape
    ds = cp.empty(n, dtype=cp.float64)
    kernel = cp.RawKernel(KERNEL, 'distances', options=('--std=c++17', '--fmad=false'))
    records = []
    begin = time.perf_counter()
    for q in qids:
        kernel(((n+255)//256,), (256,), (soa, ds, np.int32(n), np.int32(d), np.int32(q)))
        partial = cp.argpartition(ds, 31)[:32]
        ceiling = float(cp.max(ds[partial]).get())
        selected = cp.flatnonzero(ds <= ceiling)
        candidate_ids=cp.asnumpy(selected)
        candidate_ds=cp.asnumpy(ds[selected])
        order=np.lexsort((candidate_ids,candidate_ds))[:32]
        ids=candidate_ids[order].astype(np.int32)
        squared=candidate_ds[order]
        ties = {}
        for k in (8, 32):
            boundary = squared[k-1]
            ties[str(k)] = {'strictly_closer_ids': ids[squared < boundary].tolist(),
                            'boundary_ids': cp.asnumpy(cp.flatnonzero(ds == boundary)).tolist(),
                            'boundary_squared': float(boundary)}
        # CPU RN arithmetic independently checks all selected distances and some
        # widely spaced non-neighbors, not just the implementation's own output.
        checks = np.unique(np.r_[ids, np.arange(0, n, max(1,n//31))]).astype(np.int32)
        cpu = np.zeros(len(checks), dtype=np.float64)
        for j in range(d):
            delta = data[checks,j].astype(np.float64)-float(data[q,j])
            cpu += delta*delta
        gpu = cp.asnumpy(ds[cp.asarray(checks)])
        assert np.array_equal(cpu, gpu), 'CPU/GPU RN oracle disagreement'
        records.append({'qid': int(q), 'ids': ids.tolist(), 'squared': squared.tolist(), 'ties': ties})
    cp.cuda.Stream.null.synchronize()
    record = {'N': n, 'D': d, 'Q': len(qids), 'layout_s': layout_s,
              'oracle_s': time.perf_counter()-begin, 'records': records,
              'cpu_spotcheck': 'bitwise FP64 RN, selected neighbors plus 31 distributed rows/query'}
    Path(out).write_text(json.dumps(record, indent=2)+'\n')


def quality(ids, distances, reference, data, k, allow_missing=False):
    assert ids.shape == distances.shape == (reference['Q'], k)
    valid=(ids>=0)&(ids<len(data))
    assert np.all(valid|(ids==-1)) and np.isfinite(distances[valid]).all()
    if not allow_missing:assert valid.all(), 'Incomplete GTS neighbor output'
    missing_slots=int((~valid).sum())
    deterministic, tie_aware = [], []
    max_abs, max_rel, max_squared_rel = 0.0, 0.0, 0.0
    for row, record in enumerate(reference['records']):
        returned = set(map(int, ids[row][valid[row]]))
        assert len(returned) == int(valid[row].sum()), 'duplicate neighbor IDs'
        deterministic.append(len(returned.intersection(record['ids'][:k]))/k)
        tie = record['ties'][str(k)]
        closer, boundary = set(tie['strictly_closer_ids']), set(tie['boundary_ids'])
        hits = len(returned & closer) + min(k-len(closer), len(returned & boundary))
        tie_aware.append(hits/k)
    flat_valid=valid.reshape(-1)
    flat_ids=ids.reshape(-1)[flat_valid]
    query_ids=np.repeat(np.array([r['qid'] for r in reference['records']],dtype=np.int32),k)[flat_valid]
    squared=np.zeros(len(flat_ids),dtype=np.float64)
    for j in range(data.shape[1]):
        delta=data[flat_ids,j].astype(np.float64)-data[query_ids,j].astype(np.float64)
        squared+=delta*delta
    delivered=distances.reshape(-1)[flat_valid].astype(np.float64)
    truth=np.sqrt(squared)
    difference=np.abs(delivered-truth)
    max_abs=float(difference.max());max_rel=float((difference/np.maximum(truth,1.0)).max())
    squared_error=np.abs(delivered*delivered-squared)
    max_squared_rel=float((squared_error/np.maximum(squared,1.0)).max())
    return {'recall_deterministic': float(np.mean(deterministic)),
            'recall_tie_aware': float(np.mean(tie_aware)),
            'missing_neighbor_slots': missing_slots,
            'complete_query_fraction': float(np.mean(np.array(tie_aware)==1)),
            'per_query_recall': tie_aware,
            'distance_max_abs': max_abs, 'distance_max_relative_scale1': max_rel,
            'squared_distance_max_relative_scale1': max_squared_rel,
            'distance_tolerance_pass': max_squared_rel <= 5e-5}


def read_gts(path):
    with Path(path).open('rb') as f:
        n,d,q,k = struct.unpack('<iiii', f.read(16))
        ids = np.fromfile(f,dtype='<i4',count=q*k).reshape(q,k)
        distances = np.fromfile(f,dtype='<f4',count=q*k).reshape(q,k)
        assert f.read(1) == b''
    return n,d,k,ids,distances


def run_faiss(data, qids, reference, configs, repeats, warm, out):
    import faiss
    assert faiss.__version__ == '1.15.1' and 'GPU' in faiss.get_compile_options()
    faiss.omp_set_num_threads(16)
    rng = np.random.default_rng(2026100307)
    train_ids = rng.choice(len(data), min(200000,len(data)), replace=False)
    training = np.asarray(data[train_ids],dtype=np.float32,order='C')
    build, rows = [], []
    for nlist in dict.fromkeys(c['nlist'] for c in configs):
        resources = faiss.StandardGpuResources()
        config = faiss.GpuIndexIVFFlatConfig()
        config.use_cuvs = False
        config.device = 0
        index = faiss.GpuIndexIVFFlat(resources,data.shape[1],nlist,faiss.METRIC_L2,config)
        begin=time.perf_counter();index.train(training);train_s=time.perf_counter()-begin
        begin=time.perf_counter();index.add(data);add_s=time.perf_counter()-begin
        assert index.ntotal == len(data)
        build.append({'nlist': nlist, 'train_s': train_s, 'add_s': add_s})
        for c in (x for x in configs if x['nlist']==nlist):
            k,b=c['K'],c['B'];index.nprobe=c['nprobe']
            assert index.nprobe == c['nprobe'] <= min(nlist,2048)
            def batch(start,count):
                begin=time.perf_counter()
                query=np.asarray(data[qids[start:start+count]],dtype=np.float32,order='C')
                ds,ii=index.search(query,k)
                ii=ii.astype(np.int32)
                # Native squared distances -> common Euclidean FP32 output.
                dd=np.sqrt(np.maximum(ds,np.float32(0)))
                cp.cuda.Stream.null.synchronize()
                return (time.perf_counter()-begin)*1000,ii,dd
            for _ in range(warm):batch(0,min(b,len(qids)))
            for repeat in range(repeats):
                times=[];ids=np.empty((len(qids),k),dtype=np.int32);dist=np.empty_like(ids,dtype=np.float32)
                begin=time.perf_counter()
                cp.cuda.nvtx.RangePush("formal.query_pass")
                for start in range(0,len(qids),b):
                    count=min(b,len(qids)-start)
                    elapsed,ii,dd=batch(start,count);times.append(elapsed)
                    ids[start:start+count]=ii;dist[start:start+count]=dd
                cp.cuda.nvtx.RangePop()
                total=(time.perf_counter()-begin)*1000
                row={**c,'sample':repeat,'total_ms':total,'batch_p50_ms':float(np.quantile(times,.5)),
                     'batch_p95_ms':float(np.quantile(times,.95)),'quality':quality(ids,dist,reference,data,k,allow_missing=True)}
                rows.append(row)
                print(json.dumps({key:value for key,value in row.items() if key!='quality'}),flush=True)
        del index,resources
    Path(out).write_text(json.dumps({'build':build,'rows':rows,'faiss_version':faiss.__version__,
        'backend':'native GpuIndexIVFFlat; use_cuvs=False','train_seed':2026100307},indent=2)+'\n')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode',choices=('oracle','faiss','check-gts'))
    p.add_argument('--data',required=True);p.add_argument('--qids')
    p.add_argument('--reference');p.add_argument('--configs')
    p.add_argument('--result');p.add_argument('--out',required=True)
    p.add_argument('--repeats',type=int,default=1);p.add_argument('--warm',type=int,default=2)
    a=p.parse_args();data=load_data(a.data)
    if a.mode=='oracle':make_oracle(data,read_qids(a.qids),a.out)
    elif a.mode=='faiss':
        reference=json.loads(Path(a.reference).read_text());qids=read_qids(a.qids)
        assert qids.tolist()==[r['qid'] for r in reference['records']]
        run_faiss(data,qids,reference,json.loads(Path(a.configs).read_text()),a.repeats,a.warm,a.out)
    else:
        reference=json.loads(Path(a.reference).read_text())
        n,d,k,ids,dist=read_gts(a.result)
        assert (n,d)==data.shape
        Path(a.out).write_text(json.dumps(quality(ids,dist,reference,data,k),indent=2)+'\n')


if __name__=='__main__':main()
