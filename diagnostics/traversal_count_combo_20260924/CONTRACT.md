# Traversal-grid × dead count-stage screen

For the fused, batch-one path, `Fixed::enqueue` first CUB-reduces the flag
array into `candidate_count`, then launches `getQnodeCount` to reduce the same
flags again and scans its single-element output. The `nodecount/nodeprefix`
values are read only by the **unfused** result branch, never by the fused E/P
branch. The old count kernel lasts about 2.53 ms on all three million-point
traces, dominating Tloc after result fusion.

From the same pinned source and fixtures, compare E (original traversal,
count stage), R (original traversal, skip dead count and its one-item scan),
P (L2-specific multi-CTA traversal, count stage), and Q (both changes). All
arms retain the same result fusion, CUDA Graph, output copy, tree, radius,
arithmetic, pruning predicate and complete batch-one host-ready query scope.
E/R and P/Q isolate the dead count stage; E/P and R/Q isolate the traversal
change; E/Q is the observed combination. No speedups from different campaigns
are multiplied. Validate complete ordered float32 output against the original
and CPU oracle before timing. Run memcheck/synccheck on R/Q, then four fresh
paired rounds with both orders represented; trace kernel counts and selected
durations separately. No production source is changed.

Do not use an occupied GPU. Acquire its advisory lock, monitor for external
compute processes, and preserve any interrupted attempt. Profiling time is
diagnostic, never an end-to-end latency denominator.
