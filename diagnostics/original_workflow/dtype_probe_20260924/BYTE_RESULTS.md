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

## Load, build, and first query

On 2026-09-25, a follow-up measured the continuous path from reading SIFT1M
and Q32 through index construction and its GPU synchronization to delivery of
the **first** Q32/r500 query's counts to the CPU. The same FP32 and `uint8`
scratch variants, data, 4090 GPU0, MAX_H=6 and query source were used. Only
phase timers were added to the scratch harness; its full-table integer oracle
was moved after the first query so that validation did not enter the timed
path. Every process still passed that oracle. Six fresh-process pairs alternated
variant order under the GPU0 lock, with no other compute process observed.
The data file was read from a warm host file cache. Process launch, CUDA
context initialization, validation, later warmups and later queries are outside
this timing.

| SIFT1M Q32/r500 phase | FP32 mean ms | `uint8` mean ms | Difference ms |
|---|---:|---:|---:|
| Load data and query IDs | 184.954 | 165.401 | 19.554 |
| Build index and synchronize | 2677.523 | 2615.534 | 61.989 |
| First complete query | 170.727 | 117.153 | 53.573 |
| **Load + build + first query** | **3033.204** | **2898.088** | **135.116** |

Thus this measured full path improves by **1.0466×**, or **4.45% lower
latency**; a seed-0, 10,000-resample bootstrap 95% interval over the six
paired ratios is [1.0445, 1.0495]. Index construction accounts for most of
the elapsed time, so the 1.454× steady-query speedup does not transfer to a
one-query cold index lifecycle. Raw phase samples are in
[full-flow SIFT1M samples](fullflow_sift1m_q32.json). The `process_s` field
in that file includes the diagnostic oracle and later queries and is **not**
the full-flow benchmark metric. The follow-up FP32 and `uint8` binaries have
SHA-256 hashes `3a979d489f56317c5a7cc15a7a736129e928573a906437abc2448fbdedc79aba`
and `f135ea46d017f03027cc47a772e2e551b22ab3bfd155f0eb4a98b3eb529d5437`.

## One leaf node per block: 512 versus 32 threads

A separate 2026-09-25 control changed exactly one scratch-source launch:
`dataProcessRnn<<<block_num, THREAD_NUM>>>` to
`dataProcessRnn<<<block_num, 32>>>`. `block_num` still equals the number of
candidate leaf nodes, so **one block still owns one node**; this does not pack
multiple nodes into a 512-thread block. With MAX_SIZE=20, 32 threads still
cover every point/flag slot. Build, other query stages, arithmetic and data
format were unchanged within each comparison. On the same idle-checked 4090
GPU0 under its lock, three fresh-process pairs per format alternated launch
order. Every run passed the independent SIFT1M full-table integer count oracle.
Each process retained eight complete Q32/r500 queries after three warmups.

| SIFT1M Q32/r500 | 512-thread mean of process medians | 32-thread mean of process medians | Paired 512/32 speedup |
|---|---:|---:|---:|
| FP32 complete query | 173.904 ms | 170.337 ms | 1.021× |
| FP32 leaf stage | 75.458 ms | 72.377 ms | 1.043× |
| `uint8` complete query | 119.810 ms | 115.844 ms | 1.034× |
| `uint8` leaf stage | 21.265 ms | 17.825 ms | 1.193× |

All six complete-query pair ratios favored 32 threads, but the measured
end-to-end query benefit is modest: 2.05% lower latency for FP32 and 3.31%
for `uint8`. No build-plus-query or multi-node-per-block benefit is implied.
Raw observations are in [leaf32 SIFT1M samples](leaf32_sift1m_q32.json).
The FP32 and `uint8` 32-thread binary SHA-256 hashes are
`e541ef604e2f213a0d93bc3c29300dcd890b627e7686423953824160642d7e7e`
and `fe5f13eaa0a6cc8660ae3027d93d1f7b0877ec4be189592c1d8e5c22250cb976`.

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
- FP8 E3M4: CUDA 13.1 Tile IR lists `e3m4` as a hardware-accelerated type on
  Blackwell (including the RTX PRO 6000's `sm_120`), but not on Ada/RTX 4090.
  The installed CUDA 13.1 `tileiras` on pro6000-8 also contains
  `builtin.f8E3M4`. This corrects the earlier inference from CUDA's usual FP8
  APIs that E3M4 is merely a software type on all NVIDIA GPUs. The Tile IR
  documentation is internally inconsistent: its 13.1 type/support tables say
  E3M4, while its FP8 operation and bytecode tables say E4M3FN; later type
  documentation also says E4M3FN. The exact encoding and whether a GTS kernel
  lowers to native FP8 instructions on that GPU have not been verified. Direct
  E3M4 storage cannot be assumed to preserve all SIFT coordinate values or
  exact range-query results. No pro6000-8 GPU workload was run for this report.

Source format references: [NVIDIA CUDA FP8 types](https://docs.nvidia.com/cuda/cuda-math-api/cuda_math_api/group__CUDA__MATH__FP8__MISC.html),
[NVIDIA cuBLASDx supported MMA types](https://docs.nvidia.com/cuda/cublasdx/requirements_func.html),
[CUDA 13.1 Tile IR types](https://docs.nvidia.com/cuda/archive/13.1.1/tile-ir/latest/13.1/sections/types.html),
[CUDA 13.1 Tile IR hardware matrix](https://docs.nvidia.com/cuda/tile-ir/latest/13.1/sections/stability.html),
[CUDA 13.1 Tile IR operations](https://docs.nvidia.com/cuda/tile-ir/13.1/sections/operations.html),
[CUDA 13.1 Tile IR bytecode](https://docs.nvidia.com/cuda/archive/13.2.0/tile-ir/13.1/sections/bytecode.html),
[CUDA 13.3 Tile IR types](https://docs.nvidia.com/cuda/tile-ir/13.3/sections/types.html).

Provenance: the SIFT1M `.fvecs` file SHA-256 is
`21f66e2975057b5728ba56de1c825bac4f4d89d596609ae985741c6242631816`;
the generated Q32 ID list is
`563c24c15534f0669f3e09369a43b4986099e06923413339050c070ec6c68dda`.
The SIFT1M FP32 and `uint8` binary SHA-256 hashes are
`37910a8627d8296a528b5e313f4bf29693ce9466c052846a0fae1006b447f0d1`
and `556843ae32bded80b25350da63cbafd522507a2c7e54c8a298d0875845c149c1`.
Their `search_v2.cuh` bytes are identical (SHA-256
`d50cd31510ae682c3b0c67c1b64d992d32d07904dcc7d7869f2f3768a32025be`).
