# E1 resumption — mandatory guard97/98 stop, no GPU results

## Conclusion and strongest evidence

**No decision-grade dynamic result exists.** Guard refused source upload with97
(cgroup headroom24.5GiB, required25GiB) despite host MemAvailable212.9GiB.
The already-running read-only inventory returned98 on its existing connection
(cgroup headroom23.8GiB<24GiB, peakRSS0.04GiB, elapsed17s). No new remote
command was issued after the first observed97. No retry, reconnect, new epoch,
CUDA build, sanitizer or GPU launch occurred. See
[STOP_CAMPAIGN](../evidence/resume_20261026_0450/STOP_CAMPAIGN.json).

The preceding failed inventory's final receipt was recovered first: child
exit120 after20.041s, not a resource kill. No prior E1 task appeared in the
recovery process snapshot. This does not establish the original SSH255 cause.

The narrow Linux CPU runner-cancellation/lock composition fixtures passed,
including setsid/orphan children and injected signal failure, with ordinary
watchdog child-kill status247 (child-9), not97/98/3. Their scope does NOT prove
standalone resource-guard timeout/RSS containment, concurrent-fork teardown or
outer-runner death safety. The GPU hard block remains enabled. Independent
review confirms this blocker; no full integrity-audit CLEAN verdict is claimed.

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

## Completed work and exact gate boundaries

- Frozen CONTRACT.md unchanged: SHA256
  `36d1d270a5e536d20a3614206fd847d577491e7221bbd4fe6421548ca75ddd28`.
  All new user decisions were appended before implementation/execution.
- P/G native kNN implementation selected, both mandated patches derived with
  exact pins. P numeric queries use external vectors/res_ids; edit/G use an
  external payload row/QID. G output-only adaptation carries full IDs/distances.
  Runtime native kNN, full-distance correctness and CUDA compilation are NOT
  validated. The refused upload did not start its extraction/build command.
- Native tombstone handling overfetches k+deleted-tree ranks, filters the bitmap
  and merges exact delta using returned GPU distances. Its full costs stay in
  operation latency. Native static per-query allocations mean the old C1
  update-workspace contrast is NOT established by this path.
- Range kernels were not repaired or validated; query-before-insert range remains
  pending and must become correctness-failed if complete-output oracle checks fail.
- Current safety candidate has additional local-only corrections after the exact
  CPU-tested snapshot. Tested source bytes and hashes are retained separately;
  do not apply the earlier runtime pass to the later code.
- GIST/Deep exclusion authorized (expected17/42 corpus rows), full standard query
  sets retained by the preparer. Actual new real-data manifests are NOT prepared.
- Larger-corpus inventory was killed; its partial remote output/logs were not
  fetched after the stop. Existing four snapshot records remain partial evidence.
  No larger replacement corpus was authorized or admitted.

## Remaining work and reopen conditions

1. User explicitly resumes after cgroup headroom is restored/isolated; high host
   MemAvailable alone is insufficient. Do not lower the guard's24GiB headroom.
2. Resolve complete process-tree/runner-death containment without editing E4's
   shared guard. An E1-only hardened guard was proposed, not authorized or used.
3. Independently review/validate that containment, then clear the GPU block only
   in an evidence-backed reviewed change. Recheck current code, not prior hashes.
4. Recover final guard logs and inventory output without relabelling the killed
   attempt complete; finish inventory and obtain the user's capacity decision.
5. Fresh guarded build, all-metric memcheck/synccheck, all21complete smoke cases
   and full per-load outputs, including native distances and added range workloads.
6. Only passed loads enter B* calibration, six paired rounds/sweep, separate final
   evaluation, counters, E3static parity and final independent integrity audit.

Deadline2026-11-08 remains unchanged. No missing workload is replaced, shortened
or extrapolated. All ops/s, p99, ratios/CI, rebuild counts and predicted/optimalB
remain N/A, not zero. SIFT50K literal historical cause remains unresolved.
