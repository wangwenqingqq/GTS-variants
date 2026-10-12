# Decision: reject the frozen multi-view candidates
**MULTI_VIEW_LINEAR_CERTIFICATE_KILLED**, by predeclared K1. All eleven distinct multi-view configurations have lower hard alignment than PCA8 at every measured level. Every region record is 64B.

| Configuration | L3 hard alignment | L4 hard alignment | L5 hard alignment |
|---|---:|---:|---:|
| PCA8 keeper | 22.8859% | 29.8107% | 40.4884% |
| PCA blocks 2x4 | 22.1644% | 26.9385% | 34.9267% |
| Interleaved 2x4 | 18.3221% | 23.2591% | 29.3346% |
| Spread32 2x4 | 13.4228% | 14.0105% | 16.3391% |
| Random 2x4 | 0% | 0% | 0% |

## Mechanism diagnosis
Splitting fixed coordinates loses joint squared-gap energy under max composition. Full-PCA8 dominance and nested contiguous-block controls pass numerically. D1 aliases the blocks control; D2-8x1 is also an alias, not an independent observation.

Direction diversity does not compensate here. Random views prune zero pairs on all eight frozen queries at every level. Some layouts have complementarity, but this is gain over the **best constituent**, not over PCA8. The largest L4 hard complementarity is 2.3201 pp (blocks 8x1); the largest L5 value is 3.5638 pp (blocks 4x2). Neither establishes a keeper advantage.

The canary 359924 at L4 declines from 7.0556% (PCA8) to 6.2450% (blocks 2x4), 2.0516% (interleaved 2x4), and 0.7306% (Spread32 2x4); random is zero. Figures 2/3 were preregistered for all four distinct 2x4 families at L4, not selected after outcomes.

## Separate lookahead probe
**LOOKAHEAD_CLOSED** only for the sixteen frozen parents and this two-level proposal family. Both comparators use the same grandchildren horizon: immediate-greedy first split + best second split versus lookahead-selected first split + best second split.

- Depth-2 parents: 500 additional pruned pairs / 480,000 parent-universe pairs = **0.1042 pp**.
- Depth-3 parents: 70 / 48,000 = **0.1458 pp**.
- Pooled: 570 / 528,000 = **0.1080 pp**.

These are full-parent-universe pruning-fraction gains, **not truth-prunable alignment gains**. Pooling weights depth-2 parents ten times as much by universe size; both depth-specific summaries also pass closure. A sampled finite-horizon probe cannot bound global/deeper/alternative-family coordination.

## Implementation, mechanism, thesis
- Implementation: declared exact-safety, packing/count bridges, cross-runtime replay pass.
- Mechanism: reject this frozen 64B max-ensemble family on P2 and these queries.
- Thesis: no universal linear-representation impossibility, held-out quality, latency, or GPU-tree claim follows. No paper text or GPU campaign is promoted.

Reopen only for a genuinely different representation/composition mechanism with a cheap falsification test and independent query contract, or decisive same-contract counterevidence. Do not rescue this result through a seed/workload sweep or by renaming constituent complementarity as keeper gain.
