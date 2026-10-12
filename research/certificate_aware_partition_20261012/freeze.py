#!/usr/bin/env python3
"""Freeze input/source hashes and region ordinals before constructing candidates."""
import argparse, json, sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'certified_navigation_20261010'))
from audit import sha, save
from partitions import LEVELS, PARTITIONS


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args(); a.out.mkdir(parents=True, exist_ok=False)
    prior = HERE.parent / 'projection_certificate_20261011'
    im = json.loads((prior / 'evidence/INPUT_MANIFEST.json').read_text())
    receipt = json.loads((prior / 'evidence/BUILD_RECEIPT.json').read_text())
    contract = json.loads((HERE / 'CONTRACT.json').read_text())
    ancestor_path = HERE.parent / 'certificate_compression_20261011/local/stageA2/ancestors.npz'
    ancestor = np.load(ancestor_path)
    assert sha(ancestor_path) == im['ancestors_sha256']
    samples = []
    for partition, seed in zip(PARTITIONS[1:], [2026101201, 2026101202]):
        rng = np.random.default_rng(seed)
        for level, count in [(3, 43), (4, 43), (5, 42)]:
            choices = rng.choice(8 * 10 ** level, count, replace=False)
            for value in choices:
                qi, ri = divmod(int(value), 10 ** level)
                samples.append(dict(partition=partition, level=level, query_index=qi,
                    query_id=im['queries'][qi], region_index=ri, objects=LEVELS[level]))
    save(a.out / 'SAMPLES.json', dict(seeds=[2026101201, 2026101202], pairs=samples,
         before_construction=True, outcome_conditioned=False))
    sources = [HERE / x for x in ['CONTRACT.json', 'freeze.py', 'partitions.py',
               'build.py', 'evaluate.py', 'test_partition.py']]
    sources += [prior / 'projection_math.py', prior / 'build_projection.py',
                prior / 'evidence/BASIS.json', prior / 'evidence/per_level_summary.csv',
                prior / 'evidence/per_query_summary.csv',
                HERE.parent / 'certificate_compression_20261011/certificates.py',
                HERE.parent / 'certified_navigation_20261010/audit.py']
    save(a.out / 'INPUT_IDENTITY.json', dict(base_commit=contract['base_commit'], queries=im['queries'],
        data_sha256=im['data_sha256'], index_sha256=im['tree_sha256'],
        scores_sha256=im['prior_scores_sha256'], ancestors_sha256=im['ancestors_sha256'],
        projected_sha256=receipt['projected_sha256'],
        prior_intervals_sha256=sha(prior / 'local/run4/intervals.npz'),
        samples_sha256=sha(a.out / 'SAMPLES.json'),
        sources={str(x.relative_to(HERE.parent)): sha(x) for x in sources},
        U_star_squared_hex=[float(x).hex() for x in ancestor['U_star_squared']],
        near_threshold_hex=[[float(f * np.sqrt(u)).hex() for f in [1., 1.05, 1.10]]
                            for u in ancestor['U_star_squared']],
        source_numpy=np.__version__, primary_native_bound=False, secondary_P0_native_bridge=True))
    print('Frozen: 256 region ordinals, identities, U and diagnostic thresholds; no candidate built')


if __name__ == '__main__': main()
