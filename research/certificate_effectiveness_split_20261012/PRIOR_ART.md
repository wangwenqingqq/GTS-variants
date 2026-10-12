# Gate 0: prior art and claim boundary

Checked primary sources on 2026-10-12, before construction:

| Category | Primary source | Overlap and boundary |
|---|---|---|
| Workload-aware / query-aware partitioning | [Qd-tree, SIGMOD 2020](https://www.microsoft.com/en-us/research/wp-content/uploads/2020/06/qdtree-sigmod20.pdf), Sections 2, 4, 5 | Greedy top-down candidate-cut selection optimizes skipped tuples for a workload. It explicitly separates local greedy choices from globally optimized trees. Relational workload, not this exact GIST/PCA8 certificate. |
| Learned index construction | [RLR-Tree, PACMMOD 2023](https://zhengwang125.github.io/paper/RLR_Tree_SIGMOD_2023.pdf) | Learned subtree/split choices for spatial R-trees; generic construction optimization is not new. No learned method is implemented here. |
| PCA / RP / kd / variance / two-means split heuristics | [Verma, Kpotufe and Dasgupta, UAI 2009](https://arxiv.org/pdf/1205.2609) | Data-dependent space-partition trees and local geometry are established; axis/radial proposals are diagnostic alternatives, not contributions. |
| Spill trees / nearest-neighbor partition structures | [Muja and Lowe, TPAMI 2014](https://www.cs.ubc.ca/~lowe/papers/14mujaPAMI.pdf), related work | Approximate search and established kd/PCA/RP/k-means/spill structures; no ANN or broader family sweep is admitted. |
| Metric partition and GPU execution | [GTS, 2024](https://arxiv.org/html/2404.00966v1) | Original metric-tree ownership is the immutable P0 comparator, not replaced by a claimed new GPU algorithm. |

## Cheap novelty kill test

**Rejected as a new thesis:** choosing the split that best skips a given workload.
Qd-tree already establishes that mechanism in its problem setting. Engineering a
PCA-based variant does not rescue that generic novelty claim.

**Admitted only as diagnosis:** does a fixed, exact-safe 64 B PCA8 certificate gain
material ancestor-level coverage when a local oracle picks among twelve legal,
balanced splits? This is a same-contract count experiment, not a novel learned
index, external performance comparison, or universal limit. A positive result
would require a query-independent construction mechanism and decisive external
same-contract end-to-end evidence before any paper promotion. A negative result
rejects this tested local-greedy path, not globally optimized trees or every GPU
index.
