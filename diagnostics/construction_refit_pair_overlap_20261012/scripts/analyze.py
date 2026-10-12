#!/usr/bin/env python3
"""Source-exact pair reconstruction from existing, hash-pinned native captures."""
import argparse
import csv
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[1]
HELPER = HERE.parent / 'rebuild_instability_causal_20261012/scripts/analyze.py'
assert hashlib.sha256(HELPER.read_bytes()).hexdigest() == json.loads((HERE/'CONTRACT.json').read_text())['helper_sha256']
spec = importlib.util.spec_from_file_location('causal_analysis', HELPER)
prior = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prior)
Tree, NODE, sha, sig = prior.Tree, prior.NODE, prior.sha, prior.sig


def dump(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + '\n')


def pairs(pivot, objects):
    objects = np.asarray(objects)
    assert np.all(objects >= 0) and np.all(objects < 2**32)
    p = np.asarray(pivot)
    assert np.all(p >= 0) and np.all(p < 2**32)
    return (p.astype('<u8') << np.uint64(32)) | objects.astype('<u8')


def overlap(c, r):
    cu, cc = np.unique(c, return_counts=True)
    ru, rc = np.unique(r, return_counts=True)
    common, ci, ri = np.intersect1d(cu, ru, assume_unique=True, return_indices=True)
    repeated = int(np.minimum(cc[ci], rc[ri]).sum())
    return {'construction_tasks': len(c), 'refit_tasks': len(r),
            'construction_unique': len(cu), 'refit_unique': len(ru),
            'overlap_unique': len(common), 'overlap_over_refit_unique': len(common)/len(ru),
            'overlap_over_construction_unique': len(common)/len(cu),
            'repeated_refit_tasks': repeated, 'task_overlap_fraction': repeated/len(r)}, (cu, cc, ru, rc, common)


def save_tasks(folder, stage, level, codes, owners):
    assert len(codes) == len(owners)
    np.save(folder/f'{stage}_L{level}.pairs.npy', codes)
    np.save(folder/f'{stage}_L{level}.owner_dictionary_indices.npy', owners)


def verify_inputs(roots):
    contract = json.loads((HERE/'CONTRACT.json').read_text())
    assert sha(HELPER) == contract['helper_sha256']
    manifest = json.loads((HERE/'evidence/INPUT_MANIFEST.json').read_text())
    for row in manifest['files']:
        path = roots[row['group']] / row['file']
        assert path.stat().st_size == row['bytes'] and sha(path) == row['sha256'], str(path)
    audit = json.loads((roots['prior']/'SOURCE_AUDIT.json').read_text())
    for name, digest in audit['keeper_files'].items():
        assert sha(roots['source']/name) == digest, name
    quality = json.loads((roots['prior']/'QUALITY.json').read_text())
    assert quality['passed'] and quality['ordered_payloads_identical']
    assert quality['rebuild_trigger_steps_zero_based'] == [48, 216]
    assert quality['full_quality']['queries'] == 256
    return {'input_files_verified': len(manifest['files']), 'keeper_files_verified': len(audit['keeper_files']),
            'inherited_quality_pass': True, 'new_gpu_processes': 0, 'helper_sha256': sha(HELPER)}


