# Limits and design-space novelty audit

## Admission decision before population evaluation

**No universal lower-bound or limits-paper novelty admission.** The authorized
work is a bounded falsification of the proposed empirical boundary on one
fixed range workload. General high-dimensional indexing degeneration,
I/O-aware search, filter/refine and query-aware partial-distance ordering are
established topics. None of the sources below establishes the proposed
1.015 GB/query finite-population bound under this dynamic GPU contract; their
absence of that bound also does not establish novelty. No manuscript is drafted.

| Primary source and inspected scope | Established result / mechanism | Transfer limit and kill-test implication |
| --- | --- | --- |
| [Weber, Schek, Blott, VLDB 1998, sections 2–4](https://www.vldb.org/conf/1998/p194.pdf), full paper | Uniform independent coordinates support an average-case block-access model for partitioning/clustering degeneration. VA-file uses compact approximations followed by refinement. | Disk blocks, distribution assumptions and nearest-neighbor queries are not this finite GIST GPU-byte contract. It also provides a positive metadata alternative: degeneration is not an arbitrary-representation impossibility. |
| [Barkol and Rabani, JCSS 2002](https://www.sciencedirect.com/science/article/pii/S0022000002918313), publisher abstract only, DOI 10.1006/jcss.2002.1831 | Exact/decision nearest-neighbor cell-probe space–word-size–time tradeoffs are proved for the Hamming cube, including randomized two-sided-error algorithms. | Worst-case restricted-model probe counts cannot be substituted for source bytes on a fixed dataset. No new theorem or stronger transfer is inferred from the abstract. |
| [Pestov, arXiv:cs/9901004](https://arxiv.org/abs/cs/9901004), author abstract | Concentration and geometric assumptions explain high-dimensional similarity-search difficulty. | Distributional geometry is not a pointwise guarantee about this population's original/reordered FP64 partial sums. |
| [Volnyansky, arXiv:0905.2141](https://arxiv.org/abs/0905.2141), author abstract | In an iid concentrating metric-space sequence, with stated dimension scaling and o(n/d) pivots, pivot indexing becomes asymptotically linear. Each full distance is counted as one computation. | The restricted pivot model does not count GPU coordinates, sectors, control, output, or updates. It cannot rule out selective coordinates or another representation. |
| [Hellerstein, Koutsoupias, Papadimitriou, PODS 1997](https://cgi.di.uoa.gr/~elias/papers/paper-hkp97.html), author abstract | Indexability formalizes the tradeoff between storage redundancy and block-access overhead for a workload. | The proposed bytes/update map is not a new general tradeoff framework. Object-block access overhead differs from metadata-bit and partial-coordinate costs. |
| [Hong and Kung, STOC 1981, sections 2–3](https://www.eecs.harvard.edu/~htk/publication/1981-stoc-hong-kung.pdf), full paper | Red-blue pebbling derives I/O bounds for specified computation DAGs and fast-memory capacity. | A fixed-DAG bound is not automatically a bound over data-dependent pruning, preprocessed metadata, all representations, or online schedulers. A search-family reduction would be required; none is claimed. |
| [de Vries et al., SIGMOD 2002](https://ir.cwi.nl/pub/10425/10425D.pdf), full paper | BOND combines vertical decomposition with branch-and-bound distance evaluation and dimension prioritization. | Query-aware dimensional access is prior art, not a new mechanism if the oracle finds headroom. No published speedup is transferred to the frozen GPU range contract. |
| [Kuffo, Krippner, Boncz, SIGMOD 2025, sections 5–7](https://ir.cwi.nl/pub/35044/35044.pdf), full paper | PDX-BOND couples partial-distance pruning, query-aware dimension/zone order, and SIMD-friendly layout. It explicitly studies pruning versus access efficiency, including cases where linear scan wins. | Fewer logical dimensions do not establish a GPU traffic or end-to-end improvement. Execution/layout remains material; a universal 'only information demand matters' thesis is too strong. Their rule uses distance to collection means; our nonhit mean-squared-contribution oracle is not that implementable policy. |

The existing [INT8 audit](../certified_int8_gate0_20261014/DECISION.md) and
[cross-query audit](../cross_query_reuse_gate0_20261014/PRIOR_ART.md) remain
scoped parent evidence, not additional failures of all precision or batching
mechanisms. The INT8 population/GPU tests were not run. The Poisson batching
study was synthetic and excluded GPU service and updates.

## Cheap thesis kill tests

1. Sort each pair's contributions with free construction. A ratio below 0.40
   rejects near-saturation **even in the deliberately restricted family**.
2. Give a single query order access to all nonhit labels. Savings above 40%
   reject the claimed shared-order saturation, without implying implementability.
3. Compute the eager-metadata/full-fallback plane. A sub-90% break-even rejects
   the proposed strong metadata barrier, not the existence or absence of a
   realizable representation.
4. Retain positive parent layout/certificate/progressive counterexamples and
   unknown maintenance costs. Do not select only historical negative gates.

All four tests may falsify the thesis; none proves an arbitrary-index physical
lower bound. A stop leaves no automatic kernel, layout, paper or GPU follow-up.
