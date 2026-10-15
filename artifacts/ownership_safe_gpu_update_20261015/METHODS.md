# Denominators and interpretation

## Data and workload

GIST1M has 1,000,000 rows x 960 FP32 coordinates=3,840,000,000 raw vector bytes(3.84GB decimal). Queries are B1 inclusive exact range queries,not kNN or approximate recall tests. The fixed32 query identities and radius are in CONTRACT.json. Incoming vectors are the inherited coordinate-rotated replacement payload,not an independent new real-world dataset.

Microbenchmarks perform 8,192 point deletions/insertions or 8,192 replacement pairs at B1/32/512,with 8 warmup queries and 32 final validation queries excluded from ACK timing. A replacement denominator includes both its delete and insert and the outer pair ACK;sub-ACKs must not be added again.

Full W2 performs 500,000 replacements(1,000,000 point updates),977 delete batches,977 insert batches and 160 formal queries,plus 8 excluded warmups. It has no repeated deletion of newly inserted occurrences. It is not a 100k-query campaign or a 1B-vector scalability result.

The service denominator is **events+release**,not just update/query kernels. Initial build,input loading and full-state verification/export are separately retained and excluded from that declared service denominator. No claim of cold-start time or fully inclusive process wall time is made. Every new variant includes validation,ownership bookkeeping,planning,audit append,submission and required stream wait inside ACK. New NATIVE measures the shared ledger overhead against the unchanged CURRENT parent binary.

## Controls and uncertainty

NATIVE,WAVES and FINAL use fresh frozen PLAIN/MARKED builds. S1 Progressive and CURRENT Frozen-PDX use immutable parent binaries remeasured on the same admitted GPU. Query SASS is identical for all three new variants and the parent Frozen-PDX. This does not imply identical cache state or zero query cost.

Every admitted target passed two-sided GPU process isolation on the same card and matched NUMA binding. CPU cores were not exclusively reserved;other host and other-GPU jobs could still affect shared Host resources. The retained process/order distributions characterize this campaign,not an exclusive-machine throughput limit.

The public estimator is the median of 6 independent process means. Process-paired geometric ratios and fixed-seed 20,000-resample bootstrap 95% intervals are separate;forward/reverse strata and all process values are retained. ACK p50/p95 are finite within-process quantiles,not service-level SLA estimates. Effect size,uncertainty and workload applicability are reported separately.

Individual update ACKs begin with a ready Host batch;client batch-vector construction and sample journaling are outside each I/D call. Those costs remain inside the full event interval;the replacement outer timer additionally includes its nested sample bookkeeping. Store-local witness/physical audit appends and all local destructor costs are inside primary call-return ACKs. No network-arrival or request-queueing SLA is measured.

MARKED calibration processes are matched by shape/variant/round to earlier PLAIN primary processes,but collected in a later phase rather than adjacent-time A/B. Their ratios can include phase drift and are not a pure causal estimate of NVTX overhead. Profiler/native comparisons likewise remain diagnostic;none changes the unprofiled primary estimator.

The dependency-shape study uses synthetic high-entropy bits,N4096,B512,D128/D960,2 warmups and32 timed intervals per dimension per process. Its frozen CSV column is named ACK_ms,but the interval ends immediately after execution and stream wait,**before local validation-set/BatchPlan destruction**. Setup,reset,full-capacity readback and those destructors are excluded. This is a synthetic submission+wait interval,not the complete Host-return ACK used by the main micro/W2 study;do not merge their ratios or promote a shape-only win to a service win. It tests arbitrary bit preservation and execution shapes,not search over NaNs or a complete dynamic GIST service. Native moves and FINAL compiled rows are different quantities;compiled_rows=0 in noncompiling paths means not compiled,not zero state change.

## Traffic and Host activity

Sequential reference bytes are immutable witness-derived logical quantities. Actual issued copy/launch/sync counts and kernel payload are separate physical-execution ledgers. A moved payload is counted once;do not confuse it with both DRAM read+write traffic.

Final row counts mean changed provenance assignments,not a data-dependent byte-difference/deduplication oracle. Equal-coordinate occurrences remain distinct,and the compiler does not inspect vector contents to omit identical-value writes. The delivered shared validator strengthens physical-ledger binding;the initial and continuation runtime validators are preserved separately and all recorded targets are rechecked offline against the independent mutation-derived execution model.

NSYS reports profiled API spans,overlaid DMA/kernel activity and sampled device activity. API spans can contain blocking/staging/backpressure;remaining Host spans can contain unobserved driver work. Neither is a pure CPU-compute measurement. CPU user/system seconds are process consumption,not a decomposition of GPU waiting.

NCU query counters cover selected progressive kernels;update counters cover only FINAL's materialization kernels,not H2D metadata or native copy-engine traffic. They do not establish total native-versus-FINAL update DRAM savings. The frozen CONTRACT.json phrase that no application update kernels were expected applies to NATIVE;FINAL explicitly introduces one. This clarification preserves the original contract file rather than rewriting it after measurement.

No concurrent-reader,CUDA Graph,cross-stream simultaneous update,multi-GPU or production admission is claimed. Unsupported batches>512 and invalid IDs remain fail-closed. All negatives and the initial CPU validator false alarm are retained;the approved continuation changes no GPU binary,query,timing scope or numerical gate.
