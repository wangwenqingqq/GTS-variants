#!/usr/bin/env python3
"""One-core offline construction; full candidate safety and independent G4."""
import argparse, csv, gzip, hashlib, io, json, os, resource, shutil, struct, sys, time
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'certified_navigation_20261010'))
sys.path.insert(0, str(HERE.parent / 'certificate_aware_partition_20261012'))
from partitions import pca_partition, audit
from splits import candidates, score_proposals, LEVELS, PARTITIONS
from independent import enumerate_scores
from projection_math import endpoints, exact_gram_bound, ETA, RHO
from audit import sha, save


def check_sources(im):
    for name, expected in im['sources'].items():
        assert sha(HERE.parent / name) == expected, 'source drift: ' + name


def csv_write(path, rows):
    with path.open('x', newline='') as f:
        w = csv.DictWriter(f, list(rows[0]), lineterminator='\n'); w.writeheader(); w.writerows(rows)


def compressed_csv(path, rows):
    with path.open('xb') as raw, gzip.GzipFile(fileobj=raw, mode='wb', filename='', mtime=0) as gz:
        with io.TextIOWrapper(gz, newline='') as f:
            w = csv.DictWriter(f, list(rows[0]), lineterminator='\n'); w.writeheader(); w.writerows(rows)


def build(z, queries, u, scores, partition):
    perm = np.arange(len(z), dtype=np.int32); rows = []; table = []; lookup = {}
    t = time.process_time(); wall = time.monotonic()
    for depth in range(5):
        size = len(z) // 10 ** depth
        for parent in range(10 ** depth):
            start = parent * size; ids = perm[start:start + size].copy()
            proposals = candidates(z, ids, depth)
            counts, diagonal = score_proposals(z, proposals, queries, u, scores)
            all8 = counts.sum(1); hard6 = counts[:, 2:].sum(1)
            objective = all8 if partition == 'ORACLE_ALL8' else hard6
            selected = int(np.argmax(objective)); baseline = int(objective[0]); best = int(objective[selected])
            assert best >= baseline
            unique = len({hashlib.sha256(p.tobytes()).digest() for p in proposals})
            row = dict(partition=partition, child_level=depth + 1, parent_id=parent, object_count=size,
                baseline_proposal=0, oracle_proposal=selected, baseline_score=baseline, oracle_score=best,
                regret=best - baseline, normalized_regret=(best - baseline) / ((8 if partition == 'ORACLE_ALL8' else 6) * size),
                baseline_box_diagonal=float(diagonal[0].mean()),
                parent_box_diagonal=float(np.linalg.norm(z[ids].max(0) - z[ids].min(0))),
                oracle_child_mean_diagonal=float(diagonal[selected].mean()),
                oracle_child_max_diagonal=float(diagonal[selected].max()),
                hard_query_gain=int(hard6[selected] - hard6[0]), all_query_gain=int(all8[selected] - all8[0]),
                tied_best_proposals=int((objective == best).sum()), unique_proposal_orders=unique)
            rows.append(row); lookup[(depth + 1, parent)] = counts.copy()
            for s in range(12):
                table.append(dict(partition=partition, child_level=depth + 1, parent_id=parent, proposal=s,
                    score_all=int(all8[s]), score_hard=int(hard6[s]),
                    **{f'q{qi}_pruned_objects': int(counts[s, qi]) for qi in range(8)}))
            perm[start:start + size] = proposals[selected]
        print(partition, 'child level', depth + 1, 'constructed; complete candidate safety PASS', flush=True)
    cost = dict(process_CPU_seconds=time.process_time() - t, elapsed_resource_seconds=time.monotonic() - wall,
        parents=len(rows), candidate_proposals_evaluated=len(table), sort_operations=len(table),
        sorted_object_occurrences=12 * 5 * len(z), oracle_query_child_bound_evaluations=len(table) * 10 * 8,
        construction_score_queries=8 if partition == 'ORACLE_ALL8' else 6,
        explicit_array_scratch_proxy_bytes=len(z) * 256 + 120 * 8 * 56,
        scratch_scope='conservative array live-set proxy; excludes allocator/sort internals and retained Python result tables',
        scope='query/U*-dependent greedy oracle construction including every-proposal cached-truth safety check; NOT deployable build time')
    assert len(rows) == 11111 and len(table) == 133332
    return perm, rows, table, lookup, cost


