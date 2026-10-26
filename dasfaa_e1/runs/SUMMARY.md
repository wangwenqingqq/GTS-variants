# E1 continuation summary — stopped, no new GPU results

## Outcome

**No decision-grade dynamic results exist from this continuation.** A guarded
CPU inventory SSH session returned 255 after four snapshot records. Remote
work stopped without reconnecting or retrying. No CUDA build, sanitizer or GPU
job was launched. The root cause and final remote CPU process state are unknown.
See [STOP evidence](../evidence/continuation_20261026/STOP_CAMPAIGN.json).

The original frozen contract remains byte-identical to commit `0168a1a`.
User-authorized changes were appended to [AMENDMENTS](../AMENDMENTS.md).
All prior P/G repeated-query results remain invalid; old prefix checks are not
relabelled complete smoke tests.

## Required primary matrix (100K, 4:4:2, random, k=8)

N/A means not measured under the required gates, **not zero**.

| Dataset | G ops/s; p99 | G+B* ops/s; p99 | P ops/s; p99 | D ops/s; p99 | P/G (95% CI) | P/(G+B*) (95% CI) | Rebuilds G/B/P |
|---|---|---|---|---|---|---|---|
| SIFT-1M | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| GIST-1M | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| Deep-1M | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| T-loc 1M | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| Word 611K | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| Protein 52K | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| ChEMBL 50K | N/A | N/A | N/A | N/A | N/A | N/A | N/A |

All skew tables, other ratios/lengths/k, query-before-insert k1/k8/range,
B* prediction/empirical optimum and work counters remain unmeasured. Existing
small-corpus capacity-infeasible rows remain in the matrix; no IDs were reused
or payloads synthesized. SIFT/T-loc 1M-operation traces and CPU H remain P1/P2
uncompleted. P-approx is removed by the user's decision, not an omitted result.

## Decisions

| Rule | Status and reason |
|---|---|
| C3': P/G>=2 on >=4/7 primary datasets | Undecided; no new paired evidence |
| C1: median P/(G+B*)>=1.2 | Undecided; no new paired evidence |
| P versus D; story A/B | Undecided; no new same-contract comparison |
| Skew order separately | Uncompleted; no pooling or extrapolation |
| B* predicted versus measured optimum | Uncompleted; no calibration/sweep |
| SIFT-50K historical abort | Unresolved; compaction-ID and leaf-stride bugs are leads, not a literal causal replay |

## Completed local work, with boundaries

- Audited old logs and source provenance. Both exact mandatory search_v2 patches
  are reproducibly derived from pinned originals. They are not executed by the
  existing range-candidate adapter; this is explicitly disclosed.
- Added real-payload query isolation/90-10 preparation and full workload matrix
  generation with fresh stable IDs and capacity checks. Real full datasets were
  not prepared/evaluated in this continuation. ANN GIST=17/Deep=42 feature-match
  rows remain blocked pending user decision; no silent corpus edits.
- Added strict fail-stop handling, >=30s NVML snapshot spacing, `timeout 10`,
  pre-allocation N/int32 guards, partial-result stop ordering and PID ownership
  regressions. **23 local tests pass**; mock teardown tests are not Linux proof.
- Independent scope-limited review found no fabrication/evaluator modification,
  but did NOT clear GPU launch or issue a full-session CLEAN verdict. See
  [AUDIT_RESULTS](../AUDIT_RESULTS.md).
- A hard pre-admission block is set in the runner. Linux process-tree
  teardown/late-fork/lock-lifetime validation remains required. Do not bypass it.
- Larger real-data inventory is partial; see [INVENTORY](../INVENTORY.md).

## Reopen sequence (requires explicit user resumption, not automatic retry)

1. Resolve the SSH failure externally; establish the prior CPU guard's final
   receipt/process state without starting a new experiment automatically.
2. Validate bounded Linux guarded-subtree teardown and lock lifetime; only then
   remove the launch block in a reviewed code change.
3. Resolve the executed P/G path: retain the documented range-candidate adapter,
   or implement native dynamic kNN with live-only bounds/full stable-ID output.
   Do not promote an unused-header patch as an executed correctness repair.
4. Resolve ANN collision policy; finish the remaining inventory and capacity
   decision. Freeze actual inputs/hashes by append-only amendments.
5. Guarded fresh build, all-metric memcheck/synccheck and complete 21-case smoke,
   then full-output correctness per load. Only passed loads enter six-round
   paired timing, B* sweep, final separate evaluation and integrity audit.
