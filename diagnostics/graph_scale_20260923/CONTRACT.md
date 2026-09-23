# GTS Graph scale campaign (preregistered)

Experiment: gts_20260923_graph_scale_words. Engineering attribution, not novelty.
The nearest mechanism is standard repeated-work CUDA Graph replay (NVIDIA 2019,
2024); the cheap question is whether the prior small-N benefit survives scale.
Do not combine result fusion, traversal deduplication, layout or distance changes.

## Frozen workload and variants

- Original source pin: 3bac1b725e92e98e3b69d5cb79ad9c56ccb5e639, unchanged.
  Reuse graph_query_20260923/graph_bench.cu, SHA256
  6065bd4b9f2de6cb231ca416afeea55dce395f5d2713c37aae1c79c0a60ee3a5.
- Real Words byte strings: N=2000,20000,100000,611756; evenly spaced subsets,
  full original at the largest N. Immutable tree, inclusive r=4, self included,
  no updates, complete CPU-resident IDs/distances/count and native stable order.
- 64 deterministic IDs: 32 evenly spaced plus 32 seeded random unique IDs,
  shuffled with a fixed seed. Independent full CPU integer-DP distances.
- A: configured original functions under common host driver. Tree height limit
  selected before construction so every leaf fits MAX_SIZE=20; fanout=10.
  This is NOT the untouched default-height executable. No original source edits.
- B: scale the prior fixed-capacity stream pipeline; C: capture exactly B.
  Node capacity is sum(10^level); object capacity = node capacity * 20.
  Retain all reductions, scans, distance code, 512-thread original kernels,
  deletion prefix and fixed-capacity CPU output copies. No fusion/prefetch.
- Primary shape set (N, serial-query bundle K): (2000,1),(20000,1),(100000,1),
  (611756,1),(611756,8),(611756,32). K>1 means sequential queries in one stream,
  one final synchronization, independent pinned input/output staging per query;
  NOT parallel batched traversal. Scratch is reused only after preceding copies.
  Report batch completion latency and amortized time/query, not individual latency.

## Safety and ownership

- Physical GPU 0 only on the verified RTX PRO 6000 Blackwell Server Edition;
  CUDA 13.1.115, sm_120, driver 590.48.01. Existing nonblocking lock, idle/foreign
  process checks before/after each process and during runs. No GPU setting changes,
  no foreign signals. Own scratch only; source/data read-only. CPU is shared.
- Freeze binaries before gates. Same B/C binary and enqueue function. Source and
  command hashes, all process order, errors and profiler evidence retained.
- Tree audit before queries: all live nodes in bounds, leaves <=20, leaf intervals
  partition N, permutation of input IDs, no unresolved live internal nodes at
  last level. Incomplete default-height trees are not benchmark comparators.
- Predicated inactive leaf blocks cannot read candidate entries. Reset all flags
  before each query. Same-stream global boundaries preserve reduction/scan/
  scatter/distance/compaction readiness. Fixed output copies complete before
  scratch overwrite; host consumes only after final bundle completion. No new
  shared handoff or custom barrier; original resource footprint is retained.

## Measurement and gates

1. Full native/CPU output checks at r4 for all primary shapes and all 64 IDs;
   boundaries r0 and r256 use four IDs, K=1 at every N. B/C negative-radius
   empty-frontier probes at largest N; native zero-grid failure is already known.
2. memcheck/synccheck A/B/C at every N (four changing IDs, K=1); initcheck B/C.
   Largest K=32 memcheck/synccheck/initcheck B/C with 64 changing IDs. No leak
   certification. Output order and float32 bits match native; CPU distances exact.
3. Stress: 1024 queries/mode/primary shape, checked against full oracle-derived
   ordered hashes. Fresh processes provide pointer churn. Reject any mismatch.
4. Six primary fresh-process rounds: ABC,CBA,BCA,ACB,CAB,BAC; 64 warmup queries,
   256 retained queries/process. Scope: host-wall submission through completed
   full host results and A teardown; no hashing/logging in timed interval.
   Build, setup, capture and first bundle recorded separately; loop CPU includes
   host hashes. K>1 timer covers a whole bundle and is divided by K only for the
   amortized metric. No cross-N or cross-K ratios interpreted as pure Graph gain.
5. Sustained: B/C forward and reverse, 1024 queries/process for each shape.
   These are bounded repetition checks, not service or thermal certification.
6. NSYS node traces of B/C at largest N, K=1 and32, after gates; validate ordered
   kernel sequence/geometry, copy bytes and host API counts. Profiler timings
   are diagnosis only. Resource dump retained; no NCU claim from this campaign.
7. Primary estimator: ratio of medians of six process mean amortized query times.
   Secondary: paired geometric ratio, exact 6^6 paired bootstrap 95% interval,
   all process means/order splits/p10,p50,p90. Shape-local acceptance requires
   all six C wins, paired lower bound >1.05, sustained no >5% regression and all
   correctness/safety gates. Otherwise measured neutral/regression/inconclusive.
   Do not hide component regressions behind an aggregate or switch estimator.
- Stop on runtime error, mismatch, capacity/coverage failure, foreign GPU activity,
  or timeout. Limit: 300 s clean/NSYS, 1800 s sanitizer. Preserve failed receipts;
  do not silently replace failures. If a gate blocks an entire shape, report it
  as unvalidated and continue only independent admissible shapes.

## Expected mechanisms and boundaries

Graph reduces host submissions, not useful distances or GPU kernels. Scaling N
increases original traversal/reduction work plus padded scans and copies; scaling
K increases graph nodes and host staging bytes while amortizing submission/sync.
Both a persistent Graph benefit and a vanishing/regressing benefit are admissible
outcomes. Full-result correctness is mandatory even if it exposes native limits.
No universal GPU-tree conclusion, no production promotion, no paper novelty claim.
Public output: portable harness, summaries, source/data/raw hashes only. No raw
fixtures, original source copies, host addresses, profiler files or credentials.

## Append-only preparation notes

- Before GPU gates, add one setup-only device synchronization after initializing
  inactive output payloads on the default stream, to establish readiness before
  the nonblocking query stream. Charged to setup, identical for B/C; no hot-path
  change. The pre-sync build was compiled but never executed; retain its hash.
- The first CPU-oracle wrapper failed because the host lacks /usr/bin/time; no
  oracle or GPU workload ran in that attempt. Preserve logs and use Python's
  monotonic/resource timing rather than installing a utility.

- Collection interruption: after five complete timing/sustained shapes, a foreign
  GPU 0 process appeared during n611756_k32/timing_1_C. The monitor stopped only
  the owned benchmark (SIGTERM); retain its failed receipt and partial round.
  Do not count or replace this observation. K32 timing/sustained and all four
  planned NSYS traces remain incomplete. Publish the five completed comparisons
  with this explicit boundary; promotion requiring missing evidence is blocked.
  A continuation requires fresh GPU admission and separately identified runs.
