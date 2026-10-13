"""Check restricted bound fixtures, provenance and explicit unmeasured outputs."""
import hashlib
import json
import re
import sys
from pathlib import Path

if sys.flags.optimize:
    raise SystemExit('Python optimized mode is unsupported: required checks must run')

from equivalence import check

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    c = read(HERE/'CONTRACT.json'); s = read(HERE/'evidence/SOURCE_FREEZE.json')
    assert sha(HERE/'CONTRACT.json') == s['contract_sha256']
    assert sha(HERE/'equivalence.py') == s['fixture_source_sha256']
    assert sha(HERE/'evidence/BOUND_EQUIVALENCE.json') == s['fixture_receipt_sha256']
    assert sha(HERE/'evidence/SOURCE_IDENTITIES.json') == s['source_review_identity_sha256']
    assert s['parent_files'] == c['parent_files']
    for path, h in {**s['parent_files'], **s.get('inherited_prior_review_files', {})}.items():
        assert sha(ROOT/path) == h, path
    assert check() == read(HERE/'evidence/BOUND_EQUIVALENCE.json')
    closure = read(HERE/'evidence/EXECUTION_CLOSURE.json')
    assert closure['complete'] and closure['parent_files_unchanged']
    assert closure['prior_art_decision'] == 'SUBSUMED'
    assert closure['empirical_training_gate'] == 'NOT_EVALUATED_NOVELTY_STOP'
    assert closure['execution_status'] == 'STOP_BEFORE_TRAINING'
    assert closure['admission_only_final_label'] == 'NO_GO_CERTIFICATE_TRAINING'
    assert closure['quality_cost_effect'] == 'UNKNOWN'
    assert not closure['loss_v0_identity_established']
    assert closure['lambda_selected'] is None and not closure['extra_comparator_or_followon_job_queued']
    for key in ('training_processes','GPU_starts','new_NCU_processes','CIFAR_queries',
                'training_seed_observations','benchmark_figures_generated'):
        assert closure[key] == 0
    for name in ('VANILLA','MRL','CERT'):
        config = read(HERE/f'training/{name}_CONFIG.json')
        assert config['status'] == 'NOT_ADMITTED_NOVELTY_STOP'
        assert config['minimum_requested_seeds'] == 3 and config['embedding_D'] == 512
        assert config['training_processes'] == 0 and config['checkpoint'] is None
        assert not config['operational_protocol_frozen']
    cert = read(HERE/'training/CERT_CONFIG.json')
    assert cert['lambdas'] == [0.1,0.3,1.0] and cert['alpha_weights'] == [4,2,1]
    metrics = {
        'quality/FULL_RETRIEVAL.json':['Recall_at_1','Recall_at_10','mAP'],
        'quality/PREFIX_RETRIEVAL.json':['Recall_at_1'],
        'certificate/REQUIRED_DIMS.json':['mean','median','p90','p95','p99',
            'P1_over_B1_mean_ratio','query_level_mean_p90_ratio','false_rejections'],
        'certificate/SURVIVOR_CURVES.json':['survivor_at_64','survivor_at_128','survivor_at_256'],
        'mechanism/ENERGY_FRONTLOAD.json':['nonhit_d64_over_d512','nonhit_d128_over_d512',
            'nonhit_d256_over_d512','per_dimension_negative_squared_difference_energy'],
        'mechanism/POSITIVE_DAMAGE.json':['hit_prefix_distance','hit_full_distance'],
        'mechanism/COVARIANCE.json':['per_prefix_effective_rank','full_covariance_spectrum','per_dimension_variance'],
    }
    for path, fields in metrics.items():
        row = read(HERE/path)
        assert row['status'] == 'NOT_EXECUTED_NOVELTY_STOP' and row['evidence_state'] == 'unknown'
        assert row['CIFAR_queries'] == row['training_seeds_measured'] == 0
        assert row['per_seed'] == [] and all(row[field] is None for field in fields)
    assert not list((HERE/'figures').glob('*.png'))
    sources = read(HERE/'evidence/SOURCE_IDENTITIES.json')['sources']
    assert len(sources) == 9 and len({x['id'] for x in sources}) == 9
    assert all(x['url'].startswith('https://') and x['bytes'] > 0 and len(x['sha256']) == 64 for x in sources)
    assert next(x for x in sources if x['id'] == 'MRL_CODE')['commit'] == '7ccb42df6be05f3d21d0648aa03099bba46386bf'
    for p in HERE.rglob('*.md'):
        for link in re.findall(r'\]\(([^)]+)\)', p.read_text()):
            if '://' not in link and not link.startswith('#'):
                assert (p.parent/link.split('#')[0]).exists(), (p,link)
    manifest = HERE/'PUBLICATION_SET.json'
    if manifest.exists():
        files = read(manifest)['files']
        actual = [str(p.relative_to(ROOT)) for p in sorted(HERE.rglob('*'))
                  if p.is_file() and p != manifest and '__pycache__' not in p.parts]
        assert [x['path'] for x in files] == actual
        for item in files:
            p = ROOT/item['path']
            assert not p.is_symlink() and p.stat().st_size == item['bytes']
            assert sha(p) == item['sha256']
    print('PASS restricted1600-pair/6400-cutoff fixture, identities, null metrics and admission/effect separation; no training or GPU')


if __name__ == '__main__':
    main()
