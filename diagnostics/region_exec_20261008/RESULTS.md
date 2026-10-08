# REGION_EXEC: first-seed workflow result

## Decision

**The bounded-region prototype is implemented and correct on the registered
N1000/D128 serialized workload, but has no incremental workflow advantage over
PAR_STRONG. Do not expand seeds/budgets or promote a fusion contribution from
this campaign.** This is a fixed-workload result, not a universal rejection of
subtree execution or fusion.

The primary consists of all 24 retained fresh processes in the supplied six
balanced four-mode orders. The handoff did not replay, replace, or modify a
primary process. Four new observer identities passed six on/off pairs each;
all 48 qualification processes were retained.

Evidence: [primary statistics](evidence/v2/RESULTS.json),
[all primary rows](evidence/v2/FORMAL_ROWS.json),
[observer qualification](evidence/v2/COST_QUALIFICATION.json),
[independent audit](evidence/v2/INDEPENDENT_AUDIT.json).

Raw rows retain the checker's historical `admission` string saying qualification
was pending. Completed observer qualification and the resulting timing admission
are recorded separately in [FORMAL_TIMER.json](evidence/v2/FORMAL_TIMER.json);
the raw rows were not retroactively edited.

## Frozen scope and denominator

- RTX PRO 6000 Blackwell Server Edition, 96 GiB, SM120; driver 590.48.01;
  CUDA 13.1.115; GPU-isolation guard and NUMA3 binding.
- Seed 2026100431, radius 0, 10000 immediate B1 range queries, 1000 physical-row
  reinsertions, 1000 live-rank deletions, and 50 actual occupancy-10 rebuilds.
- Original integer-valued fixture. The upstream `#define short float` makes
  actual storage FP32, **not int16**. Native float accumulation, ascending
  dimensions, pow expressions, bounds, and self-match handling remain unchanged.
- Primary: continuous 12000-event Host-ready/ACK trace including complete D2H
  delivery, plan refresh inside triggering rebuild/insert, and final drain.
- Secondary setup+trace includes loading, Host output preallocation, cold tree
  construction, and initial plan generation/transfers. CUDA context initialization
  is separately reported, outside both columns. Oracle and output-file writes
  are after timing.
- NATIVE is remeasured in this binary/campaign; history is not the denominator.
  The three new modes share arithmetic, actual-pid reuse, allocation policy and
  canonical collector. This is not P7 kNN, new-vector arrivals, MVCC, or concurrency.

## Primary results

Times are milliseconds. Each entry is the median of six process-level values;
tail entries are the median of six independently calculated percentiles, not
percentiles of pooled samples.

| Mode | Full trace | Setup+trace | Query p50 / p99 | Insert p99 | Delete p99 | Rebuild total | Plan refresh within those rebuilds |
|---|---:|---:|---:|---:|---:|---:|---:|
| NATIVE | 17460.317 | 17552.026 | 1.377 / 5.071 | 4.897 | 1.614 | 238.024 | 0.000 |
| PAR_STRONG | 13960.386 | 14070.948 | 1.167 / 2.871 | 5.132 | 2.469 | 253.127 | 9.122 |
| REGION_SPLIT | 14465.929 | 14576.499 | 1.183 / 2.884 | 5.369 | 2.851 | 258.835 | 9.108 |
| REGION_FUSED | 14414.702 | 14525.430 | 1.171 / 2.879 | 4.993 | 2.842 | 252.150 | 9.046 |

Rebuild is inside insert; plan refresh is inside rebuild. **Do not add these
columns to each other or to the trace.** The sum of stage medians is not the
median trace. Update-tail regressions remain visible even when aggregate trace
improves.

| Comparison, baseline/candidate | Paired geometric speed ratio | Bootstrap 95% interval | Candidate wins |
|---|---:|---:|---:|
| NATIVE / PAR_STRONG | 1.252951 | [1.243869, 1.263562] | 6/6 |
| PAR_STRONG / REGION_SPLIT | 0.963795 | [0.959634, 0.967912] | 0/6 |
| PAR_STRONG / REGION_FUSED | 0.968225 | [0.962080, 0.973090] | 0/6 |
| REGION_SPLIT / REGION_FUSED | 1.004596 | [0.997824, 1.010951] | 5/6 |
| NATIVE / REGION_FUSED | 1.213138 | [1.205126, 1.223597] | 6/6 |

Ratios pair the same round and use the frozen 20000-resample bootstrap, seed
202610081022. These intervals describe run variation on this one fixed trace,
not unseen-input/generalization uncertainty. Raw ratios and before/after order
splits are retained. The fusion interval spans parity; its point estimate is not
a demonstrated fusion win. The PAR/FUSED ratio corresponds to about 3.28% extra
candidate time under the paired estimator.

## Correctness and lifecycle closure

The independent handoff audit recomputed exact integer squared L2 and replayed
the live multiset from input operations, rather than trusting the saved expected
membership. It checked 720000 queries across the 24 primary and 48 observer
processes, exact FP32 result fields, ordered output identity, state transitions,
50 rebuilds/process, source/input hashes, registration hashes, and clean guard
receipts. Each process delivered 14990 result occurrences; equal-vector content
was not deduplicated. This is not an arbitrary-FP32 numerical proof.

The retained structural qualification covers nine topologies, six states and
both region modes, with memcheck/racecheck/synccheck. The handoff added the
missing three sanitizer checks for PAR_STRONG on the small mixed all-pass trace;
each passed the independent full-output/state audit. All three new modes have
51 plan versions in the main trajectory and finish with zero owned plan-device
bytes. These facts do not claim whole-process peak memory or concurrent safety.

