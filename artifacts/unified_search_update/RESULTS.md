# Unified integration qualification — 2026-10-09

**The scoped unified executor passes functional qualification and the frozen
legacy-PAR <=5% non-regression screen. No positive speedup is established.**
This is synthetic initial N1000/D128/B1 with integer-valued FP32 coordinates,
K8/K32, shared original-GTS physical-row reinsertion/live-rank deletion, and
occupancy-10 rebuild. It is not paper-wide GTSPP or an external comparison.

## Verification evidence

-31 guarded GPU processes;90411 complete queries and116219 events checked.
  Independent raw-output replay checks75213 range and15198 kNN answers,
  including1039 missing slots with exact `(-1,+inf)` normalization.
- PAR+BOUND, PAR+FULL and NATIVE+FULL agree on full ordered output bytes for
  high-entropy boundaries, all ties, deleted seeds, empty live sets,
  fewer-than-K answers, buffer first/last deletion and rebuild rollover.
- Three boundary sanitizer processes (memcheck/racecheck/synccheck) and one
  sparse-rollover memcheck pass with zero errors/hazards.11 malformed direct
  input checks fail before explicit GPU allocation;8 CPU guard mutations are
  rejected, with a valid control retained.
- Two mixed10k traces, K8/K32, each contain5000 range +5000 kNN,1000
  reinsertions,1000 deletions and50 rebuilds. These are synthetic shared-state
  stress, not the prior N1M final10000 static comparison.
-20 integrated and16 untouched legacy source hashes, all binary/input/output
  hashes, every registered job and lock/foreign-compute receipt are verified.
  kNN persistent workspace peaks at546056 bytes and ends at0. No other user's
  process is stopped or modified.

## Fresh same-campaign PAR regression

Denominator: observer-on warm12000-event trace with10000 range queries,
including every ACK/full D2H result, all updates, compaction, tree construction,
PAR refresh, **kNN mirror repacking** and final release/drain. Context, initial
setup/build/layout, host strict parsing/validation and disk output are excluded.
This is not full cold/process latency. The old stage decomposition covers the
range branch only; kNN is included in whole-trace/ACK but has no new per-stage
partition, so stage sums cannot explain the mixed total.

| Pair | Execution order | Legacy PAR ms | Unified ms | Unified /legacy |
| --- | --- | ---: | ---: | ---: |
| 1 | Legacy -> unified | 13929.074401 | 13876.479263 | 0.996224075 |
| 2 | Unified -> legacy | 13858.453692 | 13935.053012 | 1.005527263 |
| 3 | Legacy -> unified | 14042.638082 | 14036.462356 | 0.999560216 |

Frozen paired geometric-mean ratio: **1.000429790**;
95% process bootstrap interval **[0.996224075,1.005527263]**,
20000 resamples, seed202610090913. Each ratio and the upper bound are below1.05.
The point estimate is a0.043% increase, not an acceleration. The three pairs
are alternating with a2/1 direction split, not equal-count direction balance.
Direction-specific ratios are0.997890751 (legacy first,2 pairs) and1.005527263
(unified first,1 pair). The tiny three-pair screen does not support a broad
performance inference.

Marginal p10/median/p90 ms: legacy13872.577834/13929.074401/14019.925346;
unified13888.194013/13935.053012/14016.180487. Retain every process, including
the unfavorable reverse pair. Do not substitute old13.9s values as comparators.

## Retained unfavorable kNN control

| Mixed trace (10000 total queries) | K | Mode | Warm trace ms |
| --- | ---: | --- | ---: |
| Mixed8 | 8 | BOUND | 8695.526470 |
| Mixed32 | 32 | BOUND | 8583.566030 |
| Mixed8 unpruned control | 8 | FULL | 8177.520451 |

The single mixed8 BOUND observation is about6.33% slower than FULL. This is
one process per variant in fixed non-paired order, so it neither establishes a
robust pruning regression nor supports a cutoff speedup. The added seed score,
selection and cutoff launches are an **inferred possible cause**, not a
profiled attribution. The default is not switched post hoc to the fastest
single sample. Reopen this decision only with a new predeclared pure10k-kNN,
paired sustained campaign that includes update/layout costs and large-N shapes.

## Decision, provenance and remaining work

- Implementation: scoped functional integration admitted; original PAR path
  passes the narrow non-regression screen. Mechanism/thesis: no new novelty,
  no additional coalescing/pruning/end-to-end acceleration claim.
- Published evidence: [VERIFIED.json](VERIFIED.json). Executed implementation
  checkpoint `574a9fa088a87304865cee1abad4ff2087ac85c3`; original GTS pin
  `3bac1b725e92e98e3b69d5cb79ad9c56ccb5e639`. Target RTX PRO6000 Blackwell
  Server, driver590.48.01, CUDA13.1.115. Raw inputs/results, failed attempts,
  complete source/binaries and machine receipts remain outside Git; the archive
  digest binds them without publishing identifiers or private data.
- Local preparation A failed on provenance JSON schema; remote A was rejected
  before build because macOS archive metadata added extra header files. Remote B
  used a clean `git archive`, passed all declared GPU jobs, and preserved both
  failures. They are not deleted or reclassified as passes.
- Next contract: actual large-N shared workflow, pure10k kNN, sustained
  repeated/order-balanced processes, production ID/arrival semantics and
  matched Faiss-IVF/CAGRA comparison. None is silently inherited from static
  experiments or this N1000 integration. Paper manuscript remains untouched.
