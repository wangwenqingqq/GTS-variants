# GTSPP: shorten CPU waits by fixing GPU result aggregation

**A bounded GTSPP range-query experiment achieves 3.24–4.51× complete-query
speedup without changing the CPU wait policy.** The dominant operator was
`mergeResRnn`, not leaf distance computation. Cooperative contiguous reads and
parallel reduction remove that bottleneck. This combines better coalescing with
more query parallelism; it does **not** isolate a pure coalescing speedup.

## Baseline and scope

A is the pinned `archive/GTS_incremental` implementation, not original upstream
GTS. Its node and leaf L2 paths **already use multiplication and `sqrtf`**; the
earlier upstream `pow` diagnosis is not a new GTSPP optimization. The archive's
learned kNN pruning is not exercised by this range-query workload. Direct
insertion remains outside this experiment and is not certified safe.

Both A and B retain the native dynamic tree height, padded leaf IDs, candidates,
distance math, result segments, allocations, launches and CPU synchronization.
Common harness adjustments bound the range workspace to 256 MiB instead of
4 GiB, suppress two debug prints, add stage clocks/NVTX, return CPU counts and
free the final build buffer at process cleanup. Thus A is a controlled GTSPP
baseline, **not an untouched historical executable**.

Hardware: RTX PRO 6000 Blackwell Server Edition, 188 SMs, physical GPU0;
driver 590.48.01, CUDA 13.1.115, GCC 13.3, NCU 2025.4.1, NSYS 2025.5.2.
The workload is SIFT, N=65,536, 128 dimensions, FP32 storage of integer
coordinates in [0,255], self-inclusive exact range counts, Q in {32,128} and
radius in {300,500}. Fixture/source hashes are retained in `EVIDENCE.json` and
`../cpu_io/SOURCE_PINS.json`. Smoke uses N=2,000/Q32/r300.

The denominator is **warm query dispatch through CPU count delivery**, including
allocation, initialization, every operator, waits, cleanup and delivery. It
excludes data loading, the independent oracle, index construction and warmup.
It is not full-program startup, kNN, update, arbitrary floating-point, result-ID,
multi-tenant or all-GPU-tree evidence.

## Clean paired measurements

Each shape has six fresh-process A/B pairs, alternating AB/BA (three each).
Each process performs one checked query, three checked warmups and eight retained
queries. Table times are medians of all 48 query observations per variant;
speedup is the paired geometric ratio of the six **process medians**, with a
seed-0 10,000-resample bootstrap 95% CI. These are distinct estimators.

| Q / radius | A query ms | B query ms | Paired A/B speedup [95% CI] | B wins |
|---|---:|---:|---:|---:|
| 32 / 300 | 11.244 | 2.498 | 4.463× [4.368, 4.556] | 6/6 |
| 32 / 500 | 12.180 | 2.681 | 4.505× [4.349, 4.651] | 6/6 |
| 128 / 300 | 19.875 | 6.150 | 3.245× [3.193, 3.303] | 6/6 |
| 128 / 500 | 30.271 | 6.946 | 4.308× [4.143, 4.444] | 6/6 |

The primary Q128/r500 aggregation stage falls from **22.145 to 0.167 ms**;
main-thread CPU time falls from **30.052 to 6.943 ms/query**. Leaf stage time is
essentially unchanged (4.756 to 4.735 ms). The main thread still consumes roughly
one core while running: the improvement is **less time spent waiting per query**,
not a new blocking-wait policy or evidence of removed CPU arithmetic.

Sustained batches contain 64 consecutive complete queries, with preallocated
CPU count-history copies **inside** the batch timer and all correctness checks
afterward. Three alternating pairs per endpoint give:

| Q / radius | A ms/query | B ms/query | Paired batch speedup [95% CI] |
|---|---:|---:|---:|
| 32 / 300 | 12.402 | 3.082 | 4.032× [3.906, 4.164] |
| 128 / 500 | 30.991 | 7.719 | 4.052× [3.981, 4.163] |

