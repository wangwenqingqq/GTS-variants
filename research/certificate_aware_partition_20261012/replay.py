#!/usr/bin/env python3
"""Supplementary scalar cross-runtime fixture replay and cached ownership audit."""
import argparse, json, sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'projection_certificate_20261011'))
from build import check_sources
from audit import sha, save
from partitions import PARTITIONS, audit


def main():
    p = argparse.ArgumentParser()
    for key in ['freeze', 'run', 'out']: p.add_argument('--' + key, type=Path, required=True)
    a = p.parse_args(); im = json.loads((a.freeze / 'INPUT_IDENTITY.json').read_text()); check_sources(im)
    om = json.loads((a.run / 'OUTPUT_MANIFEST.json').read_text())
    for name, entry in om.items(): assert sha(a.run / name) == entry['sha256']
    for partition in PARTITIONS:
        perm = np.fromfile(a.run / (partition + '.i32'), dtype='<i4'); audit(perm)
        if partition == PARTITIONS[1]:
            assert np.array_equal(perm, np.random.default_rng(20261012).permutation(1000000))
    membership = json.loads((a.run / 'SAMPLED_MEMBERSHIP.json').read_text())
    frozen = json.loads((a.freeze / 'SAMPLES.json').read_text())
    assert membership['ordinal_manifest_sha256'] == im['samples_sha256']
    assert len(membership['pairs']) == len(frozen['pairs']) == 256
    for pair, original in zip(membership['pairs'], frozen['pairs']):
        assert {k: pair[k] for k in original} == original
        perm = np.fromfile(a.run / (pair['partition'] + '.i32'), dtype='<i4')
        start = pair['region_index'] * pair['objects']
        assert pair['object_ids'] == perm[start:start + pair['objects']].tolist()
    fixture = np.load(a.run / 'replay_vectors.npz'); x = fixture['vectors']; ids = fixture['row_ids'].tolist()
    b = json.loads((HERE.parent / 'projection_certificate_20261011/evidence/BASIS.json').read_text())
    matrix = [[float.fromhex(v) for v in row] for row in b['families']['PCA']]
    projection = np.zeros((len(x), 8)); scores = np.zeros((8, len(x)))
    for ri, row in enumerate(x):
        values = list(map(float, row))
        for j, direction in enumerate(matrix):
            total = 0.
            for value, weight in zip(values, direction):
                term = value * weight; total = total + term
            projection[ri, j] = total
        for qi, qid in enumerate(im['queries']):
            total = 0.
            for value, qvalue in zip(values, x[ids.index(qid)]):
                delta = value - float(qvalue); square = delta * delta; total = total + square
            scores[qi, ri] = total
    assert projection.tobytes() == fixture['projection'].tobytes()
    assert scores.tobytes() == fixture['scores'].tobytes()
    save(a.out, dict(status='PASS', rows=len(x), scalar_projection_values=len(x) * 8,
        scalar_score_query_object_pairs=len(x) * 8, bitwise_equal=True,
        ownership_partitions_rechecked=3, random_partition_independently_regenerated=True,
        frozen_sample_membership_rechecked=256, python=sys.version.split()[0], numpy=np.__version__,
        source_sha256=sha(Path(__file__)), fixture_sha256=sha(a.run / 'replay_vectors.npz'),
        scope='small scalar cross-runtime fixture; full original-vector256-pair G4 was separate remote gate'))
    print('PASS: scalar projection/scores, ownership, frozen membership and P1 regeneration')


if __name__ == '__main__': main()
