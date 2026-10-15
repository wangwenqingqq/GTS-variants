"""Complete exact answers, independently replayed ownership, and mean-policy checks."""
if not __debug__:
    raise SystemExit('Optimized Python disables mandatory checks; run without -O/PYTHONOPTIMIZE.')
import csv
import ctypes
from pathlib import Path
import numpy as np
from common import MODES, sha, load, requests, batches, ends
from prepare import input_prefix


def table(path):
    with Path(path).open() as f: return list(csv.DictReader(f))


def array(path, dtype):
    a = np.fromfile(path, dtype); assert Path(path).stat().st_size == a.nbytes
    return a


def check(prefix, job, w, reg):
    mode = job['mode']; n = job['N']; workload = job['workload']; c = load(Path(reg['repo'])/'artifacts/dynamic_query_aware_exact_gpu_20261015/CONTRACT.json') if 'repo' in reg else None
    if c is None:
        from common import HERE
        c = load(HERE/'CONTRACT.json')
    points = ends(workload, n); k = points[-1]; ip = input_prefix(w, n, workload); stem = str(prefix)
    victims = array(str(ip)+'.victims.i32', '<i4'); assert len(victims) == k
    physical = array(stem+'.physical.i32', '<i4'); reverse = array(stem+'.reverse.i32', '<i4')
    mutations = array(stem+'.mutations.i32', '<i4'); assert len(mutations) == 2*k*8
    assert len(physical) == n and len(reverse) == n+k
    library = ctypes.CDLL(str(w/'build/replay.so')); fn = library.check_mutations
    fn.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
    fn.restype = ctypes.c_int; swaps = np.zeros(1, '<u8')
    assert fn(n, victims.ctypes.data, k, workload, mutations.ctypes.data, 2*k, physical.ctypes.data, reverse.ctypes.data, swaps.ctypes.data) == 0
    ids = array(stem+'.ids.i32', '<i4'); fields = array(stem+'.dist.f32', '<f4'); raw = array(stem+'.squared.f64', '<f8')
    authority = array(stem+'.authority.f64', '<f8'); assert len(ids) == len(fields) == len(raw)
    assert np.isfinite(fields).all() and np.isfinite(raw).all() and (fields >= 0).all() and (raw >= 0).all()
    qr = table(stem+'.queries.csv'); expected = requests(workload, n); assert len(qr) == len(expected) == 168
    qids = list(range(32)) if n == 4096 else c['qids']; cutoff = c['radius']**2
    rank = np.full(n, k, '<i4'); rank[victims] = np.arange(k)
    folder = w/'cache'/f'N{n}_W{workload}'; at = 0; checked = []; maxerror = 0.
    for row, want in zip(qr, expected):
        assert all(int(row[x]) == want[x] for x in ('phase', 'slot', 'mutation'))
        q = qids[want['slot']]; count = want['mutation']; z = int(row['count']); assert int(row['offset']) == at
        base = np.memmap(folder/f'{q}.base.f64' if n == 4096 else Path(reg['reference'])/f'{q}.f64', '<f8', mode='r', shape=(n,))
        new = np.memmap(folder/f'{q}.incoming.f64', '<f8', mode='r', shape=(k,))
        old_hits = np.flatnonzero(base <= cutoff); old_hits = old_hits[rank[old_hits] >= count]
        new_hits = np.flatnonzero(new[:count] <= cutoff); wanted = np.concatenate([old_hits, n+new_hits])
        sq = np.concatenate([base[old_hits], new[new_hits]])
        actual = ids[at:at+z]; permutation = np.argsort(actual)
        assert len(np.unique(actual)) == len(actual) and np.array_equal(actual[permutation], wanted), ('complete inclusive members', mode, want)
        scores = sq[np.searchsorted(wanted, actual)]
        assert np.array_equal(raw[at:at+z].view('<u8'), scores.astype('<f4').astype('<f8').view('<u8')), 'bitwise native rounded-square observer'
        err = float(np.max(np.abs(fields[at:at+z].astype(float)**2-scores)/np.maximum(1., scores), initial=0.))
        assert err <= 5e-5; maxerror = max(maxerror, err)
        if job['diagnostic'] == 2: assert np.array_equal(authority[at:at+z].view('<u8'), scores.view('<u8')), 'internal original-order FP64 bits'
        ack = float(row['ack_ms']); assert np.isfinite(ack) and ack > 0
        checked.append(dict(**want, qid=q, count=z, complete=True, ack_ms=ack, invocation=int(row['invocation'])))
        at += z
    assert at == len(ids) and len(authority) == (at if job['diagnostic'] == 2 else 0)
    operations = table(stem+'.ops.csv'); update_rows = [r for r in operations if int(r['kind']) < 2]
    qbatches = batches(workload, n); assert len(update_rows) == len(qbatches)*2
    for b, delete, insert in zip(qbatches, update_rows[::2], update_rows[1::2]):
        assert int(delete['kind']) == 0 and int(insert['kind']) == 1
        assert int(delete['rows']) == int(insert['rows']) == b['count']
        assert int(delete['mutation']) == b['begin'] and int(insert['mutation']) == b['begin']+b['count']
        assert int(delete['n_before']) == int(insert['n_after']) == n
        assert int(delete['n_after']) == int(insert['n_before']) == n-b['count']
    assert len(operations) == len(update_rows)+160
    formal = [x for x in checked if x['phase'] >= 0]
    oq = [r for r in operations if int(r['kind']) == 2]
    assert len(oq) == len(formal) == 160
    for r, q in zip(oq, formal):
        assert all(int(r[x]) == q[x] for x in ('phase', 'slot', 'mutation')) and float(r['ack_ms']) == q['ack_ms']
        assert int(r['n_before']) == int(r['n_after']) == n
    for r in operations:
        assert all(np.isfinite(float(r[x])) and float(r[x]) >= 0 for x in ('ack_ms', 'stats_submit_ms', 'stats_tail_inclusive_ms'))
        assert float(r['ack_ms']) > 0
    metadata = load(stem+'.meta.json'); assert metadata['mode'] == MODES.index(mode)
    assert metadata['N'] == n and metadata['D'] == 960 and metadata['B'] == 1 and metadata['diagnostic'] == job['diagnostic']
    assert metadata['formal_queries'] == 160 and metadata['warmup_queries'] == 8 and metadata['replacements'] == k
    assert metadata['point_updates'] == k*2 and metadata['update_batches'] == len(update_rows)
    assert metadata['insert_H2D_request_bytes'] == k*960*4 and metadata['swap_D2D_request_bytes'] == int(swaps[0])*960*4
    assert metadata['rebuilds'] == 0 and metadata['client_complete_items'] == at
    assert metadata['statistics_rows'] == (2*k if mode == 'S2_INC' else 0)
    assert metadata['statistics_calls'] == (len(update_rows) if mode == 'S2_INC' else 0)
    assert metadata['extra_statistics_device_bytes'] == (1979648 if mode == 'S2_INC' else 0)
    assert metadata['raw_device_bytes'] == n*960*4
    assert metadata['device_owned_peak_bytes'] == metadata['raw_device_bytes']+metadata['base_query_device_bytes']+metadata['extra_statistics_device_bytes']
    assert abs(metadata['service_ms']-metadata['events_ms']-metadata['release_ms']) < 1e-7
    sums = {name: sum(float(r['ack_ms']) for r in operations if int(r['kind']) == kind) for name, kind in (('delete', 0), ('insert', 1), ('query', 2))}
    assert abs(sums['query']-metadata['query_ms']) < 1e-7 and abs(sums['delete']+sums['insert']-metadata['update_ms_including_statistics']) < 1e-7
    assert abs(metadata['events_ms']-sum(sums.values())-metadata['other_ms']) < 1e-7 and metadata['other_ms'] >= -1e-7
    proof = load(stem+'.final.json'); assert proof['passed'] and proof['all_vector_bytes_compared'] == n*960*4 and proof['live'] == n
    stages = table(stem+'.stages.csv'); depth = 1 if mode == 'S0' else 4; assert len(stages) == 168*depth
    query_stages = []
    for i, q in enumerate(checked):
        rows = stages[i*depth:(i+1)*depth]; live = n
        for s, row in enumerate(rows):
            assert int(row['invocation']) == q['invocation'] and int(row['stage']) == s+1
            assert int(row['input']) == live and 0 <= int(row['output']) <= live; live = int(row['output'])
        assert live == q['count']; increments = [960] if mode == 'S0' else [128, 128, 256, 448]
        query_stages.append(dict(phase=q['phase'], slot=q['slot'], mutation=q['mutation'],
            inputs=[int(x['input']) for x in rows], survivors=[int(x['output']) for x in rows],
            stage_coordinate_visits=sum(int(row['input'])*d for row, d in zip(rows, increments)),
            qualification_FP64_replay_coordinates=sum(int(row['replay_coordinates']) for row in rows) if job['diagnostic'] == 2 else None))
    mean_check = None
    if mode.startswith('S2'):
        mu = array(stem+'.means.f32', '<f4').reshape(5, 960); mu0 = array(w/'inputs/initial_mean.f32', '<f4')
        if mode == 'S2_STALE': assert all(np.array_equal(x.view('<u4'), mu0.view('<u4')) for x in mu)
        else:
            want = array(str(ip)+'.expected_means.f32', '<f4').reshape(5, 960)
            difference = float(np.max(np.abs(mu.astype(float)-want.astype(float)))); assert difference <= 2e-7
            mean_check = dict(anchored_mean_max_abs_error=difference, absolute_gate=2e-7, heuristic_not_score_tolerance=True)
        ordering = table(stem+'.ordering.csv'); assert len(ordering) == 168 and [int(r['invocation']) for r in ordering] == list(range(168))
        assert all(float(r['priority_ms']) >= 0 and float(r['order_submit_ms']) >= 0 for r in ordering)
    return dict(passed=True, mode=mode, N=n, workload=workload, diagnostic=job['diagnostic'],
        complete_queries_including_warmup=168, formal_queries=160, false_negatives=0, false_positives=0,
        exact_native_squared_bits=True, internal_FP64_bit_checks=at if job['diagnostic'] == 2 else 0,
        internal_FP64_bit_mismatches=0 if job['diagnostic'] == 2 else None, max_native_distance_scaled_error=maxerror,
        actual_mutation_witnesses=2*k, independent_final_maps=True, final_device_vector_bytes_compared=n*960*4,
        all_target_query_records=checked, query_stage_records=query_stages, mean_check=mean_check,
        operation_totals_ms=sums, metadata=metadata,
        raw_outputs={p.name: dict(sha256=sha(p), bytes=p.stat().st_size) for p in Path(prefix).parent.glob(Path(prefix).name+'.*') if p.is_file()})
