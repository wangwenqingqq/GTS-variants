# GTS leaf Tensor Core feasibility: modest positive component result

**Measured 2026-09-23:** a WMMA leaf-candidate replay is **1.106-1.242x** faster
than the coalesced warp-per-point SIMT comparator under the predeclared paired
batch-1 estimator; sustained 64-call batches give **1.090-1.258x**. This includes
query-mask construction, FP32-to-FP16 conversion, padding, recovery and counting.
All four required shapes pass the continuation gate. This is **not a full GTS
speedup, CPU-usage improvement, a best-CUDA comparison, or a novel tree thesis**.

## Scope and results

The original GTS tree produces actual query/leaf candidates. Both replays use
identical resident FP32 vectors, static compact leaf metadata and candidate pairs.
The baseline is a new coalesced CUDA comparator, not original GTS's slower
per-thread distance kernel or nested Thrust result reducer. Both new variants
count results within their kernels. The tree topology and traversal are unchanged.

- SIFT first 65,536 base vectors, 128D integers in [0,255]; query IDs floor(i*N/Q).
- Original GTS author commit `3bac1b725e92e98e3b69d5cb79ad9c56ccb5e639`, all 18
  file pins checked; MAX_H=5 and 256 MiB workspace are explicit resource
  adaptations. The N=2,000 smoke uses native MAX_H=3. MAX_SIZE=20 is unchanged.
- RTX PRO 6000 Blackwell Server Edition, physical GPU 0; driver 590.48.01,
  CUDA 13.1.115, GCC 13.3.0. Shared host; GPU0 pre/post process checks and
  advisory lock, no clock/power settings or foreign jobs modified.
- Six fresh direction-balanced AB/BA processes per shape (24 total), 20 warmups,
  100 batch-1 observations and 20 batches of 64 calls per process/variant.
  Raw numeric samples are in [samples.csv](samples.csv). All process results,
  host timers, order splits, p10/median/p90, hashes and gates are in
  [EVIDENCE.json](EVIDENCE.json). No failed or slow timing samples were dropped.

Times are median CUDA-event microseconds for the **complete resident candidate
operator**. Ratios >1 favor Tensor Cores. Marginal and paired estimators differ:
the paired column is the geometric mean of six within-process median ratios,
with a fixed-seed 10,000-resample process bootstrap 95% interval.

| Q | Radius | Useful tile cells | SIMT us | TC us | Marginal A/B | Paired A/B [95% CI] | Sustained paired A/B |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 32 | 300 | 34.57% | 235.17 | 212.77 | 1.105 | 1.106 [1.098, 1.117] | 1.090 |
| 32 | 500 | 40.72% | 275.62 | 233.66 | 1.180 | 1.200 [1.173, 1.228] | 1.134 |
| 128 | 300 | 34.34% | 833.57 | 737.89 | 1.130 | 1.164 [1.107, 1.223] | 1.117 |
| 128 | 500 | 40.72% | 990.34 | 787.09 | 1.258 | 1.242 [1.224, 1.261] | 1.258 |

Every shape has 6/6 positive process comparisons. Order sensitivity remains:
Q=128/r=300 has AB 1.235x versus BA 1.096x; both are positive, but the exact
magnitude is not order-invariant. The narrow Q=32/r=300 case only just exceeds
the predeclared 1.10x continuation threshold. This is a small feasibility
campaign, not an exclusive-host or production performance guarantee.

## Evidence and mechanism

**Measured correctness:** original GTS counts, sparse-candidate CPU counts, SIMT
counts and TC counts agree with an independent full-table integer-distance
oracle for all five shapes. Both replay paths also match every candidate's
integer squared distance. FP16 stores these integer coordinates exactly; FP32
accumulation is exact because dot products are <=8,323,200 and norm-sum / twice
Dot are <=16,646,400, below 2^24. No numerical correction or fallback is needed
under this contract. Arbitrary FP32, cosine and edit-distance contracts are not
covered. Export checks ensure unique pairs and a leaf partition of all objects.

**Measured safety:** memcheck/synccheck/initcheck/racecheck pass on N=2,000;
memcheck/synccheck pass on N=65,536/Q=128/r=500. Repeated buffer reuse passes
before and after timing. Fresh processes recreate allocations. CUDA Graphs,
multiple streams, explicit address-churn fuzzing and production integration were
not tested and are not promoted.

