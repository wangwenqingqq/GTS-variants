#!/usr/bin/env python3
"""CPU-only attribution of existing reports; never launches CUDA/profilers."""
import argparse
import bisect
import collections
import csv
import hashlib
import json
import re
import sqlite3
import statistics
from pathlib import Path


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(8 << 20), b''):
            h.update(block)
    return h.hexdigest()


def load(path):
    return json.loads(Path(path).read_text())


def metric_csv(path):
    with Path(path).open() as f:
        rows = list(csv.DictReader(f))
    units = next(r for r in rows if not r['ID'])
    records = [r for r in rows if r['ID']]
    assert len(records) == 1, 'requires exactly one selected launch'
    return records[0], units


def identity_fields(identity):
    # Paths can change through registered relocation. Match bytes, not spelling.
    names = ('opt_knn_bench', 'gts_bench_p7', 'data.f32bin',
             'GIST_diagnostic32.qid', 'GIST_warm32.qid', 'GIST.index',
             'seeds_1000000.i32', 'knn_verify.cuh', 'knn_cutoff.cuh',
             'opt_knn_bench.cu', 'gts_bench_p7.cu', 'search_v2.cuh')
    return {Path(p).name: h for p, h in identity['files'].items()
            if Path(p).name in names}


def same_launch(work, traffic):
    return all(work[k] == traffic[k] for k in
               ('ID', 'Kernel Name', 'Grid Size', 'Block Size'))


def byte_value(metric):
    return float(metric['value']) * {'byte': 1, 'Kbyte': 1000,
                                    'Mbyte': 10**6, 'Gbyte': 10**9}[metric['unit']]


def union_ns(intervals):
    end = None
    total = 0
    for a, b in sorted(intervals):
        total += b - max(a, end if end is not None else a) if end is None or b > end else 0
        end = max(b, end if end is not None else b)
    return total


def profile_stages(db):
    c = sqlite3.connect('file:' + str(db) + '?mode=ro', uri=True)
    strings = dict(c.execute('SELECT id,value FROM StringIds'))
    ranges = [(a, b, text or strings.get(i)) for a, b, text, i in
              c.execute('SELECT start,end,text,textId FROM NVTX_EVENTS WHERE end IS NOT NULL')]
    ranges = sorted(v for v in ranges if v[2] in (
        'query.tree', 'query.buffer', 'query.prefix_merge', 'delete.prefix_lookup',
        'delete.buffer_merge', 'rebuild.compaction', 'rebuild.construct', 'rebuild.reset'))
    starts = [v[0] for v in ranges]
    result = {}
    per_range = collections.defaultdict(list)
    for a, b, name in ranges:
        s = result.setdefault(name, {'calls': 0, 'inclusive_host_ms': 0, 'api': {},
                                    'kernels': {}, 'copies_by_kind': {}, 'memset': {'calls': 0, 'bytes': 0},
                                    'selected_workspace_api_ms': 0, 'selected_workspace_api_calls': 0})
        s['calls'] += 1
        s['inclusive_host_ms'] += (b-a)/1e6
    device = collections.defaultdict(list)
    for a, b, nid in c.execute('SELECT start,end,nameId FROM CUPTI_ACTIVITY_KIND_RUNTIME ORDER BY start'):
        j = bisect.bisect_right(starts, a)-1
        if j < 0 or b > ranges[j][1]:
            continue
        name = ranges[j][2]
        per_range[j].append((strings[nid], a, b))
        item = result[name]['api'].setdefault(strings[nid], {'calls': 0, 'inclusive_ms': 0})
        item['calls'] += 1
        item['inclusive_ms'] += (b-a)/1e6
    # Source-verified allocation sequence: first 2 managed scalars, device
    # allocation ordinals 0..3 and 5..9, final 11 frees after merge's fence.
    # Abort rather than applying this positional mapping to an unknown trace.
    for j, calls in per_range.items():
        if ranges[j][2] != 'query.tree':
            continue
        managed = [v for v in calls if v[0].startswith('cudaMallocManaged')]
        alloc = [v for v in calls if v[0].startswith('cudaMalloc_')]
        frees = [v for v in calls if v[0].startswith('cudaFree_')]
        assert (len(managed), len(alloc), len(frees)) == (6, 15, 17)
        selected = managed[:2] + alloc[:4] + alloc[5:10] + frees[-11:]
        s = result['query.tree']
        s['selected_workspace_api_ms'] += sum((b-a)/1e6 for _, a, b in selected)
        s['selected_workspace_api_calls'] += len(selected)
    for table, columns, kind in (
        ('CUPTI_ACTIVITY_KIND_KERNEL', 'start,end,shortName', 'kernel'),
        ('CUPTI_ACTIVITY_KIND_MEMCPY', 'start,end,copyKind,bytes', 'copy'),
        ('CUPTI_ACTIVITY_KIND_MEMSET', 'start,end,bytes', 'memset')):
        for a, b, *extra in c.execute('SELECT '+columns+' FROM '+table):
            j = bisect.bisect_right(starts, a)-1
            if j < 0 or b > ranges[j][1]:
                continue
            name = ranges[j][2]
            device[name].append((a, b))
            if kind == 'kernel':
                entry = result[name]['kernels'].setdefault(strings[extra[0]], {'calls': 0, 'gpu_ms': 0})
            elif kind == 'copy':
                entry = result[name]['copies_by_kind'].setdefault(str(extra[0]), {'calls': 0, 'bytes': 0, 'gpu_ms': 0})
                entry['bytes'] += extra[1]
            else:
                entry = result[name]['memset']
                entry['bytes'] += extra[0]
            entry['calls'] += 1
            entry['gpu_ms'] = entry.get('gpu_ms', 0)+(b-a)/1e6
    for name, s in result.items():
        s['device_activity_union_ms'] = union_ns(device[name])/1e6
        s['allocation_bytes'] = None
        s['allocation_bytes_reason'] = 'runtime API export has no size arguments; source capacities only, not measured bytes'
        s['cpu_useful_ms'] = None
        s['api_wait_interpretation'] = 'inclusive API waits overlap device activity; do not add or call residual useful CPU'
    c.close()
    return result


