# 100k end-to-end workflow admission draft

Historical preflight, preserved without rewriting its original decisions.
The later scale clarification and literature-backed design are in
[BENCHMARK_PLAN.md](BENCHMARK_PLAN.md). That design targets initial active
N=1M/10M/100M/1B and exactly100000 total vector-level events, including
queries, insertions and deletions. No large-N implementation or measurement
has been admitted. Statements below describing an unresolved100k unit refer
to the earlier preflight, not the current requirement.

Status: **preflight only; not preregistered, built, measured or admitted**.
Parent integration: `0033cb2d1934768411ed1806c6729108f412c1e7`.
This is an extension of an existing mechanism, not a new novelty claim.

## Clarification before cost-bearing execution

The100k unit is unresolved: total queries, total events, or initial object count.
These cannot share a denominator. The intended comparator group is also pending.
Do not launch a formal matrix by silently treating100k as the easiest option.

| Interpretation | Required change | Material limit |
| --- | --- | --- |
| Q100k | Lift query/event/observer limits; preserve a single uninterrupted trace and all update costs | If N remains1000 this is long-workflow stress, not large-N scalability or100k distinct vectors |
| Events100k | Freeze range/kNN/insert/delete counts summing exactly100000 | Query count is less than100k; cannot report Q100k |
| N100k | Generalize packing/top-K scratch/parser/oracle and validate native tree capacity first | Current1024-physical-slot allocation is unsafe for N100k; expensive frequent rebuilds must be screened |

## Preflight procedure (private capture retained,2026-10-09)

The matching public repository branch was checked against the parent checkpoint.
Hardware, software, storage and active-process snapshots are retained privately,
not redistributed as a live machine inventory. The campaign will select one
idle single GPU under the existing dual advisory lock and PCI-derived NUMA
binding. No foreign process or GPU setting is touched. Availability must be
rechecked at admission and every process.

Current direct binary limits: initial N1000/D128, physical base+buffer<=1024,
live<=1010, Q<=10000, events<=12000. K8/K32, B1, FP32 integer coordinates in
[0,255], physical-row reinsertion and live-rank deletion. The observer reserves
Q*(1000+10)*8 host-output bytes; Q100k would reserve808000000 bytes without
changing its policy. This is not the actual answer volume or a memory forecast
for an N100k candidate.

## Comparator eligibility

| Comparator | Native/current supported contract | Admission action |
| --- | --- | --- |
| Original GTS range/update | Existing pinned RNN update loop with full IDs/fields | Remeasure under the identical newly frozen range/update trace |
| Original GTS static kNN | `searchIndexKnn` in search.cuh does not receive tombstones or insertion buffer | A named minimal dynamic adapter needs separate correctness/tie/output qualification before mixed comparison |
| Current PAR strong artifact | Range/update only | Range workflow comparator; mixed kNN needs an explicitly identified adapter, not an invented preexisting API |
| Unified PAR+BOUND | Shared range/kNN/reference-update loop; current small-N scope | Extend only the chosen scale dimension; validate rollover/output/maintenance costs first |
| Unified PAR+FULL / NATIVE+FULL | Same unified exact-kNN verifier/selector, with pruning/range-dispatch ablations | Label as ablations, **not original native GTS kNN** |
| Faiss-IVF/CAGRA | Separate frozen static kNN evidence | Inspect installed update/range APIs or declare wrappers and charge every rebuild/refinement; no automatic mixed-workflow admission |

Never preserve a stale static index after deletion, overfetch silently, omit
buffer candidates, use an approximate result as an exact baseline, or divide
whole-workflow latency by an old isolated-query number.

## Required collection once clarified

- Freeze data size/dimension, operation counts/order/seed, distribution, radius,
  K, duplicate/tie/missing-slot policy, IDs, ACK visibility and rebuild trigger.
- Keep the original native update lifecycle unless a separately named policy is
  compared. Record actual occupancy-triggered rebuilds, not cumulative inserts.
- Pass high-entropy, deleted-seed, empty/fewer-than-K, duplicate-buffer,
  nonaligned-compaction and rollover tests; then applicable sanitizers/stress.
- Use fresh comparator/candidate binaries in the same campaign and one GPU.
  At least six paired rounds with exactly3 A/B and3 B/A orders; preserve failures,
  raw processes/order and negative effects; no post-hoc faster-default switch.
- Report warm full-trace time and a separately defined cold denominator including
  host input parsing, context, initial build/layout/workspace and final drain.
  State whether disk output/CPU oracle is inside or outside each timer.
- Report throughput, CPU user/system/wall and core-equivalent utilization,
  query/insert/delete/rebuild latency tails, maintenance totals, memory high-water
  and every answer/transition correctness gate. Stage sums are attribution only.
- Predeclare process-paired geometric mean and95% bootstrap interval; retain
  marginal p10/median/p90, paired wins, order split and every shape regression.
  A interval crossing1 is inconclusive, not a confirmed end-to-end win.
- Capture diagnostic NSYS/API/copy/host evidence only where it can distinguish
  computation from scheduling/waiting; profiler duration is not the public timer.
- Keep paper files private. Publish only curated task-owned source/contracts/
  numeric evidence after the publication audit; raw data/binaries/machine captures
  and credentials remain outside Git.

## Current decision

No100k result or speedup exists in this draft. Parent small-N functional and
non-regression evidence does not qualify the new100k scope. Next action is to
resolve the two scale/comparator choices, then freeze the executable contract
and run the cheapest admission test before the formal matrix.
