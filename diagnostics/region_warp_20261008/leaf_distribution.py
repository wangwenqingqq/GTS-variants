#!/usr/bin/env python3
"""Inventory actual query-region leaf work; never infer its elapsed-time share."""
import argparse
import hashlib
import json
from pathlib import Path


def records(path, prefix):
    with Path(path).open() as stream:
        for line in stream:
            if line.startswith(prefix):
                yield line[len(prefix):].strip()


def distribution(path, parent_work=None):
    plans = {p['epoch']: p for p in map(json.loads, records(path, 'REGION_PLAN '))}
    buckets = {name: dict(query_regions=0, candidate_objects=0, distance_evaluations=0)
               for name in ('0', '1', '2-8', '>8')}
    work = list(records(path, 'REGION_WORK '))
    if parent_work:
        assert work == list(records(parent_work, 'REGION_WORK ')), 'parent work identity differs'
    epochs = set()
    for text in work:
        row = json.loads(text); plan = plans[row['epoch']]; epochs.add(row['epoch'])
        assert row['n'] == plan['n'] == len(row['objects'])
        leaf_objects = dict(plan['leaf_objects'])
        all_ids = [pid for ids in leaf_objects.values() for pid in ids]
        assert sorted(all_ids) == list(range(row['n']))
        assert set(leaf_objects) == {nid for region in plan['regions'] for nid in region['leaves']}
        assert sum(len(region['leaves']) for region in plan['regions']) == len(leaf_objects)
        selected_ids = []; accounted = 0
        for region in plan['regions']:
            selected = [nid for nid in region['leaves'] if row['leaves'][nid]]
            assert all(row['leaves'][nid] in (0, 1) for nid in region['leaves'])
            ids = [pid for nid in selected for pid in leaf_objects[nid]]
            selected_ids += ids
            evaluated = sum(row['objects'][pid] for pid in ids); accounted += evaluated
            key = '0' if not selected else '1' if len(selected) == 1 else '2-8' if len(selected) <= 8 else '>8'
            target = buckets[key]; target['query_regions'] += 1
            target['candidate_objects'] += len(ids); target['distance_evaluations'] += evaluated
        assert len(selected_ids) == len(set(selected_ids))
        assert accounted == sum(row['objects'])
        assert all(x in (0, 1) for x in row['objects']) and row['objects'][row['qid']] == 0
    totals = {key: sum(b[key] for b in buckets.values()) for key in next(iter(buckets.values()))}
    multi = {key: buckets['2-8'][key] + buckets['>8'][key] for key in totals}
    stream = ''.join(line + '\n' for line in work).encode()
    return dict(queries=len(work), epochs=sorted(epochs), buckets=buckets, totals=totals,
                multi_leaf=multi, multi_leaf_distance_work_fraction=multi['distance_evaluations']/max(1, totals['distance_evaluations']),
                normalized_work_stream_sha256=hashlib.sha256(stream).hexdigest(),
                raw_log_sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest(),
                parent_work_exactly_equal=bool(parent_work), scope='base-tree work only; no elapsed-time attribution',
                candidate_objects_definition='all objects in accepted leaves, including deleted/self slots',
                distance_evaluations_definition='actual non-self, non-deleted object evaluations')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--log', type=Path, required=True)
    p.add_argument('--parent-work', type=Path)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args(); assert not a.output.exists()
    result = distribution(a.log, a.parent_work)
    a.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
