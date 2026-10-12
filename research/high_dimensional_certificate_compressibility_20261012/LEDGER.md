# Preregistered claim-evidence ledger

Experiment: high-dimensional-certificate-compressibility-20261012. Keeper:
9797f6940c34ca9fbe927a0eb796a57ebc5298b2. All claims start unknown.

| ID | Hypothesis / denominator | Predeclared decision and evidence |
|---|---|---|
| H1 | FP32 PCA64 L4 retains >=70% of pooled hard point-set safe objects, >=60% original opportunity, >=50% canary point-set opportunity | All three necessary; admit Stage B only after G1-G4 and independent replay. |
| H2 | Strong compressibility | H1 plus PCA64 L4 retention>=85%, PCA128 L3 retention>=70%; do not waive H1. |
| H3 | Axis-aligned geometry loses too much information | Kill if PCA64 L4 retention<50% AND PCA128 L4 retention<60%; stop low-bit AABB sweep. |
| H4 | Compact/64B exact-safe summary | Unknown unless conditional formats admitted and tested, including all shared overhead and G5. |
| H5 | GPU-native value | Unknown, no evidence and no GPU/latency measurement permitted here. |

Symmetric evidence: a fully measured middle band is inconclusive and not promoted,
not an implementation failure. A kill rejects these axis-aligned regions/keeper,
not all finite summaries. Reopen only with a changed summary mechanism that first
passes Gate0 and the same-contract cheap retention check; do not repeat this
low-bit box sweep to try to improve an already enclosing FP32 box.

## Closure (2026-10-13 local /2026-10-12 UTC)

| ID | Evidence state | Exact allowed wording / evidence |
|---|---|---|
| H1 | rejected | PCA64 L4 hard retention37.03%, alignment30.34%, canary retention19.99%; none reaches promotion. `per_level_summary.csv`, `POINTSET_BRIDGE.json`. |
| H2 | rejected | Strong predicate false; PCA128 L3 retention27.34%. `aggregate_summary.json`. |
| H3 | measured | Both predeclared L4 kill conditions hold, all required exact-safety checks pass. `FP32_VALIDATION.json`, `BUILD_VALIDATION.json`, `INDEPENDENT_VALIDATION.json`, `CROSS_RUNTIME_REPLAY.json`. Reject current box mechanism under this contract. |
| H4 | unknown | No Stage B admission; no quantized formats or compact-budget feasibility measured. `QUANTIZATION_VALIDATION.json`. |
| H5 | unknown | No GPU/timing evidence; do not promote to a systems-speed claim. |

Counterevidence is retained as the whole nine-cell matrix, not just two kill cells.
PCA32 L5 retains54.30% but has42.59% original-truth alignment at256B/region;
this does not rescue the preregistered PCA64 L4 target. Reopen condition above
remains unchanged. Initial run and complete integrity-only rerun have identical
arrays/counts; see `RUN1_RUN2_BRIDGE.json` and `INTEGRITY_ONLY_REVISION.patch`.