**Measured structure:** the 65,536-object index has 10,000 leaves, mean 6.5536
points/leaf. Leaf sizes are 6 (8,100 leaves), 7 (991), 10 (9), 11 (891), and
12 (9). A 16x16 tile therefore has only 34.34-40.72% useful cells. Radius 300
still visits 83.78-84.36% of full-table query/point pairs; radius 500 visits
99.43-99.44%. Result fractions are much lower: about 0.68-0.75% and 35.76-36.27%,
respectively. **These are weak-pruning workloads, not proof for sparse traversal.**

**Static code evidence:** the exact custom tensor function contains 16
`HMMA.16816.F32` instructions (8 WMMA 16x16x16 steps); the SIMT comparator
contains none. ptxas reports tensor 40 registers / 9,216 B shared; SIMT 36
registers / 16 B shared; mask builder 12 registers / no shared. All have zero
stack/spills; normalized function SASS hashes and binary hashes are retained.
Issued tile counts are derived from actual masks, not dynamic NCU counters.

**Diagnostic-only profile:** for Q=128/r=500, Nsight Systems reports mean SIMT
1,078.365 us, tensor 818.271 us, and mask construction 15.796 us. This check
trace mixes normal calls and diagnostic distance writes, and is not the public
latency denominator. It suggests the extra mask kernel is small compared with
the tensor body; conversion, shared-memory feed, padding and epilogue costs
within that body are not individually isolated. Logical operand reuse and
2.46-2.91x padded distance-cell work explain the tradeoff, but measured DRAM
traffic / causal stall attribution are still absent. Do not substitute logical
byte counts for actual memory transactions.

The excluded setup covers file parsing, static metadata/norm construction,
independent CPU oracle, allocation, initial upload and initial validation.
The reported `setup_ms` combines these, so it is not an isolated preprocessing
benchmark. No traversal, H2D/D2H result delivery, cold-start index build or
original GTS end-to-end benefit was measured.

## Decision and claim boundary

| Claim | State | Allowed wording |
|---|---|---|
| Exact integer L2 for these candidates | measured | Both replay paths and native counts match the full-table oracle. |
| Faster resident leaf operator | partial | 1.106-1.242x paired improvement over this SIMT implementation on four SIFT shapes. |
| Tree fits efficiently into TC tiles | rejected for this mapping | Only 34.34-40.72% of computed distance cells are useful. |
| Full-tree acceleration / reduced CPU pressure | unknown | Not measured; host orchestration and traversal remain outside the denominator. |
| New research thesis from tree-to-TC conversion | rejected | Generic conversion/reuse is already prior art; no new contribution claimed. |

Keep this as a **shape-local component prototype**, not production dispatch.
Before further integration, compare a no-index dense TC baseline under the same
exact integer/result contract and measure full GTS query latency including
traversal and delivery. If removing the tree is faster on these weak-pruning
shapes, a tree-specific acceleration thesis has not survived. Strong-pruning
queries and different metrics are separate reopen conditions, not implied wins.

