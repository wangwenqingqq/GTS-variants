# PARTIAL_PADDING

Qualified diagnostic on GIST N1M/D960, FP32 row-major L2Unexpanded, same native library and admitted device. No new kernel, library change, layout change or optimization.

## Q1 — Does execution follow64/B?

Primary T64 median relative error: **0.03473428%** over all seven frozen fit points. B1 inflation **64.02223×**; B64 **1.00035×**. B128 is a held-out boundary, not used to refit T.

## Q2 — Does B64 approach useful work?

B64 inflation **1.00035×**; declared limit1.5×. Useful scalar proxy is2.879G/query, not a count of all auxiliary operations.

## Q3 — Does traffic decouple?

B64/B1 per-query FP32 factor **0.01562500**; measured DRAM factor **0.01682287**. Separation **0.10656802 log2**, required≥1: **FAIL**. Database reuse can decrease both curves together; failure does not refute arithmetic padding, but it prevents CONFIRM under the retained contract.

## Q4 — Is there independent geometry evidence?

Conservative predeclared geometry check: **FAIL**. Same normalized function/block/grid through B64: True. Actual B64 grid **[376, 1, 1]** changes to **[188, 2, 1]** at B128, with the same selected function hash. The original analysis predicate requires exactly one doubled axis with every other axis unchanged; its matching axes are []. A doubled query axis plus a reduced database axis is corroborative batch-route evidence, not evidence against padding, but does not pass that stricter predicate. No source tile constant or full runtime/JIT module image was recovered. Even a broader positive geometry interpretation cannot change the final verdict because the traffic gate fails.

## Q5 — Final decision

**PARTIAL_PADDING**. B1 complete payloads reproduce the prior keeper exactly; FADD/FFMA and selected identity reproduce. Fresh original keeper stability ratio95% CI **[1.010966, 1.020238]**, unpaired process bootstrap. Six processes/B and all eight NCU profiles passed the quality/isolation/provenance gates.

## Boundary and next action

Only dispatch/kernel-route provenance; no optimization. Preserve the original traffic gate and distinguish database reuse from repeated database loads.

Timing is complete-output native ACK, not tree/workflow/application E2E. Native batches change query shape and reuse; they are not a GTSPP speedup or a64× recoverable latency promise. Optional repeated-single was omitted (N/A). B64/128 use a separately frozen128-query pool. No detailed PRIOR_ART is produced unless CONFIRM. No manuscript update or optimization was authorized by this diagnosis.