B wins all three pairs at each endpoint. This is a small bounded sustained
test, not a general service-throughput or production-admission result.

## Why CPU wait duration falls

Separate NSYS runs measure three post-warmup query ranges on Q128/r500. The mean
sum of `cudaDeviceSynchronize` API durations drops from **29.524 to 6.609 ms**;
aggregation kernel time drops from **22.094 to 0.155 ms**. These are
profiler-instrumented diagnostics, **not** the clean timing denominator above.
API durations overlap GPU work and must never be added to kernel duration.
Default CUDA scheduling bits remain zero in every receipt; no wait-policy
change or synchronization removal is credited as speedup.

## Operator mechanism and counter-evidence

The original reduction assigns one thread to a query and invokes device-side
sequential Thrust reduction over its result segment. With Q<=128 and a 512-thread
block, all queries occupy a single CTA. Adjacent active lanes process different
segments rather than adjacent integers of one segment.

B changes only the reduction body and its range-query launch grid:

1. One CTA owns each query; each of 512 threads sums stride-512 entries of the
   **same unchanged contiguous segment**.
2. Warp shuffles produce 16 partial sums, stored in 64 static shared bytes.
3. One CTA barrier precedes a warp-0 reduction; lane 0 writes the original result
   slot. All participating warps are full, and every thread reaches the barrier.

No tensor cores, repacking, new allocation, extra launch, changed metric or
changed output contract is involved. Generic cooperative reduction is established
practice; this is an engineering bottleneck fix, **not a novelty claim**.

NCU profiles the first measured aggregation launch of each final binary using
kernel replay, no clock control and no cache flushing. Diagnostic counters:

| Aggregation, Q128/r500 | A | B |
|---|---:|---:|
| Grid CTAs / threads per CTA | 1 / 512 | 128 / 512 |
| Global-load requests | 798,800 | 805,383 |
| Global-load 32-byte sectors | 25,443,651 | 3,538,479 |
| Useful bytes per global-load sector | 4.00 | 28.77 |
| Executed warp instructions | 1,997,552 | 4,964,598 |
| Registers / static shared bytes | 24 / 0 | 22 / 64 |
| Achieved occupancy | 8.33% | 33.27% |
| DRAM read bytes | 321,280 | 1,009,408 |
| DRAM write bytes | 434,688 | 735,232 |
| L1 global-read hit rate | 87.47% | 10.10% |

The sector count falls about **7.19×**, but DRAM bytes and total warp instructions
**increase** and L1 hit rate declines. Do not claim that all memory traffic fell,
that PCIe traffic fell, or that coalescing alone explains the end-to-end gain.
Changed query ownership, CTA distribution and parallel reduction are inseparable
in this A/B. Occupancy is not whole-device utilization. NCU replay durations and
stall ratios are mechanism diagnostics, not speedup denominators.

The selected node and leaf normalized SASS hashes are identical between A/B.
`EVIDENCE.json` retains full binary hashes, selected-function hashes/resources,
source pins, raw-file hashes and every run receipt summary. The reduction changes
from 24 to 22 registers; cuobjdump's B shared total is 1088 bytes, comprising
64 static plus 1024 driver shared bytes as distinguished by NCU.

## Gates, negative evidence and decision

The 96-process collection includes eight preflight runs, 20 final correctness /
sanitizer gates, four 64-query stress runs, 48 timing processes (384 observations),
four profiler processes and 12 sustained processes (768 queries). All receipts
pass the exact independent full-table integer count oracle and post-run GPU-idle
check. Memcheck and synccheck pass for both A/B on smoke and primary shapes;
B additionally passes smoke racecheck and initcheck. No sanitizer result is
treated as an end-to-end timing result.

The predeclared leaf optimization required >=20% primary baseline leaf cost.
Preflight found about 15.5% leaf versus 78% aggregation, so that candidate was
**not implemented**. `CONTRACT.md` records the aggregation amendment made before
candidate implementation. After fixing aggregation, leaf accounts for about
66–68% at Q128: leaf ownership/coalescing is a plausible **next test**, not a
measured additional gain here. Legacy insertion safety remains unresolved.

