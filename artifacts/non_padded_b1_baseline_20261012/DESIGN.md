# Minimal B1 baseline diagnostic

One warp owns one real database row. Thirty lane-strided iterations cover D960;
each coordinate uses FP32 subtraction and FMA. Five warp shuffle/add stages
produce one squared score. A warp-uniform row guard removes tail rows; no dummy
query row is evaluated. CTA=256 threads, eight independent row-owning warps;
grid=ceil(N/8). No shared memory, barriers, compression, approximate precision,
expanded-L2, Tensor Core or cross-query reuse. No candidate tuning matrix.

Every lane owns one persistent FP32 sum and transient coordinate/difference.
Lane zero owns the output store. There is no producer/consumer scratch handoff.
The existing stream orders query H2D -> direct distance -> inclusive flags ->
CUB stable compaction -> FP32 sqrt fields/FP64 cast observer -> complete D2H ->
ACK. All workspace remains process-persistent and unchanged from the original
Scan adapter. No overlap or extra allocation is hidden outside the query timer.

Private build generation adds one include and replaces the one distance API
call in the original Scan::range. The entire threshold/materialization/transfer
body is preserved. The original batch driver is reused byte-for-byte except
its include target and a pre-workload --fixtures entry. Its B1 invocation calls
Scan::range, exactly as the comparator does. Build/source diffs are retained.

The expected core work is 960 FADD differences +960 FFMA per object, plus up to
160 lane-wise warp-reduction adds. Initial-zero contraction may lower FFMA and
add FMUL; inspect actual SASS/counters. This is approximately 1.06 executed/useful,
not promised to be exactly one. Logical dataset reads remain 3.84GB/query;
query cache behavior and physical traffic require measurement. No bytes saved
by compression/pruning. A source/resource proof is not a latency win.

The FP32 sum reduction order differs from native tile accumulation. The original
declared field tolerance (5e-5 on squared-score scale) permits that order but
does not permit membership discrepancies. Ordered FP64 remains the complete
membership oracle. Native payload bit identity stays enforced; candidate bit
differences are disclosed rather than erased.

Scope: original GIST initial-snapshot range B1 only. Fixtures cover empty sets,
duplicate vector occurrences, exact/adjacent boundaries, ragged rows, two stream
slots and pointer churn for 100 iterations. They do not imply Graph, all-shape,
full-N sanitizer or dynamic-workflow qualification. READ_ONLY is the unchanged
checksum streaming control with reduction work, not a replacement search path.