The nearest prior art is [TED-JOIN, HiPC 2022, Section III-B](https://jan.ucc.nau.edu/mg2745/publications/Gallet_Gowanlock_HiPC2022.pdf): it already uses a grid index,
shared candidate groups and Tensor Core Euclidean distances. Our test changes
the source of candidates and the precision contract; that alone is not a new
research mechanism. No timing comparison against TED-JOIN was performed.

## Reproduce

Run from a clean checkout. Required: Python 3 standard library, CUDA 13.1 nvcc,
compute-sanitizer, and optionally Nsight Systems 2025.5.2. Obtain the original
GTS source and SIFT base text separately; restricted/source datasets are not
redistributed. SIFT text header must be `128 1000000 2` (or an equivalent count
>=65,536); rows contain 128 integer-valued coordinates. The fixture manifest
pins the exact measured subset, not merely its dimensionality.

Set `AUTHOR_SOURCE_ROOT` to the directory containing `GTS/` and `GPU-Tree/`,
`SIFT_BASE_TEXT` to that text file, `CUDA_HOME` to the real CUDA toolkit root,
`SCRATCH` to a new task-owned directory, and `ADMITTED_UUID` to the explicitly
approved physical GPU0 UUID. An argument is not permission to use a shared GPU.

```sh
python3 diagnostics/tc_leaf_probe/test_prepare.py "$AUTHOR_SOURCE_ROOT"
mkdir -p "$SCRATCH/bin" "$SCRATCH/logs" "$SCRATCH/fixtures"
python3 diagnostics/tc_leaf_probe/prepare.py source "$AUTHOR_SOURCE_ROOT" "$SCRATCH/source3" --height 3
python3 diagnostics/tc_leaf_probe/prepare.py source "$AUTHOR_SOURCE_ROOT" "$SCRATCH/source5" --height 5
python3 diagnostics/tc_leaf_probe/prepare.py fixture "$SIFT_BASE_TEXT" "$SCRATCH/fixtures/n2000" --n 2000
python3 diagnostics/tc_leaf_probe/prepare.py fixture "$SIFT_BASE_TEXT" "$SCRATCH/fixtures/n65536" --n 65536
for h in 3 5; do
  "$CUDA_HOME/bin/nvcc" -std=c++17 -O2 -arch=sm_120 -rdc=true -lineinfo \
    -Xnvlink=--ignore-host-info -I"$SCRATCH/source$h/GTS/include" \
    "$SCRATCH/source$h/GTS/src/main.cu" -ldl -o "$SCRATCH/bin/export$h" \
    >"$SCRATCH/logs/build$h.log" 2>&1
done
"$CUDA_HOME/bin/nvcc" -std=c++17 -O3 -arch=sm_120 -lineinfo -Xptxas=-v \
  diagnostics/tc_leaf_probe/probe.cu -o "$SCRATCH/bin/probe" \
  >"$SCRATCH/logs/build-probe.log" 2>&1
"$CUDA_HOME/bin/cuobjdump" --dump-sass "$SCRATCH/bin/probe" >"$SCRATCH/logs/probe.sass"
for stage in extract check sanitizer timing; do
  python3 diagnostics/tc_leaf_probe/run.py "$SCRATCH" --gpu "$ADMITTED_UUID" --stage "$stage"
done
# Optional, after timed runs; profiler duration is not the public denominator:
python3 diagnostics/tc_leaf_probe/run.py "$SCRATCH" --gpu "$ADMITTED_UUID" --stage profile
nsys stats --report cuda_gpu_kern_sum --format csv --output . \
  "$SCRATCH/runs/profile_n65536_q128_r500/trace.nsys-rep"
```

Copy the intended source/docs only (not `local/`) into the scratch provenance
snapshot, then analyze:

```sh
mkdir -p "$SCRATCH/diagnostics/tc_leaf_probe"
for name in prepare.py probe.cu run.py analyze.py test_prepare.py CONTRACT.md README.md; do
  cp "diagnostics/tc_leaf_probe/$name" "$SCRATCH/diagnostics/tc_leaf_probe/$name"
done
python3 diagnostics/tc_leaf_probe/analyze.py "$SCRATCH" "$SCRATCH/curated"
```

No overwrite/resume behavior is implicit. On failure preserve the run directory
and use a new label/scratch for a repair. One early source-export anchor error
stopped before any GPU run; one sanitizer stdout parser rejected a zero-error
run because the sanitizer appends a summary after `pass`. Both were repaired
before timing; that parser attempt remains in the evidence inventory. No CUDA
candidate was tuned or replaced after performance observations.

Raw receipts/logs, full SASS, source-generation manifests, private device states,
and original Nsight reports remain in task-owned scratch. The portable evidence
manifest hashes them; its relative paths resolve against that campaign root.
No datasets, binaries, generated author source, machine configuration or raw
conversation is included in this publication. The original sources and previous
campaigns remain untouched.

### Provenance snapshots

`EVIDENCE.json.source_sha256` is the frozen campaign-collection source inventory,
not a claim that every publication file has that hash. It also retains hashes
of two incidental AppleDouble sidecars; those sidecars are not shipped or used.
The CONTRACT outcome was appended after the frozen contract, and the analyzer's
CSV writer was subsequently changed from CRLF to LF with identical numeric rows.
`delivery_source_sha256` separately pins the final scripts, kernel, contract and
README. Frozen hashes and measurements were not overwritten.
