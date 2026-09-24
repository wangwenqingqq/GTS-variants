# Graph continuation and scalable result-selection fusion

Experiment: gts_20260924_graph_fusion_scale_words. Designed before implementation.
This is engineering attribution, not a novel tree or compaction algorithm. The
nearest existing mechanism is the repository's already measured stable selector
in fused_result_20260923 (N=2000 only). The cheap falsification is its full-data
scale test, not another small-N kernel demonstration. Original author sources,
prior measurements and the interrupted Graph observation remain immutable.

## Admission and continuation

Only physical GPU 0 is admitted, on the same RTX PRO 6000 Blackwell Server host.
Recheck identity, CUDA/driver, active users/processes, lock and source/binary pins
before GPU work. Initial network probes are not GPU admission. Reuse the existing
nonblocking lock and monitored runner; no foreign signals or setting changes.
Stop and preserve evidence on foreign activity, errors, timeout or mismatch.

First use the original scale binary (SHA256
`ef898b0709155c2192c6032a06282fa455cd8c0488cbb8b331fff67ebd276bcf`)
from graph_scale_20260923 in a fresh continuation root. Verify its corresponding
source/runner pins and the prior full-output/sanitizer/stress evidence hashes.
Repeat full-output smoke A/B/C at full N, K=1 and K=32. Collect the four missing
B/C NSYS node traces, then restart all six K32 rounds (ABC,CBA,BCA,ACB,CAB,BAC)
and both sustained orders from scratch. Never splice these with the prior clean
first round or replace its interrupted second round. Prior results remain a
separately dated campaign; NSYS continuation is labeled diagnostic evidence.

## New 2 x 2 campaign

Frozen shapes: (N,K)=(2000,1),(100000,1),(611756,1),(611756,32). K is serial
query bundling, not concurrent traversal. Reuse exact scale fixtures: 64 distinct
deterministic IDs, byte-string integer edit distance, inclusive radius four,
self matches, full native-ordered count/IDs/FP32 distances on host. Data and tree
are immutable. Heights and conservative capacities are derived identically to
the scale driver; tree coverage is checked before every process.

| Mode | Result processing | Submission |
|---|---|---|
| B | Original fixed-capacity sequence | Ordinary stream |
| C | Same as B | CUDA Graph |
| D | Stable fused selection + projection | Ordinary stream |
| E | Same as D | CUDA Graph |

Use the unchanged scaled B/C enqueue branch. D/E replace only the result-stage
sequence with the existing cooperative selector, generalized from 111 candidate
slots to a checked runtime capacity. Retain the deletion-prefix scan, distance
calculation, traversal, candidate construction, host copies and full allocated
workspace. No copy-volume optimization, multi-query parallelism, candidate
fusion or traversal transformation is mixed into this test. Use CUB BlockScan;
no new dependencies or scan framework. This coupled sequence reuses ranks and
aggregate from one scan, avoiding duplicate reductions and intermediate payload
writes. It is not attribution to each eliminated suboperation independently.

## Role, live-state and readiness card

- Existing leaf CTAs produce flags and payload; a same-stream kernel boundary
  establishes global completion before result selection.
- One 512-thread CTA scans consecutive 512-slot tiles up to candidate_count*20.
  Every lane participates, including tail lanes; only hits read payload.
- Each lane owns a rank, aggregate and identical carry. Hit lanes emit unique
  carry+rank output positions and mapped IDs; thread 0 publishes final count.
- All lanes synchronize before CUB scratch reuse. No global spin protocol,
  inter-CTA barrier, atomics, distance-DP local array or payload shared tile.
- The deletion-prefix scan precedes projection. Pinned output copies complete
  before device scratch reuse and host consumption; K staging slots are distinct.
- Expected costs: one-CTA tile loop grows with candidates; retained padded copies
  still cost up to 17,777,764 D2H bytes/query. No bandwidth-saturation assumption.
- Expected savings: duplicate flag reductions, hit scan, intermediate compaction
  and separate projection kernels/traffic. Native distance work is invariant.
