# Prior-art and upstream admission (Gate 0)

**Classification: `NO_MATCHING_PATH` in the inspected complete-output FP32 `L2Unexpanded` routes. Select Path C: one minimal diagnostic B1 scan.** This is baseline strengthening, not novelty. The search is scoped, not proof that no direct squared-L2 implementation exists anywhere.

Checked before implementation on 2026-10-12. Immutable references, retrieved-file hashes and retained 404 attempts are in `SOURCES.json`; installed-package bindings remain in the parent provenance artifact. No library is upgraded or patched.

| Check | Finding | Admission consequence |
|---|---|---|
| Installed cuVS 26.8.1 (`88cd8fed`) | `L2Unexpanded` has no CUTLASS op; pairwise dispatch uses JIT `Policy4x4`, M=64. Public C/C++ arguments contain no tile-width selector. | No same-contract existing small-B complete-output path found. |
| Current cuVS main (`24b0b170`) and v26.10.00 (`24ee1bf1`) | Both inspected JIT/dispatch/L2-op routes retain the same policy. No B-small branch in that inner route. | Updating the package is not an established fix; frozen libraries unchanged. |
| Brute-force alternatives | The existing fused small-k branch requires k<=64 and returns neighbors, not all N scores/members. Larger-k general `L2Unexpanded` invokes pairwise. | A finite top-k result is not complete range; no substitution. |
| Issue #277 / small-query issues | #277 concerns outer kNN row/column output tiling and memory heuristics. Current fused/top-1 improvements and NND issues target other outputs/algorithms. | Known outer issue is not a demonstrated fix for this inner L2 contraction. |
| RAFT contraction policies | `Policy4x4Skinny` has M=32 and `Policy2x8<float>` M=16; generic template knobs are not a shipped non-padded B1 distance dispatch. JIT fragments select `Policy4x4`. | The available smaller named tiles still compute >=16 query rows at B1, above the <=1.5 work gate. A new M=1 vendor fragment/policy is not a configuration-only repair. |
| Faiss complete brute-force L2 | `k=-1` reaches all-pairwise L2; its implementation computes norms plus -2*q*x via matrix multiplication. The general direct-distance kernel is for non-L2/non-IP metrics. | Expanded L2 violates the frozen arithmetic contract even if some memberships match. |
| CUTLASS small-M / GEMV | Existing GEMV/GEMM computes matrix products and epilogues, not a drop-in unexpanded squared-difference complete-range route. | Dot-product/norm reformulation and Tensor Core use excluded. Small-M specialization is established engineering, not novelty. |

Primary sources: [current cuVS JIT policy](https://github.com/NVIDIA/cuvs/blob/24b0b17069ee1547354d15847d9c614dd4fb4a43/cpp/src/distance/detail/pairwise_matrix/jit_lto_kernels/pairwise_matrix_jit.cuh), [release JIT policy](https://github.com/NVIDIA/cuvs/blob/24ee1bf1cb17cad0ac611e39643af39ee1870124/cpp/src/distance/detail/pairwise_matrix/jit_lto_kernels/pairwise_matrix_jit.cuh), [brute-force routing](https://github.com/NVIDIA/cuvs/blob/24b0b17069ee1547354d15847d9c614dd4fb4a43/cpp/src/neighbors/detail/knn_brute_force.cuh), [issue 277](https://github.com/NVIDIA/cuvs/issues/277), [RAFT policy](https://github.com/NVIDIA/raft/blob/56b4b2ef9e4b7abec6b2ef122fc24cf9b9d5a3dc/cpp/include/raft/linalg/contractions.cuh), [Faiss complete distance](https://github.com/facebookresearch/faiss/blob/cec5702b0b1c31f242b9d35d5f193b0d80ccd9dc/faiss/gpu/impl/Distance.cu), [Faiss API routing](https://github.com/facebookresearch/faiss/blob/cec5702b0b1c31f242b9d35d5f193b0d80ccd9dc/faiss/gpu/GpuDistance.cu), [CUTLASS GEMV](https://github.com/NVIDIA/cutlass/blob/ee98dbdfd5727085ef86a018009215c2230904e3/include/cutlass/gemm/kernel/gemv.h).

## Cheap kill test and selected mechanism

The thesis “B1 specialization / 64-to-1 query-tile repair is a new contribution” is killed by existing small-M engineering and ordinary direct vector reduction. Do not rescue it with a speedup. The remaining experiment asks only whether a single direct unexpanded scan is a stronger same-contract baseline.

A warp owns one database row; lanes cover the 960 coordinates, FP32 differences/FMA and a warp sum produce one FP32 squared score. No compression, pruning, hierarchy, approximate arithmetic or Tensor Core. Reuse the original inclusive threshold/CUB compaction/field materialization/D2H unchanged. Warp reduction order differs from the native sequential tile accumulation; the inherited field contract is tolerance5e-5 against ordered FP64, **not native bit identity for the candidate**. Membership has no tolerance. Exact native keeper bit identity remains required.

Reopen A/B only with a pinned, callable existing path that meets complete-output unexpanded semantics and the B1 work bound. Search-result absence alone is not proof; retrieved dispatch and API definitions are the admission evidence.
