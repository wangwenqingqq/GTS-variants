# GTS pruning-layout controls

## Decision

**Do not promote either layout-only candidate.** No dataset passes the preregistered six-win / 95% lower-bound >1.05 gate. GIST and Deep show repeatable regressions; T-loc shows small differences rather than a useful gain. This does not reject coalescing generally, larger indexes, or different thread ownership.

This isolates metadata SoA and pivot packing. No traversal fusion, distance reuse, warp-cooperative arithmetic or precision change is combined with them. Generic layout/coalescing is an engineering control, not a novelty claim.

## Completed-query results

Six fresh processes/mode, 4096 queries/process after 64 warmups. Values are medians of process-mean completed-query wall latency, including input/output transfers and host synchronization. Construction, layout setup, capture and output hashing are excluded here and accounted separately.

E = native pruning + previously validated fused results + Graph. S = E with SoA pid/lower metadata. L = S with dimension-major packed pivots. D/U/V are stream counterparts. A anchors original-function output/order only: **this is not a speedup claim against the untouched GTS executable**.

| Dataset | D | GPU | E (us) | S (us) | L (us) | S change | L change |
|---|---:|---:|---:|---:|---:|---:|---:|
| GIST | 960 | 1 | 7565.738 | 7584.495 | 7721.813 | +0.25% | +2.06% |
| Deep | 96 | 0 | 816.168 | 820.267 | 834.678 | +0.50% | +2.27% |
| Tloc | 2 | 0 | 62.313 | 62.813 | 63.206 | +0.80% | +1.43% |

Positive latency change is slower. Each row uses remeasured same-device baselines; no ratio pools GPUs. Hardware: RTX PRO 6000 Blackwell Server Edition, 188 SMs, CUDA 13.1.115, driver 590.48.01, unchanged 600-W limit. CPU is shared/unpinned; clock locking was not independently established and no settings were changed.

| Dataset | Pair | Paired geometric speed ratio [95% interval] | Wins / 6 |
|---|---|---|---:|
| GIST | E/S | 0.997506 [0.997459, 0.997554] | 0 |
| GIST | E/L | 0.979712 [0.979585, 0.979799] | 0 |
| GIST | S/L | 0.982162 [0.982060, 0.982227] | 0 |
| Deep | E/S | 0.994987 [0.994749, 0.995193] | 0 |
| Deep | E/L | 0.978049 [0.977565, 0.978547] | 0 |
| Deep | S/L | 0.982977 [0.982542, 0.983443] | 0 |
| Tloc | E/S | 0.989655 [0.977082, 1.001764] | 2 |
| Tloc | E/L | 0.992257 [0.986205, 0.998088] | 1 |
| Tloc | S/L | 1.002629 [0.990572, 1.018614] | 2 |

Intervals use the exact 6^6 percentile bootstrap of paired process log ratios, not thousands of falsely independent queries. Marginal median ratios and paired ratios are distinct estimators. T-loc S/L estimators disagree in sign; neither supports a packing win. Per-process p10/p50/p90, order splits and every sustained case are in [EVIDENCE.json](EVIDENCE.json). Query loops still consume approximately one CPU core; layout does not remove host synchronization/spinning.

## Interruption and coverage

A foreign job entered GPU 1 during GIST `sustained_all_0_L`. The monitor stopped only the owned process group, retaining the failed receipt and partial telemetry. All six GIST primary rounds completed, but only **14/18** sustained processes completed: one aborted and three never started. This is not a completed GIST sustained pass. The primary regression is measured; promotion also remains blocked by the incomplete sustained matrix.

[CONTINUATION.md](CONTINUATION.md) was recorded before fresh GPU-0 execution. Deep and T-loc repeated full outputs, sanitizers, stress, primary timing, all 18 sustained processes and profiling on GPU 0 with the same binary. Earlier GPU-1 gates/profiles remain auxiliary evidence, not their latency denominator. Both continuation candidates pass the sustained non-regression tolerance but fail the primary speedup gate.

For the selected dataset/device campaigns: 81 full-output runs, 1536 per-level flag cases, 54 sanitizer runs and 147456 stress queries pass. Output membership matches the CPU float64 oracle, distances meet the declared tolerance, and ordered float32 outputs are directly bit-compared to native outputs. Both stream and Graph paths are covered.

Nominal process checks are 200 ms, but actual median gaps are about 0.37 s and the largest completed-run gap is 2.05 s. This is not guaranteed exclusion of transient jobs. Detected interference was preserved, not silently replaced. One nice-priority static-only native compilation overlapped GIST primary collection; no samples were dropped.

## Coalescing improved, but cache traffic and latency did not

NCU profiles the first query's two stream pruning kernels with identical 34-pass sections and no clock/cache control. These are diagnostic observations, not public latency or 64-query averages. Setup/cache states can differ because packing produces a new layout.

