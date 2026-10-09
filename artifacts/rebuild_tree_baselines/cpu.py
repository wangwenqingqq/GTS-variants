#!/usr/bin/env python3
"""Native single-thread snapshot diagnostics; complete range is never finite top-K."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import resource
import sys
import time
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'unified_target_workflow'))
import validate


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(8 << 20), b''): h.update(block)
    return h.hexdigest()


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + '\n')


def rss():
    fields = dict(line.split(':', 1) for line in Path('/proc/self/status').read_text().splitlines() if ':' in line)
    return {k: int(fields[k].split()[0]) * 1024 for k in ('VmRSS', 'VmHWM')}


def execute(a):
    contract = json.loads((HERE / 'CONTRACT.json').read_text())
    conf = contract['baseline_diagnostic']; spec = json.loads((a.snapshot / 'SNAPSHOT.json').read_text())
    assert a.method in ('CPU_KD', 'CPU_BALL', 'CPU_FLAT')
    assert spec['N'] == 1000000 and spec['D'] == 960 and len(spec['queries']) == 32
    assert sha(a.data) == spec['data_sha256']
    assert not list(a.output.parent.glob(a.output.name + '.*')), 'never replace a diagnostic'
    resource.setrlimit(resource.RLIMIT_AS, (conf['address_space_limit_bytes'], conf['address_space_limit_bytes']))
    data = validate.load(a.data); assert np.isfinite(data).all()
    radius = np.float32(contract['scope']['radius']); qids = [q['physical_qid'] for q in spec['queries']]
    version = {}; native_ms = 0.; before = rss(); start = time.perf_counter()
    if a.method == 'CPU_FLAT':
        import faiss
        faiss.omp_set_num_threads(1)
        version = dict(faiss=faiss.__version__, compile_options=faiss.get_compile_options())
        representation = data; preparation_ms = (time.perf_counter()-start)*1000
        start = time.perf_counter(); index = faiss.IndexFlatL2(data.shape[1]); index.add(representation)
        index_bytes = len(data)*data.shape[1]*4; dtype = 'float32'
        def query(task, qid):
            nonlocal native_ms
            q = np.array(data[qid:qid+1], dtype=np.float32, order='C', copy=True)
            tick = time.perf_counter()
            if task == 'knn': squared, ids = index.search(q, 8); ids, squared = ids[0], squared[0]
            else:
                limits, squared, ids = index.range_search(q, float(np.float64(radius)**2))
                assert limits.tolist() == [0, len(ids)]
            native_ms += (time.perf_counter()-tick)*1000
            return ids.astype(np.int32), np.sqrt(np.maximum(squared, np.float32(0))), squared.astype(np.float64)
        raw_kind = 'native squared L2'
    else:
        import sklearn
        from sklearn.neighbors import KDTree, BallTree
        from threadpoolctl import threadpool_limits, threadpool_info
        limit = threadpool_limits(limits=1)
        version = dict(sklearn=sklearn.__version__, pools=threadpool_info())
        representation = np.array(data, dtype=np.float64, order='C', copy=True)
        preparation_ms = (time.perf_counter()-start)*1000
        start = time.perf_counter()
        index = (KDTree if a.method == 'CPU_KD' else BallTree)(representation, leaf_size=conf['leaf_size'], metric='euclidean')
        index_bytes = sum(x.nbytes for x in index.get_arrays()) - representation.nbytes; dtype = 'float64'
        def query(task, qid):
            nonlocal native_ms
            q = np.array(data[qid:qid+1], dtype=np.float64, order='C', copy=True)
            tick = time.perf_counter()
            if task == 'knn': distances, ids = index.query(q, k=8, return_distance=True); ids, distances = ids[0], distances[0]
            else:
                ids, distances = index.query_radius(q, float(radius), return_distance=True, sort_results=False)
                ids, distances = ids[0], distances[0]
            native_ms += (time.perf_counter()-tick)*1000
            return ids.astype(np.int32), distances.astype(np.float32), distances.astype(np.float64)**2
        raw_kind = 'squared native float64 Euclidean field (not an exposed squared-score API)'
    build_ms = (time.perf_counter()-start)*1000; after_build = rss()
    module = sys.modules[index.__class__.__module__]
    version['implementation_file_sha256'] = sha(module.__file__)
    start = time.perf_counter()
    for task in ('knn', 'range'):
        for qid in qids[:8]: query(task, qid)
    warmup_ms = (time.perf_counter()-start)*1000
    payloads = []; rows = []; timing = {}; user_start = resource.getrusage(resource.RUSAGE_SELF)
    for task in ('knn', 'range'):
        native_before = native_ms
        start = time.perf_counter()
        for qi, qid in enumerate(qids):
            tick = time.perf_counter(); ids, fields, raw = query(task, qid)
            # Retain complete delivered arrays before stopping the operation timer.
            payloads.append((ids.copy(), fields.copy(), raw.copy()))
            rows.append(dict(task=task, query=qi, qid=qid, count=len(ids), offset=sum(r['count'] for r in rows), ack_ms=(time.perf_counter()-tick)*1000))
        timing[task + '_pass_ms'] = (time.perf_counter()-start)*1000
        timing[task + '_native_api_sum_ms'] = native_ms-native_before
    start = time.perf_counter(); del index; del representation
    release_ms = (time.perf_counter()-start)*1000; usage = resource.getrusage(resource.RUSAGE_SELF)
    for col, suffix, out_dtype in ((0, '.ids.i32', '<i4'), (1, '.dist.f32', '<f4'), (2, '.native_squared.f64', '<f8')):
        np.concatenate([p[col] for p in payloads]).astype(out_dtype).tofile(str(a.output)+suffix)
    with Path(str(a.output)+'.queries.csv').open('w') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    save(str(a.output)+'.native.json', dict(method=a.method, versions=version, numpy=np.__version__, dtype=dtype,
        leaf_size=conf['leaf_size'] if a.method!='CPU_FLAT' else None, requested_native_threads=1,
        affinity=list(sorted(os.sched_getaffinity(0))), representation_bytes=spec['N']*spec['D']*(4 if a.method=='CPU_FLAT' else 8), index_bytes=index_bytes,
        memory_before=before, memory_after_build=after_build, memory_final=rss(), preparation_ms=preparation_ms, build_ms=build_ms, warmup_ms=warmup_ms,
        timing=timing, final_release_ms=release_ms, trace_cpu_user_s=usage.ru_utime-user_start.ru_utime,
        trace_cpu_system_s=usage.ru_stime-user_start.ru_stime, raw_field_kind=raw_kind, radius=float(radius), source_sha256=sha(Path(__file__)), snapshot_sha256=sha(a.snapshot/'SNAPSHOT.json'),
        scope='single native 32-query B1 pass per task; complete Host-ready arrays retained; release separate, no updates; not significance or dynamic e2e'))
    print('PASS completed native diagnostic', a.method, timing, flush=True)


def quality(ids, fields, raw, sq, task, radius):
    valid = (ids >= 0) & (ids < len(sq)); unique = len(set(map(int, ids[valid]))) == len(ids)
    finite = bool(np.isfinite(fields).all() and np.isfinite(raw).all())
    returned = set(map(int, ids[valid])); missing = extra = []; recall = None
    if task == 'range':
        expected = set(map(int, np.flatnonzero(sq <= np.float64(np.float32(radius))**2)))
        missing = sorted(expected-returned); extra = sorted(returned-expected); member_pass = not missing and not extra
    else:
        boundary = np.sort(sq)[7]; closer = set(map(int, np.flatnonzero(sq < boundary))); ties = set(map(int, np.flatnonzero(sq == boundary)))
        recall = (len(closer&returned)+min(8-len(closer), len(ties&returned)))/8
        member_pass = recall == 1 and len(ids) == 8
    denom = np.maximum(1., sq[ids[valid]])
    delivered_error = float(np.max(np.abs(fields[valid].astype(np.float64)**2-sq[ids[valid]])/denom)) if valid.any() and finite else None
    raw_error = float(np.max(np.abs(raw[valid]-sq[ids[valid]])/denom)) if valid.any() and finite else None
    field_pass = finite and (delivered_error or 0.) <= 5e-5 and (raw_error or 0.) <= 5e-5
    return dict(passed=bool(valid.all() and unique and member_pass and field_pass), recall_tie_aware=recall, invalid_slots=int((~valid).sum()), unique=unique,
        missing_ids=missing, extra_ids=extra, all_fields_finite=finite, delivered_squared_error_scale1=delivered_error, native_squared_error_scale1=raw_error)


def check(a):
    sys.path.insert(0, str(HERE.parent / 'unified_target_workflow/phase_b'))
    import oracle
    from campaign import verify_cpu_library
    binding = verify_cpu_library(a.library); scores = oracle.install(a.library)
    data = validate.load(a.data); report = []; prefix = str(a.output)
    with open(prefix+'.queries.csv') as f: rows = list(csv.DictReader(f))
    assert len(rows) == 64
    offset = 0
    for r in rows:
        assert int(r['offset']) == offset and int(r['count']) >= 0
        offset += int(r['count'])
    total = sum(int(r['count']) for r in rows)
    arrays = []
    for suffix, dtype, size in (('.ids.i32','<i4',4),('.dist.f32','<f4',4),('.native_squared.f64','<f8',8)):
        assert Path(prefix+suffix).stat().st_size == total*size, 'malformed/incomplete full output'
        arrays.append(np.fromfile(prefix+suffix, dtype=dtype))
    radius = np.float32(json.loads((HERE/'CONTRACT.json').read_text())['scope']['radius'])
    # Each coordinate is scored once; it validates both task outputs.
    for qi in range(32):
        r = rows[qi]; assert int(r['query']) == qi and r['task'] == 'knn'
        assert rows[32+qi]['task'] == 'range' and rows[32+qi]['qid'] == r['qid']
        sq = scores(data, np.arange(len(data)), data[int(r['qid'])])
        for r in (rows[qi],rows[32+qi]):
            at, count = int(r['offset']), int(r['count']); cols = [x[at:at+count] for x in arrays]
            report.append(dict(task=r['task'], query=qi, **quality(*cols, sq, r['task'], radius)))
    save(prefix+'.quality.json', dict(passed=all(r['passed'] for r in report), per_query=report, CPU_binding=binding,
        output_hashes={p.name:sha(p) for p in a.output.parent.glob(a.output.name+'.*') if not p.name.endswith('.quality.json')}, scope='all-members independent exhaustive ordered-FP64 scores; native speed retained even on mismatch'))
    print('Quality', a.output.name, all(r['passed'] for r in report), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('action', choices=('execute','check'))
    p.add_argument('--method'); p.add_argument('--data',type=Path,required=True); p.add_argument('--snapshot',type=Path)
    p.add_argument('--output',type=Path,required=True); p.add_argument('--library',type=Path)
    a = p.parse_args(); assert __debug__
    repo = HERE.parents[1]; assert repo not in a.output.resolve().parents
    (execute if a.action=='execute' else check)(a)
