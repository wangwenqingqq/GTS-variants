# Figure messages and visual QA

## A — Frozen ordering retains its query advantage under this stress

All four systems use the same five W2 mutation windows. Each point is the
median of six independent process means over32 formal requests; bars are
process p10–p90, not population or request-tail confidence intervals. PDX stale
and delta nearly coincide. Absolute latency alone is not proof that drift is
harmless: compare same-window S1 and the changing exact hit population.

## B — Frozen physical traffic weakens slightly, without collapsing

All captured query kernels are charged. Frozen PDX DRAM rises from0.780090 to
0.785922GB/query, while its reduction versus S1 narrows from30.30% to26.53%.
The32-query window means come from one independent NCU process/system/workload;
no process CI or DMA traffic is implied. Close/overlapping curves are retained,
not artificially separated. Full normalized read/write/L2 and kernel families
are available beside the figure's CSV.

## C — Eager update tax grows without a corresponding query advantage

Three points show different workloads, not a measured policy Pareto frontier.
The horizontal axis is INC−STALE matched update-tax median, normalized by160
queries, **log scale**; error bars are matched-process bootstrap95% intervals.
The vertical axis uses the separate paired-geometric INC/S1 query ratio and
its95% interval. W2 batching differs from W0/W1; no line or optimal refresh
frequency is fitted. W0/W1 are deliberately not jittered to separate them.

## D — W2 service is dominated by update ACKs

Stacks use arithmetic means of six processes so query, update-including-stats,
and other-plus-release add to total service. Total bars use process SD. Panels
have independently labeled y-axis scales. Maintenance outside updates iszero;
there is no extra stack that double-counts nested statistics. This is the
segmented events+release scope, not process startup/wall time.

## Acceptance

All four PDF pages were independently rendered at400DPI and visually inspected
alongside the generated PNGs. Labels, legends, edges, hatches, error bars and
panel spacing were checked without cropping scientific content. FigureC was
changed from linear to log x solely to reveal three orders of observed tax;
the before/after numeric CSVs are byte-identical. The first drafts remain
privately retained. PDF/SVG are vector, PNG is400DPI, minimum requested font7pt;
no PDF Type3 font declaration was found. Blue plus distinct markers/linestyles,
and gray hatches in the composition, retain non-color encodings. The separately
installed style helper is an external rendering dependency, not vendored code.
