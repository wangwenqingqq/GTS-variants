# Certified-navigation E1 diagnostic

**Decision: stop memo/candidate-only promotion for this frozen snapshot.**
G1 saves 1.075346% coordinate updates; G2 saves 0.023669% leaf calls. This is
measured mechanism evidence, not a robust end-to-end speedup or a new thesis.
See [REPORT.md](REPORT.md), [CLAIMS.md](CLAIMS.md), and the append-only
[LEDGER.md](LEDGER.md). E2 is incomplete; E3 used **0/24** formal processes.

## Scope and identity

Original GTS `searchIndexKnnV2`, shared correctness/full-output repairs,
GIST N1M/D960, self-inclusive K8/B1, 32 frozen development queries. G0 is not
untouched upstream and is not a full-table search. G1 adds pivot-distance memo;
G2 adds distinct, persistent cross-layer real candidates; G3 adds both.
Distance ranking uses ordered RN FP64 squared L2 on FP32 inputs, FMA disabled,
then logical row ID. Online modes never consume exhaustive-oracle answers.

One physical RTX PRO 6000 Blackwell GPU 7 / NUMA 3 was explicitly admitted for
all four modes. Driver 590.48.01, CUDA 13.1, sm_120a. No foreign process was
signaled and no clocks/power settings were changed. Admission failures and the
v6 initcheck failure are retained, not converted into successful samples.
Final v7 makes all 16 bytes of the common sort key initialized and logs exact
visit bitsets only in the separate instrumented replay. v4/v6/v7 timing is
never pooled. Binary/source hashes live in the corresponding evidence files.

## Repository and external prerequisites

This directory is **not a standalone package or complete AE bundle**. Use the
full `wangwenqingqq/GTS-variants` repository; shared adapters, driver and guard
inputs are inherited from base `db89d2f1aa66b934f3b99b5730efafa87cee5a71`.
Their exact hashes are in `evidence/GENERATION_INPUTS.json`; v7's generated
source manifest additionally pins the shared adapter inputs. Historical v6
manifests remain unchanged. Do not mix this with another campaign's samples.

Required: Python >=3.9 (NumPy only for the CPU work model), a C++17 compiler, and
for GPU reproduction Linux, numactl, nvidia-smi, CUDA 13.1/Thrust, an sm_120a
GPU, and compute-sanitizer/NSYS for the optional diagnostic probe. Use the
actual toolkit nvcc executable, not a relocated symlink. No new dependencies
or drivers are installed by these scripts.

Supply separately, under the applicable source/data permissions:

* GTS `Source Code/GTS` at upstream commit
  `3bac1b725e92e98e3b69d5cb79ad9c56ccb5e639`; all eight source pins must match.
* Frozen GIST `data.f32bin`: little-endian `(D=960,N=1000000,metric=2)` int32
  header followed by N-by-D FP32 row-major values, all finite in [0,2].
  SHA256 `f371099f42fea105bed573c67bbfd5b522743220873cf68aa900eb6c44b388e7`.
* Exact original-tree cache, SHA256
  `4fcd14b52ec49bed23a2e49c416a80cee70ce0ed3ea2a436bbb6132dbe4bfed0`.
  The cache parser and ownership audit are in `audit.py`. A newly rebuilt
  random tree is a new experiment, not reproduction of this snapshot.

Raw data, upstream source copies, generated patches, binaries, private host
configuration and raw command logs are not shipped. The small oracle binary
is a derived result, not dataset content. This release does not certify
third-party licensing or that an outside user can obtain the exact tree cache.

## Reproduce the bounded diagnostic

Run from the full repository root. Set all paths deliberately; SCRATCH must be
an absolute existing private directory outside the repository. These commands
do not run the formal 256-query campaign. Inspect active users/processes and
obtain authorization for the selected device before any GPU run.

```sh
TASK=research/certified_navigation_20261010
# Set GTS_UPSTREAM, GTS_INDEX, GIST_DATA, SCRATCH, NVCC, GPU_UUID, NUMA_NODE.
export GTS_UPSTREAM GTS_INDEX
python3 "$TASK/test_local.py"
python3 "$TASK/test_oracle_cpu.py"
python3 "$TASK/audit.py" --source "$GTS_UPSTREAM" --index "$GTS_INDEX" \
  --out "$SCRATCH/audit"
python3 "$TASK/prepare.py" "$GTS_UPSTREAM" "$SCRATCH/generated"
python3 "$TASK/prepare_guard.py" "$SCRATCH/guard_src"
"$NVCC" -O3 -std=c++17 --fmad=false -lineinfo \
  -gencode arch=compute_120a,code=sm_120a -rdc=true \
  -I "$SCRATCH/generated/adapted/include" "$SCRATCH/generated/bench.cu" \
  -lcudadevrt -o "$SCRATCH/bench"
"$NVCC" -O3 -std=c++17 --fmad=false -lineinfo \
  -gencode arch=compute_120a,code=sm_120a "$TASK/oracle.cu" -o "$SCRATCH/oracle"
c++ -O3 -std=c++17 -fno-fast-math -ffp-contract=off \
  "$TASK/oracle_cpu.cpp" -o "$SCRATCH/oracle_cpu"
"$SCRATCH/oracle_cpu" "$GIST_DATA" "$TASK/dev32.qid" 8 "$SCRATCH/cpu_oracle.bin"
python3 "$TASK/run_e1.py" --work "$SCRATCH/e1" \
  --data "$GIST_DATA" --index "$GTS_INDEX" --gpu "$GPU_UUID" \
  --numa-node "$NUMA_NODE" --guard "$SCRATCH/guard_src/guard.py" \
  --bench "$SCRATCH/bench" --oracle "$SCRATCH/oracle"
python3 "$TASK/analyze.py" "$SCRATCH/e1" "$SCRATCH/cpu_oracle.bin" "$SCRATCH/curated"
```

All output directories must be new; the scripts fail rather than overwrite
previous evidence. The generation paths are exact pins, not an adaptation to
arbitrary upstream versions. A different machine/toolkit requires a fresh
contract and remeasurement; binary hashes need not reproduce across toolchains.
The query files are fixed and disjoint from the explicitly inventoried prior
fixtures, not certified disjoint from every undisclosed historical query.

`probe.py` runs a bounded first-two-query sanitizer/NSYS subset under the same
guard. `--memory-only` disables API-error reporting and must never be relabeled
as a strict API pass. It is a localization tool, not E2 admission. Its timeout
receipt is a failed observation. Reference-only small tests do not validate
native-tree small/N<K, ties, boundary pruning or dynamic invalidation.

## Evidence layout

* `evidence/e1_v7/`: final full outputs, per-query work, thresholds, raw
  uninstrumented timing CSVs and private-raw hashes. Instrumented timing is
  excluded. Exact visit bitset equality is checked in the private replay;
  the public threshold CSV also retains the non-cryptographic digest.
* `evidence/e1_v6/`: prior representation, preserved independently.
* CPU tree/work-model/reference records: distinguish static inventory,
  raw-FP32-bound CPU model and independent exhaustive correctness reference.
* Probe/NSYS records: diagnostic attribution only, no DRAM or SM-utilization
  measurement or formal performance ranking.

The E1 timing denominator starts with an already-resident database query ID
and ends with full K IDs/FP64 scores Host-ready. Allocations, memo clearing,
candidate maintenance, native sorting, synchronization and output copies are
charged. The external complete Host-query-vector submission scope requested
for formal E3 has **not** been implemented or admitted. Never use the numbers
here as that denominator, or multiply them by unrelated historical speedups.
