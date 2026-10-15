# Frozen attribution study

**Checkpoint status: R1 stopped; native-path attribution is not admitted.**
The original R1 contract is retained verbatim in `provenance/CONTRACT_R1.json`.
The intended scope below is not a claim that R1 achieved it. Its annotation
braces shortened the delete validation-set lifetime, moving destruction before
copy submission. Both PLAIN and MARKED were affected. Passed output checks do
not repair that Host critical-path deviation. No R1 timing is promoted here.
The current source fixes the scope and strengthens offline checks; a fresh
recovery registration and GPU qualification are still pending authorization.

Question: where does the unchanged serial exact-search update ACK spend time,
and what amortizes with batch size? No tree/index/order/statistics/async
optimization is introduced. The original frozen-PDX and S1 full-W2 binaries are
remeasured in this campaign. The previous73-file artifact remains immutable.

## Operator experiment

GIST1M/D960 FP32,32 fixed inherited queries and original range authority.
Micro I/D/R use the same first8192 inherited W2 victims/payloads, batch1/32/512.
I prepares room by untimed deleting8192 rows in512-row chunks; D starts with1M
live rows and ends with991808; R ends each pair with1M. Logical incoming IDs are
fresh occurrences. Equal final logical contents need not have equal physical
row order across batch sizes. No growth beyond the allocated1M capacity.

Eight exact warmups follow the respective operator preparation. Micro ACKs
exclude client request preparation, build, query validation, final state export
and release. Every formal update includes all native checks, ownership changes,
mutation-witness appends, copy submission and stream synchronization. R has a
true pair ACK and nested per-kind ACKs; they are never double-counted. A fixed
K means large-batch p95 has only16 samples/process: descriptive,not an SLA.
The unchanged full-W2 service supplies the real mixed-flow anchor, not a
claim that this microtrace is the old formal100k or10k-query benchmark.

## Attribution, not fabricated decomposition

PLAIN and MARKED differ only by compile-time optional NVTX scopes; there are
no per-row annotations. Six matched no-profiler comparisons at R/B1 and B512
bound marker perturbation. Primary latencies never come from NSYS. Profiling
reports its own ACK slowdown relative to unprofiled values without replacing
any sample. CPU submission and waits overlap DMA/device execution: show them
as separate tracks, not an additive100% GPU+CPU pie.

In the fixed source, validation ends before copy submission but the validation
set remains alive until after synchronization. Its destruction belongs to
operator-level Other Host time, not the `DELETE_VALIDATE` interval. Removing
annotation tokens recovers the exact parent delete body. This source proof and
the CPU lifetime test do not substitute for new GPU qualification or timing.

Current frozen update code explicitly launches no application kernels. This
is a source expectation to verify, not proof of an idle GPU: copy engines and
possibly driver-internal work still matter. Nsight Systems captures actual
transfer activities, Host API intervals and single-GPU sampled copy/SM/warp/
DRAM-interface activity. The installed gb20x set has DRAM active-interface
percentages, not exact byte counts or L2 byte metrics. Those unavailable byte
fields will be N/A, never synthesized from requests or kernel count. Measured
DMA bytes/durations, requested bytes and sampled physical activity are separate.
The bulk contiguous copy reference is a standard isolated control,not a legal
batched deletion implementation or same-contract search-system speedup.

## Gates and limits

124 starts maximum:29 qualification,84 primary,11 independent NSYS. No retries.
Qualification covers both instrument modes under boundary/pointer churn and
memcheck/racecheck/synccheck,all9 bounded and full microcells plus3 marked
full operator cells. Every nonselftest keeps complete native membership/fields,
actual transition witnesses, final bijection and every final device-vector
byte proof outside timing. Internal ordered-FP64 hit scores are checked in
qualification. Selected search SASS must match the immutable parent.

Source/input/binary identity, idle admission/two-sided ownership and a single
campaign lock precede every process. No foreign process is signaled or settings
changed. Only task-owned scratch is written. All figures/claims disclose
finite windows,serial visibility and profiling perturbation. There is no
production/concurrency/Graph/novelty admission or manuscript edit.
