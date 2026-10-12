#!/usr/bin/env python3
"""Portable independent integer-count/argmax replay of public evidence (no caches)."""
import argparse, csv, gzip, json, math
from fractions import Fraction
from pathlib import Path


def main():
    p = argparse.ArgumentParser(); p.add_argument('--evidence', type=Path, required=True)
    a = p.parse_args(); e = a.evidence
    with (e / 'per_query_alignment.csv').open() as f: qs = list(csv.DictReader(f))
    summary = json.loads((e / 'aggregate_summary.json').read_text())
    assert len(qs) == 96 and len(summary['results']) == 12
    ratio = {}
    for row in summary['results']:
        matching = [r for r in qs if r['partition'] == row['partition'] and int(r['level']) == row['level']]
        assert len(matching) == 8 and len({r['query_id'] for r in matching}) == 8
        for hard, total in [(False, 8000000), (True, 6000000)]:
            selected = [r for r in matching if not hard or r['hard_query'] == 'True']
            assert len(selected) == (6 if hard else 8)
            remaining = sum(int(r['certificate_remaining_objects']) for r in selected)
            truth = sum(int(r['truth_retained_objects']) for r in selected)
            prefix = 'hard_' if hard else ''
            assert remaining == row[prefix + 'certificate_remaining_objects'] and truth == row[prefix + 'truth_retained_objects']
            value = Fraction(total - remaining, total - truth)
            assert float(value) == row['hard_alignment' if hard else 'alignment']
            ratio[(row['partition'], row['level'], hard)] = value
        for q in matching:
            rem = int(q['certificate_remaining_objects']); floor = int(q['truth_retained_objects'])
            assert 0 <= floor <= rem <= 1000000 and float(Fraction(1000000 - rem, 1000000 - floor)) == float(q['alignment'])
    parents = 0; proposals = 0
    with (e / 'parent_split_regret.csv').open() as pf, gzip.open(e / 'proposal_scores.csv.gz', 'rt') as sf:
        pp = csv.DictReader(pf); ss = iter(csv.DictReader(sf))
        for parent in pp:
            rows = [next(ss) for _ in range(12)]; parents += 1; proposals += 12
            for i, row in enumerate(rows):
                assert int(row['proposal']) == i and all(row[k] == parent[k] for k in ['partition', 'child_level', 'parent_id'])
                values = [int(row[f'q{q}_pruned_objects']) for q in range(8)]; n = int(parent['object_count'])
                assert all(0 <= v <= n and v % (n // 10) == 0 for v in values)
                assert sum(values) == int(row['score_all']) and sum(values[2:]) == int(row['score_hard'])
            field = 'score_all' if parent['partition'] == 'ORACLE_ALL8' else 'score_hard'
            scores = [int(r[field]) for r in rows]; selected = scores.index(max(scores))
            assert selected == int(parent['oracle_proposal'])
            assert scores[0] == int(parent['baseline_score']) and scores[selected] == int(parent['oracle_score'])
            regret = max(scores) - scores[0]; assert regret == int(parent['regret'])
            assert float(parent['normalized_regret']) == regret / (int(parent['object_count']) * (8 if field == 'score_all' else 6))
            assert int(parent['hard_query_gain']) == int(rows[selected]['score_hard']) - int(rows[0]['score_hard'])
            assert int(parent['all_query_gain']) == int(rows[selected]['score_all']) - int(rows[0]['score_all'])
            assert int(parent['tied_best_proposals']) == scores.count(max(scores))
        assert next(ss, None) is None
    assert parents == 22222 and proposals == 266664
    def get(part, level, hard): return ratio[(part, level, hard)]
    high = [l for l in [3, 4] if get('ORACLE_HARD6', l, True) >= Fraction(3, 5) and
            get('ORACLE_HARD6', l, True) - get('PCA_BALANCED', l, True) >= Fraction(1, 4)]
    strong = [l for l in high if get('ORACLE_HARD6', l, True) >= Fraction(7, 10) and get('ORACLE_ALL8', l, False) >= Fraction(3, 5)]
    low = max(get('ORACLE_HARD6', l, True) for l in [3, 4]) < Fraction(2, 5)
    easy = low and max(get('ORACLE_ALL8', l, False) for l in [3, 4]) >= Fraction(3, 5)
    verdict = 'CERTIFICATE_EFFECTIVENESS_CONSTRUCTION_SUPPORTED' if strong else 'SPLIT_OBJECTIVE_HEADROOM_HIGH' if high else 'EASY_QUERY_ONLY' if easy else 'LINEAR_SPLIT_OBJECTIVE_HEADROOM_LOW' if low else 'INSUFFICIENT_EVIDENCE'
    assert verdict == summary['decision'] and high == summary['promotion_levels'] and strong == summary['strong_levels']
    print(json.dumps(dict(status='PASS', primary_cells=12, per_query_rows=96, parent_argmax_rows=parents,
        proposal_score_rows=proposals, exact_count_decision=verdict,
        scope='public integer accounting and lowest-ID argmax; not a substitute for independent geometry G4 or original-vector validation')))


if __name__ == '__main__': main()