An initial invariant-test assertion mistakenly replaced the matching kNN grid
as well as the range grid in its comparison; the test was corrected to replace
once. The implementation was unchanged. Original NCU auto-scaled CSV exports
were retained and re-exported from the **same reports** with base units; the
analyzer accepts the observed `ns` alias. The first failed analysis directory is
retained privately. These are test/export fixes, not benchmark reruns or discarded
performance observations. Collection and final-delivery source hashes are separate.

**Decision:** keep B as a bounded warm count-only RNN prototype; do not promote
to the production tree, paper novelty or a universal GPU-tree claim. No existing
GTSPP source tree is overwritten.

## Reproduction and evidence

Use a fresh checkout, Python standard library, CUDA 13.1, Compute Sanitizer,
NCU/NSYS and the pinned SIFT base text. The code intentionally reuses sibling
diagnostic modules; copy the repository, not this directory alone. Set
`SCRATCH` to a new task-owned directory, `CUDA_HOME` to the real toolkit root,
`SIFT_BASE_TEXT` to the authorized data, and `ADMITTED_UUID` to an explicitly
allocated physical GPU0. Root NCU requires separate authorization; neither a
command argument nor membership in a group is permission to seize a device.

```sh
python3 diagnostics/gtspp_coalescing/test_prepare.py
python3 diagnostics/gtspp_coalescing/test_analysis.py
mkdir -p "$SCRATCH/bin" "$SCRATCH/logs" "$SCRATCH/fixtures"
python3 diagnostics/tc_leaf_probe/prepare.py fixture "$SIFT_BASE_TEXT" "$SCRATCH/fixtures/n2000" --n 2000
python3 diagnostics/tc_leaf_probe/prepare.py fixture "$SIFT_BASE_TEXT" "$SCRATCH/fixtures/n65536" --n 65536
for v in A B; do
  python3 diagnostics/gtspp_coalescing/prepare.py "$SCRATCH/final$v" --variant "$v"
  "$CUDA_HOME/bin/nvcc" -std=c++17 -O3 -arch=sm_120 -rdc=true -lineinfo \
    -DGTS_DIAG_NVTX -Xptxas=-v -Xnvlink=--ignore-host-info \
    -I"$SCRATCH/final$v/include" "$SCRATCH/final$v/src/main.cu" \
    -ldl -o "$SCRATCH/bin/$v" > "$SCRATCH/logs/build$v.log" 2>&1
done
for stage in gates stress timing profile sustained; do
  python3 diagnostics/gtspp_coalescing/run.py "$SCRATCH" --gpu "$ADMITTED_UUID" --stage "$stage"
done
```

These commands reproduce the final A/B experiment, not the historical preflight.
`run.py` retains commands, source-independent binary hashes, flags, correctness,
pre/post GPU snapshots, stdout/stderr and profiler reports. Existing output
directories are never overwritten. The runner uses GPU0's advisory lock and
fails closed on busy-device admission, bad fixture hashes, errors or contamination.
Review the configured tool paths for another installation; do not change driver
profiling settings to bypass authorization.

`samples.csv`, `stages.csv`, `ncu_metrics.csv` and `instruction_ledger.csv` are
portable numerical exports. To regenerate this collection's exact curated
outputs, use the original private `runs`, `logs/provenance.json`, binaries and
fixtures in their recorded directory layout:

```sh
python3 diagnostics/gtspp_coalescing/analyze.py "$ORIGINAL_COLLECTION" "$NEW_EXPORT"
```

The private raw receipt/log archive SHA256 is
`e4f0644c1cd15370649d009c3c068967f6edb9d7d87189c76e4912894e5a3543`.
It is not a public download and excludes binaries, fixtures and profiler HOME
caches. Original data, private paths, process snapshots, raw SASS and tool
reports are not uploaded. Publication includes only authored overlays and curated
metrics/hashes; source licensing and data access are not expanded by this report.
