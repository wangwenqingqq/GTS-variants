#!/usr/bin/env python3
"""Freeze immutable parent ordinals and inherited input identities before outcomes."""
import argparse, json, sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'certified_navigation_20261010'))
from audit import sha, save


def main():
    p = argparse.ArgumentParser(); p.add_argument('--out', type=Path, required=True)
    a = p.parse_args(); a.out.mkdir(parents=True, exist_ok=False)
    previous = HERE.parent / 'certificate_aware_partition_20261012/evidence'
    im = json.loads((previous / 'INPUT_IDENTITY.json').read_text())
    samples = []
    for partition, seed in zip(['ORACLE_ALL8', 'ORACLE_HARD6'], [2026101211, 2026101212]):
        rng = np.random.default_rng(seed)
        for level, count in [(3, 100), (4, 128), (5, 128)]:
            choices = list(range(100)) if level == 3 else sorted(rng.choice(10 ** (level - 1), count, replace=False).tolist())
            samples.extend(dict(partition=partition, child_level=level, parent_id=int(i)) for i in choices)
    save(a.out / 'SAMPLES.json', dict(before_construction=True, outcome_conditioned=False,
         seeds=[2026101211, 2026101212], samples=samples))
    names = ['CONTRACT.json', 'splits.py', 'independent.py', 'freeze.py', 'oracle.py', 'evaluate.py', 'test_oracle.py']
    sources = [HERE / name for name in names] + [HERE.parent / rel for rel in im['sources'] if
               not rel.startswith('certificate_aware_partition_20261012/')]
    sources += [previous / name for name in ['INPUT_IDENTITY.json', 'OUTPUT_MANIFEST.json',
                'PARTITION_AUDIT.json', 'aggregate_summary.json', 'per_query_partition_summary.csv']]
    im.update(base_commit=json.loads((HERE / 'CONTRACT.json').read_text())['base_commit'],
              sources={str(path.relative_to(HERE.parent)): sha(path) for path in sources},
              samples_sha256=sha(a.out / 'SAMPLES.json'), inherited_original_vector_validation=True,
              primary_native_bound=False, secondary_P0_native_bridge=False,
              prior_output_manifest=json.loads((previous / 'OUTPUT_MANIFEST.json').read_text()),
              source_numpy=np.__version__)
    save(a.out / 'INPUT_IDENTITY.json', im)
    save(a.out / 'CANDIDATE_SPLITS.json', json.loads((HERE / 'CONTRACT.json').read_text())['proposal_contract'])
    print('Frozen 712 unique parent/oracle ordinals and source/input hashes before construction')


if __name__ == '__main__': main()