[Full-trace counter controls](evidence/v2/FULL_WORK.json) use a separate counter
binary, excluded from performance estimates. Across all 10000 queries and 51
epochs, PAR_STRONG/SPLIT/FUSED have identical per-node, pivot, leaf and object
work streams: 201320 node tests, 20132 pivot evaluations, 11459 accepted leaves,
104515 non-self object-distance evaluations. Buffer handling is unchanged and
is not part of this base-tree work ledger.

## Materialization, resources and CPU evidence

Derived logical base-tree leaf handoff only, not measured DRAM bytes:

| Mode | Leaf-list writes+reads across 10k | Region-count writes+reads |
|---|---:|---:|
| PAR_STRONG | 8000000 B | 0 B |
| REGION_SPLIT | 91672 B | 800000 B |
| REGION_FUSED | 0 B | 0 B |

PAR materializes 100 leaf slots per query; SPLIT writes/reads accepted leaf IDs
and ten per-region counts per query. FUSED keeps this handoff local. The count
ledger proves the compared work sets, not cache-line traffic. Dense node
workspaces, N-sized hit/distance/prefix arrays and stable output collection
remain. All three modes still allocate the same leaf/count workspaces; FUSED
does not claim an allocation-size saving.

Measured plan-device peak is 18908 B in each new mode, cumulative plan-device
allocation 964308 B and topology/plan transfer 601596 B across 51 refreshes.
These exclude native tree, result allocations and Thrust temporaries. The
sampled `cudaMemGetInfo` device-used value in raw summaries is whole-device
usage, not an isolated process peak. Host result capacity is 80800000 B.

Four separate [diagnostic profiles](evidence/v2/CLOSURE_PROFILE_ROWS.json)
cover the same **57 events / 19 queries / two rebuilds**, not the full 10k:

| Mode | query.tree kernel launches | Explicit cudaDeviceSynchronize calls in query.tree |
|---|---:|---:|
| NATIVE | 399 | 209 |
| PAR_STRONG | 152 | 19 |
| REGION_SPLIT | 133 | 19 |
| REGION_FUSED | 114 | 19 |

Thus launch/feedback reduction is observable, but fewer launches did not produce
an incremental full-workflow win over PAR_STRONG. Do not extrapolate this small
profile into measured full-10k launch counts. Profiler durations are diagnostic,
not substitutes for primary timing.

The profiler reports PAR verification grid 100 blocks and region grid 10 blocks;
not all launched blocks have active work. FUSED reports 52 registers/thread and
2064 static shared bytes versus 44 and 512 for PAR verification. The frozen
binary's cuobjdump reports 3088 and 1536 static shared bytes respectively and
40 stack bytes for FUSED. These tool accounting values are retained separately;
their difference is unresolved, and achieved occupancy/spill traffic was not
measured. They do not establish the cause of the slowdown.

Median CPU user time is 16.131 s NATIVE, 13.313 s PAR, 13.823 s SPLIT and
13.750 s FUSED. CPU time, inclusive waiting and GPU activity overlap: **do not
sum them or interpret all CPU user time as useful computation.** The current
evidence supports the relative workflow result, not a new CPU-wait-policy claim.

## Handoff repairs and reproducibility

- Published `region_bridge.cuh` omitted `plan=Plan{}` in final cleanup; the measured
  v2 binary already had it. The publication now matches the immutable measured
  source. No measured kernel or primary binary was changed.
- The prepared profiler controller passed bare `nsys` to a guard that hashes
  `Path(command[0])`. GPU profiling ran, but post-run receipt creation failed.
  Its files remain untouched. `profile_closure.py` uses an absolute resolved
  launcher and fresh diagnostic labels; four clean profiles then passed.
- `finish_closure.py` appended missing PAR sanitizer and full-work counters only.
  `audit_closure.py` independently validates/curates the declared evidence set.
- A fresh source-stage rebuild uses the same frozen input adapters and compiler;
  [source-identity and smoke validation](evidence/v2/ARTIFACT_REPRODUCTION.json)
  are recorded separately from primary timing. Exact binary-container differences
  were not attributed, and selected-kernel SASS identity is not established.
- Generated Python bytecode is removed from active publication and ignored.

Use [REPRODUCE.md](REPRODUCE.md). Raw outputs, immutable source snapshots,
sanitizer logs, profiler databases and guard receipts remain external; see
[raw/curated manifest](evidence/v2/PUBLICATION.json). Paper text remains outside
this public experiment delivery.

## Gate 0 and negative-evidence boundary

Nearest problem-setting baseline: [GTS](https://arxiv.org/abs/2404.00966).
Cooperative GPU tree traversal is established more broadly, including
[JZ-Tree](https://arxiv.org/abs/2604.05885); generic kernel fusion/local
intermediate reuse is not itself a new contribution. This is a lightweight
prior-art screen, not a comprehensive novelty review or a same-contract JZ-Tree
comparison. No novelty claim is admitted.

| Target / keeper | Tested mechanism | Added cost | Measured decision | Reopen condition |
|---|---|---|---|---|
| SM120, registered N1000/D128/radius0 serialized U10 / PAR_STRONG | Resource-bounded subtree execution plus local traversal-verification handoff | Local queues/barriers/live state and paid plan lifecycle; final dense collector retained | Region variants slower in all six rounds; direct fusion comparison inconclusive | A separately registered implementation must resolve a specific measured cost and show same-contract increment over PAR, without changing arithmetic/output/visibility |

Keep PAR_STRONG as an engineering candidate, including its maintenance/tail
exceptions. Keep both region implementations and negative evidence for diagnosis;
do not dispatch/promote them as a faster keeper. No additional seeds, budget
sweep, high-dimensional extension, external ANN matrix or manuscript claim was
started by this handoff.
