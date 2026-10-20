"""Scalar-only structural summaries; no private vectors, tree arrays or GPU."""
if not __debug__:
    raise SystemExit('Assertions are mandatory.')
import argparse
import json
import math
from pathlib import Path
from statistics import fmean, median

HERE = Path(__file__).resolve().parent


def load(path):
    return json.loads(Path(path).read_text())


def distribution(values):
    a = sorted(x for x in values if x is not None)
    assert values and all(math.isfinite(x) for x in a)
    if not a:
        return dict(count=len(values), non_null=0, mean=None, median=None,
                    p10=None, p90=None, minimum=None, maximum=None)
    def quantile(p):
        x = (len(a)-1)*p
        lo = math.floor(x)
        return a[lo]+(a[math.ceil(x)]-a[lo])*(x-lo)
    return dict(count=len(values), non_null=len(a), mean=fmean(a), median=median(a), p10=quantile(.1),
                p90=quantile(.9), minimum=a[0], maximum=a[-1])


def summarize(results, contract):
    n, d, q = (contract['task'][k] for k in ('N', 'D', 'queries'))
    output = {}
    for kind in contract['builders']:
        r = results[kind]
        assert r['passed'] and r['kind'] == kind
        assert r['GPU_starts'] == r['heldout_query_evaluations'] == 0
        rows, levels = r['rows'], r['levels']
        assert len(rows) == q and len(levels) == q*13
        assert [z['qid'] for z in rows] == contract['task']['qids']
        assert [z['query'] for z in rows] == list(range(q))
        for z in rows:
            assert z['false_prune_nodes'] == 0
            assert 0 <= z['retained_points'] <= n
            assert z['coordinate_proxy_bytes'] == (z['visited_nodes']+z['retained_points'])*d*4+d*4
            assert z['node_metadata_read_proxy_bytes'] == z['visited_nodes']*32
            assert z['full_scan_coordinate_bytes'] == n*d*4+d*4
            assert z['oracle_retained_points'] <= z['retained_points']
        fields = [k for k in rows[0] if k not in ('query', 'qid')]
        stats = {k: distribution([z[k] for z in rows]) for k in fields}
        pruned = [1-z['retained_points']/n for z in rows]
        full = n*d*4+d*4
        savings = [1-z['coordinate_proxy_bytes']/full for z in rows]
        per_level = []
        for depth in range(13):
            cells = [z for z in levels if z['depth'] == depth]
            assert len(cells) == q and [z['query'] for z in cells] == list(range(q))
            per_level.append(dict(depth=depth, **{
                k: distribution([z[k] for z in cells])
                for k in cells[0] if k not in ('query', 'qid', 'depth')}))
        oracle_mass = q*n-sum(z['oracle_retained_points'] for z in rows)
        actual_mass = q*n-sum(z['retained_points'] for z in rows)
        output[kind] = dict(metrics=stats, actual_pruned_fraction=distribution(pruned),
            coordinate_proxy_saving_fraction=distribution(savings),
            actual_pruned_points_total=actual_mass, oracle_prunable_points_total=oracle_mass,
            hierarchical_capture_mass_ratio=actual_mass/oracle_mass if oracle_mass else None,
            no_pruning_queries=sum(z['retained_points'] == n for z in rows),
            coordinate_proxy_below_full_scan_queries=sum(z['coordinate_proxy_bytes'] < full for z in rows),
            levels=per_level, construction_wall_seconds=r['construction_wall_seconds'])
    base = results['RANDOM_BALANCED']['rows']
    paired = {}
    for kind in contract['builders'][1:]:
        candidate = results[kind]['rows']
        paired[kind] = dict(
            fewer_retained_points=sum(b['retained_points'] < a['retained_points'] for a,b in zip(base,candidate)),
            equal_retained_points=sum(b['retained_points'] == a['retained_points'] for a,b in zip(base,candidate)),
            more_retained_points=sum(b['retained_points'] > a['retained_points'] for a,b in zip(base,candidate)))
    return dict(experiment=contract['experiment'], passed=True, N=n, D=d, queries=q,
        methods=output, paired_against_random=paired, GPU_starts=0, heldout_query_evaluations=0,
        decision='DESCRIPTIVE_ONLY_NO_GPU_OR_INDEX_ADMISSION',
        scope='Fixed development-only structural counts and conditional source proxies;not physical traffic or end-to-end timing')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, default=HERE)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    c = load(a.root/'CONTRACT.json')
    r = {k: load(a.root/'results'/(k+'.json')) for k in c['builders']}
    with a.out.open('x') as f:
        json.dump(summarize(r,c), f, indent=2, sort_keys=True, allow_nan=False)
        f.write('\n')
