# REGION_WARP frozen design

Parent: GTS-variants `a7b16a672eb8b744e5d8bfbfeff2acc2bfe3b51a`.
User plan: `GTS_REGION_WARP_简要完备工作计划_20261008.md`.

Gate 0: warp-per-leaf ownership and local kernel fusion are established CUDA
engineering techniques. This is one mapping intervention, not a novelty claim.
The cheap falsification tests are the actual query-region opportunity inventory
and a bounded 8-leaf x20-object microcheck. No new radius, seed, budget or input
selection is allowed after viewing the inventory.

## Contract

- Target: isolated RTX PRO 6000 Blackwell Server SM120, CUDA 13.1.115,
  driver 590.48.01, same NUMA binding and dual-lock runner as the parent.
- N1000/D128, integer-valued FP32 storage, B1, radius0, seed2026100431.
  10000 queries, 1000 physical-row reinsertions, 1000 live-rank deletions,
  50 actual occupancy10 rebuilds. Logical duplicates stay distinct.
- Original ascending-dimension pow/float accumulation and self branch unchanged.
  One thread owns an object's entire distance; no warp floating-point reduction.
- 256 threads/CTA, 8 warps, original region 256-object/128-node budgets.
- No new tree/layout, precision, dynamic queue, cross-query batching, allocation
  policy, update mapping or collector. Dense final arrays remain unchanged.
- Primary: continuous 12000-event Host-ready/ACK trace, complete D2H output,
  paid refresh and rebuild, final release/drain. Secondary setup+trace includes
  load/output-buffer/cold-build/initial plan; context and post-timing writes/audit
  are separately reported. Nested maintenance intervals are never added twice.

## Ownership, live state and ready graph

| Phase | Owners | Live state | Publication / last use |
|---|---|---|---|
| query load | full CTA | shared 128-float query | existing CTA barrier before traversal/verification |
| traversal | unchanged CTA | existing frontier/next/leaf lists | last existing traversal CTA barrier publishes leaf list |
| nl0 | full CTA | uniform nl | uniform return |
| nl1 | full CTA | old object loop | unchanged verify_leaf |
| nl>=2 | warp w owns leaves w,w+8,...; lane l owns j=l,l+32,... | per-thread node/id/float distance and loop indices | no barrier inside warp-specific leaf loops |
| hit store | unique (leaf_slot[nid]+j) owner | unchanged final arrays | stream completion before common reduce/scan/collector |

Expected useful distance work and dimensions: identical. Mapping exposes up to
8 independent leaves within one CTA; it does not change bytes algebraically or
promise coalescing. Added state is warp/lane/leaf-loop indices; shared memory is
unchanged. Any register/stack change is recorded from the new binary, not guessed
as an occupancy or slowdown cause. No register cap or Tensor Core is introduced.

## Five-mode campaign

A PAR_STRONG; B SPLIT_SERIAL; C FUSED_SERIAL; D SPLIT_WARP; E FUSED_WARP.
Orders: ABCDE, EDCBA, BDAEC, CEADB, CAEBD, DBEAC. Every pair has 3/3 ordering.
Six fresh processes/mode, 30 primary processes, no replay of failed/slow runs.
New observer identity: six alternating on/off pairs/mode, exact output identity,
paired bootstrap upper95 <=1.03. Rejected observation cannot be relabeled passed;
if rejected, whole-trace off timing is possible but tails/stages are not admitted.

Paired geometric baseline/candidate ratios; 20000 bootstrap resamples,
seed202610081022, 95% interval, wins, process distributions and order splits.
Comparisons: B/D, C/E, D/E, A/E, A/D; secondary B/C retained.
A confidence interval spanning 1 is inconclusive, not a stable speedup.

## Gates and stop

Reuse parent structure/fallback/stale/capacity and mixed update checks. Add nl
0/1/7/8/9, size1/20/32/33 (only budget-admissible combinations), mixed ragged sizes,
deletion and high-entropy integer data. Compare exact object counts, canonical
slots, integer membership and SERIAL FP32 fields; audit actual warp owners.
memcheck/racecheck/synccheck, pointer churn and repeated state clearing are required.
Counter and micro/profiler runs are separate from primary timing.

Opportunity inventory reports every query-region, including inactive regions:
0/1/2-8/>8 leaves, candidate objects and actual non-self distance evaluations.
Missing parent epoch/leaf/object mapping is recovered with one diagnostic-only
counter trajectory; its work stream must exactly match retained parent records.
If opportunity is almost absent AND the microcheck does not improve, stop before
primary without claiming measured real-workflow failure. Otherwise finish all
30 processes. No expansion unless a separate contract is approved; micro/kernel
wins cannot substitute for complete-workflow gains or external baseline evidence.

Synchronization reference: [CUDA 13.1.1 language extensions](https://docs.nvidia.com/cuda/archive/13.1.1/cuda-programming-guide/05-appendices/cpp-language-extensions.html).
