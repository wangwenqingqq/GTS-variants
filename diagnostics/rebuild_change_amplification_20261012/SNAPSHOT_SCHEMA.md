# Frozen snapshot schema

**Read POSTPROCESS_CLARIFICATION.md first for the final count/attribution
interpretation. This original pre-run schema is retained, not silently rewritten.**

Little-endian contiguous vector payloads. Native TN = 20 bytes: pid i32,
min_dis f32, size i32, lid i32, is_leaf i32. Empty nodes are excluded from
canonical analysis. The observed target is arity 10, leaf threshold 20.

PRE is after the triggering insertion becomes logically visible and before
compaction. POST is after compaction, construction, reset, numeric refit, PAR
refresh and KNN refresh. Rebuild itself preserves the logical live set.
Published PRE membership still contains base tombstones; pending insertions are
not in its tree. Report this published representation and a live-filtered view;
do not pretend PRE and POST have identical indexed universes.

`base.i32` maps base physical rows to immutable occurrence IDs, including PRE
tombstones. `deleted.i32` records actual native tombstones. `buffer.i32` and
`buffer_positions.i32` contain ordered immutable IDs and actual scratch rows.
`live.i32` is the exact sorted logical live set. `nodes.bin`, `empty.i32`,
`order.i32`, `lo.f64`, `hi.f64`, `packed.f32` capture native representation.
`plan_*.i32` serialize persistent Plan payloads; regions are six int32 fields.
All pack coordinates of valid base rows are captured; capacity padding, pending
buffer packed rows and transient query scratch are excluded.

Leaf primary identity is exact sorted membership bytes hashed with SHA256.
For modified/new/removed inventory only, unmatched leaves are paired greedily by
largest occurrence intersection, ties by canonical signature, with one-to-one
ownership. This is descriptive correspondence, not persistent leaf identity.
Exact-match change rates and per-object membership equality do not depend on it.
Nodes are aligned by `(level, subtree membership)`; pivot and ordered child
membership signatures define topology. Numeric state is min_dis f32 plus lo/hi
f64 bit patterns. Unmatched nodes are structural change, not numeric-only change.

Refit raw slot differences are reported, but only canonically same-topology
entries justify recomputed-but-identical state. Structurally unmatched entries
are reported separately. KNN reports physical-slot changes and occurrence-aligned
surviving coordinate equality separately. Address relocation is never inferred
from pointers. All canonical content maps use immutable occurrences.

PAR comparison includes each scalar in regions, leaf_slot, slot_pid, leaves,
owners, parents, skeleton, level_offsets and skeleton_offsets. For content
alignment, node-indexed slots are keyed by canonical node; object slots by
immutable occurrence; list entries by canonical referenced membership and level;
region records by canonical root. Raw integer payload bytes remain a separate
positional comparison. Vector/container and device View pointers are excluded.
Regenerated entries means complete output scalar writes of make_plan, not every
intermediate CPU loop or hidden allocator instruction.

Dynamic construction hooks copy active split flags and node sizes before each
existing dispatch. They count pivot-object distance tasks, full sort API input
slots, active split nodes, and created children. Refit distance task counts follow
actual POST node sizes and the exact valid-node/pivot predicates in refit.
Compaction reads candidates Nbase+buffer, skips tombstones, writes Npost complete
rows; coordinate writes = Npost*D. Pack32 writes Npost*D. Full library internals
are unknown. Counts are source-derived from captured runtime inputs, not hardware
instruction counters. No additional GPU kernel is introduced.

Direct affected (A) includes dependencies containing any mutation-touched ID.
Remaining changed state (B) is observed transitive churn, not proven unavoidable.
Identical content/numeric state (C) is a redundant recomputation opportunity, not
proof that skipping it is correct or beneficial. Never pool unrelated scalar,
object, leaf and node units into an aggregate percentage.

Exact PAR normalization used by the reader: leaf_slot references its canonical
leaf instead of its absolute offset; slot_pid is keyed by occurrence and stores
canonical leaf plus local ordinal; owners is keyed by occurrence and stores
canonical region-root membership. Leaves/parents/skeleton are membership-keyed
sets with multiplicity-one entries (parents/skeleton preserve level); regions
use root-membership keys, numeric counts, and membership-normalized root and
leaf_offset references. Offsets preserve level-indexed numeric counts. Native
list order, numeric node indices and absolute flattened offsets remain in raw
byte comparison. Node pivots/numeric values are not duplicated in Plan and are
charged in the separate node ledger. This describes stored plan content only,
not correctness of reusing a plan after changing its referenced tree.