def rebuild(roots, out, number, source_counts):
    name = f'R{number}'
    snapshot = roots['snapshot']/f'POST_{name}'
    replay = roots['capture']/f'runs/{name}_C0'
    for filename in ('nodes.bin', 'empty.i32', 'order.i32'):
        assert (snapshot/filename).read_bytes() == (replay/filename).read_bytes(), filename
    assert json.loads((replay/'NATIVE_GATE.json').read_text())['passed']
    tree = Tree(snapshot, replay)
    meta = json.loads((snapshot/'meta.json').read_text())
    assert len(set(tree.keys.values())) == len(tree.nodes)
    for filename in ('lo.f64', 'hi.f64'):
        assert len(np.fromfile(snapshot/filename, dtype='<f8')) == len(tree.nodes)
    lo = np.fromfile(snapshot/'lo.f64', dtype='<f8')
    hi = np.fromfile(snapshot/'hi.f64', dtype='<f8')
    assert np.all(lo <= hi) and np.all(np.isfinite(lo[1:])) and np.all(np.isfinite(hi[1:]))
    raw = out/name
    raw.mkdir()
    with (raw/'OWNER_DICTIONARY.csv').open('w') as f:
        writer = csv.writer(f)
        writer.writerow(['dictionary_index', 'canonical_membership_sha256', 'members'])
        writer.writerows((i, tree.keys[i], int(tree.nodes[i]['size'])) for i in range(len(tree.nodes)))

    c_levels, b_levels, r_levels, same_owner_pairs = {}, {}, {}, []
    same_owner_tasks = 0
    captures = []
    for level in range(5):
        hn = tree.audit(level, 'input.nodes', NODE)
        he = tree.audit(level, 'input.empty', '<i4')
        split = tree.audit(level, 'input.split', '<i4')
        order = tree.audit(level, 'input.order', '<i4')
        ordered = tree.audit(level, 'sorted.order', '<i4')
        pids = tree.audit(level, 'distance.pids', '<i4')
        children = tree.audit(level, 'after_split.nodes', NODE)
        geometry = json.loads((replay/f'audit/build0/level{level}.GEOMETRY.json').read_text())
        first = (10**level-1)//9
        assert geometry['threads'] == 512 and geometry['start'] == first
        assert geometry['slots'] == 10**level and geometry['grid'] == geometry['slots']*geometry['tiles']
        active = [i for i in range(first, first+10**level) if split[i] == 1]
        assert active == tree.level[level]
        c, co, b, bo = [], [], [], []
        tasks = 0
        for i in active:
            node = hn[i]
            at, size = int(node['lid']), int(node['size'])
            assert he[i] == 0 and size > 20
            # The inherited helper independently checks sort permutation, keys and membership.
            assert sig(tree.base[order[at:at+size]]) == tree.keys[i]
            assert pids[i] == order[(2*at+size-1)//2]
            pivot = int(tree.base[pids[i]])
            code = pairs(pivot, tree.base[order[at:at+size]])
            c.append(code)
            co.append(np.full(size, i, dtype='<i4'))
            assert geometry['tiles']*512 >= size
            tasks += sum(max(0, min(512, size-t*512)) for t in range(geometry['tiles']))
            if level and tree.base[tree.nodes[i]['pid']] == pivot:
                same_owner_pairs.append(code)
                same_owner_tasks += size
            for child in range(i*10+1, i*10+11):
                v = children[child]
                assert int(v['pid']) == int(pids[i])
                assert v['min_dis'].tobytes() == tree.nodes[child]['min_dis'].tobytes()
                start, count = int(v['lid']), int(v['size'])
                assert sig(tree.base[ordered[start:start+count]]) == tree.keys[child]
                b.append(int(pairs(pivot, tree.base[ordered[start]])))
                bo.append(child)
        c_levels[level] = np.concatenate(c)
        b_levels[level] = np.asarray(b, dtype='<u8')
        assert tasks == len(c_levels[level]) == 1000000
        assert len(b) == len(active)*10
        assert len(c_levels[level]) == meta['build_levels'][level]['distance_tasks']
        assert len(active) == meta['build_levels'][level]['active_nodes']
        save_tasks(raw, 'scoring', level, c_levels[level], np.concatenate(co))
        save_tasks(raw, 'boundary', level, b_levels[level], np.asarray(bo, dtype='<i4'))
        captures.append({'scoring_level': level, 'active_parents': len(active),
                         'tiled_loop_source_count': tasks, 'captured_scoring_pairs': len(c_levels[level]),
                         'nodeSplit_loop_source_count': len(active)*10, 'captured_boundary_pairs': len(b)})
    refit_source_count = 0
    for level in range(1, 6):
        codes, owners = [], []
        for i in tree.level[level]:
            node = tree.nodes[i]
            assert tree.empty[i] == 0 and node['size'] > 0 and node['pid'] >= 0
            code = pairs(int(tree.base[node['pid']]), tree.members[i])
            codes.append(code)
            owners.append(np.full(len(code), i, dtype='<i4'))
            refit_source_count += int(node['size'])
        r_levels[level] = np.concatenate(codes)
        save_tasks(raw, 'refit', level, r_levels[level], np.concatenate(owners))
    assert tree.nodes[0]['pid'] == -1  # Root launches but performs no distance task.
    c = np.concatenate(list(c_levels.values()))
    b = np.concatenate(list(b_levels.values()))
    r = np.concatenate(list(r_levels.values()))
    assert len(c) == source_counts['construction_distance_tasks'] == 5000000
    assert len(b) == source_counts['active_split_nodes']*10 == 111110
    assert len(r) == refit_source_count == source_counts['refit_distance_tasks'] == 5000000
    assert len(c) == meta['build_distance_tasks'] and len(r) == meta['refit_distance_tasks']
    assert len(b) == meta['build_created_children']
    main, (cu, cc, ru, rc, common) = overlap(c, r)
    boundary, (_, _, _, _, bc) = overlap(b, r)
    assert np.all(np.isin(b, c))
    boundary_refit_tasks = int(rc[np.searchsorted(ru, bc)].sum())
    owner_unique = np.unique(np.concatenate(same_owner_pairs)) if same_owner_pairs else np.array([], dtype='<u8')
    assert np.all(np.isin(owner_unique, common))
    # Balanced, disjoint canonical memberships make owner equality possible only at one identical level.
    owner = {'matching': 'maximize same (pair, canonical member set) first, then match residual pair tasks',
             'same_owner_matched_tasks': same_owner_tasks,
             'different_owner_matched_tasks': main['repeated_refit_tasks']-same_owner_tasks,
             'same_owner_task_fraction': same_owner_tasks/len(r),
             'unique_overlap_with_any_same_owner_match': len(owner_unique),
             'unique_overlap_only_different_owner': len(common)-len(owner_unique),
             'adjacent_level_matched_tasks_same_owner': 0,
             'adjacent_level_matched_tasks_different_owner': len(r),
             'boundary_same_owner_matched_tasks': len(b)}
    rows, matrix = [], []
    for cl in range(5):
        for rl in range(1, 6):
            count = len(np.intersect1d(c_levels[cl], r_levels[rl]))
            matrix.append({'construction_level': cl, 'refit_level': rl, 'unique_intersection': count,
                           'fraction_of_refit_level_tasks': count/len(r_levels[rl])})
        aligned, _ = overlap(c_levels[cl], r_levels[cl+1])
        rows.append({'construction_level': cl, 'refit_level': cl+1, **aligned})
    self_unique = int(np.count_nonzero((common >> np.uint64(32)) == (common & np.uint64(0xffffffff))))
    self_tasks = int(np.count_nonzero((r >> np.uint64(32)) == (r & np.uint64(0xffffffff))))
    # These classify the source contract, not accidental equality of uncaptured per-pair interval endpoints.
    numeric = {'scope': 'existing nominal construction output -> exact frozen refit interval output',
               'same_numeric_contract_unique': 0, 'convertible_self_pair_unique_optimistic': self_unique,
               'incompatible_nonself_unique': len(common)-self_unique,
               'certified_compatible_unique_admission_ceiling_fraction': self_unique/len(ru),
               'convertible_self_pair_task_optimistic': self_tasks,
               'certified_compatible_task_admission_ceiling_fraction': self_tasks/len(r),
               'ceiling_definition': 'existing source-contract-admitted categories plus optimistic trivial self-zero exception; not a mathematical bound on all conversion algorithms or accidental equality',
               'per_pair_value_bit_equality': 'unknown: refit captures node extrema only',
               'does_not_prove': 'every nonself nominal value differs numerically; all future build-produced certificates are impossible'}
    storage = {str(width): len(common)*width for width in (4, 8, 16)}
    decision = 'NO_GO_REUSE' if min(main['overlap_over_refit_unique'], numeric['certified_compatible_unique_admission_ceiling_fraction']) < .5 else 'CONDITIONAL'
    if main['overlap_over_refit_unique'] >= .8 and numeric['certified_compatible_unique_admission_ceiling_fraction'] >= .8:
        decision = 'STRONG_OVERLAP'
    result = {'rebuild': name, 'counts': captures, 'refit_source_count': refit_source_count,
              'scoring_vs_refit': main, 'boundary_vs_refit': boundary,
              'boundary_identity_present_refit_tasks_nonexclusive': boundary_refit_tasks,
              'scoring_boundary_union_overlap_unique': len(np.intersect1d(np.union1d(cu, np.unique(b)), ru)),
              'boundary_is_subset_of_scoring': True, 'multiplicity_equal': bool(np.array_equal(cu, ru) and np.array_equal(cc, rc)),
              'unique_pair_set_sha256': hashlib.sha256(cu.astype('<u8', copy=False).tobytes()).hexdigest(),
              'refit_pair_multiplicity_histogram': {str(int(v)): int(np.count_nonzero(rc == v)) for v in np.unique(rc)},
              'owner': owner, 'aligned_levels': rows, 'level_matrix': matrix, 'numeric': numeric,
              'storage_identity_overlap_bytes': {'FP32_nominal': storage['4'], 'FP64_nominal': storage['8'],
                                                'two_FP64_interval_endpoints': storage['16'],
                                                'two_uint32_occurrence_ID_mapping': storage['8'],
                                                'two_uint64_occurrence_ID_mapping': storage['16']},
              'current_scoring_value_survives_to_refit': 'NO',
              'boundary_scalar_lifetime': 'YES: TN.min_dis persists, but is a nominal FP32 scalar, not the refit certificate',
              'decision': decision}
    dump(raw/'RESULT.json', result)
    return result


def self_check():
    c = pairs([2, 2, 2, 3], [7, 7, 8, 9])
    r = pairs([2, 2, 3, 5], [7, 7, 9, 1])
    result, _ = overlap(c, r)
    assert result['overlap_unique'] == 2 and result['repeated_refit_tasks'] == 3
    assert result['task_overlap_fraction'] == .75
    assert pairs(2, [7])[0] != pairs(7, [2])[0]
    assert pairs(1, [2])[0] != pairs(0, [2])[0]
    assert sig([1, 2, 3]) == sig([3, 2, 1]) and sig([1, 2, 3]) != sig([1, 2, 4])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture-root', type=Path)
    parser.add_argument('--snapshot-root', type=Path)
    parser.add_argument('--source-root', type=Path)
    parser.add_argument('--prior-root', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    self_check()
    if args.self_test:
        print('SELF_TEST_PASS')
        return
    assert all((args.capture_root, args.snapshot_root, args.source_root, args.prior_root, args.output))
    args.output.mkdir()  # Never replace an existing run.
    roots = {'capture': args.capture_root, 'snapshot': args.snapshot_root, 'source': args.source_root, 'prior': args.prior_root}
    gate = verify_inputs(roots)
    counts = json.loads((roots['prior']/'PRIOR_COUNTS.json').read_text())['rebuilds']
    results = [rebuild(roots, args.output, i+1, v['work']) for i, v in enumerate(counts)]
    assert len(results) == 2
    dump(args.output/'RESULTS.json', {'validation': gate, 'rebuilds': results, 'performance_claim': False})
    raw_files = [{'file': p.relative_to(args.output).as_posix(), 'bytes': p.stat().st_size, 'sha256': sha(p)}
                 for p in sorted(args.output.rglob('*')) if p.is_file()]
    dump(args.output/'DERIVED_MANIFEST.json', raw_files)
    print(json.dumps({'decisions': [r['decision'] for r in results], 'input_files_verified': gate['input_files_verified']}))


if __name__ == '__main__':
    main()
