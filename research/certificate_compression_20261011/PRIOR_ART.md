# Gate 0: prior-art kill test

Verified 2026-10-11. This round measures an established baseline; it does not
propose pivot intervals as novel geometry. No paper drafting or GPU mechanism
implementation is admitted by a favorable offline count alone.

| Work | Established mechanism | Consequence for this experiment |
|---|---|---|
| [AESA, Vidal (1986)](https://www.sciencedirect.com/science/article/pii/0167865586900139) | Metric-distance elimination with precomputed distance information, with quadratic space costs | Triangle-inequality elimination is not new. No constant-time claim is transferred to this GIST workload. |
| [LAESA, Mico/Oncina/Vidal (1994)](https://www.sciencedirect.com/science/article/pii/0167865594900957) | Linear preprocessing/storage variant using reference objects | A small reference-object family is not itself a contribution. |
| [M-tree, Ciaccia/Patella/Zezula (1997)](https://www.vldb.org/conf/1997/P426.PDF) | Paged dynamic metric hierarchy; covering regions and distance-based safe exclusion | A safe region bound or dynamic metric-tree packaging is not new. |
| [Pivoting M-tree, Skopal (2004)](https://ceur-ws.org/Vol-98/paper3.pdf) | Fixed global pivots and per-region min/max hyper-ring intervals, combined with the original region constraint | This directly subsumes GLOBAL interval-summary geometry in this plan. Global pivot bounds remain a classical comparator. |
| [G-PICS, Lewis/Tu](https://cse.usf.edu/~tuy/pub/tech09-002.pdf) | GPU tree construction and concurrent spatial/similarity query execution | GPU processing, level concurrency, and tree reorganization alone are not novelty. The linked primary author report predates the final journal version. |
| [GTS, Zhu et al. (2024)](https://arxiv.org/html/2404.00966v1) | Pivot-based metric tree, GPU list tables, batch/sequential query grouping | Existing GPU metric indexing already couples geometry to GPU execution. The baseline here is the frozen repaired G0, not an unmodified-paper throughput reproduction. |

The PM-tree primary paper explicitly defines each routing interval using the
minimum and maximum pivot distance over its descendant objects. Its general
pivot-based approach also describes query-pivot distances and triangle-based
elimination. Therefore simply adding more such intervals to GTS cannot enter
the paper's contribution list.

## Candidate questions and verdicts

1. **GLOBAL intervals:** same summary exists; geometry novelty is killed.
   Removing the GTS background leaves ordinary multi-pivot ring filtering.
2. **REGION_ORACLE selection:** selects dimensions to cover this frozen query
   set. A positive result is diagnostic headroom, not a held-out or deployable
   selection algorithm and not established novelty.
3. **Packed IDs / aligned FP32 metadata:** engineering cost accounting only.
   Do not rescue a subsumed thesis by a few bytes or packaging.
4. **GPU-native execution / budgeted representation:** still unknown. A future
   proposal needs a distinct mechanism, stronger closest-work comparison,
   same-contract end-to-end evidence, and costs that beat the classical
   comparator. No such proposal is claimed by this round.

This diagnostic is allowed to proceed because the user explicitly requests a
classical-baseline compressibility kill test. A negative result kills only the
declared pivot family / sampling / budget on these eight queries, not all
possible certificates or partition choices.
