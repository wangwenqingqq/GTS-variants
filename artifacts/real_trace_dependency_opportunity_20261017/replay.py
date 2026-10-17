"""Strict opaque-row replay of pinned flat public runbooks; no vector/GPU timing."""
if not __debug__:
    raise SystemExit('Mandatory checks require ordinary Python.')
import argparse
from array import array
import collections
import csv
import hashlib
import importlib.util
import json
import re
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent / 'dependency_update_mechanism_20261017'
spec = importlib.util.spec_from_file_location('frozen_planners', PARENT/'planners.py')
planner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(planner)


def sha(body):
    return hashlib.sha256(body).hexdigest()


def save(path, obj):
    with path.open('x') as f:
        json.dump(obj, f, indent=2, sort_keys=True)
        f.write('\n')


def quantile(values, q):
    if not values:
        return None
    values = sorted(values)
    at = (len(values)-1)*q
    lo, hi = int(at), min(int(at)+1, len(values)-1)
    return values[lo] + (values[hi]-values[lo])*(at-lo)


def read_runbook(path):
    # Only the pinned flat scalar format is supported, not general YAML.
    # No YAML dependency is installed merely to read these three tiny files.
    entries, metadata, current = {}, {}, None
    lines = path.read_text().splitlines()
    assert lines and lines[0] == 'wikipedia-1M:'
    for line in lines[1:]:
        match = re.fullmatch(r'  ([1-9][0-9]*):', line)
        if match:
            current = int(match[1])
            assert current not in entries
            entries[current] = {}
            continue
        match = re.fullmatch(r'    ([a-z_]+): (\S+)', line)
        if match:
            assert current is not None
            key, value = match.groups()
            assert key not in entries[current]
            entries[current][key] = int(value) if value.isdecimal() else value
            continue
        match = re.fullmatch(r'  (max_pts|gt_url): (\S+)', line)
        assert match, 'Unsupported flat runbook syntax'
        key, value = match.groups()
        assert key not in metadata
        metadata[key] = int(value) if value.isdecimal() else value
        current = None
    assert set(entries) == set(range(1, len(entries)+1))
    assert set(metadata) == {'max_pts', 'gt_url'}
    for row in entries.values():
        kind = row['operation']
        fields = {'search': {'operation'},
                  'insert': {'operation', 'start', 'end'},
                  'delete': {'operation', 'start', 'end'},
                  'replace': {'operation', 'tags_start', 'tags_end', 'ids_start', 'ids_end'}}
        assert kind in fields and set(row) == fields[kind]
        for start, end in (('start', 'end'),) if kind in ('insert', 'delete') else (
                (('tags_start', 'tags_end'), ('ids_start', 'ids_end')) if kind == 'replace' else ()):
            assert type(row[start]) is int and type(row[end]) is int
            assert 0 <= row[start] < row[end] <= 1_000_000
        if kind == 'replace':
            assert row['tags_end']-row['tags_start'] == row['ids_end']-row['ids_start']
    return [entries[k] for k in range(1, len(entries)+1)], metadata


def summarize(rows):
    moves = sum(r['M'] for r in rows)
    final = sum(r['F'] for r in rows)
    ratios = [(r['M']-r['F'])/r['M'] for r in rows if r['M']]
    return dict(batches=len(rows), batches_with_moves=len(ratios), M=moves, F=final,
                eliminated=moves-final,
                weighted_elimination=(moves-final)/moves if moves else None,
                batch_ratio_p50=quantile(ratios, .5), batch_ratio_p90=quantile(ratios, .9),
                composable_batches=sum(r['F'] < r['M'] for r in rows),
                composable_batch_fraction=sum(r['F'] < r['M'] for r in rows)/len(rows) if rows else None,
                RAW=sum(r['RAW'] for r in rows), WAW=sum(r['WAW'] for r in rows),
                WAR=sum(r['WAR'] for r in rows),
                depth_p50=quantile([r['levels'] for r in rows], .5),
                depth_p90=quantile([r['levels'] for r in rows], .9),
                width_max=max((r['width_max'] for r in rows), default=0),
                requested_row_metadata_bytes_before=8*moves,
                requested_row_metadata_bytes_after=8*final)


