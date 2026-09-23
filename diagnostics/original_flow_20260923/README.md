# Original GTS: CPU, device memory, and intermittent GPU work

Date: 2026-09-23. **NSYS completed; NCU hardware-counter collection was attempted
but denied. No optimization or source repair was applied.**

## Conclusion

The query-only update entry keeps about **one CPU core busy while issuing many
small GPU operations**. In the lighter NSYS recording, GPU kernel/copy/memset
activity covers **26.0%** of its query-kernel span; **87.8% of kernel launches have
only one thread block** on a 188-SM GPU. This is direct evidence of temporal gaps
and small dispatches in this particular path, not a hardware-counter measurement
of achieved SM throughput.

The broader hypothesis needs qualification: device memory was **not just a few
MiB** (about 13.26 GiB sampled), and batched kNN behaved differently (70.4% traced
GPU-work coverage). Low memory-capacity occupancy is not itself inefficiency.
The untouched static range path failed its native workspace allocation before
producing results; it is not a valid performance observation.

**Material limit:** Words N=2,000 and 4,096 queries, formed by repeating 32 checked
IDs 128 times. This fits the untouched source's MAX_H=3 / leaf-capacity=20 contract.
It is not a full-dataset result or a statement about all GPU trees. The user's
original problematic launch command was not supplied. Query-only update is not
insertion/deletion throughput. Valid results are counts/kth distances, not full IDs.

## Provenance and execution

- Author source: `ZJU-DAILY/GTS`, commit
  `3bac1b725e92e98e3b69d5cb79ad9c56ccb5e639`; all eight GTS CUDA files matched
  the pinned originals before copying and remained unchanged afterward.
- Fresh binary: SHA-256
  `0e55ca2ec490644913759e6d864ea077e048adfa2f7352feb26feed73da03293`.
- RTX PRO 6000 Blackwell Server Edition, physical GPU 0, 188 SMs; driver
  590.48.01, CUDA 13.1.115, GCC 13.3; NSYS 2025.5.2 and NCU 2025.4.1.
- Byte-identical source, native memory policy/height, default CUDA waits. Only
  build flags and external tracing/sampling were used. This is not the paper's
  historical binary/toolchain and not yesterday's workspace-capped executable.
- Nonblocking GPU lock and live process checks; no foreign process, clock,
  driver setting, or profiling permission changed. GPU returned to 14 MiB,
  0% utilization and no compute processes at closure.
- Contract: [CONTRACT.md](CONTRACT.md). Numeric results, all receipts and hashes:
  [EVIDENCE.json](EVIDENCE.json). Raw data/source copies/logs remain excluded.

## 1. Clean runs: high CPU means one core, not the whole host

Three fresh unprofiled processes per valid path. Wall time is observed externally;
CPU time comes from `wait4` for the application and excludes monitor processes.
The external wall denominator has up to one 100-ms polling interval plus admission
check latency. Query totals below are native per-query printed timings multiplied
by 4,096; their six-decimal print precision limits accuracy, especially for kNN.

| Path, N=2,000 / Q=4,096 | Process wall samples (s) | CPU samples, one-core denominator | Native query totals (s, rounded) |
|---|---|---|---|
| Query-only update entry | 2.836 / 2.845 / 2.840 | 92.1% / 92.1% / 93.3% | 2.318 / 2.367 / 2.392 |
| One batched kNN | 0.505 / 0.506 / 0.506 | 89.5% / 85.9% / 83.5% | 0.020 / 0.020 / 0.016 |

The update path remains CPU-active beyond startup. For kNN, useful query time is
only a small fraction of its fresh-process lifecycle; its high whole-process CPU
percentage must not be called high steady-query CPU computation. CUDA/context
initialization, loading, construction and cleanup are included in that denominator.
CPU sampling via perf is unavailable under existing permissions. This campaign
does not provide a CPU arithmetic/wait flame graph; the adjacent September 22
wait-policy control is separate evidence, not an intervention performed here.

Coarse 100-ms management samples for the three update runs show GPU utilization
medians **36% / 36% / 35%**, with maxima **41% / 39% / 38%**. We did not reproduce
repeated whole-GPU 100% spikes. kNN's roughly 10-20-ms query is too short for such
samples: one run sampled 0% throughout despite a completed, correct GPU query.
Management utilization, temporal activity, and SM throughput are different metrics.

## 2. NSYS: gaps and small grids are both present

Two recordings per valid path: full UVM-fault/allocation tracking and a lighter
recording with those two expensive features disabled. All outputs were checked.
Profiler process/export time is excluded from the query-kernel spans below.
The spans run from first query kernel start to last query kernel end, excluding
initial query setup and final cleanup; they are not exact whole-query timers.

