# GTS pruning-layout control

Preregistered 2026-09-23 before candidate implementation or GPU execution.
Experiment: `gts_20260923_pruning_layout_l2_2000`.

## Question and novelty gate

Can changing pruning metadata/pivot layout, without changing distance arithmetic,
thread ownership, predicate work or pruning semantics, improve completed queries?
Generic SoA, coalescing and compact tree layouts are established engineering
techniques (CUDA best-practices guide; Harmonia, PPoPP 2019). This is a cheap
mechanism test, not a new research contribution or cross-index result.

## Frozen workload and comparator

- Three independently assessed L2 datasets: GIST-1M D=960, Deep-1M D=96,
  T-loc-1M D=2, with source identities pinned to the dataset-profile campaign.
  Sample exactly 2000 distinct uniformly selected base rows with Python seed
  2026092301; sort selected source indices before extraction. Use 64 distinct
  local query IDs selected with seed 2026092317. No native prefix-query bias.
- This first screen deliberately retains the verified original H=3/fanout=10/
  leaf-capacity=20 tree and 111 node/2220 result capacity. A full-million run
  would require a separately validated height/capacity baseline; it is excluded.
- Stored coordinates are float32 with round-trip decimal serialization; inclusive
  Euclidean range, immutable tree, batch one, complete stable ordered host IDs,
  distances and count. No dimension truncation, changed precision, vectorization,
  sparse skipping, query batching/reordering, pivot-distance reuse, arithmetic
  reassociation or traversal fusion. No approximate pruning.
- Normal radius: float32 median of the 64 per-query 50th nonself neighbor
  distances computed in CPU float64 on the frozen float32 fixture. It is fixed
  before any GPU execution. Additional radius 0 and all-hit radius
  float32(maximum CPU query-point distance + 1); radius -1 is an empty-result
  robustness gate. The CPU oracle must confirm exact membership, not just counts.
- Common driver/result-selector from revision 1964108, original author files
  pinned to 3bac1b7. Modes D/E are unchanged traversal + fused results in
  stream/Graph. U/S use SoA pruning pid/lower-bound metadata only. V/L additionally
  use dimension-major, 16-parent-tiled pivot storage (one stored pivot per parent,
  but the SAME per-child distance evaluations). Primary E/S and E/L; S/L is
  secondary packing attribution. D/U/V provide stream correctness/stress checks.
- A uses original functions for full-output/native-order anchors at nonnegative
  radii only. No performance ratio against the untouched executable is claimed.

## Device and safety

The user's authorization for other idle GPUs remains in force. Fresh preflight
found all eight devices free of compute processes. Admit physical GPU 1 only,
RTX PRO 6000 Blackwell Server Edition, 188 SMs, sm_120, CUDA 13.1.115,
driver 590.48.01, unchanged 600-W limit and unlocked clocks. Use UUID-based
snapshots, the existing GPU-1 nonblocking advisory lock, 200-ms process checks
and 100-ms telemetry. Record actual sampling coverage; pre/post checks and an
advisory lock do not guarantee exclusion of uncooperative transient jobs.
Abort only the owned child process group on interference/timeout. No foreign
process, device setting, driver, or service may be changed. Original sources,
prior binaries and observations remain untouched in a fresh scratch root.

## Layout, ownership and cost card

Each pruning thread still owns one child's flag. The original level launch and
parent-clear boundary stay intact, including the two-level loop. Original
per-child scalar metric loops and pruning expressions are copied from pinned
source. No shared memory or new query-time barrier is introduced.

S: two 111-entry arrays store pid and lower boundary; original node structs remain
for the common downstream path. L: S plus a [tile][dimension][16 parent] array,
with 11 useful parents padded to 16. Parent groups are selected from the first
nonempty child; all nonempty sibling pivot IDs must agree. Empty metadata and
padded slots are initialized, never filled from uninitialized nodes.

A separate setup kernel produces the layout after original tree construction.
Its completion precedes Graph capture and queries; storage remains immutable
until final query completion, then is freed. No producer/consumer overlap or
cross-block barrier is emulated. Report allocation+packing+synchronization time,
extra bytes and first-query timing separately, and compute workload-amortized
cost for the measured query count. Layout construction is not free or credited
to hot-query savings. No update-maintenance claim.

Expected: fewer sectors for metadata and distinct pivot coordinates, unchanged
logical distance count and query launch count. Counterexamples: original sibling
broadcast/cache reuse may already be effective; dim-major access may hurt
per-thread locality; padding/setup/cache footprint may cost more than it saves.
A smaller instruction count or sector count alone is not an end-to-end win.

## Gates, timing and decision

1. Source/fixture hashes, generator drift test, fresh common binary, final
   REG/STACK/LOCAL/SHARED and selected SASS. Compare source arithmetic unchanged.
2. Full CPU-oracle output validation at -1/0/normal/all for D/E/U/S/V/L; A anchors
   stable native order at 0/normal/all. Distances must agree with float64 oracle
   within max(2e-6,2e-5*distance), while membership/count are exact. Candidate
   ordered float32 outputs must be bit-identical to the keeper. Any ambiguity
   or baseline mismatch is a failed gate, not permission to drop a query.
3. Diagnostic mode checks per-level flags against the original for all 64
   queries and all four radii; dump flags/tree for useful-work/address analysis.
   Validation instrumentation stays outside production timing.
4. Memcheck/synccheck for all six stream/Graph modes at normal radius;
   initcheck/racecheck for three Graph modes. 8192-query stress per mode.
5. Primary six fresh-process rounds, 4096 completed queries after 64 warmups;
   fixed orders ESL, LSE, SLE, ELS, LES, SEL. Three wins in each pair's direction.
   Public estimator: median process-mean hot completed-query wall time,
   including input/output transfers and host completion, excluding construction,
   setup/capture and output hashing. Also report paired log-ratio geometric mean,
   exact six-pair bootstrap 95% interval, process wins and per-process quantiles.
6. Sustained 8192 queries/process, radii 0/normal/all, forward ESL and reverse LSE.
   NSYS node traces for E/S/L at normal radius check unchanged query kernel count.
   Same-binary NCU profiles first two level kernels per mode/dataset: identical
   sections including MemoryWorkloadAnalysis_Tables. No clock/cache control;
   profiling uses existing authorized sudo. Replayed duration is diagnostic only.
7. Accept per dataset only with all correctness/resource/safety gates, six primary
   wins, paired lower bound >1.05 and no >5% sustained latency regression. Do not
   promote a global layout if any required dataset fails. Keep negative effects,
   packaging cost and reopen conditions. Do not combine layout with a new warp
   mapping to rescue an attribution failure in this campaign.

Sources: CUDA C++ Best Practices Guide, Coalesced Access to Global Memory;
https://cs.tulane.edu/~lpeng3/papers/ppopp-19.pdf . Raw source/data/profiler/machine
artifacts remain private; curated code, contract and evidence may be published
under the existing task-authorized GitHub branch after review.

### Pre-run profiler clarification

NCU uses the stream counterparts D/U/V, so kernel replay profiles the same
pruning device functions without Graph instrumentation. The first two matching
level launches, sections and input query are identical. E/S/L remain the
primary completed-query denominator and NSYS node-trace variants.

### Clock-verification clarification before primary timing

This campaign performs no clock or power-setting operation. The live device
query records a 600-W limit and dynamic SM-clock observations, but does not
expose an independently verifiable current locked-clock range. The earlier
"unlocked clocks" wording is therefore not an established driver-state fact;
report clock control as unchanged/uncontrolled rather than verified unlocked.
Direction-balanced processes and retained raw observations remain required.