def metadata(z, scores, perm, im):
    data = dict(query_projection=z[im['queries']].copy(), U_star_squared=np.array([float.fromhex(v) for v in im['U_star_squared_hex']]))
    ordered = z[perm]
    for level, size in LEVELS.items():
        group = ordered.reshape(10 ** level, size, 8)
        lo, hi = endpoints(group.min(1), group.max(1))
        truth = np.empty((8, 10 ** level)); near = np.empty((3, 8, 10 ** level), dtype=np.int16)
        for qi in range(8):
            values = scores[qi, perm].reshape(10 ** level, size)
            truth[qi] = values.min(1); distances = np.sqrt(values)
            for fi, threshold in enumerate(im['near_threshold_hex'][qi]):
                near[fi, qi] = (distances <= float.fromhex(threshold)).sum(1)
        assert np.array_equal(truth <= data['U_star_squared'][:, None], near[0] > 0)
        data.update({f'low_{level}': lo, f'high_{level}': hi, f'truth_sq_{level}': truth, f'near_{level}': near})
    return data


def main():
    p = argparse.ArgumentParser()
    for key in ['freeze', 'prior-run', 'projected', 'scores', 'out']: p.add_argument('--' + key, type=Path, required=True)
    a = p.parse_args(); a.out.mkdir(parents=True, exist_ok=False)
    im = json.loads((a.freeze / 'INPUT_IDENTITY.json').read_text()); check_sources(im)
    assert sha(a.freeze / 'SAMPLES.json') == im['samples_sha256']
    assert os.environ.get('CUDA_VISIBLE_DEVICES') == '' and len(os.sched_getaffinity(0)) == 1
    threads = {k: os.environ.get(k) for k in ['OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS']}
    assert all(v == '1' for v in threads.values()) and os.getpriority(os.PRIO_PROCESS, 0) >= 10
    assert sha(a.projected) == im['projected_sha256'] and a.projected.stat().st_size == 128000000
    assert sha(a.scores) == im['scores_sha256'] and struct.unpack('<4i', a.scores.open('rb').read(16)) == (1000000, 960, 8, 8)
    for partition in PARTITIONS[:2]:
        for ext in ['i32', 'npz']:
            name = partition + '.' + ext
            assert sha(a.prior_run / name) == im['prior_output_manifest'][name]['sha256']
    z = np.memmap(a.projected, dtype='<f8', mode='r', shape=(1000000, 16))[:, 8:16]
    scores = np.memmap(a.scores, dtype='<f8', offset=16, mode='r', shape=(8, 1000000))
    assert np.isfinite(z).all() and np.isfinite(scores).all() and (scores >= 0).all()
    u_sq = np.array([float.fromhex(v) for v in im['U_star_squared_hex']]); u = np.sqrt(u_sq)
    for qi in range(8): assert np.partition(scores[qi], 7)[7] == u_sq[qi]
    basis = json.loads((HERE.parent / 'projection_certificate_20261011/evidence/BASIS.json').read_text())
    matrix = np.array([[float.fromhex(v) for v in row] for row in basis['families']['PCA']])
    upper, _ = exact_gram_bound(matrix); assert upper <= 1
    assert str(upper) == basis['certificates']['PCA']['exact_gram_infinity_bound']
    queries = z[im['queries']].copy(); samples = json.loads((a.freeze / 'SAMPLES.json').read_text())['samples']
    started = time.monotonic(); t = time.process_time()
    p2, p2stats = pca_partition(z)
    assert p2.tobytes() == (a.prior_run / 'PCA_BALANCED.i32').read_bytes(), 'P2 permutation bridge'
    costs = {'PCA_BALANCED': dict(process_CPU_seconds=time.process_time() - t, **p2stats,
        scope='same frozen max-spread reconstruction, CPU counts only')}
    perms = {'GTS_ORIGINAL': np.fromfile(a.prior_run / 'GTS_ORIGINAL.i32', dtype='<i4'), 'PCA_BALANCED': p2}
    rows = []; table = []; checks = []; ownership = {}; candidate_checks = 0
    for partition in PARTITIONS[2:]:
        perm, rr, tt, lookup, costs[partition] = build(z, queries, u, scores, partition)
        perms[partition] = perm; rows.extend(rr); table.extend(tt)
        candidate_checks += costs[partition]['oracle_query_child_bound_evaluations']
        t = time.process_time()
        for sample in (s for s in samples if s['partition'] == partition):
            level = sample['child_level']; parent = sample['parent_id']; size = 1000000 // 10 ** (level - 1)
            ids = perm[parent * size:(parent + 1) * size]
            independent, proposals = enumerate_scores(z, ids, level - 1, queries, u)
            assert np.array_equal(independent, lookup[(level, parent)]), 'G4 full enumeration mismatch'
            objectives = independent.sum(1) if partition == 'ORACLE_ALL8' else independent[:, 2:].sum(1)
            selected = int(np.argmax(objectives)); recorded = rr[(10 ** (level - 1) - 1) // 9 + parent]
            assert selected == recorded['oracle_proposal']
            assert np.array_equal(np.sort(proposals[selected].reshape(10, -1), axis=1), np.sort(ids.reshape(10, -1), axis=1)), 'G4 selected child ownership'
            checks.append(dict(**sample, object_count=size, selected=selected, all12_score_vectors_match=True,
                selected_children_match=True, parent_membership_sha256=hashlib.sha256(np.sort(ids).astype('<i4').tobytes()).hexdigest()))
        costs[partition]['independent_G4_CPU_seconds'] = time.process_time() - t
        print(partition, 'independent G4 all proposals/argmax/child ownership PASS', flush=True)
    bridges = {}
    for partition, perm in perms.items():
        ownership[partition] = audit(perm)
        perm.astype('<i4').tofile(a.out / (partition + '.i32'))
        data = metadata(z, scores, perm, im)
        if partition in PARTITIONS[:2]:
            old = np.load(a.prior_run / (partition + '.npz'))
            assert set(data) == set(old.files)
            for key, values in data.items(): assert values.tobytes() == old[key].tobytes(), 'prior metadata/truth bridge: ' + key
            bridges[partition] = dict(all_metadata_and_truth_bytes_identical=True, permutation_identical=True)
        np.savez_compressed(a.out / (partition + '.npz'), **data)
        print(partition, 'final ownership / metadata / own truth PASS', flush=True)
    csv_write(a.out / 'parent_split_regret.csv', rows)
    compressed_csv(a.out / 'proposal_scores.csv.gz', table)
    save(a.out / 'PARTITION_AUDIT.json', dict(status='PASS', ownership=ownership, prior_bridges=bridges,
        exact_contraction_rechecked=True, G4_pairs=len(checks), G4_scope='independent cached-coordinate candidate generation, scalar boxes/bounds, score vectors, argmax and child ownership',
        G4_checks=checks, original_vector_validation='inherited base 6c0932f; not repeated here',
        all_candidate_bounds_checked=candidate_checks, candidate_bounds_above_truth=0, candidate_false_topK_prunes=0,
        inputs=im, GPU_used=False, ETA=ETA, RHO=RHO))
    cpu = next(line.split(':', 1)[1].strip() for line in Path('/proc/cpuinfo').read_text().splitlines() if line.startswith('model name'))
    save(a.out / 'BUILD_RECEIPT.json', dict(CPU=cpu, python=sys.version.split()[0], numpy=np.__version__,
        CPU_affinity_count=1, thread_config=threads, GPU_used=False, costs=costs,
        process_cumulative_peak_RSS_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        peak_scope='entire worker including input mappings, result tables, metadata and G4; not isolated per-proposal scratch',
        elapsed_resource_seconds=time.monotonic() - started, no_latency_measured=True))
    save(a.out / 'OUTPUT_MANIFEST.json', {path.name: dict(sha256=sha(path), bytes=path.stat().st_size)
        for path in sorted(a.out.iterdir()) if path.is_file()})
    print('G1/G3/G4 and all-candidate G2 PASS; no primary curves evaluated', flush=True)


if __name__ == '__main__': main()
