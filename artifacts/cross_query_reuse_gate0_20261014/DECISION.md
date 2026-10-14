# Decision: NO_GO_CROSS_QUERY_REUSE

## Q1. Is this ordinary batching/GEMM?

Cap/window scheduling, multi-query full scans and shared dataset evaluation are
established. The proposed stronger strict deadline/mixed-output/update system
has no admitted distinct mechanism yet. Direct full-contract subsumption was
not established either. In particular, OpenViking's published performance report
explicitly predates its microbatch implementation; a current runnable harness
does not turn that report into a new-path SLA evaluation. Novelty is NOT_ADMITTED.
The user authorized this CPU-only opportunity test despite that unresolved gate.

## Q2. What batches form within500us?

Four100k-query traces yield mean B=1.049362,1.252285,1.501141,3.515680 at
100,500,1000,5000qps. There are no two qualifying non-extreme rates; none reaches
mean B>=4. p90/p99 deliberate collection wait is500us at every point. This is
not complete queueing or Host-ready latency: GPU busy time, runtime dispatch and
service stability are omitted. The arrival trace is synthetic, not observed traffic.

The analytic oracle explains the discrepancy with the plan examples. First
arrival plus the arrivals in0.5ms gives min(1+Poisson(lambda/2000),8), not a
steady batch of8. At5000qps only1.385178% of finite-trace batches have B=8,
covering3.152% of queries. Query-experienced mean B=4.21246 is size-biased and
must not be substituted as the effective amortization denominator.

## Q3. Does complete amortization beat the keeper?

Primary bytes/query = DB_BYTES * batch_count / query_count. At5000qps,
28444 batches /100000 queries cost1,092,249,600 ideal source bytes/query.
That exceeds the frozen1,014,828,776 range-source reference by77,420,824B
(7.628954345%). The plan's1.0GB NO_GO threshold fails at all four points;
its0.75GB GO target is farther away. Even the uncapped continuous-Poisson
long-run lower bound at the highest rate is1.097142857GB, before all extras.

The batch-weighted diagnostic E_batch[3.84/B] is1.400618GB at5000qps. Both
weightings are retained as the user confirmed; they answer different questions.
No query state, output, control, exact score or update overhead is priced as zero.
The reference is from exact range only; mixed/kNN keeper costs are UNKNOWN.
No actual DRAM, throughput, latency or external-index superiority is claimed.

## Q4. Can mixed range/kNN share a distance phase?

Mathematically yes: a common immutable database row can feed independent
query-specific distance expressions and independent range/top-k consumers.
This does not remove B-query arithmetic or selection/output costs. It does not
prove reassociated GEMM scores match the authoritative ordered-FP64 oracle.
Only type tags/ownership were tested; actual mixed outputs were NOT_RUN.

## Q5. Can updates coexist with epochs?

A dispatch pin can order queries against update commit/ACK without holding a
writer lock throughout the scan. This is a protocol construction, not a validated
GPU mutable store without rebuild. Copy-on-write/version, memory growth and
reclamation costs are UNKNOWN. A strictly arrival-ordered serial Q/I/D workflow
must split at update barriers; otherwise a delayed Q may observe an update that
the old reference forbids. Such barriers are omitted from the optimistic model.

## Final gate and reopening

All four points satisfy a NO_GO source condition. At5000qps the mean-B
CONDITIONAL condition also holds; the human-confirmed NO_GO priority resolves
the overlap without weakening any threshold. No unclassified result occurred.

Implementation: CPU model only. Mechanism opportunity: rejected in the frozen
Poisson/500us/v0 scope. Thesis admission: unresolved/NOT_ADMITTED. GPU, exact
search numerical validation and dynamic integration: NOT_RUN/NOT_ADMITTED.

Do not revive this frozen direction through offline B8/32/64 numbers, synthetic
backlog, an uncharged longer window, or architecture changes. Reopening needs
an independently motivated workload/scheduler mechanism with proven opportunity
under a new explicit contract, prior-art admission, actual service/visibility
costs and same-contract comparison. This result does not reject batching at
other rates, bursty arrivals, other budgets or other workload distributions.