def analyze_plan(commands, entry, labels, step, scope, ordinal, count):
    net = planner.generic(commands)
    assert not set(net).intersection(net.values()), 'Final plan is not in-place independent'
    assert all(labels[r] == entry[net.get(r, r)] for r in entry)
    # The replay writes only rows registered in entry. All other allocated rows
    # are untouched. This includes all retired rows, not just the live prefix.
    dep = planner.dependencies(commands)
    depth, widths = {}, collections.Counter()
    for src, dst in commands:
        level = 1 + max(depth.get(src, -1), depth.get(dst, -1))
        depth[dst] = level
        widths[level] += 1
    assert max(widths, default=-1)+1 == dep['levels']
    return dict(request_step=step, scope=scope, subbatch=ordinal, deletes=count,
                M=len(commands), F=len(net), width_max=max(widths.values(), default=0), **dep)


def replay(path, out):
    out.mkdir()
    operations, metadata = read_runbook(path)
    universe = max((op.get(key, 0) for op in operations
                    for key in ('end', 'tags_end', 'ids_end')), default=0)
    owner, labels = array('q'), array('q')
    pos = array('q', [-1])*universe
    payload = array('q', [-1])*universe
    born_step = array('q', [-1])*universe
    born_mutation = array('q', [-1])*universe
    seen_births, update_targets = bytearray(universe), bytearray(universe)
    kinds, points = collections.Counter(), collections.Counter()
    rows, checkpoints, calls, cases = [], [], [], []
    lives, ages = [], []
    mutations = repeated_targets = reinserts = peak = 0
    for step, op in enumerate(operations, 1):
        kind = op['operation']
        kinds[kind] += 1
        n_before = len(owner)
        if kind in ('insert', 'delete'):
            ids = range(op['start'], op['end'])
            points[kind] += len(ids)
        elif kind == 'replace':
            ids = range(op['tags_start'], op['tags_end'])
            points[kind] += len(ids)
        else:
            ids = ()
        call = dict(request_step=step, operation=kind, points=len(ids), live_before=n_before)
        if kind == 'insert':
            for logical in ids:
                assert pos[logical] == payload[logical] == -1, 'Insert of live ID'
                reinserts += bool(seen_births[logical])
                seen_births[logical] = 1
                pos[logical] = len(owner)
                owner.append(logical)
                if pos[logical] == len(labels):
                    labels.append(logical)
                else:
                    labels[pos[logical]] = logical
                payload[logical] = logical
                born_step[logical], born_mutation[logical] = step, mutations
                mutations += 1
        elif kind == 'replace':
            for logical, source in zip(ids, range(op['ids_start'], op['ids_end'])):
                assert pos[logical] >= 0 and payload[logical] >= 0, 'Replace of absent ID'
                repeated_targets += bool(update_targets[logical])
                update_targets[logical] = 1
                payload[logical] = source
                labels[pos[logical]] = source
                mutations += 1
        elif kind == 'delete':
            commands, entry, chunk_commands, chunk_entry = [], {}, [], {}
            chunk_start, chunk_rows = len(owner), 0
            for j, logical in enumerate(ids):
                assert pos[logical] >= 0 and payload[logical] >= 0, 'Delete of absent ID'
                repeated_targets += bool(update_targets[logical])
                update_targets[logical] = 1
                lives.append(step-born_step[logical])
                ages.append(mutations-born_mutation[logical])
                row, last = pos[logical], len(owner)-1
                if row != last:
                    for r in (last, row):
                        if r not in entry:
                            entry[r] = labels[r]
                        if r not in chunk_entry:
                            chunk_entry[r] = labels[r]
                    commands.append((last, row))
                    chunk_commands.append((last, row))
                    labels[row] = labels[last]
                    moved = owner[-1]
                    owner[row], pos[moved] = moved, row
                owner.pop()
                pos[logical] = payload[logical] = -1
                mutations += 1
                chunk_rows += 1
                if chunk_rows == 512 or j == len(ids)-1:
                    rows.append(analyze_plan(chunk_commands, chunk_entry, labels, step,
                                             'within_call_512', j//512, chunk_rows))
                    cases.append(dict(scope='within_call_512', request_step=step,
                                      n=chunk_start, deleted=chunk_rows, commands=chunk_commands))
                    chunk_commands, chunk_entry = [], {}
                    chunk_start, chunk_rows = len(owner), 0
            rows.append(analyze_plan(commands, entry, labels, step, 'source_call', 0, len(ids)))
            cases.append(dict(scope='source_call', request_step=step, n=n_before,
                              deleted=len(ids), commands=commands))
        elif kind == 'search':
            # Independent logical payload authority plus full inverse-map check.
            own, pp = np.frombuffer(owner, dtype=np.int64), np.frombuffer(pos, dtype=np.int64)
            vv, truth = np.frombuffer(labels, dtype=np.int64), np.frombuffer(payload, dtype=np.int64)
            assert np.count_nonzero(pp >= 0) == np.count_nonzero(truth >= 0) == len(owner)
            assert np.array_equal(pp[own], np.arange(len(owner)))
            assert np.array_equal(vv[:len(owner)], truth[own])
            checkpoints.append(dict(request_step=step, live=len(owner), capacity=len(labels),
                                    owner_sha256=sha(owner.tobytes()),
                                    allocated_labels_sha256=sha(labels.tobytes()),
                                    positions_sha256=sha(pos.tobytes()),
                                    logical_payloads_sha256=sha(payload.tobytes())))
            del own, pp, vv, truth
        peak = max(peak, len(owner))
        call.update(live_after=len(owner), capacity_after=len(labels))
        calls.append(call)
    assert peak == metadata['max_pts']
    assert operations[-1]['operation'] == 'search', 'Final logical checkpoint required'
    with (out/'batches.csv').open('x', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else [
            'request_step', 'scope', 'subbatch', 'deletes', 'M', 'F', 'width_max', 'RAW', 'WAW', 'WAR', 'levels'], lineterminator='\n')
        w.writeheader()
        w.writerows(rows)
    save(out/'calls.json', calls)
    save(out/'checkpoints.json', checkpoints)
    save(out/'cpu_cases.json', cases)
    scopes = {scope: summarize([r for r in rows if r['scope'] == scope])
              for scope in ('source_call', 'within_call_512')}
    result = dict(passed=True, input_sha256=sha(path.read_bytes()), provenance_grade='B: exact public runbook replay',
                  distribution_grade='C: generated expiration/replacement choices',
                  physical_adapter='Packed ordered swap-delete, not source-system storage',
                  call_counts=dict(kinds), point_counts=dict(points), initial_live=0, final_live=len(owner),
                  max_live=peak, allocated_rows=len(labels), source_operations=len(operations),
                  query_barriers=len(checkpoints), query_results_verified=False,
                  full_symbolic_allocated_state_verified=True, scopes=scopes,
                  completed_lifetimes=len(lives), lifetime_source_call_p50=quantile(lives, .5),
                  lifetime_source_call_p90=quantile(lives, .9),
                  lifetime_mutation_steps_p50=quantile(ages, .5),
                  lifetime_mutation_steps_p90=quantile(ages, .9),
                  repeated_noninsert_targets=repeated_targets, reinserted_IDs=reinserts,
                  within_call_repeated_logical_targets=0,
                  singleton_visibility_control=dict(M=scopes['source_call']['M'],
                      F=scopes['source_call']['M'], weighted_elimination=0 if scopes['source_call']['M'] else None,
                      scope='Different, stricter visibility contract; not a performance comparator'),
                  GPU_starts=0, full_service_evidence='UNKNOWN')
    save(out/'RESULT.json', result)
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--runbook', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    r = replay(a.runbook, a.out)
    print('REPLAY_PASS', a.runbook.name, r['source_operations'], r['scopes'], 'GPU starts 0')
