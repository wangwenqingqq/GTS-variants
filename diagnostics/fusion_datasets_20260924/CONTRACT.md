# Result-fusion effect across four pinned datasets

Registered 2026-09-24 before this campaign's compilation or GPU execution.
Question: does the Words N=2000 result-fusion benefit persist across data
modalities and dimensions? This is a within-dataset C/E comparison, not a claim
that absolute latency or the radii are comparable across datasets.

## Fixed arms and inputs

N=2000, immutable tree, batch one, radius inclusive. Words byte edit distance,
GIST 960D / Deep 96D / Tloc 2D float32 L2. Reuse the exact Words 64-query
fixture and the independently CPU-oracled 64-query GIST/Deep/Tloc fixtures from
the earlier traversal/layout work. Use each L2 fixture's recorded normal,
zero, all-hit, negative radii. Words uses 4, 0, 256, -1. No new query tuning or
data sampling. Hash inputs and original author source.

C: original unfused result pipeline + CUDA Graph. E: same pipeline with the
published fusedResultSelect (one CTA, 512 threads, sequential tiles) + Graph.
Same binary, original traversal/native pivot layout, same tree, 111 nodes,
2220 slots, memory allocation and fixed-size host copies. Keep the already
unused intermediates allocated in E. Only extend the old fixed-2000 driver
shape assertion to the three L2 dimensions/metric; use 9-digit output text
for full float32 audits. No traversal fusion, new layout or retuning.
Native A is an output reference only. Preserve the previous Words binary as
a same-session C/E timing and output bridge; do not mix it into the dataset
comparison. The same 2000-capacity selector and source are used across arms.

## Gates, measurement and boundaries

Before timing: independent CPU oracle full-output membership, distance,
count and native-ordered float32-bit checks for A/C/E at normal/zero/all,
C/E at negative; old Words C/E at normal. Any native A negative-radius failure
is outside this control. Verify complete ordered result hashes for every later
query. C/E memcheck and synccheck on all four; E initcheck/racecheck on all four.
Stress C/E with 256 changing queries and 64 warmups per dataset.

Six fresh paired rounds, C/E order alternating; dataset order forward/reverse
alternating. Words old-binary C/E bridge immediately follows its new-binary
pair each round. Warmup 64. Timed queries/process: Words and Tloc 4096,
GIST and Deep 512. Summary median process-mean completed hot-query latency,
C/E ratio; exact 6^6 paired log-ratio bootstrap 95% interval and wins/6.
Record all samples, setup, capture and first-query costs. Two longer C/E
pairs in opposite order use twice those query counts per dataset.

NSYS C/E per dataset: 8 query IDs, 8 warmups, one repeat plus first call;
verify actual kernel signatures/counts and unchanged common path. Profiled
kernel timings are diagnostic only. Report losses as well as wins and the
fraction of C time consumed by the old count kernel only as a diagnostic,
without adding profiler times to hot-query wall times.

Target one freshly admitted idle RTX PRO 6000 / sm_120, CUDA 13.1.115; hold
the existing GPU advisory lock, monitor before/through/after, stop only owned
work on foreign activity. No hardware setting changes. CPU shared/unpinned;
clocks uncontrolled. Save all raw inputs, binaries, logs and profiler data
locally. Timer includes input, computation, complete host delivery and
synchronization, excluding build, load/tree, setup/capture, warmup and hashing.
No production or 1M-point claim, and no absolute comparison of L2 and edit
distance query difficulty.
