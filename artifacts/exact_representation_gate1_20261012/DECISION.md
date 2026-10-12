# GO_BYTE_REDUCTION

**GO_BYTE_REDUCTION**: mean **167.291615** dimensions; ideal coordinate payload **3.840000→0.669166GB/query**, reduction **82.573790%**.

## Q1 — Required dimensions

Mean167.291615, median155.000000, p1045.000000, p90295.000000, p95352.000000, p99486.000000; denominator all32M pairs. True hits(6590) require960. Nonhits-only mean167.128333 is secondary, not the admission denominator.

## Q2 — Byte headroom

Mean669.166459B/object versus3840B. Ideal0.669166GB/query versus3.840000GB, reduction82.573790%. The diagnostic computed all960 for proof; it did not realize these savings or measure traffic/latency.

## Q3 — Query robustness

Query-mean min/p10/median/p90/max:6.190577/96.515813/181.399689/233.553414/257.853106. All32 query means satisfy the384-dimension point threshold, not just a few easy queries. Their observed variation is finite-pool evidence, not a confidence guarantee for future queries, radii or snapshots.

## Q4 — Where savings arise

Far nonhits contribute99.824472% of coordinate savings and represent99.592191% of nonhits. Their mean is165.279099 dimensions. Near nonhits average876.708406 dimensions and remain expensive; hits require full evaluation. Margin thresholds were fixed before measurement and never altered the gate.

## Q5 — Frozen verdict

Mean167.291615≤384 and p90(query mean)233.553414≤480: GO. Human clarified NO-GO precedence and UNCLASSIFIED uncovered outcomes before measurement; original numeric thresholds were not relaxed. Every full960 score matches the original ordered-FP64 reference bit-for-bit;0 reference hits were rejected.

## Implementation / mechanism / thesis

- Implementation: CPU-only diagnostic qualified on the frozen full population;0 GPU starts.
- Mechanism: substantial original-order per-object coordinate-payload opportunity survives Gate1. Sector/warp/stage granularity and control costs can still erase a GPU gain.
- Thesis: partial-distance elimination is established; this result is not a novel contribution or GTSPP end-to-end benefit.

Only design-only128/256/512/960 accounting follows. No GPU prototype, reordered dimensions, coding or dynamic workload was started. Separate prior-art, conservative arithmetic, total-cost and strengthened same-contract end-to-end gates remain. Reopen/narrow if a new query/radius/snapshot fails these thresholds, safe arithmetic materially delays rejection, or charged execution costs exhaust payload savings. This is not a claim that every exact representation or every GPU tree must behave this way.
