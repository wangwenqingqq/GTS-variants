# Exact packed-bit Tanimoto scan: implementation and local validation

## Status and freeze boundary

This is a new, local-only implementation for the required E3 ChEMBL S arm.
No existing frozen source, evaluator, workload or GPU artifact is changed.
The parent campaign must freeze source/input hashes and the policies below
before any GPU execution. Compilation, sanitizer, full-output correctness,
and paired timing are distinct future gates. No benchmark result is claimed.

## Design card before implementation

- **Target and hypothesis:** one admitted sm_120 GPU; exhaustive 2048-bit
  popcount is a memory/selection workload. This is a baseline implementation,
  not a novelty claim or optimization campaign.
- **Input:** little-endian int32 `[rows, 2048]` followed by exactly
  `rows*32` little-endian uint64 words, no padding or trailing bytes. Base N is
  an available prefix, with IDs `[0,N)`. Query input is separate and no query
  becomes an indexed object. Source-float-to-bit conversion and exact-value
  holdout isolation belong to the parent input freeze, not these programs.
- **Metric:** FP64 `1 - popcount(A&B)/popcount(A|B)`; when the union is zero,
  both fingerprints are empty and distance is explicitly **0**. Exactly one
  empty fingerprint gives distance1. This empty policy requires explicit
  adoption in the E3 phase amendment; it is not asserted to match an absent
  archived metric8 branch.
- **Shape:** E3 ChEMBL N=50,000, k8, Q=1,32,full1000; generic available
  int32 N is validated, but not a resource/capacity guarantee. Internal GPU
  query tile32 does not change the outer full-Q timing denominator.
- **Ownership:** one CUDA thread owns one `(query, indexed fingerprint)`
  distance. Each thread uses private integer intersection/union accumulators
  in `[0,2048]`, reads 32 uint64 pairs, and writes one FP64 distance.
- **Geometry and state:** 128 threads per block, a one-dimensional grid over
  `tile_queries*N` pairs, size_t indexing. No shared memory, TMEM, async copy,
  warp/cluster communication, custom barrier, cross-thread accumulator or
  persistent pipeline state. No swizzle or bank-conflict assumptions.
- **Ready graph/live set:** resident base upload completes before queries;
  host query copy -> tile H2D -> popcount scan -> CuPy top-k -> complete IDs
  and distances D2H. Every tile's results are host-ready before their CPU
  concatenation; the next overwrite cannot precede the blocking D2H.
- **Timing:** dataset loading, resident-base upload, kernel compilation and
  warmup are outside retained query timing and reported separately. The
  timer includes contiguous host-query materialization, H2D, exhaustive GPU
  distance scan, CuPy top-k, both complete output transfers, and host assembly.
- **Work:** `Q*N` pair distances and `32*Q*N` 64-bit intersection/union popcount
  pairs. Logical base payload volume is `Q*N*256` bytes, not measured DRAM
  traffic; caches, selection, query/results and temporary traffic are excluded
  from that logical-byte label. No throughput prediction is promoted to data.
- **Verification ladder:** local independent CPU tests -> target compile ->
  bounded memcheck/synccheck -> every-output CPU-oracle audit -> frozen paired
  host-ready timing. Any missing gate leaves the GPU path unvalidated.

## Files owned

- `bit_scan.py`: custom exhaustive CUDA 64-bit popcount scan plus CuPy selection;
  no native-library proxy naming.
- `bit_oracle.cpp`: independent exhaustive CPU top10 with deterministic
  `(distance, ID)` ordering, <=32 OpenMP workers, strict packed-data validation,
  and atomic, non-overwriting publication of the binary oracle.
- `audit_bits.py`: independently recomputes returned/oracle-ID distances using
  Python arbitrary-precision integer `bit_count`; enforces tie-aware kth
  threshold, complete outputs, unique IDs, valid IDs and consistent distances.
- `test_bits.py`: local fixture, malformed-input, oracle and audit checks.

## Integration responsibilities retained by the parent

Freeze converted ChEMBL data and its bit order/threshold semantics; prove query
isolation; compile under guard; record source/binary hashes; run target-GPU
correctness and sanitizer gates; preserve every contract workload and raw log.
P/G lack an approved metric8 branch and must not be represented as supported by
this new S implementation. No P/G kernel change is included.

## Local check

`python3 test_bits.py` requires Python >=3.10 (`int.bit_count`) and compiles the CPU oracle into a new task-local temporary
directory and runs independent high-entropy, sparse, tie, zero, prefix,
invalid-header/payload, invalid-ID, duplicate-ID and output-preservation checks.
It never imports installed CuPy or invokes CUDA, SSH, NVML or GPU tools. The
scan host-flow check uses an explicitly labeled NumPy mock and is not GPU
evidence.

## API compatibility reference

CuPy's `lexsort` does not support the NumPy-style `axis` argument. This scan
therefore uses supported `argsort(..., axis=1)` on selected distances; ties may
choose any distinct qualifying IDs under the frozen tie-aware rule. See the
[official CuPy sorting implementation](https://github.com/cupy/cupy/blob/main/cupy/_sorting/sort.py).
This source check does not replace a build/run with the target CuPy version.

## Local validation result

On 2026-10-26 UTC, `python3 test_bits.py (Python >=3.10)`
(Python3.13.12, NumPy2.4.3, system C++17 compiler, no OpenMP in this local
smoke build) passed **10 tests**. The machine's `/usr/bin/python3` is3.9 and
cannot provide `int.bit_count`; use the verified >=3.10 environment. CPU
OpenMP source caps workers at32, but a target OpenMP build remains untested.
The NumPy-mock scan check covered Q1, Q32 with a ragged tail, and a full35-row
batch internally tiled32+3; it provides no CUDA correctness or timing evidence.
