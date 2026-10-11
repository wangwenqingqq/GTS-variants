# Claim-to-evidence and non-claims

| ID | Allowed statement | Evidence | Material boundary |
|---|---|---|---|
| B1 | Fixed C0 LOCAL_BALL retains 92.2501% / 93.4250% of blocks, versus GLOBAL4 68.8995% / 67.8749% | query/SUMMARY_COMPARISON.json; figures/summary_survival.csv | These exact two snapshots and 64 fixed range queries only |
| B2 | Zero false prune on all 64 queries; conservative triangle-inequality rule | NUMERICS.md; test_ball.py; evidence/PROOF.json; evidence/VERIFY.json | CPU ordered-FP64 semantics; not CUDA/sanitizer qualification |
| B3 | LOCAL_BALL is worse on 63/64 queries and better on one | query/SUMMARY_COMPARISON.json; figures/local_vs_global.csv | Not worse on every query; no workload-wide statistical inference |
| B4 | Oracle gap averages 3763.59375 / 3811.34375 blocks | query/SUMMARY_COMPARISON.json; figures/oracle_gap.csv | Oracle uses exhaustive reference and is not online available |
| B5 | Ball summary costs 4096 distance evals plus 15,728,640 coordinate bytes/query before survivor verification | CONTRACT.json; query/COST_PROXY.md; per-query counts | Logical work/payload, not actual memory transactions or time |
| B6 | All 8192 C0 selections and 2,262,144 fresh pair scores pass independent reconstruction | evidence/VERIFY.json; verify_ball.py | Separate O0 build, reversed pair orientation, scalar center selection; shared conservative-envelope helper is not an independent mathematical proof |
| B7 | Frozen NO_GO_LOCAL_BALL triggers on both snapshots | CONTRACT.json; evidence/DECISION.json; DECISION.md | No promotion, center tuning, new family experiment or GPU launch authorized by this result |

No new claim about CPU waiting time, coalesced transactions, kernel speed,
end-to-end speed, update locality, sustained operation, kNN, other datasets,
all GPU trees or impossibility of all metric summaries follows. The previous
capacity-aware 4167-block update study uses a different layout; it is not
silently merged into this 4096-block static result. C0 is nearest to the
signature mean, not exact original-space medoid selection. The classic
metric-ball mechanism is not claimed as novel.
