# Decision: substantial causal support, not strict full GO

**Measured:** C2 and C3 early-pivot interventions preserve a large fraction of the original leaf organization on both rebuilds, under identical POST input bytes and unchanged native sorting/split rules. C3 reduces churn from about 100% to 29.008% / 29.909%. All actual selected pivots and correspondence/admission/fallback decisions were independently reconstructed from captured inputs.

**Inferred:** early pivot/order decision drift is a major causal amplification contributor for these two frozen rebuilds. Root-only stability is insufficient; the instability repeatedly moves to the next unfrozen construction level. This does not prove that middle-pivot drift alone causes every change; encoded-key rounding/ties, ordered ranks and quantile boundaries remain part of the construction system.

## Predeclared gates, unchanged

| Gate | Result |
|---|---|
| Native PRE and POST C0 byte replay | PASS on both rebuilds |
| Identical POST FP32 inputs and valid counterfactual structures | PASS |
| C2 >=30 percentage-point reduction | PASS: 40.248 / 41.452 pp |
| Strict monotonic C0→C1→C2→C3 on both | NOT MET: R2 C1 changes one additional leaf |
| STRONG_GO <=20% churn | NOT MET: C3 remains about 29% |
| NO_GO all tested doses >=90% | FALSE: C2/C3 give substantial preservation |
| Production / performance admission | NOT ATTEMPTED |

Overall: **CAUSAL_SUPPORT_WITH_ROOT_ONLY_EXCEPTION; STRICT_GO_EARLY_CASCADE_NOT_MET; STRONG_GO_NOT_MET.** Neither negative evidence nor the positive C2/C3 preservation is erased by this classification. Do not promote it to a production keeper or claim a speedup.

## Next action and boundary

Stop GPU expansion at C3. Use the captured first-unfrozen L3 rank/pivot/boundary evidence to localize the remaining approximately 29% churn; do not add C4 or freeze all pivots. This task does not authorize a stable-tree production mechanism. Before any later mechanism direction, explicitly resolve the strict-gate exception and run the dynamic metric-tree / stable partition / persistent-pivot prior-art Gate 0. Fixed pivots by themselves are not a novelty claim.

Reopen only with a separately frozen diagnostic that distinguishes actual next-level pivot drift from same-pivot encoded-key/tie/partition-boundary effects. Do not rescue a subsumed research thesis with a longer engineering checklist or a kernel-only number.
