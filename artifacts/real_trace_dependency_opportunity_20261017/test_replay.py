"""Small exact semantic fixtures and adversarial input checks; no GPU."""
if not __debug__:
    raise SystemExit('Mandatory checks require ordinary Python.')
import argparse
import itertools
import json
from pathlib import Path
from replay import planner, quantile, read_runbook, replay
from capture import validate


def main(out):
    out.mkdir()
    cases = 0
    commands = [(src, dst) for src in range(3) for dst in range(3) if src != dst]
    for length in range(5):
        for program in itertools.product(commands, repeat=length):
            actual = list(range(3))
            for src, dst in program:
                actual[dst] = actual[src]
            net = planner.generic(program)
            assert actual == [net.get(i, i) for i in range(3)]
            cases += 1
    fixture = '''wikipedia-1M:
  1:
    operation: insert
    start: 0
    end: 1
  2:
    operation: insert
    start: 3
    end: 4
  3:
    operation: insert
    start: 2
    end: 3
  4:
    operation: insert
    start: 1
    end: 2
  5:
    operation: search
  6:
    operation: delete
    start: 0
    end: 3
  7:
    operation: search
  8:
    operation: insert
    start: 4
    end: 5
  9:
    operation: replace
    tags_start: 4
    tags_end: 5
    ids_start: 5
    ids_end: 6
  10:
    operation: search
  max_pts: 4
  gt_url: https://example.invalid/fixture
'''
    path = out/'fixture.yaml'
    path.write_text(fixture)
    result = replay(path, out/'replay')
    assert result['scopes']['source_call']['M'] == 3
    assert result['scopes']['source_call']['F'] == 1
    assert result['scopes']['source_call']['WAW'] == 3
    assert result['point_counts'] == dict(insert=5, delete=3, replace=1)
    assert result['final_live'] == 2 and result['allocated_rows'] == 4
    assert result['query_barriers'] == 3 and result['within_call_repeated_logical_targets'] == 0
    assert result['singleton_visibility_control']['F'] == 3
    assert quantile([], .5) is None and quantile([0, 2], .5) == 1
    rejected = 0
    for bad in (fixture.replace('  2:', '  1:', 1),
                fixture.replace('  2:', '  22:', 1),
                fixture.replace('operation: insert', 'operation: unsafe', 1),
                fixture.replace('end: 1', 'end: 0', 1),
                fixture.replace('start: 0', 'start: !!python/object:exploit', 1)):
        path.write_text(bad)
        try:
            read_runbook(path)
        except (AssertionError, KeyError):
            rejected += 1
        else:
            raise AssertionError('Invalid runbook admitted')
    for bad in ({}, dict(rcid=1, pageid=1, revid=1, old_revid=0,
                        timestamp='2026-10-16T00:10:00Z', type='new', actor='not-retained')):
        try:
            validate(bad)
        except AssertionError:
            rejected += 1
        else:
            raise AssertionError('Unexpected metadata admitted')
    assert rejected == 7
    print(json.dumps(dict(passed=True, arbitrary_copy_programs=cases,
                         retired_row_and_append_fixture=True,
                         stable_ID_replace_not_delete_insert=True,
                         input_rejections=rejected, GPU_starts=0), sort_keys=True))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    main(a.out)
