#!/usr/bin/env python3
"""Full fixed-PCA8 12-cell matrix, safety, baseline bridge and diagnostics."""
import argparse, csv, gzip, json, sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
from oracle import check_sources, csv_write
from splits import LEVELS, PARTITIONS, decision
from projection_math import prefix_bounds, serialize
from audit import sha, save


def main():
    p = argparse.ArgumentParser()
    for key in ['freeze', 'run', 'out']: p.add_argument('--' + key, type=Path, required=True)
    a = p.parse_args(); a.out.mkdir(parents=True, exist_ok=False)
    im = json.loads((a.freeze / 'INPUT_IDENTITY.json').read_text()); check_sources(im)
    assert sha(a.freeze / 'SAMPLES.json') == im['samples_sha256']
    om = json.loads((a.run / 'OUTPUT_MANIFEST.json').read_text())
    for name, entry in om.items(): assert sha(a.run / name) == entry['sha256']
    gate = json.loads((a.run / 'PARTITION_AUDIT.json').read_text())
    assert gate['status'] == 'PASS' and gate['inputs'] == im and gate['G4_pairs'] == 712
    old_summary = json.loads((HERE.parent / 'certificate_aware_partition_20261012/evidence/aggregate_summary.json').read_text())
    with (HERE.parent / 'certificate_aware_partition_20261012/evidence/per_query_partition_summary.csv').open() as f:
        old_q = list(csv.DictReader(f))
    rows = []; queries = []; near_rows = []; near_summary = []; sensitivity = []; validations = []; records = {}
    for partition in PARTITIONS:
        d = np.load(a.run / (partition + '.npz')); usq = d['U_star_squared']; u = np.sqrt(usq)
        assert [float(v).hex() for v in usq] == im['U_star_squared_hex']
        for level, size in LEVELS.items():
            r = 10 ** level; lo = d[f'low_{level}']; hi = d[f'high_{level}']; truthsq = d[f'truth_sq_{level}']
            truth = truthsq <= usq[:, None]
            bounds = np.array([prefix_bounds(lo, hi, q)[8] for q in d['query_projection']])
            assert np.all(bounds <= np.sqrt(truthsq)), 'bound exceeds truth'
            pruned = bounds > u[:, None]; assert not np.any(pruned & truth), 'false topK prune'
            rem = int((~pruned).sum()) * size; floor = int(truth.sum()) * size
            hardrem = int((~pruned[2:]).sum()) * size; hardfloor = int(truth[2:].sum()) * size
            row = dict(partition=partition, level=level, certificate='PCA8', regions=r, objects_per_region=size,
                truth_retained_objects=floor, certificate_remaining_objects=rem, safe_pruned_objects=8000000 - rem,
                alignment=(8000000 - rem) / (8000000 - floor), truth_residual=floor / 8000000,
                certificate_residual=rem / 8000000, hard_truth_retained_objects=hardfloor,
                hard_certificate_remaining_objects=hardrem, hard_alignment=(6000000 - hardrem) / (6000000 - hardfloor),
                hard_truth_residual=hardfloor / 6000000, hard_certificate_residual=hardrem / 6000000,
                bytes_per_region=64, total_metadata_bytes=r * 64, bound_evaluations=8 * r)
            rows.append(row)
            if partition in PARTITIONS[:2]:
                old = next(x for x in old_summary['results'] if x['partition'] == partition and x['level'] == level and x['k'] == 8)
                for k in ['truth_retained_objects', 'certificate_remaining_objects', 'safe_pruned_objects', 'truth_residual', 'certificate_residual']:
                    assert row[k] == old[k], 'P0/P2 pooled count/residual bridge: ' + k
                assert row['alignment'] == old['alignment_efficiency']
            for qi, qid in enumerate(im['queries']):
                rq = int((~pruned[qi]).sum()) * size; fq = int(truth[qi].sum()) * size
                qq = dict(query_id=qid, partition=partition, level=level, alignment=(1000000 - rq) / (1000000 - fq),
                    truth_residual=fq / 1000000, certificate_residual=rq / 1000000,
                    truth_retained_objects=fq, certificate_remaining_objects=rq,
                    hard_query=qi >= 2, exception_query_660835=qid == 660835)
                queries.append(qq)
                if partition in PARTITIONS[:2]:
                    prev = next(x for x in old_q if x['partition'] == partition and int(x['level']) == level and int(x['k']) == 8 and int(x['query_id']) == qid)
                    for k in ['truth_retained_objects', 'certificate_remaining_objects', 'truth_residual', 'certificate_residual']:
                        assert qq[k] == float(prev[k]), 'P0/P2 per-query bridge: ' + k
                    assert qq['alignment'] == float(prev['alignment_efficiency'])
            remain7 = int((~pruned[1:]).sum()) * size; floor7 = int(truth[1:].sum()) * size
            sensitivity.append(dict(partition=partition, level=level, excluded_query=660835, denominator=7000000,
                alignment=(7000000 - remain7) / (7000000 - floor7), certificate_remaining_objects=remain7, truth_retained_objects=floor7))
            near = d[f'near_{level}']; assert np.array_equal(near[0] > 0, truth)
            for fi, factor in enumerate([1., 1.05, 1.10]):
                values = near[fi][truth].astype(np.int64); fractions = values / size
                near_summary.append(dict(partition=partition, level=level, factor=factor,
                    truth_retained_regions=len(values), total_near_objects=int(values.sum()),
                    total_far_objects=int(len(values) * size - values.sum()), mean_near_fraction=float(fractions.mean()),
                    p50_near_fraction=float(np.quantile(fractions, .5)), p90_near_fraction=float(np.quantile(fractions, .9)),
                    single_near_region_fraction=float((values == 1).mean()), scope='truth-retained query-region pairs only'))
                for qi, ri in np.argwhere(truth):
                    count = int(near[fi, qi, ri]); near_rows.append(dict(partition=partition, level=level,
                        query_id=im['queries'][qi], region_index=int(ri), factor=factor, near_objects=count, far_objects=size - count))
            payload = serialize(lo, hi, 8); restored = np.frombuffer(payload, dtype='<f4').reshape(r, 8, 2)
            assert len(payload) == 64 * r and np.array_equal(restored[:, :, 0], lo) and np.array_equal(restored[:, :, 1], hi)
            records[f'{partition}_L{level}'] = dict(bytes=len(payload), sha256=__import__('hashlib').sha256(payload).hexdigest(), roundtrip=True)
            validations.append(dict(partition=partition, level=level, bounds_checked=8 * r, bounds_above_truth=0, false_topK_prunes=0))
    baseline = {x['level']: x for x in rows if x['partition'] == 'PCA_BALANCED'}
    for row in rows:
        row['oracle_split_gain'] = row['alignment'] - baseline[row['level']]['alignment']
        row['hard_oracle_split_gain'] = row['hard_alignment'] - baseline[row['level']]['hard_alignment']
    regret = []; frequency = []
    with (a.run / 'parent_split_regret.csv').open() as f: parents = list(csv.DictReader(f))
    with gzip.open(a.run / 'proposal_scores.csv.gz', 'rt') as f: scores = list(csv.DictReader(f))
    assert len(parents) == 22222 and len(scores) == 266664
    # Recompute every recorded selection from the entire retained score table.
    for index, parent in enumerate(parents):
        ss = scores[index * 12:(index + 1) * 12]
        field = 'score_all' if parent['partition'] == 'ORACLE_ALL8' else 'score_hard'
        values = [int(x[field]) for x in ss]; best = max(values); selected = values.index(best)
        assert all(x['partition'] == parent['partition'] and x['parent_id'] == parent['parent_id'] and x['child_level'] == parent['child_level'] for x in ss)
        assert int(parent['oracle_proposal']) == selected and int(parent['regret']) == best - values[0]
    for partition in PARTITIONS[2:]:
        for level in range(1, 6):
            selected = [x for x in parents if x['partition'] == partition and int(x['child_level']) == level]
            values = np.array([int(x['regret']) for x in selected]); normalized = np.array([float(x['normalized_regret']) for x in selected])
            regret.append(dict(partition=partition, child_level=level, parents=len(selected),
                mean=float(values.mean()), median=float(np.median(values)), p90=float(np.quantile(values, .9)),
                fraction_zero_regret=float((values == 0).mean()), mean_normalized=float(normalized.mean()),
                p90_normalized=float(np.quantile(normalized, .9)),
                mean_unique_proposal_orders=float(np.mean([int(x['unique_proposal_orders']) for x in selected])),
                fraction_best_score_ties=float(np.mean([int(x['tied_best_proposals']) > 1 for x in selected]))))
            for s in range(12):
                count = sum(int(x['oracle_proposal']) == s for x in selected)
                frequency.append(dict(partition=partition, child_level=level, proposal=s, parents=len(selected), selected_count=count, fraction=count / len(selected)))
    for name, contents in [('per_level_summary.csv', rows), ('per_query_alignment.csv', queries),
          ('leave_660835_out.csv', sensitivity), ('region_contamination.csv', near_rows),
          ('contamination_summary.csv', near_summary), ('regret_summary.csv', regret), ('proposal_frequency.csv', frequency)]: csv_write(a.out / name, contents)
    verdict = decision(rows)
    save(a.out / 'aggregate_summary.json', dict(base_commit=im['base_commit'], certificate='PCA8', partitions=PARTITIONS,
        levels=list(LEVELS), queries=im['queries'], all_denominator=8000000, hard_denominator=6000000,
        distinct_cells=len(rows), per_query_rows=len(queries), primary_native_bound=False, results=rows, **verdict,
        scope='fixed-query local-greedy oracle diagnostic; NOT global family upper bound or deployable latency'))
    save(a.out / 'CERTIFICATE_VALIDATION.json', dict(status='PASS', G1_G4='PASS', GPU_used=False,
        bounds_checked=sum(x['bounds_checked'] for x in validations), validations=validations,
        serialized_metadata=records, baseline_pooled_rows_identical=6, baseline_per_query_rows_identical=48,
        all_parent_argmax_records_replayed=22222))
    print(json.dumps(verdict)); print('\n'.join(f"{r['partition']} L{r['level']} all={r['alignment']:.9f} hard={r['hard_alignment']:.9f}" for r in rows))


if __name__ == '__main__': main()
