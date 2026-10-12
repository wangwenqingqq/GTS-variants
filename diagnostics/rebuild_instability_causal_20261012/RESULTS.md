# Measured structural results

Frozen N=1,000,000, D=960 FP32, arity 10, leaf threshold 20. Each rebuild has 100,000 leaves and 999,990 common live base occurrences. There are ten actual GPU construction processes: four native PRE/POST controls, two C1, two admitted C2 and two admitted C3. No service replay or performance claim.

## Table A: exact canonical leaf churn

| Rebuild | Mode | Frozen decision levels | Changed leaves | Leaf churn | Changed common objects | Freeze admitted/requested |
|---|---|---|---:|---:|---:|---:|
| R1 | C0 | 0 | 99,982 | 99.982% | 999,810/999,990 | 0/0 |
| R1 | C1 | 1 | 84,875 | 84.875% | 848,740/999,990 | 1/1 |
| R1 | C2 | 2 | 59,734 | 59.734% | 597,330/999,990 | 11/11 |
| R1 | C3 | 3 | 29,008 | 29.008% | 290,070/999,990 | 111/111 |
| R2 | C0 | 0 | 99,985 | 99.985% | 999,840/999,990 | 0/0 |
| R2 | C1 | 1 | 99,986 | 99.986% | 999,850/999,990 | 1/1 |
| R2 | C2 | 2 | 58,533 | 58.533% | 585,320/999,990 | 11/11 |
| R2 | C3 | 3 | 29,909 | 29.909% | 299,080/999,990 | 111/111 |

C2 reduces leaf churn by **40.248 / 41.452 percentage points** versus C0. C3 reduces it by **70.974 / 70.076 percentage points**. This is structural preservation, not saved maintenance time. All requested freezes were admitted; there were no missing-pivot or ambiguous-correspondence fallbacks.

## Table B: PRE selected-pivot survival by decision level

| Rebuild / mode | L0 / 1 | L1 / 10 | L2 / 100 | L3 / 1,000 | L4 / 10,000 |
|---|---:|---:|---:|---:|---:|
| R1 / C0 | 0 | 0 | 0 | 2 | 115 |
| R1 / C1 | 1 | 3 | 16 | 153 | 1588 |
| R1 / C2 | 1 | 10 | 46 | 409 | 4088 |
| R1 / C3 | 1 | 10 | 100 | 734 | 7159 |
| R2 / C0 | 0 | 0 | 0 | 2 | 110 |
| R2 / C1 | 1 | 0 | 0 | 2 | 86 |
| R2 / C2 | 1 | 10 | 47 | 419 | 4224 |
| R2 / C3 | 1 | 10 | 100 | 721 | 7062 |

L3 and L4 together are the deeper L3+ inventory; they are reported separately to avoid hiding duplicate occurrence identities across levels. These are selected split-pivot occurrences, not inherited TN.pid counts.

## Causal localization

| Rebuild / dose | Scoring level | Same PRE pivot under correspondence | Retained common parent objects | Objects crossing child segment |
|---|---:|---:|---:|---:|
| R1 / C0 | 0 | 0/1 | 999,990 | 815,949 |
| R1 / C1 | 0 | 1/1 | 999,990 | 13 |
| R1 / C1 | 1 | 3/10 | 999,977 | 600,861 |
| R1 / C2 | 1 | 10/10 | 999,977 | 71 |
| R1 / C2 | 2 | 46/100 | 999,906 | 456,159 |
| R1 / C3 | 2 | 100/100 | 999,906 | 298 |
| R1 / C3 | 3 | 734/1000 | 999,608 | 220,557 |
| R2 / C0 | 0 | 0/1 | 999,990 | 843,173 |
| R2 / C1 | 0 | 1/1 | 999,990 | 17 |
| R2 / C1 | 1 | 0/10 | 999,973 | 817,197 |
| R2 / C2 | 1 | 10/10 | 999,973 | 56 |
| R2 / C2 | 2 | 47/100 | 999,917 | 453,241 |
| R2 / C3 | 2 | 100/100 | 999,917 | 277 |
| R2 / C3 | 3 | 721/1000 | 999,640 | 235,023 |

The instability moves to the first unfrozen level. C1 leaves only 13 / 17 root child-segment crossings, but native L1 pivots change in 7 / 10 and 10 / 10 corresponding parents. C2 leaves 71 / 56 L1 segment crossings, while L2 pivot survival is only 46 / 100 and 47 / 100. C3 leaves 298 / 277 L2 crossings, but L3 still has 220,557 / 235,023 segment-crossing objects within matched parents. This repeated localization supports recursive amplification through early pivot/order decisions; it does not establish that middle-pivot drift is the only possible cause.

Exact partition divergence and correspondence-based object movement are distinct. In particular, PRE full root membership changes by definition when occurrences are replaced, while all common occurrences retain the same corresponding root parent. Raw per-boundary counts, rank distributions, complete canonical topology, encoded-key tie groups and actual decisions are retained privately and hash-bound. The public [RESULT.json](summary/RESULT.json) reports all construction levels, with denominators and detailed-boundary hashes.

## Gate exceptions

- R2 C1 changes **one more leaf** than C0 (99,986 vs 99,985). The strict C0→C1→C2→C3 monotonicity criterion is not met on both rebuilds. Deterministic evidence is not dismissed as noise.
- C3 still changes 29.008% / 29.909% of leaves, above the <=20% STRONG_GO threshold.
- No C4, freeze-all, mechanism implementation, query correctness, sanitizer/stress, latency or throughput gate was attempted.
