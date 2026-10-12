#!/usr/bin/env python3
"""Validate the bounded Gate 0 record, not scientific novelty or GPU correctness."""
import argparse
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

parser = argparse.ArgumentParser()
parser.add_argument('--check-local-sources', action='store_true')
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
ship = [
    '.gitignore', 'README.md', 'CONTRACT.json', 'SEARCH_SCOPE.md',
    'PRIOR_ART_MATRIX.md', 'EVIDENCE_CARDS.md', 'NEAREST_WORK.md',
    'NOVELTY_DECISION.md', 'NEXT_MECHANISM.md', 'CLAIM_EVIDENCE.md',
    'PUBLICATION_GATE.md', 'evidence/SOURCES.json', 'evidence/CARDS.json',
    'evidence/DECISION.json', 'scripts/validate.py',
]
contract = json.loads((root / 'CONTRACT.json').read_text())
sources = json.loads((root / 'evidence/SOURCES.json').read_text())['sources']
cards = json.loads((root / 'evidence/CARDS.json').read_text())
decision = json.loads((root / 'evidence/DECISION.json').read_text())
ids = {s['id'] for s in sources}
assert len(sources) == len(ids) == 13
assert len(cards) == len({c['id'] for c in cards}) == 12
assert {f for c in cards for f in c['family'].split('/')} == {'A', 'B', 'C', 'D'}
assert contract['gpu_process_budget'] == decision['gpu_processes_started'] == 0
assert contract['prototype_budget'] == 0
assert decision['prototype_status'] == 'not implemented'
assert decision['performance_measured'] is False and contract['performance_claims'] is False
assert decision['decision'] == 'CONDITIONAL' and decision['gate0_pass'] is False
assert decision['generic_thesis'] == decision['gpu_only_thesis'] == 'KILL'
assert decision['system_novelty_risk'] == 'HIGH'
assert set(decision['decisive_source_ids']) <= ids
required = {
    'id', 'family', 'index_type', 'exact_or_approximate', 'construction_stages',
    'build_computes_distances', 'distances_reused_for_node_bounds',
    'separate_post_build_refit', 'topology_bound_fusion', 'numeric_contract',
    'safe_interval_certificate', 'nearest_overlap', 'key_difference',
    'novelty_risk', 'material_caveat', 'source_ids', 'locators',
}
card_text = (root / 'EVIDENCE_CARDS.md').read_text()
for c in cards:
    assert set(c) == required
    assert all(isinstance(v, str) and v for k, v in c.items() if k != 'source_ids')
    assert c['source_ids'] and set(c['source_ids']) <= ids
    assert c['novelty_risk'] in {'HIGH', 'MEDIUM', 'LOW'}
    for k in ('build_computes_distances', 'distances_reused_for_node_bounds',
              'topology_bound_fusion', 'safe_interval_certificate'):
        assert c[k] in {'YES', 'PARTIAL', 'NO', 'UNKNOWN'}
    assert c['separate_post_build_refit'] in {'YES', 'NO', 'CONDITIONAL', 'UNKNOWN'}
    assert '## ' + c['id'] + ' — ' in card_text
    assert all(v in card_text for k, v in c.items() if k not in {'id', 'source_ids'})
assert {c['id']: c for c in cards}['karras2012']['separate_post_build_refit'] == 'YES'
checked_bytes = 0
for s in sources:
    assert urlsplit(s['url']).scheme == 'https' and s['checked_sections']
    if 'checked_pdf_pages_1_based' in s:
        assert all(1 <= p <= s['pdf_page_count'] for p in s['checked_pdf_pages_1_based'])
    if s['kind'] == 'official_source':
        assert re.fullmatch(r'[0-9a-f]{40}', s['commit']) and s['commit'] in s['url']
    if s['id'] == 'gpu_kdtree':
        assert s['sha256'] is None and s['bytes'] is None and s['local_filename'] is None
        assert '403' in s['retrieval']
        continue
    assert re.fullmatch(r'[0-9a-f]{64}', s['sha256']) and s['bytes'] > 0
    checked_bytes += 1
    if args.check_local_sources:
        raw = (root / 'local/sources' / s['local_filename']).read_bytes()
        assert len(raw) == s['bytes']
        assert hashlib.sha256(raw).hexdigest() == s['sha256']
assert checked_bytes == 12
baseline = root.parent.parent / 'diagnostics/construction_refit_pair_overlap_20261012/summary/RESULTS.json'
raw = baseline.read_bytes()
assert hashlib.sha256(raw).hexdigest() == contract['baseline_pair_result_sha256']
prior = json.loads(raw)
assert len(prior['rebuilds']) == 2
for r in prior['rebuilds']:
    overlap = r['scoring_vs_refit']
    assert overlap['construction_tasks'] == overlap['refit_tasks'] == 5_000_000
    assert overlap['overlap_over_refit_unique'] == overlap['task_overlap_fraction'] == 1.0
    assert r['multiplicity_equal'] is True
for item in ship:
    text = (root / item).read_text()
    assert not re.search(r'/(?:Users|home)/|gh[pousr]_[A-Za-z0-9]{20,}', text)
    if item.endswith('.md'):
        for target in re.findall(r'\]\(([^)]+)\)', text):
            if not urlsplit(target).scheme:
                assert (root / target.split('#', 1)[0]).exists(), target
for name in ('README.md', 'NOVELTY_DECISION.md', 'CLAIM_EVIDENCE.md'):
    text = (root / name).read_text()
    assert 'CONDITIONAL' in text and 'KILL' in text
print('PASS: 12 complete cards, 13 source records, bounded CONDITIONAL/generic KILL, links, baseline hash, zero-GPU/no-prototype contract.')
if args.check_local_sources:
    print('PASS: all 12 retained primary payload hashes; kd-tree remains explicitly web-only, not hash-verified.')