| Path / lighter trace | Span (ms) | Union of GPU work (ms) | GPU-work coverage | No recorded GPU work (ms) |
|---|---:|---:|---:|---:|
| Query-only update entry | 2,831.623 | 735.204 | **25.96%** | 2,096.418 |
| Batched kNN | 9.644 | 6.789 | **70.40%** | 2.855 |

Union includes kernels, copies and memsets without double-counting overlap.
The complementary gap is **not pure CPU arithmetic**: it can contain host
control, CUDA runtime/driver overhead, memory-fault handling and tracing effects.
The heavier trace changes update coverage to 17.84% and kNN coverage to 57.85%,
showing why profiler percentages must not be presented as unprofiled throughput.
Even the lighter recording adds overhead; no exact clean GPU-duty fraction is claimed.

### Query-only update entry: a large number of small launches

- 98,304 query-kernel executions for 4,096 queries: **24 per query**.
- 86,272 executions (**87.76%**) have grid size one block.
- Those one-block kernels consume **75.01% of traced kernel time**.
- `findNextRnn`, `getQnodeCount`, and `getQresultCount` use one block of 512
  threads. One block can occupy at most one of the 188 SMs at a time; that is a
  launch-geometry bound, **not an NCU achieved-occupancy measurement**. In the
  result counter, a single query leaves most block threads without an output to own.
- The lighter query span includes 49,151 device synchronizations, 36,864 stream
  synchronizations, about 98,000 allocation calls and 98,298 frees. Counts exclude
  operations outside the declared kernel-to-kernel window.
- Allocation/free API intervals sum to approximately 734.38 ms in that trace.
  They can overlap GPU execution; do not add them to kernel durations or equate
  them with useful CPU computation. Kernel launches add about 377.49 ms of API
  intervals, and device synchronizations about 891.36 ms, also overlapping.

### Batched kNN is a counterexample to a universal small-grid claim

There are only 27 query kernels. `dataProcessKnn` launches 409,600 blocks, while
radix-sort kernels launch 1,778 blocks each. Only 2.06% of kernel time is spent
in one-block launches. kNN still has timeline gaps, but its main distance kernel
is not suffering from the same one-block dispatch geometry. NCU is needed to
quantify achieved occupancy, active lanes, stalls, and compute/DRAM throughput.

## 3. Device memory: small logical working set is not small total footprint

| Measurement | Query-only update entry | Batched kNN |
|---|---:|---:|
| Maximum sampled device used memory, clean runs | 13,576 MiB (13.26 GiB) | 13,444-13,576 MiB; brief peaks can be missed |
| Peak simultaneously live explicit device/managed allocation bytes, full NSYS | 541,539 B (0.516 MiB) | 9,629,296,303 B (8.968 GiB) |
| Largest explicit allocation | 222,000 B | **9,496,100,864 B (8.844 GiB)** |

The device capacity reported by management sampling is 97,887 MiB. The update
sample is about 13.9% of capacity, but this is not a bandwidth or SM utilization
metric. NSYS explicit-allocation totals exclude context/driver allocations and
compiler-managed thread-stack backing. They cannot replace a total-memory gauge.
Conversely, 100-ms management sampling can miss kNN's very short workspace peak.

The compiled distance kernels report **47,528 bytes of stack per thread** in
`cuobjdump --dump-resource-usage`, including `getPivotDis`, `findNextRnn`,
`leafProcessRnnUpdate` and `dataProcessKnn`. The source has per-thread edit-distance
DP tables. This is a plausible contributor to the large non-explicit footprint,
but this campaign did not isolate all context/stack allocations causally.
NSYS kernel local-memory fields reported zero; do not treat that as proof of
zero stack memory when the compiler resource record reports a nonzero stack.

In the full update trace, explicit D2H transfers total only 32 KiB; recorded UVM
transfers total about 16.7 MiB in both directions. Small copy payloads do not
exclude page-fault/control overhead. They do not support a bulk PCIe-bandwidth
bottleneck here. See EVIDENCE.json for counts, transfer duration and UVM events.

## 4. Failed gates and missing measurements

- **Static range:** both clean and NSYS attempts fail `cudaMalloc` at
  `search_v2.cuh:805` before returning any query result. The original converts
  half the free device memory to a signed 32-bit element count (`size_a`). Its
  capacity-dependent narrowing is a source-established portability hazard on
  this device. The exact failed allocation argument was not intercepted, so
  the narrowing diagnosis is an inference, not an observed argument value.
  No workspace cap or source fix was substituted into this original-only campaign.
