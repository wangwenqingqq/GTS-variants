# Gate -1: certificate-demand sector packing

**Verdict: DISTINCT_ENOUGH_TO_TEST.** This admits one bounded CPU
information/representation test, not a novelty claim or a GPU admission.
Reviewed on 2026-10-14, before training IDs, packing or population replay.

The narrow question is whether a query-distribution-derived, single global
dimension permutation, grouped into eight-coordinate transactions, improves
exact partial-distance rejection under the same 512-byte source-payload budget.
The reviewed primary sources establish substantial component overlap, but do
not directly establish this complete narrow policy in exact search. This is
bounded search evidence, not a proof that no such work exists. An identical
same-setting source would reverse admission to SUBSUMED immediately.

## Required coverage

| Area | Primary source and inspected boundary | Admission consequence |
|---|---|---|
| BOND ordering / physical organization | [BOND, SIGMOD 2002](https://www.cs.uoi.gr/~nikos/sigmod02.pdf), Sections 1 and 5.1: decomposed dimensions permit query/statistics-dependent ordering and exact partial-distance bounds. | Exact early rejection and dimension ordering are established, not contributions here. It does not specify training-query pair co-selection into fixed-width within-row groups. |
| PDX / PDX-BOND layout | [PDX, SIGMOD 2025](https://ir.cwi.nl/pub/35044/35044.pdf), Sections 3, 4.3, 6 and 7: dimension-major storage within vector blocks and query/mean-aware dimension visitation. | Layout plus exact pruning is established. Its object-block transposition is not the proposed within-row eight-coordinate grouping. |
| Cache-aware feature/dimension packing | [Data Morphing, VLDB 2003](https://pages.cs.wisc.edu/~jignesh/publ/dmg.pdf), Sections 4 and 6-7: query-workload attribute grouping and cache-line colocation. | Packing co-demanded values into cache lines is old. The setting is relational access, not this exact-distance rejection policy. |
| SIMD dimension permutation | [Faiss distance source](https://github.com/facebookresearch/faiss/blob/main/faiss/utils/distances_simd.cpp), snapshot hash in SOURCES.json; PDX Section 6. | SIMD/transposed distance evaluation is established. The inspected implementations do not learn coordinate co-demand groups from held-out query distributions. A SIMD port is not a new mechanism. |
| Query-distribution-aware column ordering | [HYRISE, PVLDB 4(2)](https://www.vldb.org/pvldb/vol4/p105-grund.pdf), Sections 4.1-4.3: workload weights, cache cost, non-overlapping layouts and co-access graph partitioning. | This is the strongest generic overlap. Workload-aware physical grouping cannot be claimed as new. The paper does not evaluate exact partial-L2 certificate yield. |
| Feature co-access / colocation | HYRISE Section 4.3; [automated vertical/horizontal partitioning, VLDB 2004](https://cs.brown.edu/courses/cs227/archives/2012/papers/partitioning/agrawal-2004.pdf), Sections 4.2-4.3: workload column groups and useful-byte fractions. | Co-selection affinity and locality objectives are established. Renaming access demand as certificate demand does not make the matrix/greedy algorithm novel. |
| GPU transaction-aware vector layout | [CUDA Best Practices 12.9.1, coalescing](https://docs.nvidia.com/cuda/archive/12.9.1/cuda-c-best-practices-guide/index.html#coalesced-access-to-global-memory); [DF-GAS, MICRO 2023](https://nicsefc.ee.tsinghua.edu.cn/nics_file/pdf/867cd930-3413-4af5-9bf6-f3640820d0e7.pdf), Section 5.B, inspected as adjacent feature-packing evidence. | NVIDIA documents 32-byte transaction accounting; that is hardware background, not novelty. DF-GAS packs outstanding feature requests across ANN processing elements, not the proposed learned global coordinate permutation. It is FPGA approximate graph search, not a substitute for a same-contract exact baseline. |
| Exact-search dimension permutation | BOND Section 5.1; [UCR suite, KDD 2012](https://www.cs.ucr.edu/~jzaka001/pdf/SearchingMiningTrillionTimeSeries.pdf), Section 4.2.2: query-ordered early abandoning of exact distance calculations. | Permutation invariance in real arithmetic and query-adaptive ordering are established. Neither inspected method trains one workload-dependent fixed physical sector partition. Floating-point order still needs its own gate. |

## Mechanism kill test and strongest caveat

Write U[q,j]=1 if coordinate j occurs in the training query's existing C1 top128.
The proposed matrix is exactly W=U^T U. For disjoint groups G, its pair-affinity
objective is sum_G sum_(i<j in G) W[i,j] =
sum_q sum_G choose(|S_q intersect G|,2). This is generic co-access clustering;
the proposed greedy fill contains no distance outcomes, thresholds, or new
certificate learning. The generic algorithmic novelty thesis is therefore
**not admitted**. HYRISE is not asserted to implement this exact PACK8 greedy.

What remains testable is a narrower, empirical hypothesis: applying that old
affinity primitive to moment-selected exact-distance coordinates can recover
enough information density lost to a fixed physical sector budget. Combining
the adjacent papers does not, by itself, prove direct same-setting subsumption.
No GPU port, broader packaging or small gain can rescue a subsumed thesis.
Any numerical result stays a diagnostic; paper claims are prohibited this round.

## Search and limits

Searches covered exact partial-distance packing, dimension reordering/permutation,
SIMD distance layouts, workload column ordering, feature co-access and GPU/FPGA
vector access. Primary full texts/code were inspected; unrelated results,
secondary summaries and ANN row/graph reordering were not used as direct evidence.
Sources and immutable snapshot identities are in SOURCES.json. PDFs/source
snapshots remain private and are not redistributed.

No decisive source was found for the complete narrow policy; that absence is
uncertainty, not a positive novelty proof. The next permitted action is exactly
the frozen 1024-query training and one 32-query CPU evaluation in CONTRACT.json.
