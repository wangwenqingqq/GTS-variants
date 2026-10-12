# Source-supported fixed-query-tile route

**The installed-package source route supports a 64-query compute tile; the original campaign remains `PARTIAL_PADDING`.** This continuation uses CPU-only source inspection and replays existing counters. It adds no GPU launch, benchmark, optimization, or manuscript change. Its parent measurement is commit `0901d7c`.

## 1. Build identity, not just the version label

The live installed cuVS package reports `26.08.01`, build commit `88cd8fedf10bd878f3c1ae28c98c9dfdeb73bb95`. The release tag points to a different commit, `25b1be43a8c127e5ab6d2f29f20c62dbfd3351ab`. All 34 inspected common cuVS source files are byte-identical between those commits; the additional three route/dependency files are pinned at the installed commit. The installed C API and pairwise-fragment headers also match that source byte-for-byte.

Installed RAFT policy/load headers match commit `ebf92684b8a15addcddb43f442a382d528e8bd77`, version `26.08.00`. Both cuVS library ELF hashes were rechecked against the measured registration. These checks bind package provenance and source; **they do not recover the cuVS build's complete dependency lock or the runtime-linked cubin**. Exact hashes and immutable links are in `SOURCE_PROVENANCE.json` and `SOURCES.json`.

## 2. Why this semantic contract selects the JIT route

The source call chain is C `cuvsPairwiseDistance` → row-major FP32 pairwise distance → `L2Unexpanded` → `l2_unexp_distance_op` → pairwise dispatch. That op has no CUTLASS operation, so the compile-time dispatch chooses JIT-LTO regardless of the device's SM80+ capability. It is not evidence of an accidental Blackwell architecture fallback. The selected entrypoint name is `pairwise_matrix_kernel`, matching every prior runtime capture. [Dispatch source](https://github.com/NVIDIA/cuvs/blob/88cd8fedf10bd878f3c1ae28c98c9dfdeb73bb95/cpp/src/distance/detail/pairwise_matrix/dispatch-inl.cuh#L95-L117), [L2 op](https://github.com/NVIDIA/cuvs/blob/88cd8fedf10bd878f3c1ae28c98c9dfdeb73bb95/cpp/src/distance/detail/distance_ops/l2_unexp.cuh).

## 3. The independent tile constant and padded work

The JIT route uses `Policy4x4<float, veclen>` without a batch-dependent policy branch. Its row policy has four accumulator rows/columns per thread and 16 thread rows/columns: **Mblk=Nblk=64, Kblk=32, 256 threads**. With vector length four, double-buffered shared storage is `2 × (64+64) × (32+4) × 4 = 36,864 bytes`, matching all eight measured launches. Alignment and shared storage support vector-four inference; no launcher-key log was acquired. [JIT dispatch](https://github.com/NVIDIA/cuvs/blob/88cd8fedf10bd878f3c1ae28c98c9dfdeb73bb95/cpp/src/distance/detail/pairwise_matrix/jit_lto_kernels/pairwise_matrix_jit.cuh#L159-L208), [RAFT policy](https://github.com/NVIDIA/raft/blob/ebf92684b8a15addcddb43f442a382d528e8bd77/cpp/include/raft/linalg/contractions.cuh#L49-L152).

Query loads outside M are zero-filled. Accumulation still visits the entire register tile; it has no per-output M/N guard. Stores are guarded by the real row/column extents. Thus a partial query tile computes dummy rows without reading nonexistent queries or emitting extra results. This is a source-supported mechanism, not just a fitted `64/B` curve. [Load guards](https://github.com/NVIDIA/raft/blob/ebf92684b8a15addcddb43f442a382d528e8bd77/cpp/include/raft/linalg/detail/contractions.cuh#L182-L214), [Accumulation and stores](https://github.com/NVIDIA/cuvs/blob/88cd8fedf10bd878f3c1ae28c98c9dfdeb73bb95/cpp/src/distance/detail/pairwise_distance_base.cuh#L210-L298).

For this tail-free N1M/D960 input, padded coordinate-pair work is `ceil(B/64) × 64 × N × D`. One difference plus one FFMA gives an executed proxy of three operations per coordinate. The original useful proxy is `N × (3D−1)` per query. Therefore the small 0.0347% discrepancy is exactly explained by `3D/(3D−1)`, not an unexplained timing residual.

`CPU_REPLAY.json` reproduces every captured FADD, FFMA, FMUL, executed proxy and inflation value exactly. It also reproduces block/shared geometry. Grid generation caps total blocks using an occupancy budget; conditioned on the **inferred** 376-block budget from B1, it predicts `[376,1,1]` through B64 and `[188,2,1]` at B128. Halving X while doubling Y is the expected redistribution, not negative evidence against query tiling. This does not retroactively pass the original stricter one-axis predicate. [Grid generation](https://github.com/NVIDIA/cuvs/blob/88cd8fedf10bd878f3c1ae28c98c9dfdeb73bb95/cpp/src/distance/detail/pairwise_distance_base.cuh#L303-L329).

## 4. Why the retained traffic gate fails

Measured main-kernel DRAM **reads per invocation**, not per query, are 3.84096 GB at B1 and 3.84032 GB at B64, versus a 3.84000 GB database payload. Arithmetic padding coexists with database reuse across real queries: division by B makes both per-query curves decrease almost together. A 64-fold database reread is not supported by these observed reads. This is not an L2-cache residency claim; request/sector behavior and all auxiliary traffic are separate questions.

The original arithmetic/total-DRAM separation remains 0.106568 log2, below its retained threshold of one. The source interpretation is stronger, but **`CONFIRM_PADDING` is not granted by changing or discarding that gate after observing results**. Native batched throughput is still not GTSPP tree/workflow end-to-end improvement or a promise of 64× recoverable latency.

## 5. Remaining identity boundary and decision

The source planner links prebuilt LTO fragments and generates an architecture-specific cubin at runtime. No exact linked-module bytes/hash, launch-correlated module load, or full dependency build lock was recovered. Literal entrypoint scans of both pinned parent ELFs returned no match; this does not disprove the JIT route and is not a runtime image acquisition. Keep the prior normalized selected-function hash as instruction-stream evidence, not a full container hash. [Planner/linker source](https://github.com/NVIDIA/cuvs/blob/88cd8fedf10bd878f3c1ae28c98c9dfdeb73bb95/cpp/src/detail/jit_lto/AlgorithmPlanner.cpp#L41-L114).

**Implementation:** unchanged. **Mechanism:** source-supported, not fully module-bound. **Campaign decision:** original `PARTIAL_PADDING`. **Thesis impact:** baseline diagnosis only; no novelty or speedup claim. See `NEXT_STEPS.md` for the remaining bounded acquisition gate.

## CPU verification

```sh
python3 verify.py
python3 verify.py --fetch-sources
```

The second command fetches immutable public source into memory and verifies all 39 hashes and route assertions. Neither command initializes CUDA. Full reference regeneration, sanitizer and GPU timing remain the original campaign's gates, not claims made by these CPU checks.
