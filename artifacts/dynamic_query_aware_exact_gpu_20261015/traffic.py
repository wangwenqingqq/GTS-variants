"""All-capture NCU accounting with interned symbols; profiler duration stays diagnostic."""
import collections
import csv
import math
import re
import numpy as np
from common import sha


def read(path, metrics):
    with path.open() as f: rows = list(csv.reader(f))
    header, units = rows[:2]; unit = dict(zip(header, units)); assert 'Kernel Name' in header and 'ID' in header
    factors = dict(ns=1., nsecond=1., us=1e3, usecond=1e3, ms=1e6, msecond=1e6, second=1e9, s=1e9)
    assert unit[metrics[0]] in factors and all(unit[k] == 'byte' for k in metrics[1:5])
    names = []; records = []; active = 0
    for row in rows[2:]:
        assert len(row) == len(header); r = dict(zip(header, row)); name = r['Kernel Name']
        if name not in names: names.append(name)
        match = re.search(r'progressive_stage<\s*(\d+),\s*(\d+)', name)
        if match:
            kind = 'scan'; start, end = map(int, match.groups()); stage = 1 if start == 0 else (128, 256, 512, 960).index(end)+1
        elif 'progressive_fields' in name: kind, stage = 'fields', active
        elif 'gather_deleted' in name: kind, stage = 'statistics_gather', 0
        elif 'maintain_mean' in name: kind, stage = 'statistics_sum', 0
        elif 'cub::' in name or 'DeviceSelect' in name or 'DeviceCompact' in name: kind, stage = 'compact', active
        else: kind, stage = 'other', active
        active = stage
        values = [float(r[k].replace(',', '')) for k in metrics]; values[0] *= factors[unit[metrics[0]]]
        assert all(math.isfinite(v) and v >= 0 for v in values)
        assert abs(values[1]-values[2]-values[3]) <= max(1., values[1]*1e-6)
        records.append([int(r['ID']), names.index(name), kind, stage, *values])
    return dict(raw_CSV_sha256=sha(path), columns=['capture_id', 'kernel_index', 'kind', 'stage', *metrics], kernel_table=names,
                normalized_units={**{k: unit[k] for k in metrics}, metrics[0]: 'ns'}, captures=records)


def summarize(rows):
    assert rows
    return dict(DRAM_bytes=sum(r[5] for r in rows), DRAM_read_bytes=sum(r[6] for r in rows),
                DRAM_write_bytes=sum(r[7] for r in rows), L2_bytes=sum(r[8] for r in rows), kernel_ms=sum(r[4] for r in rows)/1e6)


def query(path, checked, metrics):
    capture = read(path, metrics); groups = []; current = []
    for row in capture['captures']:
        if row[2] == 'scan' and row[3] == 1:
            if current: groups.append(current)
            current = []
        assert current or (row[2] == 'scan' and row[3] == 1), 'kernel outside a recognized query'
        current.append(row)
    if current: groups.append(current)
    assert len(groups) == 160
    queries = checked['all_target_query_records'][8:]; stages = checked['query_stage_records'][8:]; records = []
    for rows, q, stage in zip(groups, queries, stages):
        assert [r[3] for r in rows if r[2] == 'scan'] == [i+1 for i, n in enumerate(stage['inputs']) if n > 0]
        assert sum(r[2] == 'fields' for r in rows) == int(q['count'] > 0)
        assert not any(r[2].startswith('statistics') for r in rows)
        for index, n in enumerate(stage['inputs']):
            if n > 0: assert any(r[2] == 'compact' and r[3] == index+1 for r in rows)
        records.append(dict(phase=q['phase'], slot=q['slot'], mutation=q['mutation'], qid=q['qid'], hits=q['count'],
            launches=len(rows), kernel_kind_counts=dict(collections.Counter(r[2] for r in rows)),
            **summarize(rows), stage_coordinate_bytes=stage['stage_coordinate_visits']*4))
    windows = []
    for phase in range(5):
        qs = [q for q in records if q['phase'] == phase]; assert len(qs) == 32
        rows = [r for group, q in zip(groups, records) if q['phase'] == phase for r in group]
        families = []
        for kind, stage in sorted(set((r[2], r[3]) for r in rows)):
            subset = [r for r in rows if (r[2], r[3]) == (kind, stage)]
            families.append(dict(kind=kind, stage=stage, launches=len(subset), mean_per_query={k: v/32 for k, v in summarize(subset).items()}))
        windows.append(dict(phase=phase, means={k: float(np.mean([q[k] for q in qs])) for k in ('DRAM_bytes', 'DRAM_read_bytes', 'DRAM_write_bytes', 'L2_bytes', 'kernel_ms', 'stage_coordinate_bytes', 'hits')},
                            DRAM_query_p10_median_p90=np.quantile([q['DRAM_bytes'] for q in qs], [.1, .5, .9]).tolist(), families=families))
    return dict(scope='All formal query kernels;160 queries,32/window;one NCU process,no process CI;no DMA',
        profiler_duration_not_primary=True, mode=checked['mode'], workload=checked['workload'], launches=len(capture['captures']),
        windows=windows, queries=records, raw=capture)


def maintenance(path, checked, metrics, batch_count):
    capture = read(path, metrics); rows = capture['captures']
    counts = collections.Counter(r[2] for r in rows)
    assert counts['statistics_gather'] == batch_count and counts['statistics_sum'] == 2*batch_count
    assert counts['scan'] == counts['fields'] == counts['compact'] == 0
    totals = summarize(rows); duration = sum(r[4] for r in rows); assert duration > 0
    weighted = {k: sum(r[4]*r[4+i] for r in rows)/duration for i, k in enumerate(metrics) if i >= 5}
    return dict(scope='All INC/W2 update-region kernels;copy-request bytes separate;no profiler latency promotion',
        point_updates=checked['metadata']['point_updates'], update_batches=checked['metadata']['update_batches'],
        kernel_counts=dict(counts), total_kernel_metrics=totals,
        per_point_update={k: v/checked['metadata']['point_updates'] for k, v in totals.items()},
        duration_weighted_selected_kernel_percent=weighted, raw=capture)
