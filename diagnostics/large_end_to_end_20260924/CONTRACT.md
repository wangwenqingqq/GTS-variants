# Large L2 end-to-end improvement ledger

Registered before the new GPU runs on 2026-09-24. The question is the
incremental and cumulative completed-query benefit of existing GTS query
changes at N=65,536 and N=1,000,000 on GIST, Deep and Tloc. Use the identical
pinned fixtures, query IDs, radii and sm_120 executable from
`fusion_large_l2_20260924`; do not change CUDA source, loader, arithmetic,
capacity, tree, layout, traversal or output transfer. The binary float32
loader is before tree construction and excluded from every timed query.

| Mode | Result path | Submission | Improvement identified by the pair |
|---|---|---|---|
| A | Original native function | Native | Original-path reference |
| B | Fixed-capacity unfused | Stream | A/B includes workspace reuse and changed delivery |
| C | Same as B | CUDA Graph | B/C isolates Graph replay |
| D | Fused stable result selection | Stream | B/D isolates result fusion on stream |
| E | Same as D | CUDA Graph | C/E isolates result fusion under Graph; D/E isolates Graph with fusion |

A/B is an implementation package, not a pure single-kernel improvement:
the original native path allocates/frees per query and returns valid results,
while B reserves fixed capacity and copies the complete output slots. Do not
attribute A/B to Graph or result fusion. A/E is the observed cumulative
hot-query effect of this package plus Graph and fusion; it is not the product
of ratios from separate campaigns.

The previous C/E campaign on GPU 1 completed all 192 correctness, sanitizer,
stress, timing, sustained and NSYS runs and supplies CPU-validated exact
ordered output hashes. This new campaign starts from fresh run directories
but reuses only its byte-identical code/binary, immutable fixtures and gold
hashes. The previous timings are never pooled with new samples. Full B/D
normal-radius output is checked against the independent CPU float64 full
matrix and original A ordered float32 output at both sizes. At N=1M, B/D
also get zero/all/negative-radius full output. B/D memcheck and synccheck run
at every shape; D initcheck and racecheck run at N=1M. B/D get changing-query
stress. All later queries must match the CPU-validated original ordered hash.

For each of six dataset/size shapes, four independent process rounds use
orders ABCDE, EDCBA, CDEAB and BAEDC, with alternating dataset/size order.
At N=65,536 use 16 warmups plus 32 measured queries/process (eight IDs x4);
at N=1M use eight warmups plus eight measured queries/process. Two opposite
order sustained rounds double the measured queries. Report mode medians of
process means, within-round ratios A/B, B/C, B/D, C/E, D/E and A/E, wins/4,
and exact 4^4 paired log-ratio bootstrap intervals. No ratios or timing
processes are borrowed from the prior campaign. B/D NSYS traces cover two
fixed IDs, two warmups, one repeat and the first call (five executions);
profiling time is diagnostic, never a query-latency denominator.

The timed scope is one completed hot query: query input, GPU work, full output
delivery and CPU completion. Build, data load, tree construction, workspace
setup/Graph capture, first query, warmups and hashing are recorded separately.
All modes use the same GPU UUID and normal radius within a shape. CPU is
shared/unpinned, GPU clocks and settings unchanged. Admit a freshly idle RTX
PRO 6000 under its advisory lock; monitor every child process and stop owned
work on foreign activity. Preserve failed runs and do not replace samples.

Traversal fusion and pivot layout have only N=2,000 L2 experiments so far.
They are outside this frozen five-mode executable and get no fabricated
million-point gain in this ledger. Their large-scale extension requires a
separately validated dynamic-height implementation.
