"""Verify the scoped Phase A artifact and rational witness; no population or GPU."""
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
    assert (a.repo/'artifacts/query_block_order_gate2_20261014').resolve() == HERE
    manifest = load(HERE/'PUBLIC_MANIFEST.json')['files']
    files = {str(f.relative_to(HERE)): f for f in HERE.rglob('*') if f.is_file() and f.name != 'PUBLIC_MANIFEST.json'}
    assert set(files) == set(manifest)
    for name, record in manifest.items():
        assert sha(files[name]) == record['sha256'] and files[name].stat().st_size == record['bytes'], name
        assert files[name].suffix in ('.json', '.md', '.py'), 'No third-party PDF/source or data/figure redistribution'
    contract = load(HERE/'CONTRACT.json')
    for name, digest in contract['parents'].items():
        assert sha(a.repo/name) == digest, ('parent drift', name)
    admission = load(HERE/'evidence/ADMISSION.json')
    assert admission['final'] == 'SUBSUMED_MECHANISM' and admission['contract_sha256'] == sha(HERE/'CONTRACT.json')
    assert admission['literal_second_moment_formula_in_BOND_PDX'] == 'NOT_ESTABLISHED'
    assert admission['CPU_population_starts'] == admission['GPU_starts'] == admission['NCU_starts'] == 0
    assert admission['new_real_dataset_loaded'] is False and admission['phases']['B'] == admission['phases']['C'] == 'NOT_RUN'
    historical = [('logical/ORIGINAL.json', 'artifacts/exact_gpu_limits_gate1_20261014/b1_information_floor/ORIGINAL_ORDER.json', 'mean'),
                  ('logical/DIM_ORACLE.json', 'artifacts/exact_gpu_limits_gate1_20261014/b1_information_floor/QUERY_GLOBAL_ORACLE.json', 'nominal')]
    for dest, source, key in historical:
        value = load(a.repo/source)
        mean = value['mean'] if key == 'mean' else value[key]['mean']
        current = load(HERE/dest)
        assert current['mean'] == mean and current['status'] == 'HISTORICAL_REFERENCE_ONLY'
        assert current['block32_rounded_mean'] is None and current['new_population_run'] is False
    for name in ('BLOCK_ORACLE', 'QBLOCK32'):
        value = load(HERE/'logical'/f'{name}.json')
        assert value['status'] == 'NOT_RUN' and value['tested_real_pairs'] == 0
        assert all(value[k] is None for k in ('mean', 'p50', 'p90', 'p95', 'p99', 'false_rejections', 'full_score_bit_mismatches'))
    assert load(HERE/'source/COORDINATE_BYTES.json')['candidate_bytes_per_query'] is None
    assert load(HERE/'source/SECTOR_MODEL.json')['sector_amplification'] is None
    assert load(HERE/'updates/STATS_MAINTENANCE.json')['query_overhead'] is None
    expected = witness()
    expected['contract_sha256'] = sha(HERE/'CONTRACT.json')
    expected['executed_source_sha256'] = sha(HERE/'kill_test.py')
    assert expected == load(HERE/'evidence/FORMULA_WITNESS.json')
    a.out.mkdir(parents=True, exist_ok=False)
    env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'}
    command = [sys.executable, str(HERE/'kill_test.py'), '--out', str(a.out/'witness.json')]
    subprocess.run(command, env=env, check=True)
    assert load(a.out/'witness.json') == expected
    rejected = subprocess.run(command, env=env, capture_output=True)
    assert rejected.returncode != 0 and b'FileExistsError' in rejected.stderr
    for name in ('kill_test.py', 'verify.py'):
        rejected = subprocess.run([sys.executable, '-O', str(HERE/name)], env=env, capture_output=True)
        assert rejected.returncode != 0 and b'Optimized Python disables mandatory checks' in rejected.stderr
    assert all(sha(files[name]) == record['sha256'] for name, record in manifest.items())
    receipt = {'passed': True, 'public_files': len(files)+1, 'parent_files': len(contract['parents']),
               'rational_checks': 3, 'source_identity_and_NOT_RUN_semantics': True,
               'optimized_Python_rejected': True, 'overwrite_rejected': True,
               'real_population_or_GPU_started': False, 'public_manifest_sha256': sha(HERE/'PUBLIC_MANIFEST.json')}
    (a.out/'RECEIPT.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
