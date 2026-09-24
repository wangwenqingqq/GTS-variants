# Original GTS: exact 8-bit SIFT format on RTX 4090

The SIFT1M file used here contains 1,000,000 rows of 128 finite integer
coordinates, all in [0,218]. A separate scan of every coordinate verified
this before conversion. Thus `uint8` stores this fixture losslessly; direct
signed `int8` does not represent values above 127. The original GTS source
uses `#define short float`, so its nominal `short*` vector buffer is FP32.

## Controlled comparison

All binaries derive from the pinned original GTS query-stage diagnostic source.
Both FP32 and `uint8` variants share the **same** range-query source: in the
internal-node and leaf L2 paths, `pow(d,2)` is replaced by an explicit FP32
multiply and `pow(sum,0.5)` by `sqrtf`. Both cast coordinates to FP32 before
subtraction. This established arithmetic specialization is a common comparator,
not a claimed new contribution. The variant switch alone changes
`#define short float` to `#define short unsigned char`; it changes data storage
and the type used by the unchanged index build. The separate `uint8+DP4A`
probe uses three unsigned packed-byte dot products per four coordinates to
compute `||a-b||² = ||a||² + ||b||² - 2a·b` in the leaf, followed by `sqrtf`.
It retains the common internal-node path. No tensor-core kernel was used.

The same RTX 4090, physical GPU0 UUID
`GPU-015723f9-1f4b-502b-017d-4530ee371ad9`, CUDA 12.8, driver 580.159.04,
served every comparison. No compute process was present before/after each
fresh-process run; the per-device advisory lock was held. The host/GPU were
otherwise shared. All variants passed the independent full-table integer
range-count oracle in their check runs and each timing process. `uint8` and
`uint8+DP4A` passed `compute-sanitizer --tool memcheck` at N=65,536;
the `uint8` scalar variant also passed at SIFT1M.

For N=65,536, resource-adapted MAX_H=5 and the bounded 256 MiB query workspace were
used. Three cyclic process triples measured Q32/r300; six cyclic triples
measured Q128/r500. Each process ran one checked query, three checked warmups,
then eight retained complete queries. All timings start at query dispatch and
end after CPU count delivery; loading, index construction and oracle are out of
timer. Raw samples are [Q32/r300](byte_sift65k_q32.json) and
[Q128/r500](byte_sift65k_q128.json).

| SIFT65,536 shape | FP32 full ms | `uint8` full ms | `uint8+DP4A` full ms | Paired FP32/`uint8` speedup |
|---|---:|---:|---:|---:|
| Q32/r300 | 9.082 | 8.995 | 9.007 | 1.017× (3 triples) |
| Q128/r500 | 19.182 | 16.809 | 18.002 | 1.138× (6 triples) |

The Q128/r500 leaf stage falls from 7.069 to 4.759 ms (paired 1.449×).
The DP4A version is slower than plain `uint8` scalar L2 on that shape;
packing bytes into an instruction is not itself an end-to-end win.

For SIFT1M, both builds use MAX_H=6 and the same 256 MiB query workspace.
A common harness reads the original `.fvecs` file into each build's resident
vector buffer; input parsing remains outside the timed query. Q32/r500 was
checked against the complete 1,000,000-point integer oracle. Six fresh-process
pairs alternate FP32/`uint8`, with eight retained queries per process. The raw
observations are in [SIFT1M samples](byte_sift1m_q32.json).

| SIFT1M Q32/r500 | FP32 | `uint8` | Paired FP32/`uint8` ratio |
|---|---:|---:|---:|
| Complete query, median process ms | 173.922 | 119.635 | **1.454×** [1.452, 1.456] |
| Leaf stage, median process ms | 75.517 | 21.285 | **3.543×** [3.529, 3.552] |

Ratios are geometric means of six paired process medians; intervals are
seed-0, 10,000-resample bootstrap 95% intervals over those six pairs.
The complete-query reduction comes almost entirely from the measured leaf
stage reduction. This diagnoses the effect's location, but does not distinguish
cache behavior, memory transactions, occupancy or instructions inside that
kernel. No hardware-counter attribution was collected in this campaign.

These results establish a lossless SIFT range-query opportunity on this 4090
workload. They do **not** certify GIST/other real-valued data, kNN, insertions,
deletions, rebuilds, result IDs, concurrency, arbitrary radii or other GPUs.
The original FP32 source and earlier reports remain unchanged; this experiment
does not promote the scratch variants as a production implementation.

## Format decision

- `uint8`: exact for this SIFT1M file; the measured scalar variant wins.
  Centering each value by 128 would also allow signed `int8`, but adds no
  information and was not benchmarked.
- FP8 E4M3: supported by SM89 tensor-core MMA, but a 4-bit significand cannot
  retain every SIFT integer. The file contains 213 distinct coordinate values,
  including both 128 and 129; those two collapse under direct E4M3 rounding.
  Using it for tree pruning or final range membership would require an
  error-bound/refinement design to avoid false negatives.
- FP8 E3M4: the IEEE-like format in the StableHLO proposal has a maximum finite
  value of 15.5 before scaling; NVIDIA's exposed FP8 MMA formats are E4M3 and
  E5M2. An E3M4 software representation is therefore not a native 4090 FP8 MMA
  input and also cannot losslessly encode all 213 observed coordinate values.

Source format references: [NVIDIA CUDA FP8 types](https://docs.nvidia.com/cuda/cuda-math-api/cuda_math_api/group__CUDA__MATH__FP8__MISC.html),
[NVIDIA cuBLASDx supported MMA types](https://docs.nvidia.com/cuda/cublasdx/requirements_func.html),
[StableHLO E3M4 proposal](https://fuchsia.googlesource.com/third_party/github.com/openxla/stablehlo/+/refs/tags/v1.8.8/rfcs/20240808-f8E4M3_f8E3M4.md).

Provenance: the SIFT1M `.fvecs` file SHA-256 is
`21f66e2975057b5728ba56de1c825bac4f4d89d596609ae985741c6242631816`;
the generated Q32 ID list is
`563c24c15534f0669f3e09369a43b4986099e06923413339050c070ec6c68dda`.
The SIFT1M FP32 and `uint8` binary SHA-256 hashes are
`37910a8627d8296a528b5e313f4bf29693ce9466c052846a0fae1006b447f0d1`
and `556843ae32bded80b25350da63cbafd522507a2c7e54c8a298d0875845c149c1`.
Their `search_v2.cuh` bytes are identical (SHA-256
`d50cd31510ae682c3b0c67c1b64d992d32d07904dcc7d7869f2f3768a32025be`).