| Dataset | Mode | Load requests | L1 load sectors | L1 misses / TEX L2 reads | Replay pruning (us) |
|---|---|---:|---:|---:|---:|
| GIST | D | 9660 | 18510 | 1656 | 5105.184 |
| GIST | U | 9660 | 18353 | 1616 | 5119.456 |
| GIST | V | 9660 | 10673 | 3176 | 5262.816 |
| Deep | D | 1020 | 2094 | 252 | 531.040 |
| Deep | U | 1020 | 1937 | 212 | 529.696 |
| Deep | V | 1020 | 1169 | 368 | 549.376 |
| Tloc | D | 54 | 133 | 50 | 21.696 |
| Tloc | U | 54 | 78 | 38 | 21.376 |
| Tloc | V | 54 | 74 | 38 | 21.792 |

For GIST, D to V reduces requested L1 sectors by **42.34%**, but L1 misses / TEX L2 read sectors rise from **1656 to 3176**. Load requests remain 9660. Eight of nine dataset/mode profiles report zero DRAM read bytes; Deep/D reports 256 bytes across its two levels. All report zero local load/store sectors. These are small, replayed, predominantly cache-resident cases, not a cold-million-point DRAM test.

**Measured:** for packed V versus D, fewer sectors per request did not translate into faster pruning; its Graph counterpart L also did not improve completed-query latency over E. **Inference:** dimension-major packing improves same-warp coalescing while its 64-byte dimension stride loses locality enjoyed by the original 4-byte per-vector stride. This is a cache-level tradeoff, not proof that repeated sibling loads originally caused separate DRAM reads.

## Stronger bottleneck leads, not optimized here

NSYS retains exactly 17 kernels/query in E/S/L. Native GIST's two pruning kernels consume **5097.666 us** of **7555.004 us** summed query-kernel time in that trace. The unchanged scalar distance path is therefore a substantial target.

The L2 loop retains FP64 conversions and relocations to `__internal_accurate_pow`. A separate static build of unmodified author `main.cu` has **identical normalized native pruning SASS** to the harness, excluding a harness-header explanation. On the selected GIST second level, NCU reports **92.57% no-eligible**, and **83.83% FP64-pipe activity on the most active SM**, versus **0.446% averaged across the device**. The launch is one CTA; this is not whole-GPU saturation.

Expensive scalar math / limited ready parallelism is a strong next-control hypothesis, not a measured speedup from replacing `pow`. Any arithmetic control must preserve or explicitly revalidate membership and the float contract; blindly substituting float multiply or reordered reduction is not equivalent.

| Dataset | Median surviving leaves / 100 | Mean child distances/query |
|---|---:|---:|
| GIST | 100 | 108.28125 |
| Deep | 100 | 110.00000 |
| Tloc | 9 | 30.78125 |

Normal radii target a median of roughly 50 neighbors among 2000 points. High-dimensional cases nevertheless retain a median of all 100 leaves. This is observed weak pruning in these trees, consistent with—but not an isolated causal proof of—high-dimensional distance concentration. It is not a result about every GPU tree index.

## Added costs and resources

| Dataset | S bytes | L bytes | Median S layout setup (us) | Median L layout setup (us) |
|---|---:|---:|---:|---:|
| GIST | 888 | 62328 | 59.361 | 75.704 |
| Deep | 888 | 7032 | 62.389 | 70.305 |
| Tloc | 888 | 1016 | 35.642 | 394.995 |

Layout setup includes allocation, packing and synchronization. Per-process first-query, capture, setup and setup+first-query charged over 4096 measured queries are retained in EVIDENCE. That last derived value excludes benchmark warmups and construction, so it is not cold full-application runtime. There is no observed break-even from amortizing a positive layout cost over these slower hot-query medians.

E/S/L use 50/48/44 registers, zero query shared memory and the same 47528-byte static stack reservation inherited from retained generic metric branches. Static LDL/STL instructions in the unused edit-distance path are not measured L2 spills. See [STATIC_EVIDENCE.json](STATIC_EVIDENCE.json) and [NCU_EVIDENCE.json](NCU_EVIDENCE.json). Fewer registers do not establish an occupancy win for a one-CTA launch with only 10 or 100 useful pruning threads.

## Reproduce

[CONTRACT.md](CONTRACT.md) fixes seeds, radii, dimensions, arithmetic, capacities and estimators. Dependencies: Python with NumPy (observed 1.26.4), CUDA 13.1, compute-sanitizer, NSYS, NCU and nvidia-smi. Fetch pinned author source separately; no datasets, binaries, machine setup or profiler dumps are published. Generation verifies author-file hashes.

