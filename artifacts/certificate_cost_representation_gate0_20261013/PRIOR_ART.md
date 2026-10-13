# Prior-art admission: SUBSUMED at the broad core-thesis level

Review date: 2026-10-13. Only primary papers, a technical disclosure and pinned
official source support this matrix. Full source contents stay private; their
retrieval identities are in evidence/SOURCE_IDENTITIES.json. A search miss is
not a proof that no work exists.

| Requested coverage | Primary source | Objective/mechanism inspected | Admission relevance |
|---|---|---|---|
| MRL; prefix-aware representation/metric learning | [MRL](https://arxiv.org/html/2205.13147v4), [official code](https://github.com/RAIVNLab/MRL/blob/7ccb42df6be05f3d21d0648aa03099bba46386bf/MRL.py) | Task losses at nested representation lengths; adaptive shortlisting and refinement | Not a proof of a certificate-cost objective. MRL vectors can still use safe partial squared-L2 bounds; do not claim that MRL inherently cannot support exact search |
| Nested/elastic embeddings; model early exits | [2DMSE](https://arxiv.org/abs/2402.14776) | Elastic embedding dimensions and encoder depth | Model-computation exit is different from exact pair-distance rejection |
| Compute-aware retrieval using learned prefixes | [AdANNS](https://arxiv.org/html/2305.19435v2) | Different dimensional capacities across ANN construction/search phases | Accuracy/compute trade-off, not this zero-false-rejection certificate contract |
| Learned dimension selection/order | [SMEC](https://aclanthology.org/2025.emnlp-main.1332/) | Sequential Matryoshka training, adaptive dimension selection, cross-batch learning | Retrieval compression quality; an explicit exact expected-dimensions loss is not established here |
| Training representations for cheap exact certificates; metric early rejection | [HN, arXiv2606.27280v1](https://arxiv.org/html/2606.27280v1) | Trained energy allocation, admissible prefix bound and exact refinement | Direct overlap with the broad core thesis; see the derivation below. The specified softplus objective is not shown identical |
| Earlier technical disclosure of trained major/minor descriptors | [US11797603B2](https://patents.google.com/patent/US11797603B2/en) | Hierarchical normalization, descriptor-network training and prefix/full comparison | Technical context only; no legal scope, validity, ownership or freedom-to-operate conclusion |
| Hardware-aware embedding training | [CQ-CiM](https://arxiv.org/abs/2602.20083) | Joint compression/quantization and hardware-aware shaping for memory-compute retrieval | A different hardware/quality objective; not admitted as an exact raw-distance certificate baseline |
| Fixed-vector partial-distance pruning/layout | [BOND](https://www.cs.uoi.gr/~nikos/sigmod02.pdf), [PDX](https://arxiv.org/html/2503.04422v1) | Previously audited partial distances and physical organization | Context from unchanged parent Gate4, not a new trained-representation experiment |

## Decisive source locators, not performance adoption

HN is a June 2026 preprint, predating this plan. Inspect §§3.1–3.3 for its
normalization/bound/search and §4 for fine-tuning. Its training uses a triplet
objective, not the proposed cost surrogate. Its reported benchmark is different;
no reported speedup, quality result or numerical determinism claim is reproduced
or adopted here. The patent's descriptor training discussion is secondary
technical context, not the sole admission basis.

## Independently derived relation

Use squared-distance cutoff **t** (a radius would be tau with t=tau²).
For HN vectors with both suffix squared norms alpha and both full norms one,
write s as the prefix inner product and U=s+alpha. Then:

```text
prefix_d2 = ||q_prefix||² + ||x_prefix||² -2s
          = 2(1-alpha)-2s
          = 2-2U
full_d2   >= prefix_d2
full_d2   <= prefix_d2+4alpha

prefix_d2 > t  <=>  U < 1-t/2
```

The first inequality follows from a nonnegative suffix squared distance; the
second from the suffix norm bound. For inclusive range membership, equality
must continue to exact refinement. This is an algebraic adaptation of a bound,
**not** a reproduction of the paper's top-1 algorithm, tie rule or FP32 code.

The identity holds under **HN's equal fixed-energy constraints**, not for every
arbitrary full-L2-normalized candidate. It neither equates the two training
objectives nor proves P1's quality/cost effect. The rational fixture checks this
limited relation and boundary witnesses, not trained-network superiority.

## Research decision and strongest unresolved distinction

`SUBSUMED` applies to the broad claim that learned representations can make
prefix-certified exact retrieval cheaper. The requested variable-energy,
multi-stage cost loss could behave differently; its non-incremental mechanism,
quality retention and advantage over HN are **UNKNOWN**. A different loss formula,
dataset or dimensionality alone does not meet the user's research admission bar.

Therefore stop before paid training. This is not an empirical rejection of the
P1/MRL hypothesis and not an impossibility result. Reopening needs a specifically
non-incremental distinction and a newly frozen comparison that includes HN;
no extra baseline, loss search or GPU run is silently added to this plan.
