# Original GTS: SIFT storage-format control

The pinned original GTS source has `#define short float` in `config.cuh` (SHA-256
`788987154529da5660c2df912a81abd4c135efad5536a97ef725aa350ac199fc`).
Thus its apparent `short*` vector storage is actually FP32. This corrects the
earlier literal reading of the declaration. The FP64 work observed in the
PRO 6000 profile comes from the compiled general `pow` path, not from FP64
vector storage.

This bounded test changed **the repository's data-format switch only**: the
comparison build comments out that macro, making SIFT coordinates actual
16-bit `short` values. This also changes load conversions and may change
mathematical overload resolution; it does not isolate memory bandwidth.
Both builds make the same harness-only declaration `short* x` (which expands to
`float*` in the FP32 build). The original `pow` arithmetic, query stages,
launches, tree parameters, wait policy and 256 MiB workspace remain in both.
The first 65,536 SIFT vectors have 128 integer coordinates in [0,255], so the
conversion is lossless for this fixture. It is not lossless for general GIST or
other real-valued vectors. Each build passed the independent full-table integer
range-count oracle before timing and in every timing process.

The test ran on `4090-left`, physical GPU0 UUID
`GPU-015723f9-1f4b-502b-017d-4530ee371ad9`, RTX 4090, driver 580.159.04,
CUDA 12.8, `sm_89`. Before and after each run, `nvidia-smi` listed no compute
process; the per-GPU advisory lock was held. The GPU had a display/other
non-compute memory allocation, and the shared host was not exclusive. Both
variants used the same GPU and fresh processes. Three pairs alternated
FP32/short, short/FP32, FP32/short. Each process built the index, passed one
checked query and three checked warmups, then timed eight complete queries.
The timed denominator is query dispatch through CPU count delivery; it excludes
loading, index construction, warmup and oracle. The leaf stage is separately
instrumented. Raw per-query observations are in [samples.json](samples.json).

| Pair | FP32 query median ms | short query median ms | FP32 leaf median ms | short leaf median ms |
|---:|---:|---:|---:|---:|
| 0 | 781.343 | 780.427 | 740.323 | 739.594 |
| 1 | 781.522 | 780.673 | 740.373 | 739.674 |
| 2 | 780.774 | 780.803 | 739.641 | 739.634 |

The geometric mean of paired process-median FP32/short ratios is **1.00074×**
for complete query and **1.00065×** for the leaf stage. This is not a material
speedup. Three pairs are too few to claim that the true effect is exactly zero.
The narrower conclusion is that this lossless FP32-to-short switch did not
resolve the observed CPU-wait/leaf-kernel latency on this 4090 workload. It
does not test a redesigned integer-distance kernel, post-`pow` arithmetic,
SIFT1M, GIST, kNN, or update workflows. It does not transfer the 4090 times to
the earlier PRO 6000 profile.

The FP32 and short binaries have SHA-256
`faf8c0d7169e56c8a5938806b88547b558c4c0f6ede56d6ae1a8576993642a4c`
and `45a86431032e95d687078ecfcb7deead1dfb644b16c6c217a0ce4e4cb42af58a`.
The SIFT fixture and Q128 query file have SHA-256
`9f52f677707001aef51fe464937dd1e9ef4bce706f8944d4510250bc2db85868`
and `fec8b53defacf4dc385ef310a754b50d1b6c43661f705367b6ea030a4aba6998`.
