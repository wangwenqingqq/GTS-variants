#!/usr/bin/env python3
"""Small regressions for exact gates, boundaries and tie metric semantics."""
import copy
import numpy as np
from attribute import boundary, pivot_dominant, tie_diagnostics, sig

assert sig(np.array([3, 1, 2])) == sig(np.array([2, 3, 1]))
assert sig(np.array([3, 1, 2])) != sig(np.array([3, 1, 4]))
counts, degree = boundary(np.array([99, 100, 50, 899]),
                          np.array([100, 99, 350, 899]), 1000, 1000)
assert degree.tolist() == [1, 1, 3, 0] and counts.sum() == 5
assert (degree > 0).sum() == 3 and (degree > 1).sum() == 1

tie, drift = tie_diagnostics(np.arange(3), np.array([2, 1, 0]),
                            np.ones(3, dtype='u8'), np.ones(3, dtype='u8'))
assert tie['reordered_persistent_common_tie_subgroups'] == 1
# The middle object changes pair relations, not its subgroup ordinal position.
assert tie['ordinal_position_changed_objects_in_persistent_tie_subgroups'] == 2
assert tie['non_tied_in_both_builds_objects'] == 0
tie, drift = tie_diagnostics(np.arange(3), np.arange(3) + 1,
                            np.arange(3, dtype='u8'), np.arange(3, dtype='u8'))
assert tie['non_tied_full_rank_changed_objects'] == 3
assert tie['non_tied_common_only_rank_changed_objects'] == 0
assert not drift.any()

groups = [{'group': 'SAME_PIVOT', 'changed_leaves': 10, 'descendant_leaves': 100},
          {'group': 'CHANGED_PIVOT', 'changed_objects': 90, 'changed_leaves': 90},
          {'group': 'UNKNOWN', 'parents': 0}]
total = {'changed_objects': 100, 'changed_leaves': 100}
assert pivot_dominant(groups, total)
for group, key, value in ((1, 'changed_objects', 89), (1, 'changed_leaves', 89),
                           (0, 'changed_leaves', 11), (2, 'parents', 1)):
    altered = copy.deepcopy(groups)
    altered[group][key] = value
    assert not pivot_dominant(altered, total)
assert not pivot_dominant(groups, {'changed_objects': 0, 'changed_leaves': 0})
print('PASS exact signatures, boundary counts, retained-common ties, integer gate thresholds')
