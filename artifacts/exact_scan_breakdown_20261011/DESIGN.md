# Diagnostic design, not a new scan implementation

Keep cuVS FP32 L2Unexpanded unchanged. FULL_OUTPUT calls the immutable Scan::range
unless independent diagnostic instrumentation is explicitly requested. The extra
persistent buffers are outside query timing and disclosed in setup; native keeper
processes remain a separate six-process denominator. No kernel is promoted.

READ_ONLY uses a coalesced float4 grid-stride pass (256 threads; SM count *8 CTAs),
a live FP32 accumulator, CUB BlockReduce, CUB aggregate and scalar D2H. Every
coordinate is consumed once. It is a reachable streaming control with reduction
cost, not an exact zero-arithmetic floor or identical cuVS instruction schedule.
DISTANCE_ONLY reuses cuVS and adds CUB score sum plus scalar D2H.
THRESHOLD_COUNT reuses cuVS and CUB transformed inclusive predicate sum. It avoids
IDs/fields, but reduction is not identical to keeper compaction. Signed A/B deltas
include replacement-control work; they are not additive exclusive cost buckets.

Ownership: every CTA owns one checksum partial; every thread owns its FP32 sum;
CUB owns reduction handoffs. One stream orders query upload, cuVS/reduction,
output transfers, and scalar/array ACK. Scratch has process/service lifetime.
No barrier protocol, arithmetic contract or production schedule is changed.
Read partials and sum survive until reduction and D2H; scratch is reused only after
stream completion. Tail shapes are multiples of four, rows1..1M, dimensions
128/256/512/960. Partial-block handling stays in CUB and native distance.

CUDA-event phases are collected only in diagnostic processes. Event spans can
include launch gaps and CPU-resize waits; NSYS kernel/copy interval unions own
active-time attribution. Runtime API waits overlap GPU execution and cannot be
summed with it. The requested stacked breakdown uses actual exclusive timeline
phases (distance read+arithmetic fused), not invented separate read/arithmetic bars.
FP32 native exact membership is validated against ordered-FP64 full scores, with
original native field tolerance5e-5*max(1, score); no membership tolerance/correction.
Checksum outputs are diagnostic aggregates (relative tolerance1e-4), not range IDs.

Novelty gate0: GPU brute-force distance is existing cuVS/Faiss functionality.
Roofline analysis and reduction/control ablations are established measurement
methods. This campaign makes no novelty or new mechanism claim. A future research
mechanism needs a new prior-art kill test, exactness proof and same-contract E2E gate.