def write_csv(path, rows):
    with path.open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--raw-root', type=Path, required=True)
    ap.add_argument('--workflow-root', type=Path, required=True)
    ap.add_argument('--sass', type=Path, required=True)
    ap.add_argument('--evidence', type=Path, default=Path(__file__).parent/'evidence/recovery')
    ap.add_argument('--out', type=Path, default=Path(__file__).parent)
    a = ap.parse_args()
    raw, ev = a.raw_root, a.evidence
    provenance = load(raw/'EXACT_WORK_COUNTERS.json')
    physical = load(ev/'PASS_PHYSICAL_COUNTERS.json')
    rows, sources = [], []
    sass = a.sass.read_text()
    expected = 1_000_000*960*32
    full = next(p for p in provenance if p['method'] == 'O_FULL')
    full_cmd = full['receipt']['command']
    full_path = Path(full_cmd[full_cmd.index('--export')+1]+'.metrics.csv')
    full_row, _ = metric_csv(full_path)
    dm = 'smsp__sass_thread_inst_executed_op_dmul_pred_on.sum'
    da = 'smsp__sass_thread_inst_executed_op_dadd_pred_on.sum'
    df = 'smsp__sass_thread_inst_executed_op_dfma_pred_on.sum'
    assert int(float(full_row[dm])) == expected
    assert '__dmul_rn(dx,dx)' in (raw/'knn_verify.cuh').read_text()
    for p in provenance:
        mode = p['method']
        command = p['receipt']['command']
        stem = Path(command[command.index('--export')+1])
        source = {'method': mode, 'report_sha256': p['report_sha256'],
                  'csv_sha256': p['csv_sha256'], 'raw_name': stem.name}
        sources.append(source)
        label = 'ncu_pass_'+mode+('_dataProcessKnn' if mode == 'GTS_ORIG' else '_verify_distances')
        wi = load(raw/'runs'/stem.name/'identity.json')
        ti = load(raw/'runs'/label/'identity.json')
        source['identity_sha256'] = sha(raw/'runs'/stem.name/'identity.json')
        source['traffic_identity_sha256'] = sha(raw/'runs'/label/'identity.json')
        source['domain'] = identity_fields(wi)
        source['observer_mode'] = wi['observer_mode']
        source['environment'] = wi['environment']
        wc = Path(str(stem)+'.metrics.csv')
        reason = []
        if not wc.exists():
            reason.append('missing_raw_source')
            wr, units = {}, {}
        else:
            assert sha(wc) == p['csv_sha256']
            assert sha(Path(str(stem)+'.ncu-rep')) == p['report_sha256']
            wr, units = metric_csv(wc)
        tc = ti['command']
        ts = Path(tc[tc.index('--export')+1])
        assert sha(Path(str(ts)+'.metrics.csv')) == physical[label+'.metrics']['csv_sha256']
        tr, _ = metric_csv(Path(str(ts)+'.metrics.csv'))
        if identity_fields(wi) != identity_fields(ti):
            reason.append('source_input_identity_mismatch')
        if (wi['observer_mode'], wi['environment']) != (ti['observer_mode'], ti['environment']):
            reason.append('environment_mismatch')
        for name in ('opt_knn_bench', 'gts_bench_p7', 'knn_verify.cuh', 'knn_cutoff.cuh'):
            if name in source['domain']:
                assert sha(raw/name) == source['domain'][name], 'current source/binary drift'
        if wr and not same_launch(wr, tr):
            reason.append('launch_mismatch')
        source['output_bitwise_equal'] = sha(Path(str(stem)+'.bin')) == sha(Path(str(ts)+'.bin'))
        if not source['output_bitwise_equal']:
            reason.append('output_mismatch')
        if mode != 'GTS_ORIG':
            keys = ('mode', 'N', 'D', 'Q', 'K', 'B', 'effective_depth', 'seed_M', 'force_all')
            wm, tm = load(Path(str(stem)+'.json')), load(Path(str(ts)+'.json'))
            source['configuration'] = {k: wm[k] for k in keys}
            if any(wm[k] != tm[k] for k in keys):
                reason.append('configuration_mismatch')
        source['scope'] = 'first matching launch inside formal.query_pass after eight warm batches; replay=kernel/cache=none/clock=none'
        signature = f'_Z16verify_distancesILi2ELb{int(mode != "O_FULL")}ELb{int(mode == "O_MASK")}EE'
        function = next((v for v in sass.split('Function : ') if v.startswith(signature)), '')
        if mode == 'GTS_ORIG':
            reason.append('pow_arithmetic_not_one_DMul_per_coordinate; selected_iterative_launch_not_entire_pass')
        elif not function or 'DFMA ' in function or 'DMUL ' not in function:
            reason.append('missing_compiled_coordinate_mapping')
        coords = int(float(wr[dm])) if wr and not reason else None
        if coords is not None:
            assert int(float(wr[da])) == 2*coords and float(wr[df]) == 0
        pm = physical[label+'.metrics']['records'][0]['metrics']
        read, write = byte_value(pm['dram__bytes_op_read.sum']), byte_value(pm['dram__bytes_op_write.sum'])
        duration = pm['gpu__time_duration.sum']
        gpu_ms = float(duration['value'])*{'s': 1000, 'ms': 1}[duration['unit']]
        rows.append({'method': mode, 'kernel': tr['Kernel Name'], 'launch_ordinal': tr['ID'],
                     'grid': tr['Grid Size'], 'block': tr['Block Size'], 'N': 1000000, 'D': 960,
                     'Q': 32, 'B': 32, 'K': 8, 'candidate_pairs': 32000000 if mode == 'O_FULL' else '',
                     'candidate_pair_scope': 'including self; masked rejection slots unknown' if mode != 'GTS_ORIG' else 'iterative slots; not total-pass pairs',
                     'coordinate_updates': coords if coords is not None else '', 'shared_coordinate_steps': '',
                     'shared_steps_reason': 'no direct shared-load counter; DMUL counts active arithmetic only',
                     'dram_read_bytes': read, 'dram_write_bytes': write, 'units': 'decimal SI bytes',
                     'global_load_requests': pm['l1tex__t_requests_pipe_lsu_mem_global_op_ld.sum']['value'],
                     'global_load_sectors': pm['l1tex__t_sectors_pipe_lsu_mem_global_op_ld.sum']['value'],
                     'read_bytes_per_coordinate_update': read/coords if coords else '',
                     'read_bytes_per_shared_step': '', 'gpu_stage_ms': gpu_ms, 'dtype': 'FP64 accumulator; FP32 storage',
                     'DMUL': wr.get(dm, ''), 'DADD': wr.get(da, ''), 'DFMA': wr.get(df, ''),
                     'admissible': not reason, 'reason': '; '.join(reason) or 'source+SASS+same-domain O_FULL calibration; no instrumented binary delta',
                     'claim_scope': 'descriptive whole-kernel bytes/coordinate; not pure object-load or coalescing causality'})
    timed = [r for r in load(ev/'U10_LEAN_TIMED_ROWS.json') if r['summary']['observe']]
    assert len(timed) == 18 and all(r['runtime_valid'] for r in timed)
    stage_rows = []
    for r in timed:
        for s in r['summary']['stages']:
            stage_rows.append({'seed': r['seed'], 'label': r['label'], 'stage': s['name'], 'calls': s['calls'],
                               'inclusive_host_ms': s['inclusive_host_ms'], 'trace_ms': r['summary']['trace_ms'],
                               'fraction_of_own_trace': s['inclusive_host_ms']/r['summary']['trace_ms'],
                               'scope': 'clean on process; stages inclusive, rebuild nested in insert'})
    summary = {}
    for seed in sorted({r['seed'] for r in timed}):
        sr = [r for r in stage_rows if r['seed'] == seed and r['stage'] == 'query.tree']
        assert len(sr) == 6
        fs = [r['fraction_of_own_trace'] for r in sr]
        summary[str(seed)] = {'processes': 6, 'tree_fraction_min': min(fs),
                              'tree_fraction_median': statistics.median(fs), 'tree_fraction_max': max(fs)}
    ns = load(raw/'U10_NSYSTEMS.json')
    command = ns['receipt']['command']
    db = Path(command[command.index('-o')+1]+'.sqlite')
    assert sha(db) == ns['trace']['trace_sha256']
    profile = profile_stages(db)
    source_manifest = load(a.workflow_root/'native_timed/SOURCE.json')
    update = a.workflow_root/'native_timed/source/include/update.cuh'
    assert sha(update) == source_manifest['sources']['include/update.cuh']
    manifest = {'name': 'U_LIFE_BRIDGE', 'status': 'selected_for_one_conditional_lifecycle_test; not implemented',
                'analyzer_sha256': sha(__file__),
                'candidate_binary_sha256': None, 'candidate_commit': None,
                'baseline_binary_sha256': source_manifest['binary_sha256'],
                'work_reports': sources, 'sass_sha256': sha(a.sass),
                'U10_stage_summary': summary, 'U10_profile': profile, 'sqlite_sha256': sha(db),
                'U10_profile_scope': 'one instrumented seed0431 process; not the 18 clean processes',
                'selected_change': 'reuse 11 internal searchIndexRnnUpdate allocations; externally owned result/count arrays and Thrust allocator unchanged',
                'selected_budget_ms': profile['query.tree']['selected_workspace_api_ms'],
                'budget_limit': 'measured inclusive API cost; not guaranteed saved critical-path time, not new performance',
                'memory_kind': '2 Managed scalars, 9 Device arrays, unchanged',
                'source_update_sha256': sha(update), 'source_lines': 'searchIndexRnnUpdate:341-450',
                'unchanged': ['GPU compute kernels', 'required resets/fences', 'range arithmetic/bounds',
                              'occupancy threshold10', 'serialized multiset/live-rank', 'all output and ACK'],
                'lifetime': 'one native process; per-call logical lengths; capacity checked on every request and after rebuild; release after final drain',
                'capacity': 'actual requested node/candidate bounds; no oracle/answer-based reservation; growth charged',
                'Graph': 'N/A', 'AoSoA': 'N/A', 'P7_knn_integrated': False,
                'pending': ['R10', '30k', 'full cold', 'new vectors', 'million dynamic', 'concurrency'],
                'inputs': {n: sha(ev/n) for n in ['PASS_COUNTER_STATUS.json', 'PASS_PHYSICAL_COUNTERS.json',
                            'U10_LEAN_TIMED_ROWS.json', 'U10_NSYSTEMS.json']}}
    a.out.mkdir(parents=True, exist_ok=True)
    write_csv(a.out/'WORK_TRAFFIC_ALIGNMENT.csv', rows)
    write_csv(a.out/'U10_STAGE_BUDGET.csv', stage_rows)
    (a.out/'CANDIDATE_MANIFEST.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'alignment': [(r['method'], r['admissible'], r['coordinate_updates']) for r in rows],
                      'U10': summary, 'selected_workspace_api_ms': manifest['selected_budget_ms']}))


if __name__ == '__main__':
    main()
