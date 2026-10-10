# GPU-Tree: observed first loss, bounded repair and independent task gates

**No GPU-Tree performance result or new GTSPP speedup is claimed.** The native
kNN failure has an observed first-loss boundary. Its minimal repair passes the
bounded complete-output check but fails a separate memory-safety gate.

| Identity / gate | Dataset and calls | Result |
|---|---|---|
| Native trace | N4096/D17, PNUM8/K8, one frozen query | Reproduces6/8 members; complete ID/field bytes match the prior native failure |
| Ownership-only reuse trace | Same index/input,32 consecutive B1 calls | Same first-call trace and all32 prior output payloads |
| `GPU_TREE_SAFE_KBOUND_ADAPT` | Same N4096/D17,48 kNN +32 range calls, one build | All80 full results pass; first kNN restores8/8, including duplicate occurrences |
| Same repaired identity, memcheck | Same80-call request file | **Failed** on the first kNN call: native candidate queue `initPQ` writes outside allocation |
| Same repaired identity, racecheck/synccheck | Conditional slots | Not run after memcheck failure; not silently counted as passes |
| Unchanged `GPU_TREE_SAFE_ADAPT`, range only | N1M/D960,32 queries per initial/first-rebuilt snapshot | Both pass:6,590 and12,429 complete returned items; no timing admission from this row |

## Mechanism evidence

The ordered-FP64 reference top8 occurrences are
`0, 1, 2263, 3385, 2548, 2101, 374, 394`.
Native output replaces374/394 with1809/1797. Both duplicate-vector instances
0/1 survive: deduplication is not the observed loss.

All4096 instances remain in the built topology and all11 roots survive the
partition/tree filters. In the initial bound traversal, the local answer heap
contains only `{0,1,2101}`. Its maximum0.952549934 is nevertheless installed
as a pruning bound. Node171, containing374/394, has lower bound0.961247087 and
is skipped before leaf verification; the true global eighth distance is about
0.965016685. The main search repeats the underfilled-heap loss. The omitted
instances never reach the local top-K, global merge or Host delivery.

The repair changes only bound readiness: preserve a valid incoming bound until
K occurrences exist; the initial bound search uses infinity while underfilled.
It changes no tree organization, PNUM, precision, deduplication or output contract.
The separately inherited tail-read protection remains explicitly named.

The new memcheck finding is independent of a successful output test. The native
candidate heap uses one-based indices1..500 with arrays of length500; its
initialization writes index500. This source issue is present in the parent,
not introduced by the bound fix, but has only been measured here on the repaired
kNN path. Further queue repair and requalification require explicit registration;
the failed attempt is not replaced. Checking child-index guards is also needed
before any future capacity repair. No sole-cause or universal-correctness claim.

## Provenance and boundaries

- Contract and design are adjacent. Tracing is observational, never timed as an
  optimization. `analyze_trace.py` verifies exact registration, all execution
  source/binary/input/command identities and prior payload parity.
- Fresh staged preparation reproduces the actual compiled trace/repair source
  bytes. The first compile-only repair attempt lacked the CUDA constants include;
  its failure remains private. The fixed compile is a distinct identity, not an
  extra GPU experiment.
- Strengthened offline checks reject missing/duplicate snapshot proofs, incomplete
  sanitizer sets, negative Euclidean fields, stale schedules and incomplete
  payloads. Exact guard/attempt sets include every new process, including the
  failed memcheck. Final live-source/output verification passes for both target
  snapshots; source and private archive/proof hashes are in
  [GPU_TREE_GAP.json](../evidence/GPU_TREE_GAP.json). The strengthened verifier
  does not rewrite the already executed source registrations.
- The old32-slot admission budget is unchanged. This campaign has its own8-slot
  ceiling and used6 processes:2 traces,1 bounded repair,1 failed memcheck and2
  independent range targets. The remaining2 conditional repair sanitizer slots
  are unexecuted, not passes or free replacements. The original range-only binary
  reuses its exact prior bounded and mem/race/sync evidence; kNN's safety failure
  does not automatically disqualify it.
- Formal Host-vector-input timing, balanced fresh P/GPU-Tree processes and any
  supplemental table require their own frozen actual executor identity. No old
  P denominator, missing method treated as a loss, or static-to-dynamic inference.

| Claim ID | State | Allowed scope / counterevidence |
|---|---|---|
| TREE-FIRST-LOSS | measured | First observed374/394 loss is premature underfilled-heap pruning on this N4096/D17 case; not the sole defect in every workload |
| TREE-KBOUND-OUTPUT | measured |80 bounded complete results pass after the minimal repair; no target-scale kNN qualification |
| TREE-KBOUND-SAFETY | rejected |The repaired identity fails memcheck; reopen only with a separately registered queue repair and renewed safety/output gates |
| TREE-RANGE-TARGET | measured |Unchanged range-only identity passes64 queries across two N1M/D960 snapshots; formal Host-input timing remains unvalidated |
| TREE-E2E | unknown |No new same-contract performance comparison or sustained-service result exists |

## Mainline and next gate

The GTSPP thesis remains redundancy -> mechanism -> module -> effect ->
end-to-end benefit. These are external-baseline correctness facts, not a new
GTSPP mechanism or coalescing speedup. Internal13.423096x remains scoped to its
original R/P short workflow. External72-row closure, optional tree supplement
and the conditional12000-event sustained workload remain separate gates.
