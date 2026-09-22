# Original GPU tree redundancy audit

Date: 2026-09-22. Status: source audit and prior-art screening, not a new GPU
performance result. Original sources and running GPU workloads were not changed.

## Conclusion

The inspected GTS and GPU-Tree implementations expose avoidable host allocation
and scheduling work, repeated intermediate processing, and some duplicate GPU
computation. They do **not** establish that every GPU tree is CPU-compute-bound,
or that repeated full-dataset PCIe transfers dominate their queries. Generic
GPU-resident traversal, workspace reuse, and query-to-leaf data reuse are not
sufficiently new research mechanisms by themselves.

The strongest existing measured caveat is a different bottleneck: the bounded
2026-09-17 adapted-author-V2 experiment spent 203.836 / 239.939 ms (84.95%) of its
profiled query timeline in GPU result counting. This must not be relabeled CPU
computation or host-device I/O. See Section 4 before designing a new experiment.

## 1. Identity and interpretation

- Source: [ZJU-DAILY/GTS](https://github.com/ZJU-DAILY/GTS), commit
  `3bac1b725e92e98e3b69d5cb79ad9c56ccb5e639`.
- All 18 `.cu` / `.cuh` files in local `Source Code/GTS` and
  `Source Code/GPU-Tree` match the user's designated remote `SourceCode` tree
  byte for byte. `SOURCE_PINS.json` records SHA-256 hashes. Paths below are
  relative to these two source directories. Build settings, dependencies, and
  existing executables are not covered by that equality.
- GPU-Tree is the **GTS authors' single-GPU general-metric adaptation of G-PICS**,
  not the original G-PICS artifact. Its distance-partitioned implementation uses
  B+-tree nodes and per-tree GPU searches. Adapter limitations must not be
  attributed to the G-PICS paper without independent evidence.
- `config.cuh` defines `short` as `float`. Numeric-data byte accounting must use
  32-bit elements, not assume 16-bit storage from the token `short`.
- Original static GTS range search returns counts; its kNN path returns kth
  distances. These are not automatically equivalent to returning complete
  CPU-resident IDs. Preserve the declared output contract in comparisons.
- The supplied GTS++ manuscript already presents workspace reuse and the
  one-query specialization as C1. Extending allocation cleanup to another
  baseline is engineering evidence, not automatically a new contribution.

## 2. Source-established work and candidate redundancy

A source location proves an active execution mechanism, not its runtime share
or the speedup attainable by removing it. Necessary output, bound construction,
and memory-budget enforcement must remain in any replacement.

| ID | Active source evidence | Interpretation and limiting condition |
|---|---|---|
| G1 | GTS `search_v2.cuh:18-33, 838-965, 1039-1220`: host stack, synchronous kernels, GPU reductions returning scalar counts, host-controlled next batch | Data-dependent host/GPU control round trips. CPU runtime work and waiting are plausible; this is not evidence of bulk PCIe traffic or costly CPU distance arithmetic. GTS's bounded-memory batch scheduling has a real purpose. |
| G2 | GTS `search_v2.cuh:30, 785-810`: derive workspace from half available GPU memory, narrow the element count to `int size_a`, zero the entire range-query workspace | For representable sizes, capacity-based allocation/initialization can exceed the active query footprint. Larger extents require a 32-bit narrowing check before any byte-count or correctness claim. Device memset is GPU memory traffic. The analogous kNN full memset is commented out and is not counted. |
| G3 | GTS `tree.cuh:198` assigns siblings the same pivot; `search_v2.cuh:49-134` independently evaluates query-pivot distance for each live child in range search | Exact duplicate distance evaluations, up to fanout for a fully live sibling group (configured fanout 10). This is GPU computation/data access, not CPU arithmetic. The kNN path already has parent-query distance reuse through `getDisPQ` at `1087`; do not claim this affects every GTS query. |
| G4 | GTS `search_v2.cuh:858-915, 1130-1170`: query-node flags, counts, scans, leaf-pair lists, fixed-capacity leaf slots and final aggregation | Dense intermediate traversal/compaction and repeated passes can cost more than the useful surviving work. kNN sorts all `lnum * MAX_SIZE` distance slots at `1160-1162`, while the final contract is kth distance. A top-k/selection replacement must account for cross-batch state and exact tie behavior. |
| G5 | GTS `update.cuh:341-348, 387-390, 423-424, 589-617`: transient query/result arrays; each stream query scans the deletion bitmap at `601` | Per-query allocation plus repeated full-bitmap prefix computation even across queries with unchanged bitmap. The latter can reuse unchanged state but IDs/remapping semantics must be preserved. `552` also scans on deletion. |
| G6 | GTS `update.cuh:484-538, 593-595`; `tree.cuh:361-383` | Buffered insertions cause buffer scans and eventual complete data compaction/rebuild. Rebuild sorts all N keys at each level, not just splitting-node segments. These are GPU operations and structural amplification, not CPU sorting. Incremental indexing and buffer policies have extensive prior art. |
| T1 | GPU-Tree `bplus_tree.cuh:707-718, 733-754, 815-819` | Node budget returns one reserved node per input point; a CPU loop performs a separate `cudaMalloc` for every reserved node (N calls for a valid partition covering N points). This is the clearest build-time host/runtime amplification. Actual insertion/construction runs on GPU, not CPU. |
| T2 | GPU-Tree `search.cuh:941-946, 975-984, 1056-1060, 1070-1074, 1153-1160, 1172-1176` | kNN allocates 2Q bound-search queues and later 2C candidate-tree queues in CPU loops; range allocates C queues. C counts surviving query-tree pairs, not distinct trees. Lifetimes are transient. The range result arrays also reserve 500C IDs and 500C distances, independent of actual matches. |
| T3 | GPU-Tree `search.cuh:955-960, 1085-1090` | CPU loops dispatch one GPU sort per query for bounds, then another per-query sort of merged tree candidates. These sorts have different inputs/purposes, so they are not duplicate sorts; they are opportunities for batched dispatch and suitable selection. `mergeKnn:843-849` contains a commented sort, not a second active final sort. |
| T4 | GPU-Tree `partition.cuh:137-179` | Each pivot partition repeats a full-N flag/scan/merge pipeline, including one scalar D2H count and multiple synchronizations. Repeated full-array GPU passes and host control can be replaced only while preserving partition contents/radii. |
| T5 | GPU-Tree `search.cuh:576-744, 968-987, 1063` | Initial bound search computes actual candidates, carries forward a scalar bound, and destroys its candidate queues. A later tree search cannot reuse those IDs/distances. Duplicate work is a conditional hypothesis when the seed tree survives; count overlap before calling it dominant. The bound also saves later work, so deleting the prepass is not a free optimization. |
| T6 | GPU-Tree `search.cuh:267-576` | Each query-tree task traverses and evaluates its own candidates inside the GPU kernel. Overlapping queries can logically reread the same records; no query-to-leaf registration/reuse stage is present in this adapter. Cache hits mean logical rereads do not equal measured DRAM or PCIe bytes. |

No active static-query path was found that copies the complete dataset back to
CPU on every query. Managed-memory residency/migration remains an empirical
question, especially where host and device touch shared metadata. A source-level
`cudaMallocManaged` call is not a measurement of migration volume.

## 3. Nearest-prior-art kill test

| Prior work | Already-established mechanism | Consequence for this direction |
|---|---|---|
| [G-PICS, author technical report (2019)](https://cse.usf.edu/~tuy/pub/tech09-002.pdf), Sections I and query processing | GPU-contained indexing/query processing; queries register with leaves, then leaf data are reused across registered queries; GPU bulk updates | The broad claim that GPU trees inherently require CPU intervention or cannot share leaf reads is false. Generic leaf-grouped reuse is subsumed. The GTS adapter does not reproduce all these mechanisms. |
| [Harmonia, PPoPP 2019](https://cs.tulane.edu/~lpeng3/papers/ppopp-19.pdf) | Compact B+-tree representation and partial query sorting improve traversal locality/coalescing; sorting cost is part of the design | Generic query reordering and compact GPU tree layout are established. An exact general-metric mechanism needs a distinction beyond applying the same technique. |
| [GPU multiversion B-tree, PACT 2022 artifact](https://github.com/owensgroup/MVGpuBTree) | Concurrent GPU point/range queries and updates with versioned snapshots | CPU-driven per-level control is not intrinsic to every dynamic GPU tree. Ordered key/value indexes do not directly solve general-metric pruning, so this is a mechanism counterexample, not a same-task performance comparator. |
| [Efficiently Indexing Large Data on GPUs with Fast Interconnects, EDBT 2025](https://openproceedings.org/2025/conf/edbt/paper-201.pdf) | GPU lookups into CPU-resident indexes; windowed key partitioning for locality and reduced path divergence | The actual host-memory access boundary has already been studied. Fast-interconnect index lookup/joins differ from an in-device general-metric tree; do not compare their rates as equivalent workloads. |

**Decision:** retain CPU/GPU boundary overhead as a diagnostic hypothesis, not
yet a paper thesis. Reject as standalone novelty: replacing many allocations
with a pool, removing redundant synchronizations, sharing leaf reads, or moving
traversal onto the GPU. A new thesis needs a same-contract mechanism not already
provided by these designs, followed by an advantage over repaired baselines.

## 4. Existing measured evidence and current uncertainty

The 2026-09-17 experiment used **adapted** author V2: Words 611,756 byte strings,
Q32, inclusive radius 4, complete CPU-resident IDs, 1 GiB workspace, PRO 6000
Blackwell, CUDA 13.1 / Thrust 3.1.4. Its raw summary and SASS record hashes are in
`SOURCE_PINS.json`. It is historical bounded evidence, not today's untouched
original executable or a GPU-Tree measurement.

- In two diagnostic traces, mean result-count time was 203.835647 ms out of
  239.939051 ms total. `mergeResRnn` calls device-side `thrust::reduce`; the
  installed dispatch and actual selected SASS execute a sequential per-caller
  reduction. CUDA API waiting can overlap this GPU work and must not be added
  to it as extra CPU compute time.
- The common CPU-ID copy was about 0.030 ms. This is not a complete accounting
  of all possible unified-memory migration and does not prove every workload
  has cheap I/O.
- Independent CPU-result comparison passed in that campaign; sanitizer scope
  was bounded fixtures, not the full dataset. No historical compiler claim
  about the original paper follows from modern Thrust behavior.
- Fixing serial aggregation is baseline/portability repair. It must precede a
  claim that a 200 ms gap is intrinsic GPU-tree redundancy or host-device I/O.
- No new CPU profile or GPU experiment was run in this audit. The user's exact
  high-CPU launch command and stage remain unpinned. Source counts above are
  not runtime attribution percentages.

## 5. Cheapest next experiment and rejection rules

1. Freeze the original high-CPU workload: build vs warmed static query vs mixed
   update stream; metric/dtype, N/Q, radius/k, results/counts/IDs and residency,
   update visibility, memory budget, source/build/library hashes. Validate the
   original fixed-height/leaf-capacity assumptions, 32-bit workspace extents,
   and GPU-Tree queue capacities
   before trusting timing. Keep exact and approximate searches separate.
2. Capture host **user/system CPU time and wall time** separately, plus allocation
   counts/time, launch/synchronization API traces, GPU kernels, explicit copy
   bytes/direction, and managed migration where available. Do not infer CPU
   arithmetic from CPU utilization or an API wait duration. Native CPU sampling
   is permission-restricted on the inspected host; do not change privileges.
3. Use the admitted GPU only after its process/ownership check and task lock.
   Do not silently switch devices or disturb foreign work. No waiting service
   or background automation was started by this audit.
4. Repair the sequential-reduction baseline in a separate variant with identical
   outputs, then run a minimal mechanism ladder: reusable workspace only;
   batched dispatch only; reduced intermediate materialization only. For build,
   measure T1 separately from queries. For range, measure G3 separately from
   host/runtime changes. Re-measure the comparator in the same campaign.
5. Reject the **CPU-compute** diagnosis if high CPU time is runtime waiting or
   startup parsing rather than useful host arithmetic. Reject the **PCIe-I/O**
   thesis if measured transfers/migrations do not account for the denominator.
   Reject standalone research novelty if the improvement disappears against
   standard repaired/pool/batched implementations or is subsumed by G-PICS.
   Conversely, absence of a current trace is uncertainty, not proof of no cost.

Local source-audit artifacts are committed separately from algorithm changes.
Publication remains gated by the unresolved repository visibility/disclosure
question; no upstream source code is copied into this report.
