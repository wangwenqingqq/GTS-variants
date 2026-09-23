# GTS fixed-capacity stream versus CUDA Graph

Experiment: `gts_20260923_graph_single_query`. Preregistered before implementation.
This is an engineering attribution experiment, not a new research contribution.
CUDA Graph replay for short kernels is established (NVIDIA, 2019 and 2024).

## Contract

- Original author revision: `3bac1b725e92e98e3b69d5cb79ad9c56ccb5e639`.
  All original CUDA source files remain byte-identical in a separate source copy.
- Words N=2000, byte-string edit distance, tree height 3, fanout 10, leaf capacity
  20, batch one, immutable tree, no insertion/deletion. Normal radius 4 inclusive.
- Full returned IDs, distances, count and original stable order; not count-only.
  Independent CPU DP oracle checks membership/distances, A supplies native order.
  Include negative/zero/large radii, changing queries, zero/all hits and replay
  state reset. No claim for larger trees, full dataset, concurrent queries or kNN.
- Physical GPU 0, RTX PRO 6000 Blackwell Server Edition, only after idle + process
  checks under the existing nonblocking lock. CUDA 13.1, sm_120, same build flags.
  Do not change clocks, driver settings, permissions, or foreign processes.

## Comparators and attribution

- Untouched executable: recompile and rerun the original native lifecycle as an
  anchor, reporting its native counts and time separately from the new denominator.
- A: byte-identical original query functions called by a common driver. Preserve
  native per-query allocation, waits, result aggregation/projection and ordering.
  The driver delivers full results to host and excludes per-query text logging.
  This is an original-function comparator, not an untouched main executable.
- B: reusable fixed-capacity buffers, device counts, fixed grids with predicates,
  original distance/traversal/count/merge kernels, preallocated CUB scan/reduce,
  stream-ordered operations and only final completion for host delivery.
- C: exactly B's enqueue function, captured once and replayed. No fusion or
  distance/arithmetic/block-size changes. B-to-C isolates Graph submission.
- Capacities are 111 node slots and 2220 object slots. Unused hit flags are reset;
  actual counts remain on device. Reuse requires prior completion. Larger shapes
  fail closed. Projection changes its host integer length to a device count;
  all other semantics remain unchanged. Padding and fixed-size output delivery
  are charged to B and C. No allocation reduction is attributed solely to Graph.

## Measurement and gates

- First smoke, then full-output oracle comparison at radii -1,0,4,256. Native
  ordering agreement for all variants. Inspect tree capacity before query runs.
- memcheck and synccheck for A/B/C; initcheck for B/C; stress at least 16384 changing
  queries with count/order/distance hashes. Multiple fresh processes supply pointer
  churn. Every replay resets state; no concurrent in-flight state sharing.
- Warmup 64 queries; normal measurement 4096 queries; sustained 16384. Each query
  timer includes input preparation/transfer, query, host result readiness and
  per-query teardown (A). Construction and one-time setup excluded from hot loop
  but reported separately. Host hashing/checking occurs outside per-query timers.
- Six independent rounds with orders ABC, CBA, BCA, ACB, CAB, BAC. Primary: ratio
  of median process means (sum of query wall intervals / query count). Also report
  per-query p10/p50/p90, paired process log ratios, bootstrap 95% interval, round
  wins and order. Preserve all observations and failures, no selective reruns.
- Accept Graph improvement only when B/C are correct, sanitizer/stress clean,
  all six normal rounds favor C, paired lower 95% bound >1.05, and the sustained
  B/C check does not regress >5%. Otherwise report measured/inconclusive/rejected.
- CPU user/system time for complete measured loop (including host validation),
  not profiler target CPU. First call, capture+instantiate and setup costs are
  separate. Report break-even only if a repeat-query saving is measured.
- NSYS only after clean gates, one short trace per variant on the same workload;
  verify matching B/C kernel sequence/geometry and eliminated host submissions.
  Existing NCU permission denial remains; do not change privileges to obtain it.
- Stop on mismatch, runtime failure, foreign GPU activity, timeout (120 s normal,
  600 s sanitizer). Signal only owned process groups. Raw failures remain.

## State ownership / ready graph

One query owns all scratch and pinned staging. Input copy precedes traversal;
node flags precede reduction/scan/scatter; candidate count/list precede leaf
CTAs; all leaf CTAs finish before hit reduction/scan/compaction; projection and
output copies finish before host consumption or reuse. Same-stream edges become
Graph dependencies, not a custom device-wide barrier. Distance stack/register
footprint is retained and checked, not presumed solved by Graph.

## Publication

Only task-owned source, harness, contract, numerical summaries, evidence hashes
and report. No original-source copies, fixtures, raw profiler outputs, paths,
UUIDs or machine configuration in Git. Preserve adjacent work unchanged.

## Collection notes (append-only)

- The negative-radius zero-frontier stress probe exposes an original A zero-grid
  launch error (although its process returns zero). Retain and reject that run;
  B/C are checked independently for this boundary. Normal radius-4 acceptance is
  unaffected; do not claim native A supports every tested boundary.
- Default NSYS graph-level tracing does not expose C's individual kernels. Keep
  that report and add matched B/C recordings with `--cuda-graph-trace=node` for
  kernel-sequence/geometry equivalence. No benchmark binary or clean timing changes.
- Loop CPU is combined user+system from getrusage; the process wrapper records
  user/system separately. Logging/full oracle dumps are absent from timing runs;
  compact host output hashes occur outside per-query timers but inside loop CPU.
- No NCU measurement was collected in this A/B/C campaign. During report assembly,
  a separate original-flow follow-up established an authorized profiling path;
  the preregistration's historical permission note is not a current availability
  claim or counter evidence for the Graph candidate.
