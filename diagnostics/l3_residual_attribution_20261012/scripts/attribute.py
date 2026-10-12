#!/usr/bin/env python3
"""CPU-only exact L3 group attribution over pinned PRE/C3 evidence."""
import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] /
                       'rebuild_instability_causal_20261012/scripts'))
from analyze import Tree, compare, dump, sha, sig, sparse_correspondence
from verify_inputs import verify_inputs

GROUPS = ('SAME_PIVOT', 'CHANGED_PIVOT', 'UNKNOWN')
BASELINE_HELPER_SHA256 = 'e5d87bbb8678e54977e414ed0f232f1cc38b740adb81804dc7b68959f2b8cc50'


def pivot_dominant(groups, total):
    bygroup = {g['group']: g for g in groups}
    changed, same = bygroup['CHANGED_PIVOT'], bygroup['SAME_PIVOT']
    return (total['changed_objects'] > 0 and total['changed_leaves'] > 0 and
            bygroup['UNKNOWN']['parents'] == 0 and
            changed['changed_objects']*10 >= total['changed_objects']*9 and
            changed['changed_leaves']*10 >= total['changed_leaves']*9 and
            same['changed_leaves']*10 <= same['descendant_leaves'])


def quantiles(values):
    return dict(zip(('p50', 'p90', 'p95', 'p99', 'max'),
                    np.percentile(values, [50, 90, 95, 99, 100]).tolist())) if len(values) else None


