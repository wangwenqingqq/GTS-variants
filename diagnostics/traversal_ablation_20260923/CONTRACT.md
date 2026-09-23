# Independent traversal ablations

Experiment: `gts_20260923_traversal_ablation_words2000`.
Preregistered before candidate implementation or measurement on 2026-09-23.

## Two independent hypotheses

- **F (traversal fusion only):** replace initialization plus two level-walk and
  two parent-clear launches with one CTA/kernel and block barriers. Preserve
  original per-child distance arithmetic, flags, and parent-clear conditions.
- **P (parent-pivot reuse only):** replace each level-walk kernel with one that
  computes distance once per live parent having a nonempty child, then broadcasts
  through shared memory. Preserve initialization, two level boundaries, two
  parent-clear launches, child interval checks, and subsequent kernels.
- No combined F+P candidate. Neither candidate fuses candidate compaction, leaf
  evaluation, or output selection with traversal. No edit-distance algorithm
  improvement, metric specialization, precision change, or host waiting change.

Generic fusion and pivot reuse are established engineering mechanisms (including
GTS's own kNN pivot reuse), not new contributions. This campaign attributes two
effects in the original range path; it makes no cross-index generality claim.

## Frozen comparator and workload

- Common inherited result-selector fusion from revision `6221ae9`, generated
  through the existing `fused_result_20260923/prepare.py`; task starting revision
  `e786bd1`. Original author sources remain pinned to `3bac1b7` and unmodified.
- Modes: D/E = baseline stream/Graph; G/F = F stream/Graph; Q/P = P stream/Graph.
  Native A is only the full-output/order anchor at nonnegative radii.
- Words N=2000, same 64 deterministic distinct query IDs; byte edit distance,
  inclusive radius, batch one, immutable height-3/fanout-10 tree, at most 20
  records per leaf, 111 node slots, 2220 result slots. Fail closed outside this
  domain. No updates, concurrent queries, larger trees, or non-Words promotion.
- Complete ordered host IDs, distances, and count; identical fixed capacity,
  allocations, result fusion, deletion-prefix scan, leaf kernels and transfers
  for every measured mode. Native zero-grid negative-radius issue stays excluded.
- RTX PRO 6000 Blackwell Server Edition, GPU 0 only; `sm_120`, CUDA 13.1.115,
  driver 590.48.01. Verify live state before admission. Existing GPU 0 advisory
  lock plus process monitoring; no foreign signals/settings changes. Initial
  preflight found another benchmark on GPU 0: do not run until it is clear and
  the nonblocking lock is acquired. Build work may proceed without GPU execution.

## Design and resource card

| Item | F | P |
|---|---|---|
| Ownership | One 512-thread CTA owns one query's flags | Same one-query CTA per level; one lane per parent computes pivot distance |
| State | Original global flag array; original per-child local distance state | Same global flags plus at most 10 shared float distances per level |
| Ready graph | Init -> barrier -> all child reads/writes -> barrier -> parent clear -> barrier -> next level | Parent live/nonempty test -> distance/shared write -> barrier -> child shared reads and interval tests -> kernel completion -> unchanged parent clear |
| Barrier owners | Every lane, including inactive lanes, reaches every barrier | Every lane reaches the shared-publication barrier; no producer overwrites before all reads |
| Live-state peak | Original metric's full DP table, reused across levels; no shared tree or cached distances | Original DP table in producer lanes, shared scalar distance in consumer phase; no larger DP state |
| Expected useful work | Same evaluated query-child distances and interval tests | One distance per evaluated parent, same evaluated child interval tests |
| Expected control delta | Traversal launches 5 -> 1; whole query 17 -> 13 | Traversal launches remain 5; whole query remains 17 |
| Added cost/risk | Block barriers and compiler/resource changes | Shared traffic/barrier and fewer parallel distance producers |

Do not assert occupancy or stack improvement in advance. Extract final resources
and selected SASS; record REG/STACK/LOCAL/SHARED and static local instructions.
No Tensor Core or asynchronous pipeline is involved. Keep the original multi-CTA
leaf parallelism. Same-stream kernel boundaries protect global producer/consumer
handoffs outside the single-CTA traversal; no grid barrier is emulated.

## Gates and estimators

1. CPU generator drift/integration checks; exact input/source hashes.
2. Fresh common binary and diagnostic traversal test. Compare complete results
   and native order for radii 0/4/256, independent CPU oracle for all modes;
   radius -1 empty-output checks exclude native A.
3. Diagnostic original-versus-candidate flag equality, pivot work counts, and
   nonempty-child edge patterns. Counter instrumentation is absent from timing.
4. Memcheck/synccheck for all six measured modes; initcheck/racecheck for F/P
   in both stream and Graph, plus all four tools on traversal regression.
   Stress each measured mode with 16384 changing-query calls (64-ID cycle).
5. Fresh-process timing: 64 warmups, 4096 completed queries/process, radius 4;
   orders `DEFGPQ`, `QPGFED`, `EFPGQD`, `DQGPFE`, `FPEDQG`, `GQDEPF`.
   Primary independent comparisons E/F and E/P; secondary D/G and D/Q.
6. Sustained: 16384 queries/process, radii 0/4/256, forward `DEFGPQ` and reverse
   `QPGFED` orders. Preserve every raw row and any contamination/failure.
7. Same-campaign NSYS node traces for E/F/P verify launch deltas and unchanged
   downstream signatures. Collect focused NCU only if needed to discriminate
   remaining causes; never use profiler duration as the public denominator.

Public latency is the median of six process-mean completed-query times, including
input transfer, all query kernels, output transfers and host completion; excludes
construction/setup/capture and output hashing. Loop CPU includes hashing and is
reported separately. Retain per-process p10/p50/p90, raw order, paired geomean and
exact six-pair bootstrap 95% interval, six process wins, and order split.
No whole-program/cold-start improvement is inferred from hot-query timing.

Accept each candidate independently only after every correctness/resource/safety
gate, six primary wins, paired lower bound >1.05, and no >5% sustained regression
in its Graph or stream comparison. Otherwise retain a rejected/inconclusive or
unvalidated result with its scope and reopen condition; do not combine candidates
to hide a failure. One bounded win is not production or all-shape admission.

## Safety, artifacts and rollback

Use a fresh task-owned scratch directory; retain prior binaries/evidence without
overwriting them. The monitored runner records child PID, commands, GPU snapshots,
receipts and outputs under `runs/`; abort only its own process group on timeout
or interference. Stop immediately on correctness/sanitizer failure and retain the
failed observation. Public Git contains generators/tests/contracts/summaries only;
external author source, data, binaries, machine details and profiler files remain
private with hashes. Rollback is selecting the unchanged D/E comparator; no
production dispatch or original source is changed.
