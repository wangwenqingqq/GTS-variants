# Mechanism-ranked nearest-prior-art matrix

`Y` = supported in the reviewed source; `P` = partial/proposed; `U` = unclear;
`N` = not the reviewed contract. Coordinate exact search is **not** arbitrary
metric indexing. Persistence means old decisions survive some updates, not a
universal unchanged-boundary guarantee. Stability goal is qualified in each card.

| Work | Exact arbitrary-metric search | Insert / delete | Persistent decision | Local maintenance | Explicit stability / deferred-repair goal | Risk |
|---|---|---|---|---|---|---|
| [EGNAT / ghost hyperplanes](https://users.dcc.uchile.cl/~gnavarro/ps/is11.pdf) | Y, range | Y / Y | P: historical membership, not fixed current center | Y | Y: avoid immediate costly reconstruction; quality rebuild proposed | HIGH |
| [dsa-tree combined deletion](https://users.dcc.uchile.cl/~gnavarro/ps/sccc03.pdf) | Y, range | Y / Y | P: historical topology/timestamps, fake nodes | Y, affected subtree can be broad | Y: evaluated fake-fraction repair/search tradeoff | HIGH |
| [Dynamic VP-tree](https://link.springer.com/content/pdf/10.1007/PL00010672.pdf) | Y | Y / Y (VP-copy erasure U) | P: interval/VP until structural event | Y, may reach root | Y: explicitly addresses downward propagation and substantial restructuring | HIGH |
| [Pkd-tree](https://pal.cs.ucr.edu/papers/2025/SIGMOD25/pkdtree.pdf) | N, exact coordinate search | Y / Y | P: outside reconstructed subtree | Y | Y: relaxed balance, thresholded reconstruction/query tradeoff | HIGH |
| [ikd-Tree](https://arxiv.org/pdf/2102.10808) | N, exact coordinate search | Y / Y | P: split planes until rebuild | Y | Y: avoid whole rebuild for small frames; balance/delete criteria | HIGH |
| [M-tree](https://www.vldb.org/conf/1997/P426.PDF) | Y | Y / U (omitted) | P: routing objects between splits | Y, upward split propagation | General dynamic balance, not dedicated identity objective | HIGH |
| [Pinned OMPL GNAT](https://github.com/ompl/ompl/blob/73bd861b15dd7d39129ceecf66b74387d3d84884/src/ompl/datastructures/NearestNeighborsGNAT.h) | Y, API intent; not run | Y / Y | P: pivot deletion forces full rebuild | Y plus full cleanup | Conditional deferred cleanup, not formal stability | HIGH |
| [PM-tree](https://ceur-ws.org/Vol-98/paper3.pdf) | Y | Y / U | Y global filter pivots; local split identity P | Y | N dedicated stability; tighter filtering | MEDIUM |
| [Slim-tree](https://www.cs.cmu.edu/~christos/PUBLICATIONS/EDBT_SlimTree.pdf) | Y | Y / U | P; Slim-down moves membership | Y | Quality optimization, not protected identity | MEDIUM |
| [MVP-tree extended](https://www.cs.cmu.edu/~eugene/refs/f-series/Bozkaya-ozsoyoglu-99.pdf) | Y | P / U | P/proposed same-pivot cache reuse | P/proposed | Skew-trigger restructuring discussed, evaluation future | MEDIUM |
| [Cover Tree](https://www.hunch.net/~jl/projects/cover_tree/paper/paper.pdf) | Y, nearest neighbor | Y / Y, documented | P: unaffected links | Y, invariant repair | N dedicated identity/quality lease | MEDIUM |
| [SIHC](https://www.scitepress.org/PublishedPapers/2009/18571/18571.pdf) | N, clustering | Y / U | Y topology under insertion, heights vary | Y | Y: explicitly avoids drastic hierarchy change after few cases | MEDIUM |
| [BDL-tree](https://arxiv.org/pdf/2112.06188) | N, exact coordinate kNN | Y / Y | P: untouched static components | Y, component merge/rebuild | Amortized buffer/carry, not across-rebuild identity | MEDIUM |
| [GNAT/STRIDE 2013](https://www.cs.rice.edu/~mmoll/publications/gipson2013resolution-independent-density-estimation.pdf) | Not an evaluated retrieval contract | Y / U | P between full rebuilds | Admission plus full rebuild | Growth-trigger rebalance | MEDIUM |
| [Original GNAT](https://www.vldb.org/conf/1995/P574.PDF) | Y, range | U / U | U under updates | Bulk hierarchy | N dynamic stability contract | LOW |
| GTS++ candidate | TARGET | TARGET / TARGET | TARGET | TARGET | TARGET explicit stability/quality trigger | Generic thesis KILL |

The [cards](EVIDENCE_CARDS.md) resolve pivot lifetime, split/overflow, rebalance,
rebuild frequency and deletion limits individually. No universal numeric rebuild
frequency is supplied when the source specifies event-triggered maintenance.

**Interpretation:** no one row has to use every proposed label. EGNAT establishes
historical metric decisions and quality-aware deferred repair; dsa-tree adds an
implemented exact-metric thresholded cleanup control. Their conceptual overlap
is sufficient to reject the generic recipe, without proving direct GTS parity.