- **NCU:** the targeted SpeedOfLight/LaunchStats/Occupancy/SchedulerStats/
  WarpStateStats run returns `ERR_NVGPUCTRPERM`. A LaunchStats-only attempt is
  also denied. There is **no successful NCU report, achieved occupancy, SM/DRAM
  throughput, or stall-counter result**. No elevation or driver change attempted.
- **Sanitizers:** kNN and query-only update pass memcheck and synccheck at both
  32 and all 4,096 queries. Every retained clean/full/light observation matches
  the native oracle. No insertion/deletion, full-ID, full-dataset or long-running
  concurrent-service certification is implied.
- **Preserved interrupted runs:** one sanitizer and one full trace were
  conservatively stopped by incomplete profiler-child tracking. They are not
  accepted measurements. Tracking was corrected, both were rerun, and all
  stopped receipts/reports are retained. Only owned process groups were signaled.
- Native update summary prints infinity for averages over zero actual update
  operations. Those fields are excluded; query timing/counts are retained.

## 5. Claim-evidence decision

| Claim | Status | Allowed conclusion |
|---|---|---|
| Original GTS consumes high CPU | measured, path/scope-qualified | About one CPU core in this lifecycle; not whole-host saturation or proof of expensive CPU distance arithmetic |
| It uses almost no device memory | rejected in this absolute form | Small explicit update workspace coexists with a roughly 13-GiB sampled device footprint; kNN reserves a large workspace |
| GPU work is intermittent | measured in NSYS, overhead-qualified | Gaps remain in the lighter trace; management sampling did not show repeated 100% spikes |
| The query-only update path has insufficient launch parallelism | measured launch geometry | Most launches have one block; hardware achieved-utilization percentages remain unknown |
| All original GTS paths share that bottleneck | rejected for this workload | Batched kNN launches large grids and has substantially greater temporal GPU coverage |

Next steps: repeat the user's actual dataset/command; obtain an administrator-
approved NCU collection under the same frozen contract; isolate dispatch/working-
set reuse separately from aggregation. Preserve the untouched baseline. Do not
turn small-N, one-query dispatch behavior into a universal GPU-tree limitation.

## 6. Reproduce without editing originals

The author source root contains `GTS/` and `GPU-Tree/`. Obtain the real Words file
separately; data are not redistributed. Use fresh, distinct fixture and run roots.

```sh
python3 diagnostics/original_tree_profile/make_fixture.py "$WORDS" "$FIXTURES" --sizes 2000
python3 diagnostics/original_flow_20260923/prepare.py "$AUTHOR_SOURCE_ROOT" "$FIXTURES" "$SCRATCH"
"$CUDA_HOME/bin/nvcc" -std=c++17 -O2 -arch=sm_120 -rdc=true -lineinfo \
  -Xcompiler=-fno-omit-frame-pointer -Xnvlink=--ignore-host-info \
  -I"$SCRATCH/source/include" "$SCRATCH/source/src/main.cu" -o "$SCRATCH/bin/gts_original"
# Run only after explicit GPU admission. Use a fresh label for every observation.
python3 diagnostics/original_flow_20260923/run.py "$SCRATCH" --gpu "$ADMITTED_UUID" --label smoke_update --kind update --mode clean
python3 diagnostics/original_flow_20260923/run.py "$SCRATCH" --gpu "$ADMITTED_UUID" --label memcheck_update --kind update --mode memcheck --long
python3 diagnostics/original_flow_20260923/run.py "$SCRATCH" --gpu "$ADMITTED_UUID" --label synccheck_update --kind update --mode synccheck --long
python3 diagnostics/original_flow_20260923/run.py "$SCRATCH" --gpu "$ADMITTED_UUID" --label clean_update_0 --kind update --mode clean --long
# Repeat clean labels 1 and 2; repeat valid stages with --kind knn and distinct labels.
python3 diagnostics/original_flow_20260923/run.py "$SCRATCH" --gpu "$ADMITTED_UUID" --label nsys_update --kind update --mode nsys --long
python3 diagnostics/original_flow_20260923/run.py "$SCRATCH" --gpu "$ADMITTED_UUID" --label nsys_light_update --kind update --mode nsys-light --long
python3 diagnostics/original_flow_20260923/run.py "$SCRATCH" --gpu "$ADMITTED_UUID" --label ncu_update --kind update --mode ncu --kernel getQresultCount
python3 diagnostics/original_flow_20260923/analyze.py "$SCRATCH"
python3 diagnostics/original_flow_20260923/test_run.py
```

Run labels cannot be overwritten. The preparer copies source without modification
and checks source/fixture hashes. Source, dataset, binary, `.nsys-rep`, SQLite,
raw receipts and exact machine records stay outside Git. The curated evidence
manifest includes raw artifact hashes, negative runs and both trace variants.
