# Claim-to-evidence and exact scope

| ID | State | Allowed statement | Evidence | Material boundary |
|---|---|---|---|---|
| A1 | measured | PCA4 box keeps 74.4102% / 75.1266% versus GLOBAL4 68.8995% / 67.8749% | query/SUMMARY_COMPARISON.json; plotting CSV | GIST N1M/D960, fixed S1/P2, original 64 range queries only |
| A2 | measured | Zero false prune; all 2M object projections, 64 query projections and 8192 boxes reconstruct | evidence/VERIFY.json; verify_box.py | Each projection has four ordered dots; shared envelope is high-precision tested; not CUDA qualification |
| A3 | measured | Ten queries improve and 54 regress against GLOBAL4 | query/SUMMARY_COMPARISON.json; projected_vs_global.csv | Not worse on every query; no inferential population claim |
| A4 | theoretical | Outward dots/boxes and exact represented Gram bound give safe reference-contract lower rejection | NUMERICS.md; DIRECTION_PROOF.json; test_box.py | Rounded eigenvectors are not assumed exactly orthonormal; squared membership scores are not assumed to be a metric |
| A5 | partial | Query model has four dots plus one numeric max reduction, 262144 endpoint bytes, 30720 direction bytes and survivor work | CONTRACT.json; query/COST_PROXY.md | Cached direction safety coefficients assumed in core model; not actual traffic, instruction or latency equality |
| A6 | measured | Initial-only PCA paid wall/CPU and resource account is retained | directions/PCA_RESOURCES.md; DIRECTION_PROOF.json; REGISTERED.json | Time includes two passes and two eigensolve/Gram checks; excludes preceding validation/build/hash; warm input pages and one host observation |
| A7 | rejected | Frozen PCA4 route fails GO and triggers NO_GO_PROJECTED_BOX; K8 inadmissible | evidence/DECISION.json; DECISION.md | Stops this tested family/configuration, not every projection or all anisotropy hypotheses |

No new CPU waiting-time, GPU coalescing, query latency, end-to-end speedup,
update locality, sustained direction stability, kNN, other-scale or 100K-workflow
claim follows. A single cross-rebuild snapshot is not an epoch-spanning drift
study. PCA global variance axes need not represent block-local directions
that determine range separation. The result does not causally establish or
refute anisotropy as the source of the whole residual gap. Old GLOBAL4/ball
results are reused hash-identically, not presented as new timing observations.
