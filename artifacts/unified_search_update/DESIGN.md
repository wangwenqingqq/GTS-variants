# Unified B1 search/update integration contract

## Gate 0 and purpose

Original GTS already includes kNN, range queries and serialized updates. Combining
these interfaces is not a new research mechanism. This work closes an artifact
integration gap, not a novelty claim, and does not inherit static O_MASK/large-N
quality, timing or external-comparison admission. No paper prose is changed.

## Frozen execution contract

- One executable, one live native base, one tombstone bitmap, one insertion
  buffer, one occupancy-10 rebuild stream. Flags: 0=physical-row reinsertion,
  1=current live-rank deletion, 2=inclusive range query, 3=exact kNN.
- Initial N1000, D128, integer-valued FP32 coordinates in [0,255]; B1, K8/K32.
  Range radii 0 and10000. Physical base+buffer <=1024; live multiset <=1010.
- Queries/reinsertions reference physical base rows, even if tombstoned. Output
  IDs are current live-multiset ranks, not stable IDs. Distinct occurrences of
  equal vectors remain distinct. kNN orders (integer squared distance, live
  rank); missing slots are (-1,+inf). Self-matches are included when live.
- Existing PAR range kernels and native update logic are unchanged. The kNN
  B1 default reuses P7 ordered-FP64 verification, AoSoA32 and hierarchical
  lexicographic top-K. The static N1M/D96/D960 wrapper/Graph/mask is not ported
  or admitted; O_BOUND is the documented B1 fallback, not a tree-mask claim.
- New glue publishes tombstone eligibility and live ranks, packs <=9 buffer
  occurrences, and normalizes missing slots. Base AoSoA refresh is inside every
  triggering rebuild before ACK, not outside trace or deferred to another task.
- Seed cutoff is selected from eligible first min(256,total physical slots).
  Fewer than K valid seeds gives infinity, retaining all candidates. Strict
  partial_sum>cutoff pruning retains ties. Buffer occurrences participate in
  final selection and have distinct live ranks.
- Same default CUDA stream for update, layout, score, selection and delivery.
  No concurrent queries/updates, Graph replay, new external vectors, stable IDs,
  multi-GPU or large-N admission. Python and direct executable reject invalid
  event/rank/shape contracts before operating the tree.

## Design card / ready and ownership ledger

| Stage | Ownership/layout | Ready edge / lifetime | Added cost / invariant |
| --- | --- | --- | --- |
| Native update | Original managed AoS base, tombstones, reference buffer | Serialized previous ACK -> update -> rebuild/reset/refresh -> next ACK | One shared update, not separate kNN/range copies |
| Initial/rebuild layout | Existing pack32, 256 threads/CTA, identity physical order | Native data compaction complete -> repack -> next query | 1024x128 FP32 capacity; repack cost belongs to setup/rebuild |
| Eligibility/rank/buffer glue | One thread per physical occurrence; AoSoA32 buffer slots | Native tombstone inclusive scan -> mask/rank publish -> score read | Unique output rank per live occurrence, no CPU distance computation |
| Seed/verify | Existing QT1 kernels, 256 threads/CTA, 512B query shared memory | Mask+packed data ready -> eligible seed top-K -> cutoff -> full verifier | Ordered RN FP64 sums; integer domain <2^24 matches range fields |
| Selection | Existing block_topk, 256 threads/CTA; two disjoint Neighbor buffers | Scores complete -> local top-K -> union top-K -> FP32 fields | No item omitted locally can belong to global K |
| Delivery/release | Shared U10 full-output observer; persistent kNN workspace | Final normalize -> full D2H before ACK; refresh never overwrites in flight | Setup/maintenance/query/drain all accounted; final owned bytes0 |

One same-stream handoff is the readiness proof; no new barriers, TMA, Tensor
Core, warp mapping or pipeline tuning is introduced. Thread/warp geometry and
selector barriers remain the established P7 implementation. New glue has unique
per-occurrence writers, no shared-memory handoff, and no persistent scores read
before overwrite. Reused scores and Neighbor buffers may be overwritten only
after the prior same-stream consumer; ACK drains before next host operation.

## Verification and timing policy, frozen before GPU execution

1. CPU scalar/array oracle and malformed-contract/guard tests; preserve parent
   16-source pins and exact legacy fixture hash before applying integration.
2. Same-binary PAR+BOUND / PAR+FULL / NATIVE+FULL full-output correctness:
   high-entropy mixed boundaries, all-tied data, sparse/empty/fewer-than-K,
   deleted seeds, buffer first/last deletion and rebuild epoch rollover.
3. memcheck/racecheck/synccheck on default mixed boundaries, plus memcheck on
   sparse rollover. All full outputs, transitions, refresh counts and release
   checked. GPU foreign activity invalidates the job; stop only own process.
4. Two independent default full traces, K8/K32: each10000 total query events,
   alternating5000 range/5000 kNN,1000 insertions/deletions,50 rebuilds. A FULL
   control at K8 is retained; one control run is not a speedup estimator.
5. Legacy PAR regression: identical original10000-range/12000-event trace,
   three fresh direction-balanced legacy/unified pairs. Rebuild mirror costs
   retained. Predeclared non-regression screen: upper95 bootstrap bound of
   unified/legacy whole-trace ratio <=1.05, each retained ratio<=1.05. This is a
   small same-fixture integration screen, not a paper-wide performance claim.
   Observer stays on in both; no new observer/phase speedup admission is asserted.

Keep all failed attempts and measured processes. No automatic failed/slow-sample
replacement, no data/seed/budget expansion, no reuse of old timings as the
comparator. Promote only scoped functional integration after gates1-4; failure
of gate5 preserves functionality but blocks default keeper promotion and must
be reported. Further external/large-N comparison needs a separate contract.

## Implementation refinement before first GPU execution

The direct executable strictly parses and retains both host inputs before any
CUDA allocation, then populates the native managed arrays from those validated
values. It does not call the permissive upstream line loader or reopen the
inputs after validation. This removes malformed-row and validate/reopen risks;
the native update/tree/range logic and input semantics remain unchanged.
Preparation attempts A/B are retained locally: A exposed a provenance-JSON
schema mismatch before compilation; B prepared all parent source pins and new
cases successfully. Neither attempted GPU execution.

## Post-execution wording clarification (no estimator/order change)

The registered three regression pairs were legacy/unified, unified/legacy,
legacy/unified: alternating with a2/1 order split, **not equal-count direction
balance**. All three are retained; no pair is added or replaced. The frozen
geometric-mean/bootstrap <=5% screen is unchanged and is not a positive speedup
claim. Host strict parsing/validation occurs before the captured context/setup
and warm timers; no process-start-to-exit or complete-cold latency is admitted.
The protocol self-test independently checks distance algebra but shares replay
logic between its two paths; independent state validation comes from the
separate read-only raw-output audit, not that self-test alone.
