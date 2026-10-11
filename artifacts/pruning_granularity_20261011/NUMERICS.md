# Unchanged GLOBAL4 safe intervals

This round reuses [the qualified distance envelope](../block_certificate_headroom_20261010/NUMERICS.md)
and its `interval`, `radius_upper`, and strict `rejected` helpers without changing
semantics. Membership remains ordered FP64 full-D squared distance <= the exact
FP64 square of the same FP32 radius. Rounded squared scores are not a metric.

All four pivot norms are conservatively enclosed before member min/max reduction.
Any whole-tile rejection therefore implies no retained-reference hit in that
tile. Only membership grouping changes; no equality/boundary pruning relaxation.
Partition uses rounded norms solely for deterministic ordering, not as certified
endpoints. Four query/pivot distances are bitwise bound to the original reference.

The primary reduction is vectorized; verification independently stable-sorts
every partition, directly reduces each member set and uses object-owner oracle
membership. All320 query rows require zero false prune. Boundary regression tests
include exact Decimal norms, ties, duplicates, subnormal/extreme FP32, equality,
final partial leaves, malformed inputs and conservative filtering. This is not
a new numerical proof, CUDA qualification or timing result.
