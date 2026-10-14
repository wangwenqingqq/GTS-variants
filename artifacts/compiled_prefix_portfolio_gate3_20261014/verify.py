"""Verify Phase A closure and rational accounting;no candidate or GPU execution."""
if not __debug__:
    raise SystemExit('Optimized Python disables mandatory checks; run without -O/PYTHONOPTIMIZE.')
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from kill_test import witness

HERE = Path(__file__).resolve().parent


def load(path):
    return json.loads(Path(path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True, help='Fresh task-owned verification scratch')
    a = p.parse_args()
    assert (a.repo/'artifacts/compiled_prefix_portfolio_gate3_20261014').resolve() == HERE
    manifest = load(HERE/'PUBLIC_MANIFEST.json')['files']
    files = {str(f.relative_to(HERE)): f for f in HERE.rglob('*') if f.is_file() and f.name != 'PUBLIC_MANIFEST.json'}
    assert set(files) == set(manifest)
    for name, record in manifest.items():
        assert not files[name].is_symlink() and sha(files[name]) == record['sha256']
        assert files[name].stat().st_size == record['bytes'] and files[name].suffix in ('.json', '.md', '.py')
    c = load(HERE/'CONTRACT.json')
    for name, digest in c['parents'].items():
        assert sha(a.repo/name) == digest, ('parent drift', name)
    admission = load(HERE/'evidence/ADMISSION.json')
    execution = load(HERE/'evidence/EXECUTION.json')
    assert admission['final'] == 'SUBSUMED_PORTFOLIO'
    assert admission['literal_CPV4_implementation_in_prior_art'] == 'NOT_ESTABLISHED'
    assert admission['primary_admission_sha256'] == sha(HERE/'PRIOR_ART.md')
    for record in (admission, execution):
        assert record['contract_sha256'] == sha(HERE/'CONTRACT.json')
        assert record['population_starts'] == record['GPU_starts'] == record['NCU_starts'] == 0
    for name, digest in execution['source_hashes'].items():
        assert sha(HERE/name) == digest, ('executed source drift', name)
    assert execution['cost_witness_sha256'] == sha(HERE/'evidence/COST_WITNESS.json')
    qids = load(a.repo/'artifacts/exact_gpu_limits_gate1_20261014/CONTRACT.json')['qids']
    split = load(HERE/'splits/FOLDS.json')
    assert split['tested_real_pairs'] == 0 and len(split['folds']) == 4
    held_out = []
    for f, record in enumerate(split['folds']):
        test = [i for i in range(32) if i % 4 == f]
        train = [i for i in range(32) if i % 4 != f]
        assert record['fold'] == f and record['test_indices'] == test and record['train_indices'] == train
        assert record['train_qids'] == [qids[i] for i in train] and record['test_qids'] == [qids[i] for i in test]
        assert len(train) == 24 and len(test) == 8 and not set(train).intersection(test)
        held_out += test
    assert sorted(held_out) == list(range(32))
    untested = {'compile/CANDIDATE_PREFIXES.json': ('candidates',),
                'compile/PORTFOLIOS.json': ('portfolios',),
                'capacity/ORACLE_ROUTE.json': ('mean_bytes', 'p50_bytes', 'p90_bytes', 'max_bytes', 'routes'),
                'capacity/SURVIVORS.json': ('oracle_survivors', 'moment_survivors'),
                'routing/DATASET_MOMENTS.json': ('mu', 'nu'),
                'routing/MOMENT_ROUTE.json': ('routes', 'mean_bytes', 'p90_bytes', 'online_latency', 'quality'),
                'routing/REGRET.json': ('survivor_regret', 'mean_per_query_bytes_regret'),
                'quality/EXACTNESS.json': ('false_rejections', 'false_positives', 'full_score_bit_mismatches')}
    for name, keys in untested.items():
        record = load(HERE/name)
        assert record['status'] == 'NOT_RUN' and all(record[k] is None for k in keys), name
    assert load(HERE/'cost/SOURCE_BYTES.json')['candidate_mean_bytes'] is None
    assert load(HERE/'cost/STORAGE.json')['actual_allocated_bytes'] is None
    assert load(HERE/'cost/UPDATE_PAYLOAD.json')['actual_operation_latency'] is None
    expected = witness()
    expected['contract_sha256'] = sha(HERE/'CONTRACT.json')
    expected['executed_source_sha256'] = sha(HERE/'kill_test.py')
    assert expected == load(HERE/'evidence/COST_WITNESS.json')
    a.out.mkdir(parents=True, exist_ok=False)
    env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'}
    command = [sys.executable, str(HERE/'kill_test.py'), '--out', str(a.out/'witness.json')]
    subprocess.run(command, env=env, check=True)
    assert load(a.out/'witness.json') == expected
    refused = subprocess.run(command, env=env, capture_output=True)
    assert refused.returncode != 0 and b'FileExistsError' in refused.stderr
    optimized_checks = 0
    for name in ('kill_test.py', 'verify.py'):
        for mode in ('-O', '-OO', 'PYTHONOPTIMIZE'):
            run_env = env.copy()
            argv = [sys.executable, str(HERE/name)]
            if mode == 'PYTHONOPTIMIZE':
                run_env['PYTHONOPTIMIZE'] = '1'
            else:
                argv.insert(1, mode)
            refused = subprocess.run(argv, env=run_env, capture_output=True)
            assert refused.returncode != 0 and b'Optimized Python disables mandatory checks' in refused.stderr
            optimized_checks += 1
    assert all(sha(files[name]) == record['sha256'] for name, record in manifest.items())
    receipt = {'passed': True, 'public_files': len(files)+1, 'parent_files': len(c['parents']),
               'folds_checked': 4, 'held_out_definition_only': True, 'exact_rational_accounting': True,
               'NOT_RUN_metrics_preserved': True, 'optimized_checks': optimized_checks,
               'overwrite_rejected': True, 'real_population_or_GPU_started': False,
               'public_manifest_sha256': sha(HERE/'PUBLIC_MANIFEST.json')}
    (a.out/'RECEIPT.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
