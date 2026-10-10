# Static Host-ready adapter freeze

This is measurement-contract repair, not a new optimization or novelty claim.
The six admitted entries preserve the supplied method permutations with only
blocked GPU_TREE removed. CPU_MVPT remains unavailable. CPU Flat is explicitly
CPU_FLAT_INCLUSIVE_ADAPT; it is not silently renamed as native inclusive range.

## Input and timing boundary

The earlier P diagnostic selects a query already resident in its database.
External native interfaces receive Host vectors. Formal P now owns one extra
non-indexed D-element query row and copies the submitted Host coordinate into
that row on every call, inside the Host-ready timer. N and the indexed multiset
remain unchanged. Every GPU tree/search/distance kernel body is unchanged.
The extra row lives with the existing data allocation, is overwritten only
after the preceding serialized ACK, and is released with that allocation.
No copy, output field, setup, buffer preparation or owned-device cleanup is
subtracted as presumed overhead.

All methods build once. Each supported task has eight warmups and 32 measured
B1 calls. Dual-task order alternates 3/3. Warmup arrays are retained like the
measured arrays, avoiding file writes in any timed pass. Host allocation,
submission/conversion, complete IDs/FP32 fields and synchronization are charged.
The qualified native-squared validation observer remains charged for external
adapters; no post-result observer subtraction. P does not have an additional
native-squared API. Serialization and final client consumption/destruction of
retained answers remain outside service costs, equally disclosed for all rows.

CPU FP32→FP64/copy preparation is separate from native index construction.
P reports data/event preparation separately from construction, bounds/mirror
setup and service-buffer preparation. Native GPU Flat and the cuVS scan have no
separate Host representation conversion (zero preparation); their build column
includes resource/workspace allocation and native index.add/database H2D.
These ownership differences are real and are not normalized into identical
internal stages. Lifecycle sums are compared only for both-task methods.

## Admission and limitations

R1 originally reserved seven GPU qualifier slots. Its first attempt failed before
CUDA because the resource executable was unavailable; that attempt is retained
and counted. R2 reserves and completes the remaining six: P bounded
memcheck/racecheck/synccheck, P on both target snapshots, and bounded range
memcheck. The redundant normal bounded range run is removed, not replaced.
Cumulative qualifier attempts are32/32; no further GPU qualification is admitted.
See STATIC_ATTEMPTS.md and both immutable contract versions.
P internal field bits and kNN order are checked against ordered-FP64 exhaustive
scores; range membership and per-ID exact fields are checked independently.
Unchanged range kernels inherit the Stage A edge/race/sync/target qualification;
new Host retention/phase timing is separately checked. Every primary rechecks
all warmup/measured members and fields; no partial validation sampling.

The supplied 72 admitted static primaries plus previous18 internal primaries
use90/102 slots. Failures count and stop the affected launch, never trigger an
automatic replacement or an extra qualifier. GPU isolation is
per-process locked/observed; the CPU host is shared, with native pools fixed to
one thread and NUMA placement recorded. No changed-clock, profiler, long-run,
dynamic superiority or production/leak-clean claim. The inherited96 B managed
context-symbol boundary remains open.
