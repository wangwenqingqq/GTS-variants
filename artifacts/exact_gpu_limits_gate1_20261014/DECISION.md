# Decision: NO_GO_LIMITS_THESIS

**The frozen near-saturation thesis is rejected on the complete fixed population.**
The primary pair/original ratio is 0.094525739111,
below 0.40; query-global saves 73.687438%, above 40%.
Both independently trigger the original B1 NO_GO rule. The guarded and ordinary
counts agree for every pair, so the decision is not a floating-order artifact.
No thresholds were relaxed, and B2 is not used to manufacture an algorithm.

## Q1. How far is the current progressive count from the pair oracle?

| Free coordinate certificate | Mean dims/object | p50 | p90 | p95 | p99 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Original | 167.29161475 | 155.0 | 295.0 | 352.0 | 486.0 |
| Query-global | 44.01871025 | 30.0 | 88.0 | 119.0 | 245.0 |
| Pair-specific | 15.81336353 | 13.0 | 27.0 | 34.0 | 56.0 |

There are 32,000,000 pairs and 6,590 true hits. The primary denominator is
the original ideal per-coordinate mean, **167.29161475**, not the
checkpoint-source-equivalent **253.707194**. Pair-specific counts save 90.547426%
of that ideal coordinate count. This is LARGE_HEADROOM in the restricted family,
not measured traffic, an implementable oracle, or a universal search lower bound.

## Q2. Can one query-global order remove most remaining coordinate headroom?

Yes **in the free, oracle-fitted diagnostic**: mean 44.01871025 dims,
73.687438% fewer than original, removing 81.379936% of the gap between
original and pair oracle. The hypothesis that most remaining count headroom is
unavoidably pair-specific is contradicted on this pool. However, the order is
fitted with all nonhit labels and all 960 contributions. Its construction is
O(ND), has no held-out evaluation, and is not a cheap online policy. Noncontiguous
access, sectors, exact-score reconstruction and update/runtime costs are untested.
BOND/PDX already cover related query-aware dimension-ordering mechanisms.

## Q3. What rejection rate does compact metadata need?

In the **conditional eager-metadata plus complete-raw-fallback model**,
1–256 B/vector requires **73.598209%–80.238834%** all-object safe rejection
just for equality with 1,014,828,776 source B/query. Strict improvement requires
strictly higher rejection. The claimed >=90% barrier is therefore
**B2_BARRIER_NOT_SUPPORTED**. This is not a realizable representation frontier,
not proof that small metadata easily produces a large gain, and not an actual
physical-byte lower bound. True-hit score coordinate reads are already included
in (1-f); control, output and maintenance remain unknown rather than free.

## Q4. Where is the online reuse break-even region?

For the ideal uncapped timer-on-first-query Poisson model, equality requires
lambda*W = 3840000000/1014828776 - 1, approximately
2.783889549462. At 500 us the rate is **5567.779098925 qps**; at 100 us it is
**27838.895494623 qps**. Exact fractions, not these rounded displays, drive gates.
At 5000 qps/500 us, ideal source is 1.097142857 GB/query, still above keeper.
Thus B3_FROZEN_REGION_BARRIER holds in the specified region. Outside it, the
algebra has winning regions, which are retained. No longer window, scheduler,
GPU service or complete SLA is executed or validated. This is not a bound on
every online batching strategy or dynamic workload.

## Q5. Can historical results be explained by one universal boundary?

No. Byte reduction is a useful accounting lens, not a demonstrated unavoidable
frontier. The static progressive mechanism genuinely reduced historical
all-kernel DRAM by 71.0181% and Host-ready range latency by 55.6625%
(2.255428x), but source bytes and DRAM are distinct. The bounded dynamic A
service ratio was 0.855934141 and missed its 0.85 admission gate; B was not run.
Contiguous tree packing and later sector/packing models show positive headroom.
INT8 has no population/GPU result. Batching has only the scoped synthetic-model
failure. These are not interchangeable proofs that every alternative fails.

## Separate dispositions and next action

- Implementation: the complete CPU diagnostic is correctness-qualified on this
  fixed workload: all 32M full authority scores match bitwise; no guarded false
  rejection; all reference/data hashes preserved.
- Mechanism: free query-aware ordering leaves large coordinate-count headroom.
  **No actual new algorithm, DRAM reduction or end-to-end speedup is admitted.**
- Thesis: **NO_GO_LIMITS_THESIS**; no lower-bound claim, paper outline, kernel,
  tuning sweep, new layout, batch execution or final GPU validation follows.
- Reopen only through a separately authorized, novelty-audited mechanism with
  charged ordering/metadata/update/output and decisive same-contract evidence.
  Do not rescue this thesis by dropping counterexamples or changing thresholds.

Confidence is high for the finite-population count decision and exact algebra;
generalization beyond these 32 range queries, one radius and one static GIST1M
snapshot remains unknown. Dynamic search in the title is the proposed thesis,
not a newly measured dynamic experiment.
