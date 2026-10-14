"""Verify the exact public subset, reconstruct scalar decisions, and run CPU fixtures; no GPU."""
if not __debug__:
    raise SystemExit('Optimized Python disables mandatory checks; run without -O/PYTHONOPTIMIZE.')
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent


def load(path):
    return json.loads(Path(path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True, help='Fresh task-owned validation scratch')
    a = p.parse_args()
    assert (a.repo / 'artifacts/exact_gpu_limits_gate1_20261014').resolve() == HERE
    manifest = load(HERE / 'PUBLIC_MANIFEST.json')['files']
    files = {str(f.relative_to(HERE)): f for f in HERE.rglob('*') if f.is_file() and f.name != 'PUBLIC_MANIFEST.json'}
    assert set(files) == set(manifest), ('file set mismatch', set(files) ^ set(manifest))
    for name, record in manifest.items():
        assert files[name].stat().st_size == record['bytes'] and sha(files[name]) == record['sha256'], name
    c = load(HERE / 'CONTRACT.json')
    for name, digest in c['parents'].items():
        assert sha(a.repo / name) == digest, ('parent drift', name)
    for name, digest in load(HERE / 'evidence/ADDITIONAL_PARENT_IDENTITIES.json')['files'].items():
        assert sha(a.repo / name) == digest, name
    identity = load(HERE / 'evidence/EXECUTION.json')
    for name, digest in identity['executed_source_hashes'].items():
        assert sha(HERE / name) == digest, ('executed source drift', name)
    assert identity['GPU_starts'] == 0 and identity['full_population_coordinators'] == 1
    assert identity['full_score_bit_mismatches'] == identity['safe_false_rejections'] == 0
    assert load(HERE / 'evidence/ANALYSIS.json')['results_sha256'] == identity['private_results_sha256']
    assert len(load(HERE / 'evidence/RAW_MANIFEST.json')['files']) == 32 * 7
    a.out.mkdir(parents=True, exist_ok=False)
    env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'OPENBLAS_NUM_THREADS': '1', 'OMP_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1'}

    def run(args, **kwargs):
        subprocess.run(args, check=True, env=env, **kwargs)

    analysis_out = a.out / 'analysis'
    analysis_command = [sys.executable, str(HERE / 'analyze.py'), '--repo', str(a.repo), '--results', str(HERE / 'evidence/SCALARS.json'), '--out', str(analysis_out)]
    run(analysis_command)
    reconstructed = 0
    for path in analysis_out.rglob('*.json'):
        actual, expected = load(path), load(HERE / path.relative_to(analysis_out))
        if path.name == 'ANALYSIS.json':
            # A public scalar input has a different hash from the private result with wall-clock logs.
            actual.pop('results_sha256')
            expected.pop('results_sha256')
        assert actual == expected, ('reconstruction mismatch', path.name)
        reconstructed += 1
    report_out = a.out / 'report'
    run([sys.executable, str(HERE / 'report.py'), '--repo', str(a.repo), '--data', str(HERE), '--out', str(report_out)])
    for path in report_out.rglob('*'):
        if path.is_file():
            assert path.read_bytes() == (HERE / path.relative_to(report_out)).read_bytes(), path
    before = {name: sha(path) for name, path in files.items()}
    rejected = subprocess.run(analysis_command, env=env, capture_output=True)
    assert rejected.returncode != 0 and b'FileExistsError' in rejected.stderr
    for name in ('run.py', 'analyze.py', 'plot.py', 'report.py', 'verify.py', 'test_oracles.py', 'test_models.py'):
        result = subprocess.run([sys.executable, '-O', str(HERE / name)], env=env, capture_output=True)
        assert result.returncode != 0 and b'Optimized Python disables mandatory checks' in result.stderr, name
    compiler = shutil.which('c++')
    assert compiler, 'Installed C++ compiler required; do not install one automatically.'
    library = a.out / 'oracles.so'
    run([compiler, *c['compiler_flags'], str(HERE / 'oracles.cpp'), '-o', str(library)])
    subprocess.run([sys.executable, '-m', 'unittest', '-v', 'test_oracles', 'test_models'], cwd=HERE,
                   env={**env, 'ORACLES_LIBRARY': str(library.resolve())}, check=True)
    assert before == {name: sha(path) for name, path in files.items()}, 'Verification mutated source artifact'
    receipt = {'passed': True, 'files': len(files) + 1, 'JSON_reconstructions': reconstructed,
               'CPU_fixtures_and_model_tests': 7, 'GPU_starts': 0, 'population_rerun': False,
               'output_overwrite_rejected': True, 'optimized_Python_rejected': True,
               'public_manifest_sha256': sha(HERE / 'PUBLIC_MANIFEST.json')}
    (a.out / 'RECEIPT.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
