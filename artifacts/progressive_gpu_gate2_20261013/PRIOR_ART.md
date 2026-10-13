# Prior-art kill test before GPU implementation

Classification: **ENGINEERING_ONLY** for this STAGED_COMPACT prototype.
The experiment is a bounded feasibility/attribution test, not admission of a
new research thesis. No paper prose or dynamic integration is authorized here.

| Source | Established mechanism | Boundary for this test |
|---|---|---|
| [UCR Suite, SIGKDD2012](https://www.cs.ucr.edu/~eamonn/SIGKDD_trillion.pdf), section4.1.3 | Exact Euclidean early abandoning uses a nonnegative partial distance. | The threshold rule is not novel. Time-series normalization and access reordering are not used here. |
| [PDX, SIGMOD2025](https://ir.cwi.nl/pub/35044/35044.pdf), sections2–5,9 | Dimension pruning, blocked vertical storage, SIMD-aware execution and exact PDX-BOND already connect avoided coordinates to access efficiency. | This is a major nearest competitor to any representation/layout thesis. The paper evaluates CPUs and identifies GPU processing as future work; that distinction is not itself a novel mechanism. Gate2 changes neither layout nor coordinate order. |
| [NVIDIA cuVS IVF-PQ](https://developer.nvidia.com/blog/accelerating-vector-search-nvidia-cuvs-ivf-pq-deep-dive-part-1/), optimization discussion | GPU fused distance evaluation already uses partial-component stopping for some metrics. | PQ/ANN membership is not this full exact raw-FP32 range contract. The generic GPU early-exit claim is nevertheless subsumed. |
| [Apache Paimon range search](https://paimon.apache.org/docs/vector-index/range-search.html), boundary discussion | A running nonnegative distance can safely abandon a row; different summation orders can disagree near a cutoff. | This prototype needs an explicit ordered-oracle interval and fallback, rather than treating two reductions as equivalent. This documentation is not a GPU staged-compaction performance result. |
| [Billeter et al., HPG2009](https://highperformancegraphics.org/previous/www_2009/presentations/billeter-efficient.pdf) | GPU stream compaction is an established primitive for retaining useful work across processing stages. | Stable CUB selection is reused; queues, compaction and fusion are not claimed as inventions. |
| [VA-file, VLDB1998](https://www.vldb.org/conf/1998/p194.pdf), section4 | Coarse filters with exact refinement precede this work. | Gate2 has no quantized representation and cannot claim generic filter/refine novelty. |

Cheap falsification question: does reduced logical coordinate demand survive
actual coalescing/cache/scratch traffic and complete-output request timing after
state, compaction, count synchronizations and numerical replay are charged?
Only one frozen candidate and one fixed32-query workload are tested. A positive
answer is implementation feasibility, not POTENTIALLY_DISTINCT_SYSTEM_DESIGN.
An eventual paper mechanism requires a non-incremental difference from these
systems and a same-contract external comparison; ordinary engineering, packaging
or a small GPU speedup cannot rescue a subsumed early-abandoning thesis.

The inspected sources do not establish an exact match to the specific four
stages, ordered-FP64 oracle and Blackwell B1 request denominator. This is a
bounded source audit, not an exhaustive absence-of-prior-art claim. Persistent
filter/compact pipelines remain established execution patterns; no persistent
implementation is included or admitted by this round.
