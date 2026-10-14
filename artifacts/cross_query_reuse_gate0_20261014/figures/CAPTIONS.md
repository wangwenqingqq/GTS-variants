# Figure messages and denominators

1. **Natural mean batch stays below four at every specified rate.** Synthetic
   window-or-cap admission,500us/Bmax8; one independent100k-query trace/rate.
   Mean is batch-weighted; the horizontal line is a gate, not an observed sample.
2. **Collection delay consumes the budget without proving a service SLA.** Mean
   and query-weighted p90 intentional wait from the same traces. p90 and p99
   equal0.50ms at all four points. Device backlog, execution and host output are
   absent; no total tail-latency claim is implied.
3. **Even optimistic shared-source bytes miss the frozen range reference.**
   Primary is3.84GB*batch_count/query_count; secondary is batch-average3.84/B.
   Reference1.014828776GB is the earlier32-range-query source model, not a
   matched mixed/kNN baseline. GO line0.75GB is an admission target. No plot
   measures DRAM or predicts GPU latency; query/output/control extras are unknown.

No repeated traces or uncertainty estimates are shown; none were invented.
PDF/SVG are vector exports, PNGs400dpi. Each figure has a companion exact CSV.
