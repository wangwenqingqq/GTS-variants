# Phase A checkpoint: target-size correctness, not speedup

**At the historical phase-A checkpoint, the capacity/numeric/lifecycle qualification is complete for the declared
scope. No target performance campaign has run.** The final executable completed
original FP32 GIST N1M/D960/B1/K8 insertion, query, deletion, query, a real
occupancy-10 rebuild and post-rebuild range/kNN in A/B/C. Complete ID/FP32-field
payloads and query ordering were identical across all three modes. They also
matched the independently exhaustive CPU reference.

The separate [phase-B result](phase_b/RESULTS.md) now records all 18 target-short
processes and the two native Flat snapshot diagnostics. The phase-A qualification
text below is historical, not a claim that target timing is still unmeasured.

## What changed

| Risk or redundancy | Mechanism | Module | Effect | End-to-end evidence |
|---|---|---|---|---|
| Fixed N1000/D128 and 4K scratch cannot represent the target | Actual header, finite FP32, checked byte products, preplayed capacity, recursive scratch sizing | input / live kNN mirror | Target allocations and tail blocks are representable | Functional qualification only; no speedup |
| Rounded FP32 range membership and old sibling thresholds can disagree with the reference | Ordered FP64 RN membership; directed actual-member intervals and analytically conservative query radius | common numeric bounds + native/PAR/buffer verification | No omitted or extra members in the admitted cases | No performance comparison yet; repairs shared by A/B/C |
| A real neighbor's FP32 field can overflow to infinity | Missing is detected from the identity sentinel, not field finiteness | kNN normalization | Legal finite FP32 inputs retain their actual neighbor IDs | Extreme-value correctness only |
| Compaction invalidates physical layout and scheduling state | Refit, PAR refresh when required and mirror repack before ACK; pointer/epoch guards | original update loop integration | All query kinds observe the same current occurrence multiset | Maintenance is not deferred; cost benefit remains unknown |
| Dense Q*N host answers can require 80 GB | On-demand complete outputs under an equal fixed 1 GiB budget, fail whole run on exhaustion | Host delivery observer | No answer truncation or count-only shortcut | Long output consumption still needs admission |

These are engineering/safety prerequisites, not a new index, a claim about all
GPU trees, or a paper novelty result. Mode A is staged GTS with common repairs,
not untouched original GTS. A does not create PAR-only plans; all three modes
retain the necessary kNN mirror.

## Measured qualification

| Scope | Evidence |
|---|---|
| Header/rank/geometry | 10 portable parser cases; rank replay through N1M; N1M/D960 data bytes 3,840,000,000; two K8 Neighbor buffers of 31,256 items each |
| Legacy D128 | K8 and K32; ties, empty/fewer-than-K, deleted seeds/pivots, first/last buffer deletion, real rebuild |
| Original GIST D960 | N255/256/257/1023/1024/1025/4096; complete exhaustive CPU members/fields and A/B/C byte identity |
| FP32 boundaries | Separate synthetic duplicate and nextafter fixtures; finite extreme input with valid infinite FP32 output fields |
| Transition | N65,536/D960 A/B/C, full CPU oracle and all-member interval checks |
| Million rebuild | 19 events, 8 queries, one actual rebuild, final physical N1,000,009; 41 complete output items, identical A/B/C |
| Million bounds | All 222,220 non-root node intervals over two epochs checked against CPU long-double norms for 10,000,045 member–pivot pairs |
| Exact boundary/nearest check | 16 pairs from initial q0 and the post-rebuild q1 coordinate; independent exact-rational/RN-step reproduction and analytic lower-factor checks |
| Height growth | D128 N1000→N2010, 101 real rebuilds, A/B/C; tree height raised when actual physical size requires it |
| Stale state | Actual common-base pointer, PAR epoch and kNN published epoch corruption each rejected before completed trace output |
| Sanitizers | Bounded memcheck/racecheck/synccheck: 0 errors; million actual-rebuild memcheck: 0 errors and identical full output |

There are 57 successful r5 qualification processes and 22 successful final-r6
processes, plus three expected stale-state rejections. No primary timing process
is counted. The r5/r6 host-only lifecycle corrections have identical normalized
static SASS for all 112 compiled functions (74,147 instructions). This identity
supports the explicitly documented kernel-validation binding; it is not a
speedup, dynamic-work measurement or universal semantic proof. Fresh final-r6
D960, growth, K32, sanitizer and million checks additionally qualify the changed
host flow. The earlier r4 million CPU reference was reused only after exact
ID/field/query and complete audited topology/bounds identity was verified.

The final executable SHA256 and source identities are in
`TARGET_CORRECTNESS.json` and `PREPARED_SOURCE_HASHES.json`.
`QUALIFICATION.csv` retains every admitted validation label and receipt hash;
`OUTPUT_HASHES.json` binds complete private payloads. Private raw logs, admitted
GPU/NUMA/lock receipts, binary/SASS files, complete outputs and tree/bound dumps
remain outside Git. No current device inventory, credentials or manuscript is
published. Qualification wall times are intentionally not used as a performance
denominator.

The public recipe also regenerates extreme-value, growth and million event
fixtures and exposes the K32/growth/million qualification stages. Its 32 emitted
files match the executed r6 fixture/trace hashes. Host replay confirmed all 79
reported A/B/C modes, complete cross-mode outputs and deterministic operation
states; operation timings are checked independently, not compared for equality.
Twelve K32/growth outputs passed the updated full CPU oracle, and a deliberately
incorrect expected mode was rejected. `RECIPE_CHECKS.json` records these
host-only follow-up checks; they add no GPU performance denominator.

## What has not happened / next execution boundary

1. Implement and qualify a separate cloned warmup state, release it, and restore
   the registered initial state before the actual trace. Qualify the affected
   observer and timing scope; do not call the current no-warmup smoke a hot run.
2. Freeze the 336-event short trace: 128 range + 128 kNN + 40 insert + 40 delete,
   two real rebuilds, seed 202610090242. Run six fresh-process balanced orders
   ABC/CBA/BCA/ACB/CAB/BAC (18 primary processes), including every maintenance,
   complete Host-ready payload, ACK and final release in the continuous timer.
3. Diagnose initial and first-rebuilt snapshots against native GPU Flat at the
   same B1/K8 and occurrence mapping (six diagnostic processes). Preserve native
   speeds, ties and each quality mismatch; do not label static snapshots dynamic
   end-to-end evidence.
4. Only after the short result, quality and strong-baseline risks justify it,
   admit the predeclared long range/kNN/mixed traces, up to 42 primary processes.
   Their 10k-query full-output budget still requires actual admission.
5. Change no default and promote no target speedup until those gates close.
   Method/evaluation prose remains in private Overleaf. N1B/E100k is a separate
   benchmark plan, not silently folded into this checkpoint.
