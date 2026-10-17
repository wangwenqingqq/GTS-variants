# Real-trace dependency opportunity: decision package

**Decision: EVIDENCE_INSUFFICIENT for observed vector-service opportunity;
retain the engineering keeper. No new mechanism or GPU claim is admitted.**

The public-input study found a concrete distinction: actual CMS target repetition
exists, but does not provide a vector request/ACK trace. The available public
Wikipedia benchmark workloads are generated update distributions; under an
explicit packed-store adapter they offer no deletion-copy assignment elimination.
Those are separate findings, not a universal real-world negative.

## 1. Redundancy → mechanism → module → role → end-to-end evidence

| Proposed redundancy | Mechanism/module | Role of this experiment | Complete-service evidence |
|---|---|---|---|
| Repeated edits to an upstream content object | `capture.py`, `metadata.py` | Observe logical reuse; reject transport pages as vector commits | UNKNOWN: vector mapping/ACK/readers absent |
| Repeated physical row assignments inside legal public runner calls | Frozen generic propagation via `replay.py` | Count M/F with all allocated symbolic rows preserved | No assignment elimination in these adapter inputs; actual service unmeasured |
| Extra work to discover a final plan | `cpu_cost.cpp`, frozen generic/wave planners | Isolate charged CPU construction+destruction | CPU-only diagnostics below, not ACK or events+release |
| Suggested new Tail/kernel mechanism | None implemented | Do not rescue the old specialization with a new name or larger batch | Not admitted |

## 2. Actual source observations are not vector-service transactions

The frozen English Wikipedia metadata window is **2026-10-16 00:00–01:00 UTC**,
namespace 0, edit/new only. It contains **4,286 events**, **3,164
distinct pages**, **1,122 repeated-target events / 26.1783%**.
There are 555 pages with multiple events; the maximum is
32. These are repeated targets, not duplicate source events.

| Check | Observed result |
|---|---|
| API pages / requested interval complete | 9 / yes |
| edit / new records | 4,204 / 82 |
| Per-page event count p50 / p90 | 1 / 2 |
| Repeated-page time gap p50 / p90 | 112.5 / 834.7 seconds |
| Within-capture revision links / discontinuities | 1,121 / 1 |
| Globally decreasing recentchange-ID transitions in API order | 1,096 |
| Repeated targets within transport pages | 669; **not an ACK-local opportunity** |
| Vector request/ACK, initial layout, chunking, query/snapshot readers | UNKNOWN |
| Vector-store M, F, weighted elimination and service gain | **UNKNOWN, not zero** |

The source order and its one revision-chain discontinuity are retained, not
repaired or sorted into a fictitious global service order. No page content,
actor names or IP addresses are requested. No CMS IDs/events are published.
This fixed hour is not a representative sample of vector services or even other
Wikipedia hours. The [source admission audit](SOURCE_ADMISSION.md) explains why
real vector datasets, upstream edits and a deployed vector-index update trace
are different evidence levels.

## 3. Exact public logical replay, declared physical adapter

All three original 1M runbooks are replayed completely, with **854 runner calls
and 300 search barriers**. No scaling, resampling, reordering or cross-call
batching is performed. B means faithful public logical replay; their generated
update distributions remain **C**, not A-grade production traces.

**1M is the source vector pool, not a fixed live database size.**

| Fixed runbook | Source pool | Peak live | Final live | Insert points | Delete points | Replace points | M | F | Weighted elimination |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Expiration/replace+delete | 1,000,000 | 415,355 | 409,851 | 713,258 | 303,407 | 215,020 | 303,407 | 303,407 | 0.00% |
| Expiration/replace-only | 1,000,000 | 698,369 | 698,369 | 698,369 | 0 | 242,696 | 0 | 0 | NA (M=0) |
| Expiration/delete | 1,000,000 | 410,000 | 400,000 | 1,000,000 | 600,000 | 0 | 600,000 | 600,000 | 0.00% |

M is non-self swap-delete row-copy commands. F is final nonidentity original-source
assignments. The weighted ratio is `(sum(M)-sum(F))/sum(M)`, not an average of
batch percentages. F is an opaque-entry-row copy-propagation count, not a lower
bound over arbitrary representations, compression or lazy indirection. When M=0
it is undefined/NA, not a demonstrated 0% saving.
Replacement is stable-ID **in-place payload overwrite**; calling it delete+insert
would change the workload/storage contract and invent extra row moves.

The complete original-call analysis has **104 deletion calls, M=F=903,407 and
RAW=WAW=WAR=0**. All nonempty call-level batch elimination p50/p90 values are 0.
The at-most-512 internal subdivision gives the same M/F across **1,814 subplans**;
it does not create extra client ACKs or cross a source request return. Both
scopes are reported, so a whole-call opportunity is not hidden by a 512 cap.
The replace-only input has no deletion calls or deletion-copy denominator.

This is conditional on packed append/swap-delete and its original row order.
Source ANN systems may use tombstones, partitions, graph repair or a different
layout; their own physical work is not measured. All symbolic allocated row
values—including retired rows—plus inverse maps and logical payload authorities
are checked. Search barriers validate symbolic state, **not ANN/exact query
outputs, native distance fields or latency**.