```sh
D=diagnostics/pruning_layout_20260923
python3 "$D/test_cpu.py"
python3 "$D/prepare.py" "$AUTHOR_SOURCE_ROOT" "$SCRATCH"
python3 "$D/fixtures.py" "$DATASET_ROOT" "$SCRATCH/data"
cp "$D/suite.py" "$D/verify_full.py" "$SCRATCH/"
mkdir -p "$SCRATCH/bin" "$SCRATCH/logs"
for ds in GIST Deep Tloc; do ln -s ../../bin "$SCRATCH/data/$ds/bin"; done
(cd "$SCRATCH" && "$CUDA_HOME/bin/nvcc" -std=c++17 -O2 -arch=sm_120 \
  -rdc=true -lineinfo -Xcompiler=-fno-omit-frame-pointer \
  -Xnvlink=--ignore-host-info -Xptxas=-v -Isource/include \
  graph_bench.cu -o bin/graph_bench)
# Verify host, idle UUID and existing advisory lock first; no settings changes.
python3 - "$SCRATCH" "$ADMITTED_UUID" "$CUDA_HOME/bin/nvcc" <<'PY_ADMISSION'
import datetime,json,re,subprocess,sys
from pathlib import Path
root,gpu,nvcc=sys.argv[1:]
fields=subprocess.check_output(['nvidia-smi','-i',gpu,
 '--query-gpu=index,uuid,name,driver_version,power.limit,compute_cap',
 '--format=csv,noheader'],text=True).strip().split(', ')
toolkit=subprocess.check_output([nvcc,'--version'],text=True)
record={'gpu_index':int(fields[0]),'gpu_uuid':fields[1],'gpu_name':fields[2],
 'driver':fields[3],'power_limit':fields[4],
 'arch':'sm_'+fields[5].replace('.',''),
 'cuda':re.search(r'V(\d+\.\d+\.\d+)',toolkit).group(1),
 'clocks_locked':None,'clock_policy':'uncontrolled; no setting changes',
 'verified_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
Path(root,'logs','admission.json').write_text(json.dumps(record,indent=2)+'\n')
PY_ADMISSION
for stage in smoke gates timing trace; do
  python3 "$D/suite.py" "$SCRATCH" "$stage" --gpu "$ADMITTED_UUID" >"$SCRATCH/logs/$stage.txt" 2>&1 || exit 1
done
# Use existing authorized counter access, without changing driver permissions.
sudo -n env PATH="$PATH" python3 "$D/suite.py" "$SCRATCH" ncu --gpu "$ADMITTED_UUID" >"$SCRATCH/logs/ncu.txt" 2>&1
python3 "$D/summarize.py" "$SCRATCH" "$SUMMARY_JSON"
python3 "$D/summarize_ncu.py" "$SCRATCH" "$NCU_SUMMARY_JSON"
```

Default admission is physical GPU 1 and all datasets. The recorded continuation used `--gpu-index 0 --datasets Deep Tloc` in a separate root. For a clean complete rerun, the summarizers take that root without `--continuation`. To regenerate this historical split record, provide the GPU-1 root plus `--continuation "$GPU0_ROOT"`. Preserve private `logs/admission.json` with verified GPU identity, driver, toolkit and settings; analysis validates source, binary, runner, inputs, outputs and actual order. Never fabricate an interruption to match this record.

## Negative-evidence boundary

| Claim | State | Allowed scope / reopen condition |
|---|---|---|
| SoA / packed pivots provide a useful query gain | Rejected under the primary gate | These N2000 batch-one cases only. Reopen with a new critical-path mechanism or workload, not the same layout rerun. |
| Packing reduces requested sectors | Measured, diagnostic | Selected first-query NCU launches; not proof of lower DRAM traffic. |
| GIST sustained matrix passed | Incomplete | Missing same-device cases remain required for any promotion. Primary negative evidence remains valid. |
| Scalar math / dimension cooperation deserves the next control | Inferred recommendation | Separate invariant-preserving arithmetic and ownership experiments; no speedup measured here. |
| All GPU trees have this bottleneck | Unknown | Requires independent source and same-contract measurements on other indexes. |

Generic layout/coalescing is established prior art: [CUDA Best Practices](https://docs.nvidia.com/cuda/cuda-c-best-practices-guide/index.html#coalesced-access-to-global-memory), [Harmonia](https://cs.tulane.edu/~lpeng3/papers/ppopp-19.pdf). Author source: [GTS revision 3bac1b7](https://github.com/ZJU-DAILY/GTS/tree/3bac1b725e92e98e3b69d5cb79ad9c56ccb5e639). No paper prose or production dispatcher was changed. Rejected implementations remain diagnostic variants only. [CHECKPOINT.json](CHECKPOINT.json) identifies the private raw archive, including auxiliary evidence and the interrupted run.
