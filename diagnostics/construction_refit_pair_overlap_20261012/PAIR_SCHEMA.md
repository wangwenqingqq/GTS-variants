# Ordered pair and canonical owner schema

`Pair = (pivot_occurrence_id, object_occurrence_id)`. Direction is retained even though L2 is symmetric. Each row address is mapped through the **same rebuild's original POST base.i32**; row relocation and duplicate coordinate vectors never merge immutable occurrences.

Both fields fit uint32 in these captures. Lossless raw encoding is `uint64(pivot_oid)<<32 | uint64(object_oid)` in little-endian uint64 NPY arrays. It is an encoding of logical occurrence IDs, not a physical-row or node identity. The level/stage appears in each filename. Each pair entry also has a parallel owner-dictionary-index entry.

## Source-exact concrete task lists

- `scoring_L0..L4`: each actually active parent scores every member from its captured **input order** against the captured selected pivot. Validate pivot equals input middle `(2*lid+size-1)//2`, the corresponding decision OID and each child's inherited pivot. Tile/range limits are enumerated from captured launch geometry.
- `boundary_L0..L4`: each actual child computes one distance to `sorted_order[child.lid]` at that split. Use the **stage-specific sorted order**, never the final recursively reordered first object. Boundary result destination/owner is that child.
- `refit_L1..L5`: every member of every nonempty positive-size original POST node with pid>=0. Use the original final tree/order and its inherited pivot. No root L0 distance task.

Scoring L is aligned to refit **L+1**, not L. A full 5×5 intersection matrix also reports nonaligned intersections. Task counts and unique counts are distinct; duplicates across levels are retained.

## Canonical owners

Owner identity = SHA256 of sorted immutable member OIDs as little-endian int32 bytes. `OWNER_DICTIONARY.csv` records hash and member count; numeric dictionary indices merely address this lookup. Actual membership is available in the pinned captures. The reused checker verifies stage membership equals final canonical membership, children partition parents, final coverage is complete and the 111,111 canonical memberships are distinct.

Scoring's owner is the parent whose pivot selection owns the scoring operation. Refit's owner is the receiving child/subtree. Boundary's owner is its destination child. On these balanced captures, canonical membership equality occurs only at the same tree level; at a given member set, SAME_OWNER pair matching requires selected scoring pivot = inherited refit pivot. The analysis checks this, rather than equating numeric node slots.

For global multiset matching, first maximize exact `(pair, canonical owner)` matches, then match remaining exact-pair multiplicities as DIFFERENT_OWNER. For a unique pair, report whether **any** SAME_OWNER match exists; this is not a claim that all task instances have that owner. Adjacent-level aligned matching is also reported separately.

## Overlap denominators

- Unique overlap: `|C_unique ∩ R_unique| / |R_unique|` and separately over C_unique.
- Task overlap: `sum_pair min(C_count, R_count) / R_tasks`.
- Boundary multiplicity overlap uses its own C list; boundary is a subset of scoring identity. Stage rows are **non-exclusive**. Never add 100% scoring plus 2.2222% boundary as an avoidable-work fraction.
- Boundary-identity-present refit tasks count every refit instance whose pair occurs anywhere in boundary, a different denominator from available boundary producer task multiplicity.

Numerical compatibility is a source-contract admission classification, **not** a measured per-pair value agreement rate; see `evidence/NUMERIC_LIFETIME.md`.