The mixed replace/delete stream has 136,593 repeated non-insert target events
across distinct calls, yet no copy dependencies in this adapter. Repetition is
not by itself a physical-dependence predictor. Detailed lifecycle step counts,
batch depth/width, both scopes, every call and all regressions are retained in
[results/REPLAY.json](results/REPLAY.json) and [tables](tables/structure.csv).
Lifetimes are measured in source-call/mutation steps, not fabricated wall time.

## 4. Bounded strong-planner cost evidence

The two existing generic planners are compiled unchanged from the parent headers
into a standalone **C++17 -O2 CPU diagnostic**, on one selected core of the
replaced-CPU Xeon Platinum 8575C host. Twelve processes cover two inputs and six
rounds. Both planners run per batch, forward/reverse order balanced across rounds.
The core is not exclusive and no CPU/GPU hardware setting is changed.

**These are CPU plan construction plus destruction, not Host-return ACK.**
Each total is the median of six process totals; per-plan means/p95 are medians
of six process summaries, not pooled percentiles.

| Input | Planner | Total planning median (ms) | Per-plan mean (µs) | Per-plan p95 (µs) |
|---|---|---:|---:|---:|
| Expiration/delete | GENERIC_WAVES | 53.585 | 44.654 | 48.727 |
| Expiration/delete | GENERIC_DSE | 65.875 | 54.896 | 58.001 |
| Expiration/replace+delete | GENERIC_WAVES | 28.686 | 46.720 | 53.239 |
| Expiration/replace+delete | GENERIC_DSE | 32.312 | 52.626 | 58.594 |

DSE includes its unique-destination/nonalias certificate; waves includes dependency
construction and grouping. The diagnostic excludes signature computation,
logical replay/raw-input validation/I/O, vector
payload movement, metadata H2D, device execution, synchronization, query handling
and actual service release. It does not divide by an old GPU time to invent an
end-to-end saving. Host allocator peak, actual device activities/DRAM/L2 and all
new Query/Update/Replacement ACK and complete-service metrics are **UNKNOWN**.
Compiler version/source/binary identity are captured; runtime library content
and per-process mappings are not claimed.

For these two no-conflict controls, both plans request the same 8-byte row-move
metadata: **7,227,256 bytes** across the 1,814 subplans. The unchanged executor
source predicts one indexed-copy launch per nonempty subplan for each method.
These are **static requested-work counts, not observed GPU traffic**. Different
assignment ordering could still affect cache/coalescing or service latency even
with M=F; this round does not reject that engineering possibility.

There is therefore no newly admitted real-service cancellation question warranting
a GPU matrix. This is not a claim that coarse GPU execution cannot accelerate
these public workloads. The previous keeper and its historical results remain
unchanged and are not relabeled as measurements of this study.

## 5. Correctness, closure and retained failures

- Three complete public runbooks and all 300 symbolic search checkpoints pass;
  full allocated opaque row state, retired rows and later append are preserved.
- The small regression program passes 1,555 arbitrary-copy programs, a positive
  M=3→F=1 case, and stable-tag overwrite/retired-row/append checks. Additional
  fixtures cover 511/512/513, zero moves, invalid live-ID lifecycle operations,
  explicit RAW/WAW/WAR pair counts and weighted-vs-unweighted ratios.
- Twelve of twelve registered CPU diagnostic processes pass with no failed
  target or retry. **Zero GPU targets** are launched. No query kernel, production
  dispatch, old source/results or confidential manuscript is changed.
- One transfer preflight rejects 102 macOS AppleDouble extras before any compiler
  or timed target. Intended payload hashes are exact; the failed copy is retained.
  A new portable-whitelist snapshot is used without overwriting/cleaning old files.
- The post-run checker binds frozen sources and original runbooks→independent
  replay→binary cases→all commands/exit status/stdout/stderr/CSV→recomputed costs.
  It rejects extra/missing raw entries and self-reported input replacement, and
  recompiles the diagnostic binary identically without rerunning a timed target.
- **135 raw files** are sealed. A private **155-member** archive retains raw data,
  actual checker snapshot and transfer failure; all sizes/SHA256s are verified
  remotely and locally. Public manifests establish identity, not public download.
  Post-run validators/reference anchors are explicitly post-run, not pre-target
  signatures or hardware attestation.

See [evidence/CLOSED_BINDING.json](evidence/CLOSED_BINDING.json),
[evidence/CUSTODY.json](evidence/CUSTODY.json),
[evidence/POSTRUN_TESTS.json](evidence/POSTRUN_TESTS.json), and
[REPRODUCE.md](REPRODUCE.md).

## 6. Research decision

**Keep the strong generic engineering artifact; do not promote a new Tail or
real-service dependency thesis.** The three generated public inputs provide a
narrow structural negative. The actual CMS record provides real target repetition
but no legal vector composition window. Neither establishes a universal limit.

The remaining question is whether an observed vector-service request/ACK trace,
with known initial storage and reader boundaries, exhibits substantial
within-request cancellation. That evidence is absent here. Do not replace it
with API pages, daily epochs, pooled independent ACKs or a larger synthetic batch.
Real-trace dependency and complete-service plots are therefore **not admitted**;
readable source/structure/cost tables are supplied instead of fabricated figures.
