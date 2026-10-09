# CPU tree / strong-scan diagnostic results

**All six native processes and all 384 complete query-quality checks passed.**
On these two N1M/D960 snapshots, native single-thread CPU Flat has lower query
latency and construction time than the fixed-leaf KDTree/BallTree diagnostics.
This keeps strong scan controls in the evaluation; it does not establish a
six-round ranking, multi-core throughput or a GTSPP dynamic-workflow speedup.

## Actual single-process measurements

Every row is one fresh process, eight warmup queries per task, then 32 B1 kNN
and 32 B1 complete range queries. Query-pass clocks include coordinate copying,
native calls, field conversion and retention of all Host-ready arrays. The mean
is continuous pass/32, **not a median or p99**. Serialization to files happens
after delivery timing; final resource release is separately recorded. Native
API sums, operation ACK samples, warmup, final release, CPU user/system usage,
array/index bytes and original receipt hashes are in `evidence/CPU_RESULTS.json`.

| Snapshot | Method | Representation/library prep s | Build s | 32 kNN pass s | Mean kNN ms | 32 range pass s | Mean range ms | Process VmHWM GiB | Quality |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| initial | CPU_KD | 2.076 | 173.481 | 36.658 | 1145.574 | 37.699 | 1178.079 | 10.973 | 64/64 |
| initial | CPU_BALL | 1.863 | 117.662 | 34.150 | 1067.192 | 32.582 | 1018.175 | 10.913 | 64/64 |
| initial | CPU_FLAT | 0.092 | 2.110 | 10.209 | 319.037 | 10.205 | 318.910 | 7.350 | 64/64 |
| first_rebuilt | CPU_KD | 1.848 | 172.660 | 36.312 | 1134.734 | 36.738 | 1148.056 | 10.972 | 64/64 |
| first_rebuilt | CPU_BALL | 1.850 | 116.142 | 33.721 | 1053.767 | 33.026 | 1032.054 | 10.913 | 64/64 |
| first_rebuilt | CPU_FLAT | 0.093 | 2.083 | 10.232 | 319.759 | 10.199 | 318.727 | 7.350 | 64/64 |

Inputs: original FP32 GIST, N=1,000,000, D=960, K=8, B=1, radius FP32 bits
`0x3f34a3d8`. Both snapshots contain one million occurrence rows, not merely
one million distinct vectors; the rebuilt snapshot retains ten repeated
occurrences. Each method uses the same registered coordinates within a snapshot.
No test-query parameter search was performed: sklearn leaf_size=128 is a fixed
diagnostic setting, not the final development-selected baseline configuration.

Libraries: scikit-learn 1.6.1/NumPy 1.26.4; Faiss 1.15.1/NumPy 2.5.2. CPU Flat
calls `omp_set_num_threads(1)`; sklearn's recorded BLAS/OpenMP threadpools all
report one thread. No auto algorithm, hidden batches, GPU resource construction
or new installation is used. Native CPU timings were completed before the
independent eight-thread validation began. All six processes exited0; total
process wall time is a guard/provenance value, not query latency.

### Representation, memory and cold-start boundary

KD/Ball promote the original FP32 coordinates exactly to a contiguous FP64
array: 7,680,000,000 representation bytes, in addition to the original
3,840,000,000 mapped input bytes. Native tree auxiliary arrays are reported
separately. CPU Flat keeps FP32 coordinates and copies 3,840,000,000 bytes into
its index. `index_bytes` is derived retained-array storage, not all allocator or
library state. VmHWM is the **whole process high-water mark**, including input
qualification and preparation; RSS is sampled before/after build and at final
release. It is not an exact construction-only allocator peak.

Source hashing/header/finite checks precede representation/build clocks. Library
import and the FP64 conversion are included in preparation; build excludes that
preparation and warmup. These are native-index diagnostic boundaries, not full
cold application wall time. Final release and raw output serialization must not
be silently omitted from a future system-wide service boundary.

## Complete membership and numerical quality

The qualified independent ordered-FP64 exhaustive row oracle scores all N rows
for every one of the 32 registered coordinates and reuses those scores only to
validate the same-coordinate kNN and range outputs. No pruned/GPU reference,
finite top-K range surrogate or unregistered query subset is used. Exact range
occurrence sets, invalid/repeated IDs, finite fields, legitimate exact-distance
kNN boundary ties and frozen scale-1 squared-field tolerance5e-5 are checked
separately. Tree native fields are Euclidean FP64 values; their squares are
reported, not falsely called an exposed native squared-score API.

`qualify_cpu.py` first verifies all six original successful receipts, complete
payload sizes/hashes, executed source, registered data/snapshot/coordinate and
contract bindings. The later analyst is distinct from the original executor.
`cpu.py` is unchanged; the delivered `cpu_jobs.py` only adds a portable
pre-registration helper absent from the originally executed launcher. Both
launcher hashes and that difference are retained in the evidence. Faiss's
extension hash was verified in a live post-run inventory and matches the
previous frozen environment; it is **not** retroactively claimed captured by
the original CPU receipt (which captured its Python binding hash).

## GPU and dynamic context: retained, not pooled

The earlier phase-B two-snapshot GPU Flat B1K8 results and their complete/tolerant
quality remain in [the original static evidence](../unified_target_workflow/phase_b/evidence/STATIC_RESULTS.json).
Native GPU Flat's32-query pass was138.114/138.166ms and its pass+release was
170.908/171.145ms. Those are **historical single diagnostics**, not fresh rounds
paired with this CPU campaign. The old integrated FULL/BOUND/control timings
remain at their original service boundaries; no CPU/GPU end-to-end factor is
manufactured by dividing different preparation/release scopes.

The original18-process A/B/C phase-B evidence is unchanged. New NSYS durations
are diagnostic attribution, not extra primary observations. CPU_MVPT and
GPU_TREE concrete source/ownership/output blockers are in `BASELINES.md`.
Neither missing rows nor native precision differences remove strong competitors
from the record. Static rows are not admitted into the336-event insert/delete
workflow without the required native/adapter semantics and logical-ID replay.

## Next gates, not yet executed

1. Submission B: one same-semantics build-distance tiling candidate; per-layer
   complete keys/pids/sort/topology and bounded/one-million rebuild quality,
   changed-kernel sanitizer gates before timing.
2. Submission C internal: only after B admission, six direction-balanced B0/B1
   pairs on the existing336-event complete workflow; retain all observations.
3. External formal: freeze leaf development on separate queries, qualify the
   GPU tree/complete-range adapters or retain explicit blockers, then register
   exact budgets and balanced six-process rounds. Multi-core CPU throughput is
   a separate configuration, not inferred from these single-thread rows.
4. Long-workflow/leak/output-consumption/novelty gates remain independent. No
   automatic42-process campaign or new research-contribution admission follows.
