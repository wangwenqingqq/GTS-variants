#!/usr/bin/env python3
"""Prepare bounded full-ID insertion-recall probes from pinned original GTS."""
import argparse
import difflib
import hashlib
import json
import math
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import prepare as base

SOURCES = [0, 1, 7, 31, 127, 255, 511, 900, 0, 31]


def cases():
    exact = [(2, 0)]
    for source_id in [0, 31, 31, 0, 511, 7]:
        exact.extend([(0, source_id), (2, source_id)])
    exact += [(2, 0), (2, 31)]

    deleted = [(0, 0), (0, 31), (2, 0), (2, 31), (1, base.N),
               (2, 0), (2, 31), (0, 0), (2, 0)]

    rebuild = []
    for source_id in SOURCES:
        rebuild.extend([(0, source_id), (2, source_id)])
    rebuild += [(2, 0), (2, 31), (2, 900), (1, base.N),
                (2, 0), (2, 31), (0, 1), (2, 1)]

    control = [(0, source_id) for source_id in SOURCES]
    control += [(2, source_id) for source_id in [0, 1, 7, 31, 127, 255, 511, 900]]

    all_include = [(2, 0)] + [(0, x) for x in SOURCES[:3]] + [(2, 0)]
    all_include += [(0, x) for x in SOURCES[3:]]
    all_include += [(2, 31), (1, base.N), (2, 0), (2, 31)]

    partial = [(0, x) for x in SOURCES[:5]] + [(2, 0), (2, 31)]
    partial += [(0, x) for x in SOURCES[5:]] + [(2, 0), (2, 31),
                (1, base.N + 3), (2, 0), (2, 31)]

    return {
        'buffer_exact': (0, exact),
        'buffer_delete': (0, deleted),
        'rebuild_exact': (0, rebuild),
        'rebuild_control': (0, control),
        'all_include': (10000, all_include),
        'partial_radius': (1200, partial),
    }


def oracle(rows, ops, radius):
    # Each list entry is one live occurrence; its index is the native logical ID.
    live = [(i, None) for i in range(base.N)]
    queries = []
    buffered = 0
    rebuilds = 0
    deletions = 0
    for op_index, (flag, idx) in enumerate(ops):
        if flag == 0:
            assert idx < base.N  # Original rows remain at these physical positions.
            live.append((idx, op_index))
            buffered += 1
            if buffered == 10:
                buffered = 0
                rebuilds += 1
        elif flag == 1:
            assert base.N <= idx < len(live)
            live.pop(idx)
            deletions += 1
            # In these fixtures deletion is from the buffer only when it is last.
            if buffered and idx >= len(live) - buffered + 1:
                buffered -= 1
        else:
            assert flag == 2 and 0 <= idx < base.N
            qrow = rows[live[idx][0]]
            hits = {}
            inserted = []
            inserted_tokens = []
            for logical_id, (source_id, token) in enumerate(live):
                d2 = sum((a-b)*(a-b) for a, b in zip(qrow, rows[source_id]))
                if d2 <= radius * radius:
                    hits[logical_id] = math.sqrt(d2)
                    if token is not None:
                        inserted.append(logical_id)
                        inserted_tokens.append(token)
            queries.append({'op_index': op_index, 'query_id': idx,
                            'phase': 'after_rebuild' if rebuilds else 'before_rebuild',
                            'after_delete': deletions > 0, 'rebuilds': rebuilds,
                            'buffered': buffered, 'live_count': len(live),
                            'hits': hits, 'inserted_ids': inserted,
                            'inserted_tokens': inserted_tokens})
    return queries


def instrument(text):
    anchor = '\t\t\tfprintf(fcost, "%d ", total_result_num);'
    assert text.count(anchor) == 1
    added = '''\t\t\tfprintf(stderr, "GTS_AUDIT_Q %d %d %d %d %d\\n",
\t\t\t        i, qid_list[0], total_result_num, tree_size, in_size);
\t\t\tfor (int gts_audit_j = 0; gts_audit_j < total_result_num; ++gts_audit_j)
\t\t\t\tfprintf(stderr, "GTS_AUDIT_H %d %d %.9g\\n", i,
\t\t\t\t        total_result_id[gts_audit_j], total_result_dis[gts_audit_j]);
\t\t\tfflush(stderr);
'''
    return text.replace(anchor, added + anchor)


