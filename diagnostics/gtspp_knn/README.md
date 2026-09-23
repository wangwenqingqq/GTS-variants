# GTSPP kNN: coalesced leaf reads and result ownership

**Decision: retain a bounded experimental overlay, not a replacement keeper.**
D64_store passes the complete-query speed gate at Q128/k10 and Q128/k100, and
both sustained endpoints, but fails both Q32 short-query gates. The native tree
and default dispatch remain untouched. This is operator engineering, not a new
kNN algorithm, a Tensor Core result, or a universal GPU-tree claim.

## Contract and result

Native comparator: the 17 source pins in `../cpu_io/SOURCE_PINS.json`
(`archive/GTS_incremental`, source revision `2c92590`). Parent delivery: `f895d51`.
Hardware: one explicitly allocated physical GPU5, RTX PRO 6000 Blackwell Server
Edition, 188 SMs; CUDA 13.1.115, driver 590.48.01, GCC 13.3. Other GPUs on the
shared host were active; host isolation was not available. No clock, driver,
wait-policy or foreign-process changes were made.

SIFT first 65,536 rows, 128D FP32 integer coordinates [0,255]; query IDs
`floor(i*N/Q)`, self included, k=10/100. RP pruning mode is fixed to **0** in both
variants, not learned/calibrated ANN. The exact independent integer oracle checks
complete top-k IDs, uniqueness, sorted squared-distance ranks and finite sorted
returned distances within 1e-3 of their exact square roots. Ties may return any
qualifying IDs. Scalar-kth and self-vector overloads also pass correctness, but
performance below is for **full-ID queries only**.

Complete warm query includes native allocations, GPU/CPU operators, waits,
CPU result delivery and cleanup. It excludes input, oracle, index construction,
calibration, one initial checked query and three checked warmups. Six fresh
process pairs/shape alternate AB/BA; eight retained queries/process. Speedup is
A/B: predeclared paired geometric mean of process medians with seed-0 10,000
bootstrap 95% CI. Marginal medians are descriptive, not the paired estimator.

| Q | k | Native median ms | D64_store median ms | Paired speedup [95% CI] | Pair wins | Short gate |
|---:|---:|---:|---:|---:|---:|---|
| 32 | 10 | 11.120 | 11.098 | 1.017 [0.995, 1.040] | 4/6 | Fail / inconclusive |
| 32 | 100 | 11.312 | 14.253 | 0.968 [0.828, 1.120] | 4/6 | Fail / noisy, marginal regression |
| 128 | 10 | 26.545 | 17.145 | 1.598 [1.525, 1.694] | 6/6 | Pass |
| 128 | 100 | 32.646 | 22.777 | 1.482 [1.332, 1.663] | 6/6 | Pass |

Each short gate requires lower CI >1.02 and >=5/6 wins. Full promotion requires
all four plus both sustained endpoints; **it failed**, without dropping shapes
or changing thresholds. A shape-local deployment would still need a separate
routing/held-out validation campaign; none is enabled here.

Sustained batches contain 64 complete queries and preallocated CPU output-history
copies inside the timer; every result is checked afterward. Three alternating
pairs/endpoint give Q32/k10 **1.050 [1.029, 1.071]** and Q128/k100
**1.488 [1.418, 1.542]**. Both pass the lower-CI >=1.00 non-regression gate.
The Q128/k100 median batch time per query is 30.976 ->20.725 ms. These batch
numbers are a distinct denominator from the short-query table.

## What changed, and why RNN's fix is not copied

`mergeResRnn` reduces a segment. By contrast `mergeResKnn` reads a kth item and
`mergeResKnnIds` copies k already-sorted items. Baseline preflight Q128/k100 took
32.963 ms/query: leaf distance 14.898 ms, final sorting 4.791 ms, final copy
0.820 ms. The material target is the shared leaf distance kernels, not an RNN
sum transplanted into the small kNN copy.

D uses 64-thread CTAs, two warp point owners. Lanes load adjacent coordinates,
accumulate the unchanged FP32 squared differences in FP64, and reduce by five
full-warp shuffles. Lane0 publishes each point's ID and sum to 240 bytes of
shared memory. After one unconditional CTA barrier, threads0..19 do the native
sqrt/threshold/key finalization and contiguous stores to the three native SoA
result arrays. Invalid slots and self distances retain native semantics.
The tree, candidates, thresholds, sorting, encoded output and host waits remain.
No extra global workspace, kernel launch or CPU synchronization is introduced.
Both shared leaf kernels cover all four kNN overloads. Integer summation is exact
under this frozen bound; arbitrary floating-point inputs are not admitted.

