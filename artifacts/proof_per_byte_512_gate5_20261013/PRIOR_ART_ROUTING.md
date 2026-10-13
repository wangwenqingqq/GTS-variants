# Dedicated routing novelty gate

**Verdict: NOT_DISTINCT_ENOUGH_TO_IMPLEMENT.** Numerical diagnostic GO does not
admit a GPU prototype. The broad query-adaptive coordinate-priority / exact
partial-distance mechanism is established. The tested moment score is not shown
to be a non-incremental departure from it.

## Primary evidence and six requested search areas

| Area | Primary evidence inspected | Consequence |
|---|---|---|
| Query-adaptive dimension ordering | [BOND (2002)](https://www.cs.uoi.gr/~nikos/sigmod02.pdf), Sections 5/7.2; [PDX-BOND (2025)](https://arxiv.org/html/2503.04422v1), Section 5 | Dimension access conditioned on the incoming query is already part of exact search. |
| Partial-distance search order | [UCR Suite (2012)](https://www.cs.ucr.edu/~eamonn/SIGKDD_trillion.pdf), Section 4.2.2 | It explicitly compares hindsight contribution ordering with a query-derived ordering for Euclidean early abandoning. The oracle-versus-cheap-probe abstraction is not new. |
| Dynamic feature ordering | BOND and UCR Suite, same sections | Different incoming queries induce different coordinate priorities; this is not equivalent to a novel routing system. |
| Exact Euclidean dimension selection | [d-D Sort (2013)](https://onlinelibrary.wiley.com/doi/abs/10.1155/2013/405680), Section 3.1; publisher paper snapshot | Query-significance order and stopping on a partial distance are explicit exact-matching techniques. Its normalized-descriptor setting is not our FP32 contract. |
| SIMD/GPU coordinate scheduling | PDX Sections 3-5 and the [official code](https://github.com/cwida/PDX/tree/467a10ee7d35b7d10191a0c2d528a870b6ae68d8); targeted GPU/coordinate/early-abandoning searches | PDX supplies CPU vectorization/layout evidence. No matching GPU mechanism was established in this bounded review. That unknown is not a novelty proof, and C1 implements no GPU scheduling. |
| PDX/BOND variants | PDX-BOND Section 5; [DCO evaluation (2026)](https://openproceedings.org/2026/conf/edbt/paper-270.pdf), Section 3 | The strong relevant family must be treated as prior art, not omitted in favor of full scan or arbitrary first dimensions. |

## Established facts, inference, and unknowns

**Fact:** PDX-BOND prioritizes dimensions by query distance from dimension means
and uses partial distances for exact pruning. Its published algorithm, not a
claimed reproduction of the current repository, is the decisive overlap. The
inspected current headers are ADSampling-based; they do not independently prove
that the paper's ordering is today's selected runtime path.

**Fact:** UCR's query ordering is motivated by expected coordinate contributions
for normalized data. Under shared zero means and equal variances, C1's score
reduces to the same absolute-query priority.

**Inference:** adding a population variance term to the mean-based priority is a
simple moment correction, not yet a distinct system mechanism. This is a research
admission decision, not a claim that one inspected source printed the identical
FP32 equation. Changing the name to Proof-per-Byte or porting this heuristic to
CUDA would not repair the missing novelty.

**Unknown:** an identical published moment equation in every setting, an
exhaustive absence result, same-contract advantage over a query-adaptive external
comparator, actual sectors/DRAM, and end-to-end GPU execution. None is inferred
from our survivor counts. Inaccessible LDC/multi-feature-ordering leads were not
used as decisive full-text evidence.

## Disposition

Keep the numerical GO as a fixed-pool information diagnostic and potential
baseline-strengthening evidence. Do not promote a new dimension-ordering thesis,
write CUDA, change the keeper, or edit the manuscript. Reopening requires explicit
authorization of a genuinely different, defensible mechanism and a new frozen
comparison against the relevant query-adaptive family; added packaging and small
engineering gains are not sufficient.

Primary snapshot URLs, revisions, byte counts and hashes are in
`evidence/SOURCE_IDENTITIES.json`; copyrighted PDFs and downloaded code snapshots
remain outside Git. No external performance number is adopted as our evidence.
