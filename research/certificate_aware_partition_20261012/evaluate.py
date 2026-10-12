#!/usr/bin/env python3
"""Full PCA-only causal matrix, native bridge and diagnostic ledgers; no timing."""
import argparse, csv, json, sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'projection_certificate_20261011'))
from projection_math import prefix_bounds, serialize
from build import check_sources
from audit import sha, save
from partitions import LEVELS, PARTITIONS, metrics, decide


def csv_read(path):
    with path.open() as f: return list(csv.DictReader(f))


def csv_write(path, rows):
    with path.open('x', newline='') as f:
        w = csv.DictWriter(f, list(rows[0]), lineterminator='\n'); w.writeheader(); w.writerows(rows)


def bridge(level, size, k, bound, old, im):
    native = old[f'native_lb_{level}']; visited = old[f'visited_{level}']
    u = np.sqrt(old['U_star_squared']); truth = old[f'truth_sq_{level}'] <= old['U_star_squared'][:, None]
    base = native <= u[:, None]; pruned = np.maximum(native, bound) > u[:, None]
    new = pruned & base; assert not np.any(new & ~visited) and not np.any(pruned & truth)
    remain = int((~pruned).sum()) * size; added = int(new.sum()) * size
    floor = int(truth.sum()) * size; old_count = int(base.sum()) * size; g0 = int(visited.sum()) * size
    ev = int(base.sum()); aligned = 8 * k; gap = (old_count - remain) / (old_count - floor)
    row = dict(family='PCA', level=level, k=k, regions=10 ** level, objects_per_region=size,
        safe_pruned_regions=int(pruned.sum()), safe_pruned_objects=8000000 - remain,
        remaining_objects=remain, residual_fraction=remain / 8000000,
        additional_G0_visited_pruned=added, G0_visited_objects=g0, incremental_G0_pruning=added / g0,
        oracle_gap_coverage=gap, logical_bytes_per_region=aligned, aligned_bytes_per_region=aligned,
        query_projection_coordinate_updates=8 * k * 960, bound_evaluations=ev,
        bound_scalar_ops=(8 * k + 3) * ev + 2 * 8 * k,
        outward_nextafter_ops=(4 * k + 2) * ev + 2 * 8 * k, metadata_bytes_read=ev * aligned,
        avoided_original_coordinate_updates=added * 960, remaining_original_coordinate_updates=remain * 960,
        shared_basis_bytes=k * 960 * 8, query_projection_cache_bytes_per_query=k * 8,
        certificate_efficiency=gap / aligned)
    perquery = []
    for qi, qid in enumerate(im['queries']):
        rq = int((~pruned[qi]).sum()) * size; aq = int(new[qi].sum()) * size
        oq = int(base[qi].sum()) * size; fq = int(truth[qi].sum()) * size; gq = int(visited[qi].sum()) * size
        perquery.append(dict(query_id=qid, family='PCA', level=level, k=k, remaining_objects=rq,
            residual_fraction=rq / 1000000, additional_G0_visited_pruned=aq, G0_visited_objects=gq,
            incremental_G0_pruning=aq / gq, oracle_gap_coverage=(oq - rq) / (oq - fq)))
    return row, perquery


