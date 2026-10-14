# Physical-locality and source-byte ledger

| Item | B0 | O2 | S1 |
|---|---:|---:|---:|
| Nominal selected coordinate payload/object | 16 x 32B = 512B | 512B, information only | 16 x 32B = 512B |
| Actual oracle diagnostic source/object | shared full scan | 3840B | not used by the probe |
| Dataset statistics | 0 | 0 | unchanged 7680B Gate5 moments |
| Selected sector IDs/query | fixed | unpriced per-pair selection | 16 uint16 = 32B |
| Full FP32 query | 3840B | 3840B | 3840B |
| Query moment scores | none | none | 960 FP64 scores + 120 group scores + stable selection, temporary |
| Per-object persistent metadata | 0 | 0 | 0 |
| New moment preprocessing | none | none | none; historical two-pass cost is not repeated |
| Measured GPU DRAM/sectors/latency | NOT_RUN | NOT_RUN | NOT_RUN |

The conditional S1 coordinate model is `512000000 + 3328*survivors` per query.
Selected sectors and complementary 104 sectors contain all 960 coordinates with
no overlap **at the source-payload level**, conditional on selected values being
retained without reread. It is conservative relative to additional progressive
coordinate pruning, not an upper bound on physical complete-search traffic.

A bit-identical full-score reconstruction would need the selected coordinates
retained (512B/survivor in FP32 form), then recomputed in original dimension order,
or reread. Register/shared-memory pressure, shared loads/stores, spills, FP64
recomputation and any fallback rereads are **unknown and unpriced**. A single
retained partial scalar is not sufficient to assert original-order final bits.
The model's numeric gate remains unchanged; its scope is conditionally priced
coordinate source bytes, not an implemented exact-result pipeline.

Future costs that are not assumed zero:

| Cost | Current status |
|---|---|
| L2 line amplification / cache reuse or eviction | UNKNOWN_NOT_MEASURED |
| Warp transaction coalescing and memory-instruction issue | UNKNOWN_NOT_MEASURED |
| Address-generation and selected-ID broadcast | UNKNOWN_NOT_MEASURED |
| Warp scheduling / occupancy / retained-value storage | UNKNOWN_NOT_MEASURED |
| Survivor compaction, IDs, masks and continuation state | UNKNOWN_NOT_MEASURED |
| Second-stage reads and exact original-order reconstruction | MODEL_ONLY_NOT_IMPLEMENTED |
| Query/metadata transfers, output, launches and host waits | UNKNOWN_NOT_MEASURED |

The [NVIDIA guide](https://docs.nvidia.com/cuda/archive/12.9.1/cuda-c-best-practices-guide/index.html#coalesced-access-to-global-memory)
Section 9.2.1 motivates 32B access units. A future device payload base must be
aligned to at least 32B; 3840B row stride then preserves group alignment. The
unchanged file's 12B header means the observed CPU pointer is **12 mod32**. No
relocation, data padding/reordering or CUDA allocation is done; alignment is a
conditional device-geometry assumption, not a CPU traffic observation.

Raw proof arrays (512MB A plus 256MB B) and frozen full scores are validation-only.
Operational process times include unequal qualification, hashing and export work;
they are not query latency and must not be compared as performance.
