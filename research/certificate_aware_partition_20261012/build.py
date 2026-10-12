#!/usr/bin/env python3
"""CPU-only construction and independent validation; emits no pruning curves."""
import argparse, hashlib, json, os, resource, struct, sys, time
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'certified_navigation_20261010'))
sys.path.insert(0, str(HERE.parent / 'projection_certificate_20261011'))
from audit import sha, save, load_index
from projection_math import endpoints, exact_gram_bound, ETA, RHO
from build_projection import ordered
from partitions import PARTITIONS, LEVELS, pca_partition, audit


def check_sources(im):
    for name, expected in im['sources'].items():
        assert sha(HERE.parent / name) == expected, 'source drift: ' + name


def original_scores(rows, query):
    total = np.zeros(len(rows), dtype=np.float64)
    for d in range(960):
        delta = rows[:, d].astype(np.float64) - float(query[d])
        square = np.multiply(delta, delta)
        np.add(total, square, out=total)
    return total


def main():
    p = argparse.ArgumentParser()
    for key in ['data', 'index', 'scores', 'projected', 'ancestors', 'prior-intervals', 'freeze', 'out']:
        p.add_argument('--' + key, type=Path, required=True)
    a = p.parse_args(); a.out.mkdir(parents=True, exist_ok=False)
    im = json.loads((a.freeze / 'INPUT_IDENTITY.json').read_text()); check_sources(im)
    assert sha(a.freeze / 'SAMPLES.json') == im['samples_sha256']
    for key in ['data', 'index', 'scores', 'projected', 'ancestors', 'prior_intervals']:
        assert sha(getattr(a, key)) == im[key + '_sha256'], 'input identity mismatch: ' + key
    assert os.environ.get('CUDA_VISIBLE_DEVICES') == ''
    assert len(os.sched_getaffinity(0)) == 1, 'one admitted CPU core required'
    threads = {k: os.environ.get(k) for k in ['OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS']}
    assert all(v == '1' for v in threads.values())
    assert os.getpriority(os.PRIO_PROCESS, 0) >= 10
    started = time.monotonic()
    assert struct.unpack('<3i', a.data.open('rb').read(12)) == (960, 1000000, 2)
    assert a.data.stat().st_size == 3840000012
    assert struct.unpack('<4i', a.scores.open('rb').read(16)) == (1000000, 960, 8, 8)
    assert a.scores.stat().st_size == 64000016 and a.projected.stat().st_size == 128000000
    x = np.memmap(a.data, dtype='<f4', offset=12, mode='r', shape=(1000000, 960))
    scores = np.memmap(a.scores, dtype='<f8', offset=16, mode='r', shape=(8, 1000000))
    z = np.memmap(a.projected, dtype='<f8', mode='r', shape=(1000000, 16))[:, 8:16]
    assert np.isfinite(scores).all() and (scores >= 0).all() and np.isfinite(z).all()
    domain = [float('inf'), -float('inf')]
    for start in range(0, 1000000, 8192):
        block = x[start:start + 8192]; assert np.isfinite(block).all()
        domain = [min(domain[0], float(block.min())), max(domain[1], float(block.max()))]
    assert 0 <= domain[0] <= domain[1] <= 2
    basis = json.loads((HERE.parent / 'projection_certificate_20261011/evidence/BASIS.json').read_text())
    matrix = np.array([[float.fromhex(v) for v in row] for row in basis['families']['PCA']])
    upper, _ = exact_gram_bound(matrix)
    assert upper <= 1 and str(upper) == basis['certificates']['PCA']['exact_gram_infinity_bound']
    ancestors = np.load(a.ancestors); prior = np.load(a.prior_intervals)
    assert [float(u).hex() for u in ancestors['U_star_squared']] == im['U_star_squared_hex']
    for qi in range(8):
        assert np.partition(scores[qi], 7)[7] == ancestors['U_star_squared'][qi]
    t = time.process_time(); wall = time.monotonic()
    n, d, h, ids, nodes, flags = load_index(a.index)
    assert (n, d, h) == (1000000, 960, 6) and not any(flags)
    for level, size in LEVELS.items():
        first = (10 ** level - 1) // 9
        assert all(node[2:4] == (size, ri * size) for ri, node in enumerate(nodes[first:first + 10 ** level]))
    p0 = np.array(ids, dtype=np.int32)
    costs = {PARTITIONS[0]: dict(process_CPU_seconds=time.process_time() - t,
        elapsed_resource_seconds=time.monotonic() - wall, scope='prebuilt index load/audit only; original GTS build unknown',
        sort_count=None, permutation_bytes=p0.nbytes, explicit_peak_scratch_bytes=None)}
    del ids, nodes, flags
    t = time.process_time(); wall = time.monotonic()
    p1 = np.random.default_rng(20261012).permutation(n).astype(np.int32)
    costs[PARTITIONS[1]] = dict(process_CPU_seconds=time.process_time() - t,
        elapsed_resource_seconds=time.monotonic() - wall, scope='random permutation generation',
        sort_count=0, permutation_bytes=p1.nbytes, explicit_peak_scratch_bytes=n * 8,
        scratch_scope='temporary int64 permutation array; excludes allocator internals')
    t = time.process_time(); wall = time.monotonic()
    p2, stats = pca_partition(z)
    costs[PARTITIONS[2]] = dict(process_CPU_seconds=time.process_time() - t,
        elapsed_resource_seconds=time.monotonic() - wall, scope='max-spread recursive partition generation',
        permutation_bytes=p2.nbytes, scratch_scope='largest explicit arrays in one sort, excludes allocator/sort internals', **stats)
    assert stats['sort_count'] == 11111 and stats['sorted_object_occurrences'] == 5000000
    permutations = dict(zip(PARTITIONS, [p0, p1, p2])); ownership = {}
    arrays = {}; pairs = json.loads((a.freeze / 'SAMPLES.json').read_text())['pairs']
    for partition, perm in permutations.items():
        ownership[partition] = audit(perm)
        perm.astype('<i4').tofile(a.out / (partition + '.i32'))
        data = dict(query_projection=z[im['queries']].copy(), U_star_squared=ancestors['U_star_squared'])
        projected_ordered = z[perm]
        for level, size in LEVELS.items():
            group = projected_ordered.reshape(10 ** level, size, 8)
            lo, hi = endpoints(group.min(axis=1), group.max(axis=1))
            truth = np.empty((8, 10 ** level)); near = np.empty((3, 8, 10 ** level), dtype=np.int16)
            for qi in range(8):
                values = scores[qi, perm].reshape(10 ** level, size)
                truth[qi] = values.min(axis=1)
                distances = np.sqrt(values)
                for fi, threshold in enumerate(im['near_threshold_hex'][qi]):
                    near[fi, qi] = (distances <= float.fromhex(threshold)).sum(axis=1)
            data.update({f'low_{level}': lo, f'high_{level}': hi,
                         f'truth_sq_{level}': truth, f'near_{level}': near})
            if partition == PARTITIONS[0]:
                assert lo.tobytes() == prior[f'low_{level}'][:, 8:16].tobytes()
                assert hi.tobytes() == prior[f'high_{level}'][:, 8:16].tobytes()
                assert truth.tobytes() == ancestors[f'truth_sq_{level}'].tobytes()
            assert np.array_equal(truth <= ancestors['U_star_squared'][:, None], near[0] > 0)
        arrays[partition] = data
        np.savez_compressed(a.out / (partition + '.npz'), **data)
        print('Ownership + metadata + reaggregated truth PASS:', partition, flush=True)
    # Freeze concrete membership IDs corresponding to preselected ordinals.
    for pair in pairs:
        start = pair['region_index'] * pair['objects']
        pair['object_ids'] = permutations[pair['partition']][start:start + pair['objects']].tolist()
    save(a.out / 'SAMPLED_MEMBERSHIP.json', dict(pairs=pairs, ordinal_manifest_sha256=im['samples_sha256']))
    selected = sorted({i for pair in pairs for i in pair['object_ids']} | set(im['queries']))
    original = x[selected].copy()
    independent = ordered(original, matrix)
    assert independent.tobytes() == z[selected].tobytes(), 'original-vector projection mismatch'
    positions = {row: j for j, row in enumerate(selected)}
    independent_scores = np.array([original_scores(original, x[q]) for q in im['queries']])
    assert independent_scores.tobytes() == scores[:, selected].tobytes(), 'original score mismatch'
    checks = []
    for pair in pairs:
        ix = [positions[i] for i in pair['object_ids']]
        lo, hi = endpoints(independent[ix].min(axis=0), independent[ix].max(axis=0))
        data = arrays[pair['partition']]; level = pair['level']; ri = pair['region_index']; qi = pair['query_index']
        assert lo.tobytes() == data[f'low_{level}'][ri].tobytes()
        assert hi.tobytes() == data[f'high_{level}'][ri].tobytes()
        assert independent_scores[qi, ix].min() == data[f'truth_sq_{level}'][qi, ri]
        checks.append({k: pair[k] for k in ['partition', 'level', 'query_id', 'region_index', 'objects']})
    # Tiny independent fixture is for portable scalar replay, not a substitute for G4.
    sample = sorted(set(im['queries']) | {p['object_ids'][0] for p in pairs} | {p['object_ids'][-1] for p in pairs})
    np.savez_compressed(a.out / 'replay_vectors.npz', row_ids=np.array(sample, dtype='<i4'),
        vectors=x[sample], projection=z[sample], scores=scores[:, sample])
    save(a.out / 'PARTITION_AUDIT.json', dict(status='PASS', ownership=ownership,
        P0_truth_and_endpoint_byte_bridge=True, exact_contraction_rechecked=True,
        independent_pairs=len(pairs), pairs_per_candidate=128, checks=checks,
        independently_recomputed_unique_objects=len(selected), independent_score_query_object_pairs=8 * len(selected),
        sampled_member_occurrences=sum(p['objects'] for p in pairs), all_objects_in_sampled_regions=True,
        ETA=ETA, RHO=RHO, data_domain=domain, inputs=im, GPU_used=False))
    cpu = next(line.split(':', 1)[1].strip() for line in Path('/proc/cpuinfo').read_text().splitlines() if line.startswith('model name'))
    save(a.out / 'BUILD_RECEIPT.json', dict(CPU=cpu, python=sys.version.split()[0], numpy=np.__version__,
        CPU_affinity_count=1, thread_config=threads, GPU_used=False, costs=costs,
        process_cumulative_peak_RSS_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        peak_scope='entire worker including mapped input data and independent validation, not per-partition scratch',
        elapsed_resource_seconds=time.monotonic() - started, no_latency_measured=True))
    save(a.out / 'OUTPUT_MANIFEST.json', {p.name: dict(sha256=sha(p), bytes=p.stat().st_size)
        for p in sorted(a.out.iterdir()) if p.is_file()})
    print('G1/G3 metadata/G4 PASS; full certificate evaluation not run', flush=True)


if __name__ == '__main__': main()