def main():
    p = argparse.ArgumentParser()
    for key in ['freeze', 'run', 'ancestors', 'out']: p.add_argument('--' + key, type=Path, required=True)
    a = p.parse_args(); a.out.mkdir(parents=True, exist_ok=False)
    im = json.loads((a.freeze / 'INPUT_IDENTITY.json').read_text()); check_sources(im)
    assert sha(a.freeze / 'SAMPLES.json') == im['samples_sha256'] and sha(a.ancestors) == im['ancestors_sha256']
    om = json.loads((a.run / 'OUTPUT_MANIFEST.json').read_text())
    for name, entry in om.items(): assert sha(a.run / name) == entry['sha256']
    gate = json.loads((a.run / 'PARTITION_AUDIT.json').read_text())
    assert gate['status'] == 'PASS' and gate['inputs'] == im and gate['independent_pairs'] == 256
    old = np.load(a.ancestors); prior = HERE.parent / 'projection_certificate_20261011/evidence'
    previous = csv_read(prior / 'per_level_summary.csv'); previous_q = csv_read(prior / 'per_query_summary.csv')
    rows = []; perquery = []; compact = []; near_rows = []; near_summary = []; sensitivity = []
    native_bridge = []; native_q = []; validation = []; records = {}
    for partition in PARTITIONS:
        data = np.load(a.run / (partition + '.npz')); u = np.sqrt(data['U_star_squared'])
        assert np.array_equal(u, np.sqrt(old['U_star_squared']))
        for level, size in LEVELS.items():
            r = 10 ** level; lo = data[f'low_{level}']; hi = data[f'high_{level}']
            truthsq = data[f'truth_sq_{level}']; truth = np.sqrt(truthsq)
            retained = truthsq <= data['U_star_squared'][:, None]
            assert np.array_equal(retained, truth <= u[:, None])
            bs = {k: np.empty_like(truth) for k in (4, 8)}
            for qi in range(8):
                bounds = prefix_bounds(lo, hi, data['query_projection'][qi])
                for k in (4, 8): bs[k][qi] = bounds[k]
            assert np.all(bs[8] >= bs[4])
            for k in (4, 8):
                lb = bs[k]; assert np.all(lb <= truth), 'bound above truth'
                pruned = lb > u[:, None]; assert not np.any(pruned & retained), 'false topK prune'
                remaining = int((~pruned).sum()) * size; floor = int(retained.sum()) * size
                row = dict(partition=partition, level=level, certificate='PCA' + str(k), k=k,
                    regions=r, objects_per_region=size, truth_retained_objects=floor,
                    certificate_remaining_objects=remaining, safe_pruned_regions=int(pruned.sum()),
                    safe_pruned_objects=8000000 - remaining, **metrics(remaining, floor, 8000000),
                    bytes_per_region=8 * k, total_metadata_bytes=r * 8 * k,
                    query_projection_coordinate_updates=8 * k * 960, bound_evaluations=8 * r,
                    bound_scalar_ops=(8 * k + 3) * 8 * r + 2 * 8 * k,
                    outward_nextafter_ops=(4 * k + 2) * 8 * r + 2 * 8 * k,
                    metadata_bytes_read_proxy=8 * r * 8 * k,
                    remaining_original_coordinate_updates=remaining * 960,
                    shared_basis_bytes=k * 960 * 8, query_cache_bytes_per_query=k * 8)
                rows.append(row)
                for qi, qid in enumerate(im['queries']):
                    remq = int((~pruned[qi]).sum()) * size; floorq = int(retained[qi].sum()) * size
                    perquery.append(dict(query_id=qid, partition=partition, level=level,
                        certificate='PCA' + str(k), k=k, truth_retained_objects=floorq,
                        certificate_remaining_objects=remq, **metrics(remq, floorq, 1000000)))
                excluding = np.arange(8) != im['queries'].index(660835)
                sensitivity.append(dict(partition=partition, level=level, certificate='PCA' + str(k),
                    k=k, excluded_query=660835, denominator=7000000,
                    **metrics(int((~pruned[excluding]).sum()) * size,
                              int(retained[excluding].sum()) * size, 7000000)))
                widths = hi[:, :k].astype(np.float64) - lo[:, :k].astype(np.float64)
                diagonal = np.sqrt((widths * widths).sum(axis=1))
                compact.append(dict(partition=partition, level=level, k=k,
                    mean_projected_diagonal=float(diagonal.mean()), p50_diagonal=float(np.quantile(diagonal, .5)),
                    p90_diagonal=float(np.quantile(diagonal, .9)), mean_width_by_dim=widths.mean(axis=0).tolist(),
                    scope='stored outward FP32 box widths converted to FP64; region-unweighted mean'))
                payload = serialize(lo, hi, k); name = f'{partition}_L{level}_C{k}.bin'
                (a.out / name).write_bytes(payload)
                restored = np.frombuffer(payload, dtype='<f4').reshape(r, k, 2)
                assert len(payload) == r * 8 * k and np.array_equal(restored[:, :, 0], lo[:, :k])
                assert np.array_equal(restored[:, :, 1], hi[:, :k])
                records[name] = dict(bytes=len(payload), sha256=sha(a.out / name), roundtrip=True, padding_bytes=0)
                if partition == PARTITIONS[0]:
                    b, bq = bridge(level, size, k, lb, old, im)
                    expected = next(x for x in previous if x['family'] == 'PCA' and int(x['level']) == level and int(x['k']) == k)
                    for key, value in b.items():
                        assert (str(value) == expected[key] if isinstance(value, str) else value == float(expected[key])), 'P0 pooled bridge ' + key
                    for v in bq:
                        expectedq = next(x for x in previous_q if x['family'] == 'PCA' and int(x['level']) == level and
                            int(x['k']) == k and int(x['query_id']) == v['query_id'])
                        for key, value in v.items():
                            assert (str(value) == expectedq[key] if isinstance(value, str) else value == float(expectedq[key])), 'P0 query bridge ' + key
                    native_bridge.append(b); native_q.extend(bq)
            near = data[f'near_{level}']; assert np.array_equal(near[0] > 0, retained)
            for fi, factor in enumerate([1., 1.05, 1.10]):
                counts = near[fi][retained].astype(np.int64); fractions = counts / size
                near_summary.append(dict(partition=partition, level=level, factor=factor,
                    truth_retained_regions=len(counts), mean_near_fraction=float(fractions.mean()),
                    p50_near_fraction=float(np.quantile(fractions, .5)), p90_near_fraction=float(np.quantile(fractions, .9)),
                    single_near_region_fraction=float((counts == 1).mean()), total_near_objects=int(counts.sum()),
                    total_far_objects=int(len(counts) * size - counts.sum()), scope='truth-retained query-region pairs only'))
                for qi, ri in np.argwhere(retained):
                    count = int(near[fi, qi, ri])
                    near_rows.append(dict(partition=partition, level=level, query_id=im['queries'][qi],
                        region_index=int(ri), factor=factor, near_objects=count, far_objects=size - count,
                        near_fraction=count / size))
            validation.append(dict(partition=partition, level=level, bounds_checked=8 * r * 2,
                false_topK_prunes=0, bounds_above_truth=0, monotone_C4_C8=True))
    verdict = decide(rows)
    for name, contents in [('per_level_partition_summary.csv', rows), ('per_query_partition_summary.csv', perquery),
                           ('leave_660835_out.csv', sensitivity), ('region_contamination.csv', near_rows),
                           ('contamination_summary.csv', near_summary)]: csv_write(a.out / name, contents)
    save(a.out / 'COMPACTNESS.json', compact)
    save(a.out / 'P0_NATIVE_BRIDGE.json', dict(status='PASS', secondary_only=True,
        primary_native_bound=False, pooled_rows=native_bridge, per_query_rows=native_q,
        all_prior_comparable_fields_identical=True, prior_commit=im['base_commit']))
    save(a.out / 'aggregate_summary.json', dict(base_commit=im['base_commit'], partitions=PARTITIONS,
        levels=list(LEVELS), certificates=['PCA4', 'PCA8'], queries=im['queries'], denominator=8000000,
        primary_native_bound=False, distinct_cells=len(rows), results=rows, **verdict,
        scope='fixed8 queries; offline counts only; no population or latency inference'))
    save(a.out / 'CERTIFICATE_VALIDATION.json', dict(status='PASS', G1_G4='PASS', GPU_used=False,
        bounds_checked=sum(v['bounds_checked'] for v in validation), validations=validation,
        serialized_metadata=records, P0_bridge_pooled_rows=6, P0_bridge_per_query_rows=48))
    print(verdict['decision'])
    for row in rows:
        if row['k'] == 8: print(row['partition'], row['level'], 'alignment', row['alignment_efficiency'])


if __name__ == '__main__': main()
