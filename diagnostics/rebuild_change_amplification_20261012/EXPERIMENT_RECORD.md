# Experiment record

| Experiment | Hypotheses | Contract | Keeper / observer | Invariants | Decision rule |
|---|---|---|---|---|---|
| GTSPP_20261012_REBUILD_CHANGE_AMPLIFICATION | Positive: sparse mutations leave most structure identical but cause full maintenance. Negative: sparse mutations trigger real global organization churn. | CONTRACT.json, frozen before the GPU process | Original P2 / separate read-only Host snapshot observer | All 336 event semantics, complete ordered payloads/field bits, final occurrences, rebuild trigger steps; unchanged device source definitions | Both observed rebuilds must meet frozen GO or NO_GO thresholds; otherwise inconclusive |

Lifecycle: designed -> resource-admissible -> built -> behavior-correct ->
state-diff. No optimization candidate, performance promotion or paper novelty
admission. One exact target replay, original warmup clone unchanged. No repeat
is automatically granted for performance statistics or a favorable result.

Timing, SASS equality, observer sanitizer, long stress and same-campaign external
comparison are not gates reached by this diagnosis. Their absence prevents any
new production or performance claim, but does not invalidate an exact saved-state
comparison after behavior parity and snapshot invariants pass.