The primary Q128/k100 clean stage median falls **14.889 ->5.484 ms (2.715x)**.
Main-thread CPU time falls **31.793 ->22.188 ms/query**; the unchanged default
wait policy can still occupy close to a CPU core while a query runs. This reduces
CPU time per query, not necessarily the instantaneous utilization percentage.
Separate three-query NSYS diagnostics show mean per-query summed
`cudaDeviceSynchronize` API duration **17.219 ->7.761 ms**, and leaf kernel mean
**14.871 ->5.454 ms**.
API waits overlap GPU work: do not add these times or use profiler durations as
the clean speedup denominator.

Q32 exposes the remaining limitation: although leaf medians fall 3.509 ->1.293
ms (k10) and 3.782 ->1.387 ms (k100), other stages erase the gain. k10 cleanup
median increases 1.504 ->3.622 ms; k100 scheduling increases 0.129 ->3.132 ms and
allocation/init 2.002 ->3.050 ms. Stage medians are not additive. These are observed
stage changes, not proof that the leaf edit caused host allocation variability.
Next falsification target is native allocation/scheduling under another frozen
campaign, not more leaf geometries or a claim of universal acceleration.

## Mechanism evidence and costs

One same-round NCU `dataProcessKnn` launch, Q128/k100; same candidate grid of
1,233,116 CTAs, 512 ->64 threads. Replay counters are diagnostic only.

| Metric | Native A | D64_store |
|---|---:|---:|
| Global load sectors | 1,272,531,693 | 331,045,176 |
| Global store sectors | 18,496,740 | 18,496,740 |
| NCU load bytes per sector | 4.08 | 26.00 |
| NCU store bytes per sector | 32 | 32 |
| DRAM read bytes | 54,865,152 | 54,132,480 |
| DRAM write bytes | 606,773,248 | 606,244,608 |
| Executed warp instructions, hardware | 3,598,245,416 | 2,102,627,230 |
| Active / eligible warps per scheduler | 3.01 / 0.18 | 8.55 / 0.28 |
| Issue-active percent | 13.69 | 21.86 |
| ID leaf REG / STACK / LOCAL | 40 / 47,528 / 0 | 43 / 47,528 / 0 |
| Static / driver shared bytes | 0 / 1,024 | 240 / 1,024 |

Loads use 3.844x fewer L1/TEX sectors while store efficiency is preserved.
DRAM bytes barely change: this is **not** a 3.844x reduction in PCIe traffic,
DRAM traffic, or total work. Ownership, reduction geometry, finalization and CTA
shape change together; this is not a pure-coalescing causal isolation.
D pays shared traffic, 834,522 reported shared bank conflicts and one CTA barrier.
cuobjdump reports D's shared total as 1,264 bytes; NCU distinguishes the 240 static
and 1,024 driver bytes. The large legacy ID-kernel stack remains (non-L2 fallback
is retained, not validated); zero LOCAL is not a zero-stack claim. Selected five
non-leaf function SASS hashes are unchanged. Full hashes/resources, source-PC
stall sites, executed instruction ledger and metrics accompany this report.
Top sampled PCs move from native FADD/distance-chain sites to a D LDG site;
PC stall location alone does not identify the producer or prove one root cause.

## Retained negative controls and validation

| Candidate | Mechanism | Complete-query paired ratios, Q32/k10; Q32/k100; Q128/k10; Q128/k100 | Decision |
|---|---|---|---|
| B512 | Warp loads, lane0 finalization/stores, 512 threads | 0.945; 0.952; 0.913; 0.853 | All short gates and both sustained gates fail |
| C64 | Same math/stores, 64 threads | 0.987; 1.088; 0.917; 0.894 | All short gates and both sustained gates fail; Q32/k100 inconclusive |
| D64_store | C64 plus shared handoff and thread-owned finalization/stores | 1.017; 0.968; 1.598; 1.482 | Partial Q128 win; full promotion fails |

B512 reduces load sectors 2.364x but raises store sectors 4x and global-store
warp instructions 20x. Fewer read transactions alone are insufficient. C64
cannot rescue sparse-lane stores/finalization. Keep their separate same-round
native comparators and every observation in `rejected_warp512/` and
`rejected_warp64/`; do not reuse their A times for D. Reopen these controls only
with a concrete changed store/finalization contract, not another favorable median.
D supplies that control but remains bounded by the host-side stage variability.