def prepare(out, original, reset, old_fixture):
    assert not out.exists()
    variants = {'original_audit': original, 'reset_audit': reset}
    pins = json.loads((HERE.parent.parent/'original_tree_redundancy/SOURCE_PINS.json').read_text())
    pinned = {k.removeprefix('GTS/'): v for k, v in pins['sha256'].items() if k.startswith('GTS/')}
    reset_record = json.loads((reset/'VARIANT.json').read_text())
    assert len(pinned) == 8
    assert reset_record['original_source_sha256'] == pinned
    for name, expected in pinned.items():
        assert base.sha(original/name) == expected, name
        assert base.sha(reset/name) == reset_record['source_sha256'][name], name
    old_manifest = json.loads((old_fixture/'manifest.json').read_text())
    assert base.sha(old_fixture/'fixtures/data.txt') == old_manifest['data_sha256']
    out.mkdir(parents=True)
    (out/'fixtures').mkdir()
    (out/'bin').mkdir()
    (out/'runs').mkdir()
    (out/'logs').mkdir()
    shutil.copy2(old_fixture/'fixtures/data.txt', out/'fixtures/data.txt')
    lines = (out/'fixtures/data.txt').read_text().splitlines()
    assert lines[0] == f'{base.D} {base.N} 2'
    rows = [list(map(int, x.split())) for x in lines[1:]]
    assert len(rows) == base.N and all(len(x) == base.D for x in rows)
    source_records = {}
    for variant, source in variants.items():
        dest = out/'variants'/variant
        before, after = {}, {}
        for name in pinned:
            before[name] = (source/name).read_text()
            after[name] = instrument(before[name]) if name == 'include/update.cuh' else before[name]
            target = dest/name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(after[name])
        diff = ''.join(''.join(difflib.unified_diff(before[n].splitlines(True), after[n].splitlines(True),
                       fromfile=f'{variant}/before/{n}', tofile=f'{variant}/after/{n}')) for n in pinned)
        (dest/'PATCH.diff').write_text(diff)
        assert [n for n in pinned if before[n] != after[n]] == ['include/update.cuh']
        assert len(re.findall(r'^\+[^+]', diff, re.M)) == 6
        source_records[variant] = {'parent': 'original' if variant == 'original_audit' else 'rnum_reset',
                                   'parent_sha256': {n: base.sha(source/n) for n in pinned},
                                   'source_sha256': {n: base.sha(dest/n) for n in pinned},
                                   'patch_sha256': base.sha(dest/'PATCH.diff')}
        (dest/'VARIANT.json').write_text(json.dumps(source_records[variant], indent=2)+'\n')
    case_records = {}
    for name, (radius, ops) in cases().items():
        updates = out/'fixtures'/f'{name}.updates'
        updates.write_text(str(len(ops))+'\n'+''.join(f'{flag} {idx}\n' for flag, idx in ops))
        truth = oracle(rows, ops, radius)
        assert truth and all(q['hits'] for q in truth)
        case_records[name] = {'radius': radius, 'operations': len(ops),
                              'updates_sha256': base.sha(updates),
                              'expected_counts': [len(q['hits']) for q in truth],
                              'queries': truth}
    record = {'source_commit': pins['commit'], 'n': base.N, 'dimensions': base.D,
              'metric': 'L2', 'data_sha256': base.sha(out/'fixtures/data.txt'),
              'variants': source_records, 'cases': case_records,
              'oracle': 'Per-occurrence live list; integer squared L2 for inclusion, sqrt for distances; current logical result IDs.',
              'scope': 'Full result IDs and distances on bounded synthetic cases; no universal or performance claim.'}
    (out/'manifest.json').write_text(json.dumps(record, indent=2)+'\n')
    return record


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('out', type=Path)
    p.add_argument('--original', type=Path, required=True)
    p.add_argument('--reset', type=Path, required=True)
    p.add_argument('--old-fixture', type=Path, required=True)
    a = p.parse_args()
    m = prepare(a.out, a.original, a.reset, a.old_fixture)
    print(f'Prepared {len(m["variants"])} audit variants and {len(m["cases"])} full-ID cases')
