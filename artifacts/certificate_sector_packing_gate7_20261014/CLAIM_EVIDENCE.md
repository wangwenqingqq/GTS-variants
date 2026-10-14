# Claim-evidence ledger

Experiment:GTSPP_20261014_CERTIFICATE_SECTOR_PACKING_GATE7. All paper promotion
is prohibited this round. Allowed wording below is for internal diagnosis only.

| ID | Statement | State / denominator | Evidence and caveat |
|---|---|---|---|
| G7-I | One frozen packing reduces average survivors22.171636% versus S1. | measured; same 32 range queries x1M, nominal128 FP32 coordinates | candidate/P1_PACKED_SECTOR_MOMENT.json; all query rows kept; eight regressions; S1 historical deterministic counts, not a fresh timing comparator |
| G7-Q | Packed-source full arithmetic matches frozen original bits with safe partial rejection. | measured;32M full-bit and 32M candidate-bound comparisons | quality/; evaluation registration, transform and raw-proof manifest; inverse original-order accumulation required |
| G7-G | C1 demand coverage transfers partially to held-out queries. | partial;1024 train vs 32 eval, no disjoint-population distance outcome training | packing/PACKING_QUALITY.json; recovery 53.247070%, purity 4.259766/8; does not establish robust survivor dominance |
| G7-B | The conditional source-byte model is817,666,504 B/query. | theoretical cost derived from measured survivor counts;32-query mean | cost/FULL_FALLBACK_BYTES.json; selected-coordinate reuse assumed;19.428132% below strong reference, not20%; retention/reconstruction/spills unknown |
| G7-P | Prior art leaves the narrow policy testable in the bounded audit. | inferred; literature scope only | prior_art/; co-access packing/ordering/layout ingredients are old; no novelty proof or direct same-setting negative inference |
| G7-L | Actual DRAM, sector traffic, Host-ready latency and end-to-end gain. | unknown; no evidence | GPU/NCU/NSYS starts 0; fallback, dynamic and kernel execution not implemented |

Decision:CONDITIONAL_PACKING. Negative evidence is preserved: mean-survivor
margin, p90 stability and strong modeled-byte GO all fail. Reopen conditions are
in DECISION.md; do not rescue novelty with a GPU port or the modest gains.