- Inspect final REG/STACK/LOCAL/SHARED and selected-function SASS. New spilling or
  unexpected large stack blocks promotion pending diagnosis. One CTA is a tested
  design limit, not a claim of an optimal scalable compaction implementation.

## Validation and measurements

1. CPU-only generator tests reject drift and check preserved B/C code. Standalone
   selector tests exercise all four capacities, zero/one/max candidates, tile
   boundaries, dense/sparse/empty hits, poisoned inactive flags, nonidentity maps,
   tail guards, large-small-zero rollover and fresh allocations. Run clean plus
   memcheck/synccheck/initcheck/racecheck on the selector.
2. Full CPU-oracle/native-order smoke A/B/C/D/E at all four shapes and 64 IDs.
   At K=1 each N, use four changing IDs for radius 0 and 256; negative radius
   probes cover B/C/D/E, not the known unsafe native empty launch.
3. Full-query D/E memcheck/synccheck/initcheck and racecheck at each K=1 N;
   use four IDs. At full N K=32 use 32 changing IDs for D/E memcheck/synccheck
   and initcheck; standalone racecheck validates the new shared collective.
   B/C reuse pinned implementation but get fresh full-output checks plus
   memcheck/synccheck at each K=1 N. No leak or production certification.
4. Stress B/C/D/E per shape: 1024 changing queries, warmup 64, oracle-derived
   ordered output hashes. Pointer churn comes from fresh processes.
5. Six primary fresh-process orders: BCDE,EDCB,CEBD,DBEC,DEBC,CBED. Warmup 64,
   retained queries 256/process. Same host-wall scope as scale: input staging
   through completed host count/IDs/distances. Hashing is outside query time,
   inside loop CPU. Report setup/capture/first bundle separately. At K>1 report
   bundle latency and amortized query time, never individual response latency.
6. Sustained radius-four rounds BCDE and EDCB: 1024 queries/process, all shapes.
   Extra radius-zero/all-hit sustained controls at full N K=1: 128 queries/mode
   for both orders. These bounded checks are not thermal or service validation.
7. NSYS B/C/D/E at full N K=1, plus C/E at N=2000 and full N K=32. Verify matched
   retained phases, removed result operations and unchanged explicit copy volume;
   retained signatures include geometry/resources. Profiler durations diagnose
   mechanisms only; no NCU or bottleneck claim without corresponding evidence.
8. Primary estimator: ratio of medians of six process-mean amortized times.
   Paired log-ratio geometric mean and exact 6^6 bootstrap 95% interval, per-round
   order, quantiles, CPU and both sustained orders remain visible. Primary fusion
   effect C/E, stream check B/D, Graph effects B/C and D/E; combined B/E reported
   separately. Shape-local fusion promotion requires all six C/E wins, lower
   bound >1.05, and no >5% sustained C/E or B/D regression. Graph is not presumed
   additive. A tiny kernel gain does not waive complete-query regressions.

Timeouts: 300 s clean/profiler, 1800 s sanitizer. Preserve every failed or
contaminated process. Missing gates mean unvalidated, not a substituted pass.
Publication contains portable code, contracts, curated evidence and hashes only;
raw source/data/binaries/host details stay in private evidence archives.

## Append-only preparation notes

- Admission is blocked before any new GPU benchmark: the gateway responds but
  target SSH/GPU queries did not reliably complete; the final bounded SSH probe
  timed out during banner exchange. The cause and GPU occupancy remain unknown.
  No foreign process or machine configuration was modified.
- Runner safety-only hardening bounds NVML queries and reaps owned benchmark/
  monitor processes on telemetry, launch or collector failures. CPU-only injected
  failures exercise this path; CUDA runtime behavior remains unvalidated.
- Successful phase markers bind benchmark/selector binaries and receipt hashes;
  timing/profile requires preceding correctness and sanitizer/stress stages.
  Original continuation carries prior gates only for its exactly pinned binary.
