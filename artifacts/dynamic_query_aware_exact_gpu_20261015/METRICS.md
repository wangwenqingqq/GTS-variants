# Denominators and interpretation

| Metric | Definition | Not interchangeable with |
|---|---|---|
| Query ACK | Host request ready → full Host native IDs/fields ready, including order and mapping | Kernel events / profiler duration / one-time build |
| Phase query latency | Mean of32 query ACKs inside each process, then six-process distribution | A population percentile or160 pooled independent samples |
| Mutation fraction | Distinct original objects replaced / initialN | Point-update count, batchACK count, or elapsed time |
| Mean drift | FP64 live-mean relative L2 difference from FP64 initial mean | Proof that stale order loses latency |
| Stage coordinates | Sum of stage input rows × stage width, from actual GPU counters | First-crossing required dimensions, measured bytes, or free restoration |
| Query traffic | All captured query-kernel DRAM/L2 per query and window | DMA-inclusive traffic or statistical repeated-process CI |
| Update ACK | Complete delete or insert batch, including INC gather/sums/mean delivery | Point latency unless divided and explicitly labeled amortized |
| Copy-request bytes | Actual issued H2D/swap D2D payload sizes | Device DRAM traffic |
| Incremental update tax | Median of six matched INC−STALE total update ACK differences, signed bootstrap CI | Isolated stats-kernel time or nonnegative guaranteed cost |
| Maintenance submit/tail | Recorded nested Host spans; tail includes queued data waiting | Additive service components or isolated CPU/control time |
| Standalone maintenance | Zero: no periodic refresh/rebuild outside update ACKs | Free incremental maintenance; it is charged inside updates |
| Segmented service | Events + complete service-owned device/maps/retained Host release | Uninterrupted process time, client inputs, or context teardown |
| Peak device-owned memory | Known simultaneously reserved allocations, no in-event growth | Maximum of every external library/driver allocation |
| CPU interval use | getrusage user/system seconds during events | Cause of time saving, all-machine utilization, or the original GTS CPU bottleneck |

Query benefit retention at window a is `(1−PDX_a/S1_a)/(1−PDX_0/S1_0)` from
same-campaign median ratios. It is undefined if the initial advantage is not
positive; it is not clamped at100%. Also report PDX_a/PDX_0: changing corpus and
answer sizes can speed all systems, so that self-ratio alone is not degradation.
Both PDX policies and every material exception are retained.

The primary estimator is ratios of medians of six independent process
aggregates. Paired geometric ratios and fixed-seed20k percentile bootstrap CIs
are separate; the paired CI does not describe the median-ratio estimator.
Composition figures use arithmetic process means so components add exactly,
not sums of component medians. INC statistics remain inside the update segment.
There is no latency, correctness or scientific gate inferred from NCU duration.

The requested outcome families are potentially overlapping descriptions, not
exhaustive disjoint numeric labels. Dynamic robustness and a query-insensitive,
update-dominated workflow can coexist. One synthetic distribution shift cannot
prove distribution-independent robustness, necessity of refresh, an impossibility
bound, or a new dynamic-specific research gap. Weak/no drift or noisy comparison
remains uncertainty rather than automatic evidence for or against a mechanism.

## Descriptive inventory

`results/SUMMARY.json` retains all six process values for each descriptive
median. Query p50/p95/p99 are computed within each160-request sequence, then
summarized across processes; they are not population/SLA percentiles. Update
rates distinguish point updates from batch ACKs and include all query and
release time. Both delete and insert batch ACK totals/means are reported.
Copy-request bytes describe issued insert H2D plus swap D2D only, excluding
statistics scratch/mean traffic; actual kernel DRAM/L2 has a separate profiler
scope. Logical coordinates likewise exclude original-order FP64 restoration.
Known device-owned peak, driver-observed device bytes, and whole-process peak
RSS including client data are deliberately different columns. Statistics
submit/tail spans are nested diagnostics, not a decomposition of the paired tax.
The known device-owned peaks are3,889,036,099B (S0/S1),3,889,036,339B (STALE),
and3,891,015,987B (INC), including the3.84GB raw representation.

For maintenance, duration-weighted SM counters describe only selected captured
kernels. Kernel DRAM does not include all DMA or flush cache-resident writes at
an end-to-end ACK boundary. Independent NCU kernel duration is never subtracted
from primary ACK latency to manufacture an unmeasured “CPU-only” remainder.
