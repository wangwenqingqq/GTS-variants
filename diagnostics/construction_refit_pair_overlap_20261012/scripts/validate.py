#!/usr/bin/env python3
"""Check curated result/claim consistency without private data or a GPU."""
import csv
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    return json.loads((ROOT/name).read_text())


def main():
    result = load('summary/RESULTS.json')
    assert result['validation']['input_files_verified'] == 190
    assert result['validation']['keeper_files_verified'] == 25
    assert result['validation']['new_gpu_processes'] == 0 and not result['performance_claim']
    assert len(result['rebuilds']) == 2
    for r in result['rebuilds']:
        m, n, o = r['scoring_vs_refit'], r['numeric'], r['owner']
        assert m['construction_tasks'] == m['refit_tasks'] == m['repeated_refit_tasks'] == 5000000
        assert m['construction_unique'] == m['refit_unique'] == m['overlap_unique'] == 4999800
        assert r['multiplicity_equal'] and m['task_overlap_fraction'] == 1
        assert r['boundary_vs_refit']['construction_tasks'] == 111110
        assert r['boundary_vs_refit']['overlap_unique'] == 111108
        assert r['boundary_identity_present_refit_tasks_nonexclusive'] == 111128
        assert r['boundary_is_subset_of_scoring'] and r['scoring_boundary_union_overlap_unique'] == 4999800
        assert o['same_owner_matched_tasks'] == 0 and o['different_owner_matched_tasks'] == 5000000
        assert o['boundary_same_owner_matched_tasks'] == 111110
        assert n['same_numeric_contract_unique'] == 0 and n['convertible_self_pair_unique_optimistic'] == 11109
        assert n['incompatible_nonself_unique'] == 4988691
        assert n['convertible_self_pair_task_optimistic'] == 11111
        assert n['certified_compatible_unique_admission_ceiling_fraction'] == 11109/4999800
        assert 'unknown' in n['per_pair_value_bit_equality']
        assert r['decision'] == 'NO_GO_REUSE' and r['current_scoring_value_survives_to_refit'] == 'NO'
        for row in r['aligned_levels']:
            assert row['construction_level']+1 == row['refit_level']
            assert row['repeated_refit_tasks'] == 1000000 and row['task_overlap_fraction'] == 1
    assert result['rebuilds'][0]['unique_pair_set_sha256'] != result['rebuilds'][1]['unique_pair_set_sha256']
    for name, key in [('LEVELS.csv', 'aligned_levels'), ('LEVEL_MATRIX.csv', 'level_matrix')]:
        with (ROOT/'summary'/name).open() as f:
            actual = list(csv.DictReader(f))
        expected = [{'rebuild': r['rebuild'], **row} for r in result['rebuilds'] for row in r[key]]
        assert actual == [{k: str(v) for k, v in row.items()} for row in expected]
    stages = []
    for r in result['rebuilds']:
        for name, key in [('scoring', 'scoring_vs_refit'), ('boundary', 'boundary_vs_refit')]:
            v = r[key]
            stages.append({'rebuild': r['rebuild'], 'stage': name, 'producer_tasks': v['construction_tasks'],
                           'producer_unique': v['construction_unique'], 'refit_unique_overlap': v['overlap_unique'],
                           'multiplicity_matched_refit_tasks': v['repeated_refit_tasks'],
                           'fraction_of_5M_refit_tasks': v['task_overlap_fraction'],
                           'identity_present_refit_tasks': 5000000 if name == 'scoring' else r['boundary_identity_present_refit_tasks_nonexclusive'],
                           'nonexclusive': True})
    with (ROOT/'summary/STAGES.csv').open() as f:
        assert list(csv.DictReader(f)) == [{k: str(v) for k, v in row.items()} for row in stages]
    inputs = load('evidence/INPUT_MANIFEST.json')['files']
    assert len(inputs) == 190 and len({(r['group'], r['file']) for r in inputs}) == 190
    for row in inputs:
        p = Path(row['file'])
        assert not p.is_absolute() and '..' not in p.parts and len(row['sha256']) == 64
    audit = load('evidence/INDEPENDENT_AUDIT.json')
    assert audit['passed'] and audit['input_files_verified'] == 190
    for r in audit['pair_results']:
        assert r['all_pair_owner_outputs_match'] and r['owner_dictionary_matches']
        assert r['unique'] == 4999800 and r['scoring_same_owner'] == 0
    docs = '\n'.join((ROOT/name).read_text() for name in ['README.md', 'RESULTS.md', 'DECISION.md', 'CLAIM_EVIDENCE.md'])
    for text in ['4,999,800', '5,000,000', '0.22218889%', 'UNKNOWN', 'NO_GO_REUSE']:
        assert text in docs
    assert 'not a mathematical upper bound' in (ROOT/'RESULTS.md').read_text()
    assert 'not measured' in docs or 'No speedup was measured' in docs
    for p in ROOT.rglob('*'):
        if p.is_file() and 'local' not in p.relative_to(ROOT).parts and '__pycache__' not in p.parts:
            text = p.read_text()
            assert not re.search(r'/(?:Users|home/data)/[A-Za-z0-9_.-]+/', text), p
    source = ROOT/'scripts/analyze.py'
    receipt = load('evidence/ANALYSIS_RECEIPT.json')
    assert receipt['analyzer_sha256'] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert receipt['result_sha256'] == hashlib.sha256((ROOT/'summary/RESULTS.json').read_bytes()).hexdigest()
    print('VALIDATION_PASS: exact counts, denominators, contract scope, source hash, and independent audit')


if __name__ == '__main__':
    main()