def boundary(ra, rb, sizea, sizeb):
    hits = np.array([(ra < k * (sizea // 10)) !=
                     (rb < k * (sizeb // 10)) for k in range(1, 10)])
    degree = hits.sum(axis=0)
    segment = ra // (sizea // 10) != rb // (sizeb // 10)
    assert np.array_equal(degree > 0, segment)
    return hits.sum(axis=1), degree


def tie_diagnostics(ra, rb, ka, kb):
    """Only exact captured encoded-key equality; never raw-distance equality."""
    common_a = np.argsort(ra)
    common_b = np.argsort(rb)
    ar = np.empty(len(ra), dtype=np.int32)
    br = ar.copy()
    ar[common_a] = np.arange(len(ra))
    br[common_b] = np.arange(len(rb))
    masks = []
    for order, keys in ((common_a, ka), (common_b, kb)):
        eq = keys[order][1:] == keys[order][:-1]
        mask = np.zeros(len(order), dtype=bool)
        mask[order[:-1][eq]] = True
        mask[order[1:][eq]] = True
        masks.append(mask)
    # Joint equality classes represent common subgroups tied in both builds.
    pairs = np.rec.fromarrays([ka, kb], names='pre,post')
    _, labels = np.unique(pairs, return_inverse=True)
    reordered_groups = reordered_objects = persistent_groups = 0
    ordering = np.lexsort((ra, labels))
    cuts = np.r_[0, np.flatnonzero(labels[ordering][1:] != labels[ordering][:-1]) + 1, len(ra)]
    for lo, hi in zip(cuts[:-1], cuts[1:]):
        if hi - lo < 2:
            continue
        indices = ordering[lo:hi]
        persistent_groups += 1
        post_order = indices[np.argsort(rb[indices])]
        changed = np.count_nonzero(indices != post_order)
        reordered_groups += int(changed > 0)
        reordered_objects += int(changed)
    tied = masks[0] | masks[1]
    delta = np.abs(br.astype(np.int64) - ar)
    return {
        'retained_common_objects': len(ra),
        'tied_in_either_build_common_subgroup_objects': int(tied.sum()),
        'non_tied_in_both_builds_objects': int((~tied).sum()),
        'non_tied_full_rank_changed_objects': int(np.count_nonzero((ra != rb) & ~tied)),
        'non_tied_common_only_rank_changed_objects': int(np.count_nonzero((delta > 0) & ~tied)),
        'persistent_common_tie_subgroups': persistent_groups,
        'reordered_persistent_common_tie_subgroups': reordered_groups,
        'ordinal_position_changed_objects_in_persistent_tie_subgroups': reordered_objects,
        'common_only_rank_changed_objects': int(np.count_nonzero(delta)),
        'common_only_absolute_rank': quantiles(delta),
        'pre_common_tie_objects': int(masks[0].sum()),
        'post_common_tie_objects': int(masks[1].sum()),
    }, delta


class L3Tree(Tree):
    def audit_gate(self):
        with (self.replay / 'DECISIONS.csv').open() as f:
            self.decisions = list(csv.DictReader(f))
        assert len(self.decisions) == 11111
        ids = self.audit(3, 'input.order', '<i4')
        ordered = self.audit(3, 'sorted.order', '<i4')
        keys = self.audit(3, 'distance.keys', '<f8')
        sortedkeys = self.audit(3, 'sorted.keys', '<f8')
        pids = self.audit(3, 'distance.pids', '<i4')
        assert len(ids) == len(ordered) == len(keys) == len(sortedkeys) == 1000000
        assert np.array_equal(np.sort(ids), np.arange(1000000))
        assert np.array_equal(np.sort(ordered), np.arange(1000000))
        assert np.isfinite(keys).all() and np.all(sortedkeys[:-1] <= sortedkeys[1:])
        byrow = np.empty(1000000, dtype='<u8')
        byrow[ids] = keys.view('<u8')
        assert np.array_equal(byrow[ordered], sortedkeys.view('<u8'))
        for node in self.level[3]:
            start = int(self.nodes[node]['lid'])
            size = int(self.nodes[node]['size'])
            assert sig(self.base[ids[start:start + size]]) == self.keys[node]
            assert sig(self.base[ordered[start:start + size]]) == self.keys[node]
            assert int(self.base[pids[node]]) == self.pivots[node]
        for row in self.decisions:
            assert int(row['chosen_pivot_oid']) == self.pivots[int(row['storage_node'])]
        self.l3_ids = self.base[ordered]
        self.l3_keys = sortedkeys.view('<u8')
        self.l3_rank = np.full(self.oidmax, -1, dtype=np.int32)
        self.l3_rank[self.l3_ids] = np.arange(1000000)
        self.l3_input_rank = np.full(self.oidmax, -1, dtype=np.int32)
        self.l3_input_rank[self.base[ids]] = np.arange(1000000)


def attribute(pre, post):
    common = np.intersect1d(np.intersect1d(pre.base, post.base),
                           np.intersect1d(pre.live, post.live))
    oldlabels = pre.labels[3][common]
    newlabels = post.labels[3][common]
    matches, overlaps = sparse_correspondence(oldlabels, newlabels, 1000)
    size = max(pre.oidmax, post.oidmax)
    common_mask = np.zeros(size, dtype=bool)
    common_mask[common] = True
    churn = np.zeros(size, dtype=bool)
    churn[common] = [pre.keys[int(a)] != post.keys[int(b)] for a, b in
                     zip(pre.leaf_label[common], post.leaf_label[common])]
    parents = []
    l4_same_l3 = {g: {'parents': 0, 'objects': 0, 'changed_objects': 0,
                          'descendant_leaves': 0, 'changed_leaves': 0} for g in GROUPS}
    arrays = {g: {'rank': [], 'normalized_rank': [], 'input_rank': [], 'common_rank': []} for g in GROUPS}
    pre_cohorts = {g: {'objects': 0, 'changed_objects': 0} for g in GROUPS}
    for slot, node in enumerate(post.level[3]):
        oldslot = matches.get(slot)
        oldnode = pre.level[3][oldslot] if oldslot is not None else None
        group = ('UNKNOWN' if oldnode is None else
                 'SAME_PIVOT' if pre.pivots[oldnode] == post.pivots[node] else 'CHANGED_PIVOT')
        current = post.members[node]
        ids = current[common_mask[current]]
        leaves = post.level[5][slot*100:(slot+1)*100]
        assert all(post.nodes[node]['lid'] <= post.nodes[x]['lid'] <
                   post.nodes[node]['lid'] + post.nodes[node]['size'] for x in leaves)
        assert len(leaves) == 100
        changed_leaves = sum(post.keys[x] not in pre.index[5] for x in leaves)
        row = {'group': group, 'post_slot': slot, 'pre_slot': oldslot,
               'post_membership_sha256': post.keys[node],
               'pre_membership_sha256': pre.keys[oldnode] if oldnode is not None else None,
               'post_selected_pivot': post.pivots[node],
               'pre_selected_pivot': pre.pivots[oldnode] if oldnode is not None else None,
               'objects': len(ids), 'changed_objects': int(churn[ids].sum()),
               'descendant_leaves': len(leaves), 'changed_leaves': changed_leaves,
               'retained_objects': 0, 'imported_common_objects': len(ids), 'exported_common_objects': None,
               'l4_pre_pivots': 0, 'l4_surviving_within_parent': 0,
               'l4_correspondence_pairs': 0, 'l4_same_pivot_under_correspondence': 0}
        if oldnode is not None:
            previous = pre.members[oldnode]
            previous = previous[common_mask[previous]]
            retained = np.intersect1d(ids, previous)
            assert len(retained) == overlaps[slot]
            pre_cohorts[group]['objects'] += len(previous)
            pre_cohorts[group]['changed_objects'] += int(churn[previous].sum())
            row.update(retained_objects=len(retained), imported_common_objects=len(ids)-len(retained),
                       exported_common_objects=len(previous)-len(retained),
                       retained_changed_objects=int(churn[retained].sum()),
                       imported_changed_objects=int(churn[ids].sum()-churn[retained].sum()))
            pa = [pre.pivots[x] for x in range(oldnode * 10 + 1, oldnode * 10 + 11)]
            pb = {post.pivots[x] for x in range(node * 10 + 1, node * 10 + 11)}
            assert len(set(pa)) == 10 and len(pb) == 10
            row['l4_pre_pivots'] = 10
            row['l4_surviving_within_parent'] = sum(x in pb for x in pa)
            # Compare only corresponding children of this matched L3 pair.
            am = pre.labels[4][retained] % 10
            bm = post.labels[4][retained] % 10
            childmatches, _ = sparse_correspondence(am, bm, 10)
            row['l4_correspondence_pairs'] = len(childmatches)
            row['l4_same_pivot_under_correspondence'] = sum(
                pre.pivots[oldnode*10+1+j] == post.pivots[node*10+1+i]
                for i, j in childmatches.items())
            if group == 'SAME_PIVOT':
                for childslot in range(10):
                    child = node*10+1+childslot
                    oldchildslot = childmatches.get(childslot)
                    childgroup = ('UNKNOWN' if oldchildslot is None else
                                  'SAME_PIVOT' if pre.pivots[oldnode*10+1+oldchildslot] == post.pivots[child]
                                  else 'CHANGED_PIVOT')
                    childids = post.members[child]
                    childids = childids[common_mask[childids]]
                    childleaves = leaves[childslot*10:(childslot+1)*10]
                    agg = l4_same_l3[childgroup]
                    agg['parents'] += 1
                    agg['objects'] += len(childids)
                    agg['changed_objects'] += int(churn[childids].sum())
                    agg['descendant_leaves'] += 10
                    agg['changed_leaves'] += sum(post.keys[x] not in pre.index[5] for x in childleaves)
            sa, sb = int(pre.nodes[oldnode]['lid']), int(post.nodes[node]['lid'])
            na, nb = int(pre.nodes[oldnode]['size']), int(post.nodes[node]['size'])
            ra, rb = pre.l3_rank[retained] - sa, post.l3_rank[retained] - sb
            counts, degree = boundary(ra, rb, na, nb)
            delta = np.abs(ra.astype(np.int64) - rb)
            row.update(crossings_by_boundary=counts.tolist(), segment_crossing_objects=int((degree>0).sum()),
                       multiple_boundary_crossing_objects=int((degree>1).sum()),
                       rank_absolute=quantiles(delta), normalized_rank_absolute=quantiles(delta/na))
            arrays[group]['rank'].append(delta)
            arrays[group]['normalized_rank'].append(delta / na)
            inputdelta = np.abs((pre.l3_input_rank[retained]-sa).astype(np.int64) -
                                (post.l3_input_rank[retained]-sb))
            arrays[group]['input_rank'].append(inputdelta)
            row['input_rank_absolute'] = quantiles(inputdelta)
            if group == 'SAME_PIVOT':
                ka = pre.l3_keys[pre.l3_rank[retained]]
                kb = post.l3_keys[post.l3_rank[retained]]
                tie, common_delta = tie_diagnostics(ra, rb, ka, kb)
                row.update(tie=tie, same_encoded_offset=oldslot == slot,
                           exact_encoded_key_changed_objects=int(np.count_nonzero(ka != kb)) if oldslot == slot else None)
                arrays[group]['common_rank'].append(common_delta)
        parents.append(row)
    sums = ('objects', 'changed_objects', 'descendant_leaves', 'changed_leaves', 'retained_objects',
            'imported_common_objects', 'exported_common_objects', 'retained_changed_objects',
            'imported_changed_objects', 'l4_pre_pivots', 'l4_surviving_within_parent',
            'l4_correspondence_pairs', 'l4_same_pivot_under_correspondence',
            'segment_crossing_objects', 'multiple_boundary_crossing_objects')
    groups = []
    for group in GROUPS:
        rows = [x for x in parents if x['group'] == group]
        agg = {'group': group, 'parents': len(rows)}
        agg.update({key: sum(x.get(key) or 0 for x in rows) for key in sums})
        agg['crossings_by_boundary'] = [sum(x.get('crossings_by_boundary', [0]*9)[k] for x in rows) for k in range(9)]
        for key, blocks in arrays[group].items():
            agg[key+'_absolute_quantiles'] = quantiles(np.concatenate(blocks)) if blocks else None
        for name, numerator, denominator in (
            ('object_churn_fraction', 'changed_objects', 'objects'),
            ('leaf_churn_fraction', 'changed_leaves', 'descendant_leaves'),
            ('segment_crossing_fraction', 'segment_crossing_objects', 'retained_objects'),
            ('l4_pivot_survival_fraction', 'l4_surviving_within_parent', 'l4_pre_pivots')):
            agg[name] = agg[numerator]/agg[denominator] if agg[denominator] else None
        ties = [x['tie'] for x in rows if 'tie' in x]
        agg['same_pivot_key_tie'] = {
            key: sum(x[key] for x in ties) for key in ties[0] if key != 'common_only_absolute_rank'
        } if ties else None
        if ties:
            agg['same_pivot_key_tie'].update(
                encoded_offset_comparable_parents=sum(x['same_encoded_offset'] for x in rows),
                encoded_offset_noncomparable_parents=sum(not x['same_encoded_offset'] for x in rows),
                exact_encoded_key_changed_objects=sum(x['exact_encoded_key_changed_objects'] or 0 for x in rows))
        groups.append(agg)
    total = {'objects': len(common), 'changed_objects': int(churn[common].sum()),
             'descendant_leaves': 100000, 'changed_leaves': sum(x['changed_leaves'] for x in parents)}
    assert all(sum(g[k] for g in groups) == v for k, v in total.items())
    for g in groups:
        g['share_of_remaining_object_churn'] = g['changed_objects']/total['changed_objects']
        g['share_of_remaining_leaf_churn'] = g['changed_leaves']/total['changed_leaves']
    gate = pivot_dominant(groups, total)
    return {'totals': total, 'groups': groups, 'matched_parents': len(matches),
            'pre_cohort_object_sensitivity': pre_cohorts,
            'descriptive_l4_groups_beneath_same_pivot_l3': l4_same_l3,
            'PIVOT_DOMINANT_pass': gate}, parents


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('inputs', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    args.output.mkdir(exist_ok=False, parents=True)
    assert sha(Path(__file__).resolve().parents[2] /
               'rebuild_instability_causal_20261012/scripts/analyze.py') == BASELINE_HELPER_SHA256
    contract = json.loads((Path(__file__).resolve().parents[1]/'CONTRACT.json').read_text())
    for file, key in (('CLOSURE.json', 'baseline_closure_sha256'),
                      ('RAW_MANIFEST.json', 'baseline_raw_manifest_sha256'),
                      ('summary_final/RESULT.json', 'baseline_result_sha256')):
        assert sha(args.inputs/file) == contract[key]
    input_receipt = verify_inputs(args.inputs, Path(__file__).resolve().parents[1])
    dump(args.output/'INPUT_CLOSURE.json', input_receipt)
    baseline = json.loads((args.inputs/'summary_final/RESULT.json').read_text())
    results = []
    for r in (1, 2):
        pre = L3Tree(args.inputs/f'prior_snapshots/PRE_R{r}', args.inputs/f'runs/R{r}_PRE')
        post = L3Tree(args.inputs/f'prior_snapshots/POST_R{r}', args.inputs/f'runs/R{r}_C3')
        for file in ('order.i32', 'nodes.bin', 'empty.i32'):
            assert sha(pre.snapshot/file) == sha(pre.replay/file)
        measured = compare(pre, post)
        expected = baseline['rebuilds'][r-1]['modes'][-1]
        assert expected['mode'] == 'C3' and measured == expected['vs_pre']
        result, parents = attribute(pre, post)
        assert result['totals']['changed_objects'] == measured['common_live_objects']['changed_exact_leaf_membership']
        assert result['totals']['changed_leaves'] == measured['leaf']['changed']
        assert result['groups'][0]['parents'] == (734 if r == 1 else 721)
        assert result['groups'][1]['parents'] == (266 if r == 1 else 279)
        assert sum(g['segment_crossing_objects'] for g in result['groups']) == expected['boundary'][3]['changed_segment_objects']
        assert sum(g['l4_surviving_within_parent'] for g in result['groups']) == measured['levels'][4]['pivot_surviving']
        for key in ('objects', 'changed_objects', 'descendant_leaves', 'changed_leaves'):
            assert sum(g[key] for g in result['descriptive_l4_groups_beneath_same_pivot_l3'].values()) == result['groups'][0][key]
        assert sum(g['retained_objects'] for g in result['groups']) == expected['boundary'][3]['matched_parent_retained_common']
        dump(args.output/f'R{r}_PARENTS.json', parents)
        result.update(rebuild=r, parent_details_sha256=sha(args.output/f'R{r}_PARENTS.json'))
        results.append(result)
        print(json.dumps(result), flush=True)
    dump(args.output/'RESULT.json', {'experiment': contract['experiment'],
         'contract_sha256': sha(Path(__file__).resolve().parents[1]/'CONTRACT.json'),
         'gpu_construction_processes': 0, 'rebuilds': results,
         'decision': 'PIVOT_DOMINANT' if all(x['PIVOT_DOMINANT_pass'] for x in results) else 'REVIEW_NONDOMINANT_GATES'})


if __name__ == '__main__':
    main()
