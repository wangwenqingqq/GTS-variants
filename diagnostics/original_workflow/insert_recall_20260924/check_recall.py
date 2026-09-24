#!/usr/bin/env python3
"""Compare audited native update results with an independent live-row CPU oracle."""
import argparse
import json
import math
import re
from collections import Counter
from pathlib import Path

Q = re.compile(r'^GTS_AUDIT_Q (\d+) (\d+) (-?\d+) (\d+) (\d+)$')
H = re.compile(r'^GTS_AUDIT_H (\d+) (-?\d+) (\S+)$')
COST = re.compile(r'Result num:\s*([^\n]+)')


def check(manifest, case, stderr, cost):
    expected = manifest['cases'][case]['queries']
    lines = stderr.splitlines()
    got = []
    format_errors = []
    current = None
    for line in lines:
        if line.startswith('GTS_AUDIT_Q '):
            m = Q.fullmatch(line)
            if not m:
                format_errors.append(f'bad header: {line[:100]}')
                continue
            if current is not None:
                got.append(current)
            op, qid, count, tree, buffer = map(int, m.groups())
            current = {'op_index': op, 'query_id': qid, 'count': count,
                       'tree_size': tree, 'buffered': buffer, 'hits': []}
        elif line.startswith('GTS_AUDIT_H '):
            m = H.fullmatch(line)
            if not m or current is None:
                format_errors.append(f'bad hit: {line[:100]}')
                continue
            op, logical_id, distance = m.groups()
            try:
                distance = float(distance)
            except ValueError:
                format_errors.append(f'bad distance: {line[:100]}')
                continue
            if int(op) != current['op_index']:
                format_errors.append(f'hit op mismatch: {line[:100]}')
            current['hits'].append((int(logical_id), distance))
    if current is not None:
        got.append(current)
    m = COST.search(cost)
    cost_counts = list(map(int, m[1].split())) if m and re.fullmatch(r'\s*\d+(?:\s+\d+)*\s*', m[1]) else None
    failures = []
    if len(got) != len(expected):
        failures.append({'kind': 'query_count', 'expected': len(expected), 'actual': len(got)})
    if format_errors:
        failures.append({'kind': 'audit_format', 'errors': format_errors[:10]})
    if cost_counts != [len(q['hits']) for q in expected]:
        failures.append({'kind': 'cost_counts', 'expected': [len(q['hits']) for q in expected],
                         'actual': cost_counts})
    inserted_expected = inserted_found = 0
    expected_tokens = set()
    found_tokens = set()
    missing_inserted = []
    max_distance_error = 0.0
    phase_stats = {}
    for q, actual in zip(expected, got):
        op = q['op_index']
        if actual['op_index'] != op or actual['query_id'] != q['query_id']:
            failures.append({'kind': 'query_identity', 'expected': [op, q['query_id']],
                             'actual': [actual['op_index'], actual['query_id']]})
        if actual['count'] != len(actual['hits']):
            failures.append({'kind': 'incomplete_audit', 'op': op, 'header_count': actual['count'],
                             'emitted_hits': len(actual['hits'])})
        if actual['count'] != len(q['hits']):
            failures.append({'kind': 'result_count', 'op': op, 'expected': len(q['hits']),
                             'actual': actual['count']})
        ids = [logical_id for logical_id, _ in actual['hits']]
        duplicates = sorted(x for x, n in Counter(ids).items() if n > 1)
        if duplicates:
            failures.append({'kind': 'duplicate_ids', 'op': op, 'ids': duplicates[:20]})
        amap = dict(actual['hits'])
        expected_ids = {int(x) for x in q['hits']}
        missing = sorted(expected_ids - amap.keys())
        extra = sorted(amap.keys() - expected_ids)
        if missing or extra:
            failures.append({'kind': 'id_set', 'op': op, 'missing': missing[:20],
                             'extra': extra[:20], 'missing_total': len(missing), 'extra_total': len(extra)})
        for logical_id in expected_ids & amap.keys():
            distance = amap[logical_id]
            diff = abs(distance - q['hits'][str(logical_id)])
            if not math.isfinite(distance) or diff > 0.001:
                failures.append({'kind': 'distance', 'op': op, 'id': logical_id,
                                 'expected': q['hits'][str(logical_id)], 'actual': distance})
            elif diff > max_distance_error:
                max_distance_error = diff
        phase = q['phase'] + ('_post_delete' if q['after_delete'] else '')
        stats = phase_stats.setdefault(phase, {'eligible': 0, 'found': 0, 'queries': 0})
        stats['queries'] += 1
        for logical_id, token in zip(q['inserted_ids'], q['inserted_tokens']):
            inserted_expected += 1
            expected_tokens.add(token)
            stats['eligible'] += 1
            if logical_id in amap:
                inserted_found += 1
                found_tokens.add(token)
                stats['found'] += 1
            else:
                missing_inserted.append({'op': op, 'logical_id': logical_id, 'insert_op': token})
    return {'pass': not failures, 'case': case, 'queries_expected': len(expected),
            'queries_emitted': len(got), 'inserted_eligible_pairs': inserted_expected,
            'inserted_found_pairs': inserted_found,
            'inserted_distinct_eligible': len(expected_tokens),
            'inserted_distinct_found': len(found_tokens),
            'missing_inserted': missing_inserted[:20], 'phase_stats': phase_stats,
            'max_distance_error': max_distance_error, 'failures': failures[:30],
            'failure_count': len(failures), 'distance_tolerance_abs': 0.001}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('root', type=Path)
    p.add_argument('case')
    p.add_argument('stderr', type=Path)
    p.add_argument('cost', type=Path)
    a = p.parse_args()
    result = check(json.loads((a.root/'manifest.json').read_text()), a.case,
                   a.stderr.read_text(), a.cost.read_text())
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['pass'] else 1)
