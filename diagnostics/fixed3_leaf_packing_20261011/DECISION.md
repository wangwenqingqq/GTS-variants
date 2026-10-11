# Decision: retain fixed3 as an original-GTS candidate

**Accept the implementation for the measured original-GTS contract; do not
promote it as current GTSPP or a standalone novel contribution.**

| Gate | Evidence | Decision |
|---|---|---|
| Correctness / resource / sanitizer | Full outputs and independent oracle pass; selected leaf resource receipt; unit/tail and whole-query sanitizer passes | Pass within recorded scope |
| Same search and arithmetic work | Byte-identical fixed 32 node sidecars, including original task ordering and masks | Pass |
| G1 leaf benefit in both NSYS orders | 1.00796x and 0.99901x G0/G1 | Not established at leaf scope |
| G2 leaf benefit over G1 in both NSYS orders | 2.99182x and 2.95152x | Pass diagnostic direction gate |
| Actual runtime geometry | 32 launches each; G2 CTAs 976,369 versus 2,929,074 | Pass; not an issued-instruction counter |
| Independent packing Host-ready gain | 2.543937x [2.541211, 2.545909], 6/6 wins | Pass formal gate |
| Total original-GTS Host-ready gain | 2.561733x [2.556026, 2.570420], 6/6 wins | Pass formal gate |
| Generality / hardware attribution | One GPU/dataset, fixed B=1, NCU counters unavailable | Not established beyond this scope |
| Standalone packing novelty | Generic task packing is established | Reject that thesis; do not rescue with speed alone |

Most of the measured gain is independent multi-leaf packing, not simply
discarding fifteen empty configured warps per original CTA. The small CTA
control has a small formal net gain, not the dominant mechanism.

Next, if separately requested, port the fixed mapping to current GTSPP and
remeasure its current keeper under the same complete contract. Only then test
strong external GPU comparators. Preserve the original-GTS result as attribution,
not the final system's multiplier. This delivery does not change current GTSPP,
try 4/5-leaf or greedy candidates, add pruning, or modify layout/precision.

Reopen/falsification conditions: a different leaf-size distribution, B>1,
different distance/layout, GPU/toolchain or output contract requires renewed
qualification and same-campaign measurement. Reject a port if its net gain
disappears, even if lane fill rises. Hardware counter availability would justify
a separately registered attribution extension, not replacing these raw timings.
