"""Post-run CPU regression checks for lifecycle, boundaries and denominators."""
if not __debug__:
    raise SystemExit('Mandatory checks require ordinary Python.')
import argparse
import json
from pathlib import Path
from replay import replay, planner, summarize


def write(path, operations, peak):
    lines = ['wikipedia-1M:']
    for step, operation in enumerate(operations, 1):
        lines.append(f'  {step}:')
        lines.extend(f'    {key}: {value}' for key, value in operation.items())
    lines.extend([f'  max_pts: {peak}', '  gt_url: https://example.invalid/fixture'])
    path.write_text('\n'.join(lines)+'\n')


def main(out):
    out.mkdir()
    results = []
    for size in (511, 512, 513):
        path = out/f'boundary_{size}.yaml'
        write(path, [dict(operation='insert', start=0, end=1026),
                     dict(operation='delete', start=0, end=size), dict(operation='search')], 1026)
        r = replay(path, out/f'boundary_{size}')
        assert r['scopes']['source_call']['M'] == r['scopes']['source_call']['F'] == size
        assert r['scopes']['within_call_512']['batches'] == (size+511)//512
        assert r['scopes']['within_call_512']['M'] == r['scopes']['within_call_512']['F'] == size
        results.append(size)
    path = out/'zero.yaml'
    write(path, [dict(operation='insert', start=0, end=1),
                 dict(operation='delete', start=0, end=1), dict(operation='search')], 1)
    r = replay(path, out/'zero')
    assert r['allocated_rows'] == 1 and r['final_live'] == 0
    assert r['scopes']['source_call']['M'] == r['scopes']['source_call']['F'] == 0
    assert r['scopes']['source_call']['weighted_elimination'] is None
    bad = [dict(operation='insert', start=0, end=1),
           dict(operation='delete', start=1, end=2),
           dict(operation='replace', tags_start=1, tags_end=2, ids_start=2, ids_end=3)]
    rejections = 0
    for i, operation in enumerate(bad):
        path = out/f'invalid_{i}.yaml'
        write(path, [dict(operation='insert', start=0, end=1), operation,
                     dict(operation='search')], 1)
        try:
            replay(path, out/f'invalid_{i}')
        except AssertionError:
            rejections += 1
        else:
            raise AssertionError('Invalid lifecycle admitted')
    for commands in ([(3, 0), (2, 0), (1, 0)], [(3, 2), (2, 0)]):
        dep = planner.dependencies(commands)
        raw = sum(a[1] == b[0] for i, a in enumerate(commands) for b in commands[i+1:])
        waw = sum(a[1] == b[1] for i, a in enumerate(commands) for b in commands[i+1:])
        war = sum(a[0] == b[1] for i, a in enumerate(commands) for b in commands[i+1:])
        assert (dep['RAW'], dep['WAW'], dep['WAR']) == (raw, waw, war)
    assert len(planner.generic([(3, 2), (2, 0)])) == 2  # Retired row2 remains observable.
    rows = [dict(M=10, F=0, RAW=0, WAW=0, WAR=0, levels=1, width_max=10),
            dict(M=100, F=99, RAW=0, WAW=0, WAR=0, levels=1, width_max=100)]
    summary = summarize(rows)
    assert summary['weighted_elimination'] == .1 and summary['batch_ratio_p50'] == .505
    assert rejections == 3
    print(json.dumps(dict(passed=True, deletion_boundaries=results, zero_move_control=True,
                         invalid_lifecycle_rejections=rejections, dependency_pair_oracle=True,
                         weighted_not_mean_ratio=True, GPU_starts=0), sort_keys=True))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    main(a.out)