Each candidate has 32 final correctness/sanitizer gates, four 64-query stress
processes (every result checked), 48 clean timing processes, four profiler
processes and 12 sustained processes: 100 final processes. B additionally retains
17 preflight processes and an earlier 32-gate round. All final receipts pass
correctness and post-run device-clear checks. A/B memcheck/synccheck cover smoke
N2,000 and primary N65,536; B racecheck/initcheck cover smoke shared handoffs.
Pointer allocation churn occurs naturally across queries/processes; Graph replay,
concurrent streams, non-L2 metrics, held-out ANN recall, updates and production
integration are not tested.

Before final timing, the oracle was hardened to reject nonfinite full-ID distances
and explicitly check returned float order; both binaries were rebuilt and all
32 gates repeated. The initial gates remain preserved. An initial preparation
anchor mismatch was fixed before generation; the failed partial is retained.
B512's first analysis incorrectly required cross-collector instruction equality:
source-PC totals equal `sass__inst_executed_per_opcode`, but the hardware total
exceeds the source total by 0.624% of the hardware total (0.628% of source).
Both totals and the unresolved discrepancy remain, without
normalization. All D source/opcode/hardware totals match exactly. NVIDIA documents
[software-patched source metrics and collection overhead](https://docs.nvidia.com/nsight-compute/ProfilingGuide/#overhead);
that distinction does not explain this particular B512 gap. No timing or
acceptance threshold changed during these analysis fixes.

## Reproduce and audit

Use the entire checkout (sibling diagnostic helpers are reused), Python stdlib,
CUDA13.1, Compute Sanitizer, NCU2025.4.1, NSYS2025.5.2 and authorized SIFT text.
Set `SCRATCH` to a fresh task-owned directory, `CUDA_HOME` to the toolkit,
`SIFT_BASE_TEXT` to the pinned data and `ADMITTED_UUID` to an explicitly allocated
physical GPU5. The runner intentionally refuses other GPU indices. Review real
tool paths and permissions; sudo profiling requires authorization, never a driver
settings change. Existing outputs are never overwritten.

```sh
python3 diagnostics/gtspp_knn/test_prepare.py
python3 diagnostics/gtspp_knn/test_analysis.py
mkdir -p "$SCRATCH/bin" "$SCRATCH/logs" "$SCRATCH/fixtures"
for n in 2000 65536; do
  python3 diagnostics/tc_leaf_probe/prepare.py fixture "$SIFT_BASE_TEXT" "$SCRATCH/fixtures/n$n" --n "$n"
done
python3 diagnostics/gtspp_knn/prepare.py "$SCRATCH/finalA" --variant A
python3 diagnostics/gtspp_knn/prepare.py "$SCRATCH/finalB" --variant D
for v in A B; do
  "$CUDA_HOME/bin/nvcc" -std=c++17 -O3 -arch=sm_120 -rdc=true -lineinfo \
    -DGTS_DIAG_NVTX -Xptxas=-v -Xnvlink=--ignore-host-info \
    -I"$SCRATCH/final$v/include" "$SCRATCH/final$v/src/main.cu" \
    -ldl -o "$SCRATCH/bin/$v" > "$SCRATCH/logs/build$v.log" 2>&1
  "$CUDA_HOME/bin/cuobjdump" --dump-sass "$SCRATCH/bin/$v" > "$SCRATCH/logs/$v.sass"
  "$CUDA_HOME/bin/cuobjdump" --dump-resource-usage "$SCRATCH/bin/$v" > "$SCRATCH/logs/$v.resources"
done
python3 diagnostics/gtspp_knn/record.py "$SCRATCH"
for stage in gates stress timing profile sustained; do
  python3 diagnostics/gtspp_knn/run.py "$SCRATCH" --gpu "$ADMITTED_UUID" --stage "$stage"
done
python3 diagnostics/gtspp_knn/analyze.py "$SCRATCH" "$NEW_EXPORT"
```

For the rejected controls use separate fresh collections and prepare B with
`--variant B` or `--variant C`; never overwrite D or select a subset of its rows.
`EVIDENCE.json` stores collection and delivery source hashes separately, full
binary and selected-function hashes, fixture manifests, all run summaries and
private raw-file hashes. CSVs preserve every timed sample, stage, NCU metric and
opcode count. The private raw receipt/log archive SHA256 is
`a67a3aee6bf792db6b00af092f41cd09ae32efb89f2545eb7c128e39f7f7bce6`.
It is not a public download and excludes binaries, fixtures and profiler HOME
caches. Raw host snapshots, paths, SASS, reports and original inputs stay private.
No paper, original source tree, repository visibility or data license is changed.
