"""Frozen process estimators; descriptive outcomes, no posthoc winner threshold."""
if not __debug__:
    raise SystemExit('Optimized Python disables mandatory checks; run without -O/PYTHONOPTIMIZE.')
import numpy as np
from common import MODES, load


def distribution(x):
    x = np.asarray(x, dtype=float); assert x.shape == (6,) and np.isfinite(x).all()
    return dict(p10=float(np.quantile(x, .1)), median=float(np.median(x)), p90=float(np.quantile(x, .9)),
                arithmetic_mean=float(np.mean(x)), process_values=x.tolist())


def compare(keeper, candidate):
    a, b = np.asarray(keeper, dtype=float), np.asarray(candidate, dtype=float)
    assert a.shape == b.shape == (6,) and np.isfinite(a).all() and np.isfinite(b).all() and min(a) > 0 and min(b) > 0
    logs = np.log(b/a); rng = np.random.default_rng(2026101503)
    boot = np.exp(np.mean(logs[rng.integers(0, 6, size=(20000, 6))], axis=1))
    return dict(median_ratio=float(np.median(b)/np.median(a)), paired_geometric_ratio=float(np.exp(np.mean(logs))),
        paired_95_CI=np.quantile(boot, [.025, .975]).tolist(), paired_ratios=(b/a).tolist(), wins=int(np.count_nonzero(b < a)),
        arithmetic_mean_ratio=float(np.mean(b)/np.mean(a)),
        order_strata={name: dict(paired_geometric_ratio=float(np.exp(np.mean(logs[ids]))), wins=int(np.count_nonzero(b[ids] < a[ids])), pairs=3)
                      for name, ids in (('forward', [0, 2, 4]), ('reverse', [1, 3, 5]))})


def difference(stale, incremental, queries=160, updates=1):
    d = np.asarray(incremental, float)-np.asarray(stale, float); assert d.shape == (6,) and np.isfinite(d).all()
    rng = np.random.default_rng(2026101503); boot = np.median(d[rng.integers(0, 6, size=(20000, 6))], axis=1)
    med = float(np.median(d))
    return dict(estimator='median of matched-round total update ACK differences;not a separately isolated kernel cost',
        paired_difference_ms=d.tolist(), median_difference_ms=med, paired_difference_95_CI_ms=np.quantile(boot, [.025, .975]).tolist(),
        difference_ms_per_query=med/queries, difference_us_per_point_update=med*1000/updates)


def run(w):
    out = {}
    for workload in range(3):
        runs = {mode: [load(w/'primary'/f'W{workload}_r{r}_{mode}.checked.json') for r in range(1, 7)] for mode in MODES}
        systems = {}
        for mode, rows in runs.items():
            cells = []
            for phase in range(5):
                cells.append(dict(phase=phase, query_mean_ms=distribution([float(np.mean([q['ack_ms'] for q in row['all_target_query_records'] if q['phase'] == phase])) for row in rows]),
                    stage_coordinate_visits_per_query=distribution([float(np.mean([q['stage_coordinate_visits'] for q in row['query_stage_records'] if q['phase'] == phase])) for row in rows])))
            systems[mode] = dict(windows=cells, totals={metric: distribution([row['metadata'][metric] for row in rows]) for metric in
                ('service_ms', 'events_ms', 'release_ms', 'query_ms', 'update_ms_including_statistics', 'other_ms',
                 'device_owned_peak_bytes', 'cpu_events_user_s', 'cpu_events_system_s')},
                point_updates=rows[0]['metadata']['point_updates'], update_batches=rows[0]['metadata']['update_batches'])
        comparisons = {}
        for candidate, keeper in (('S1', 'S0'), ('S2_STALE', 'S1'), ('S2_INC', 'S1'), ('S2_INC', 'S2_STALE')):
            comparisons[candidate+'_over_'+keeper] = dict(
                service=compare(systems[keeper]['totals']['service_ms']['process_values'], systems[candidate]['totals']['service_ms']['process_values']),
                query=compare(systems[keeper]['totals']['query_ms']['process_values'], systems[candidate]['totals']['query_ms']['process_values']),
                windows=[compare(systems[keeper]['windows'][p]['query_mean_ms']['process_values'], systems[candidate]['windows'][p]['query_mean_ms']['process_values']) for p in range(5)])
        for mode in ('S2_STALE', 'S2_INC'):
            static_gain = 1-comparisons[mode+'_over_S1']['windows'][0]['median_ratio']
            comparisons[mode+'_over_S1']['gain_retention_vs_own_zero_mutation'] = [
                (1-p['median_ratio'])/static_gain if static_gain > 0 else None for p in comparisons[mode+'_over_S1']['windows']]
            systems[mode]['dynamic_over_own_static'] = [compare(systems[mode]['windows'][0]['query_mean_ms']['process_values'],
                systems[mode]['windows'][p]['query_mean_ms']['process_values']) for p in range(5)]
        tax = difference(systems['S2_STALE']['totals']['update_ms_including_statistics']['process_values'],
                         systems['S2_INC']['totals']['update_ms_including_statistics']['process_values'],
                         updates=systems['S2_INC']['point_updates'])
        out[f'W{workload}'] = dict(systems=systems, comparisons=comparisons, incremental_update_tax=tax)
    return dict(scope='Same campaign,serial static-query/mutation windows;segmented events+complete service release',
        primary_estimator='ratios of medians of six process aggregates', paired_estimator='matched-round geometric ratios',
        bootstrap=dict(seed=2026101503, resamples=20000, unit='matched independent process rounds', CI='percentile'), workloads=out,
        outcome_policy='descriptive potentially overlapping patterns;no automatic novelty/admission threshold')


def check():
    a = np.arange(1, 7, dtype=float); c = compare(a, a*.8)
    assert c['wins'] == 6 and abs(c['median_ratio']-.8) < 1e-14 and all(abs(v-.8) < 1e-14 for v in c['paired_95_CI'])
    d = difference(a, a-1, updates=2); assert d['median_difference_ms'] == -1 and d['difference_us_per_point_update'] == -500
    assert difference(a, a)['paired_difference_95_CI_ms'] == [0, 0]
    print('PASS:paired estimators,strict scope,and signed maintenance differences')


if __name__ == '__main__': check()
