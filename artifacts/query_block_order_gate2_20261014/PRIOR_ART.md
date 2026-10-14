# Phase A: query-aware block-ordering admission

**Decision: SUBSUMED_MECHANISM at the flow/mechanism-family level.**
The closest prior mechanism is statistics-driven query-specific contiguous
dimension-zone visitation with exact partial-distance pruning. The proposed
changes do not establish a non-incremental distinction. This is an admission
judgment, **not** a claim that an existing implementation is literally QBLOCK32.
The following direct facts and boundaries were checked before any population run.

## Primary evidence and scope

| Area | Primary evidence | Admission relevance / boundary |
| --- | --- | --- |
| BOND query/statistics-dependent order | [de Vries et al., SIGMOD 2002](https://ir.cwi.nl/pub/10425/10425D.pdf), section5.1, printed p326 | Orders distance evaluation using query values and collection statistics. Does not specify this second-moment score or GPU warp mapping. |
| Query-only collection statistics and exact progressive pruning | [PDX, SIGMOD 2025](https://ir.cwi.nl/pub/35044/35044.pdf), section5, printed pp196:11–12 | PDX-BOND prioritizes dimensions using query distance to collection means and rejects with partially computed distances. |
| Contiguous dimension blocks rather than arbitrary gathers | Same PDX section5/Figure5, PDF page12 | Its dimension zones group consecutive coordinates and are ranked per query to trade pruning for sequential access. This is the central direct overlap, not just arbitrary-dimension ordering. |
| Shared ordering / exact early abandoning | [UCR suite, KDD 2012](https://www.cs.ucr.edu/~jzaka001/pdf/SearchingMiningTrillionTimeSeries.pdf), section4.2.2, PDF page5 | Query-magnitude ordering is motivated by expected contributions around a normalized candidate mean. Different time-series normalization/metric contract; not a direct QBLOCK32 implementation. |
| Mean and variance as query-aware priorities | [Tahmoush,2008 dissertation](https://api.drum.lib.umd.edu/server/api/core/bitstreams/842b3599-86de-46ef-936c-2e3c3aca14a4/content), section6.2, printed pp80–81 | Combines query deviation and dimensional variance. Its metric and priority expression differ; cited only as adjacent evidence, not exact formula or L2-search subsumption. |
| Dimension reordering in heterogeneous search | [HEGJoin](https://link.springer.com/article/10.1007/s41019-020-00145-x), section3.2.1 | Static average-distance dimensional order is part of its **CPU Super-EGO component**. It is not query-adaptive GPU block ordering. |
| GPU transaction geometry | [CUDA Best Practices12.9.1, section9.2.1](https://docs.nvidia.com/cuda/archive/12.9.1/cuda-c-best-practices-guide/index.html#coalesced-access-to-global-memory) | Aligned adjacent4-byte warp accesses use four32-byte transactions on the documented architectures. Hardware background, not a research contribution or actual layout qualification here. |

The latest official [PDX code](https://github.com/cwida/PDX/tree/33949c4c67f440f3733b2bd045b1d97897c2aab3)
was inspected only in selected README/searcher/pruner/utility files. Its current
layout/pruning paths have evolved; those selected files are not assumed to be
the publication's zone-order implementation. No upstream code was executed,
installed or redistributed. The paper is the direct zone-mechanism evidence.
GPU execution is discussed as future work in the paper's conclusion, so no
published GPU implementation or same-contract GPU advantage is asserted.

## Exact formula: established identity, not literal source identity

The proposed score has the exact-real decomposition

`q_j^2 - 2*q_j*mu_j + nu_j = (q_j-mu_j)^2 + Var[x_j]`.

Summing inside a fixed block adds its variance trace to a squared
distance-to-mean priority. The rational check in `kill_test.py` preserves both
positive and negative cases: equal block-variance offsets keep that proxy order;
heterogeneous offsets can reverse it. That proxy is **not asserted to be the
published PDX zone aggregation**. The inspected primary evidence does not
establish that BOND/PDX literally used this exact formula. A bounded unsuccessful
formula search is uncertainty, not evidence of absence or equivalence.

The local [Gate6 predictor](../sector_proof_per_byte_gate6_20261014/run.py),
lines43–51, already used `(q-mean)^2+variance` to score groups. This is internal
reuse evidence only, not external prior art or proof of block32 performance.

## Mechanism kill test and retained difference

The policy's data flow remains: precomputed low-dimensional statistics →
query-specific priority → visit shared contiguous dimension groups → same
partial-distance certificate and refinement. Variance changes a ranking
heuristic;32-lane ownership changes the execution grain. Neither introduces a
new rejection certificate, information representation or ownership/maintenance
mechanism in this plan. Grouped sequential access is already the direct prior
design response to gather/locality loss. No new same-contract advantage was
measured, and hypothetical gains cannot establish a non-incremental mechanism.

Accordingly, the broad research mechanism is not admitted under this plan's
explicit rule that a CUDA/Blackwell/32-d port is insufficient. Literal predictor,
layout, arithmetic, updates and performance equivalence remain **NOT_ESTABLISHED**.
This distinction prevents the admission label from being misreported as either
an empirical C1 failure or proof that no different implementation could improve
the keeper. No second predictor, sweep or workload was tried.

## Search boundary and stop

Queries covered BOND/PDX dimension/zone priority, expected-distance and
mean/variance ordering, query-adaptive feature order, GPU partial-distance
reordering, heterogeneous search, and physical permutations/replicas. Unrelated
results and secondary summaries were excluded from technical conclusions.
Fixed replicas or per-query database rearrangement are not needed by the
described zone visitation; absence of those phrases in a source is not a proof
about every implementation. No exhaustive all-literature absence claim is made.

Follow the Phase A stop: no dataset moments, real C1 orders,32M pairs, source
survivor model, alignment test, maintenance benchmark or GPU candidate this
round. Source hashes and primary locators are published; downloaded PDFs,
selected source/text snapshots and the inspected page render stay private.
