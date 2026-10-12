# Source-level cost model, not performance

Fixed shape: N=1,000,000 physical rows, D=960 FP32, five captured scoring levels, tree order 10, 111,111 allocated nodes. Account the scoring/refit overlap only. Keep native boundary recomputation, native sort, host validation, allocator/publication and region/live refresh common unless explicitly redesigned and proved.

## Per aligned level

| Item | B0 whole scoring + refit | Strong C2 whole scoring + bound | C2 minus B0 |
|---|---:|---:|---:|
| Coordinate sweeps for overlap pairs | 2 | 1 proposed shared traversal | -1 |
| Object coordinate operand reads | 7.68 GB | 3.84 GB | -3.84 GB |
| Pivot coordinate operand reads | 7.68 GB | 3.84 GB | -3.84 GB |
| Combined coordinate source operands | 15.36 GB | 7.68 GB | -7.68 GB |
| Native nominal scoring stream | unchanged | unchanged | 0 |
| Directed FP64 subtract calls | 1.92 billion in refit | 1.92 billion in scoring | 0 total; moved stage |
| Directed FP64 multiply calls | 1.92 billion in refit | 1.92 billion in scoring | 0 total; moved stage |
| Directed FP64 add calls | 1.92 billion in refit | 1.92 billion in scoring | 0 total; moved stage |
| All six directed calls/coordinate | 5.76 billion | 5.76 billion | 0 total |
| Directed FP64 roots | 2 million | 2 million | 0 total |
| Global per-pair endpoint capacity | 0 | 16,000,000 B | +16 MB peak |
| Endpoint writes | 0 | 16,000,000 B | +16 MB |
| Endpoint reads | 0 | 16,000,000 B | +16 MB |
| Added N-entry owner map | 0 | 0 | 0 |
| Added sort endpoint payload | 0 | 0 | 0 |
| Child/node extrema work | present | present | ownership/schedule changes, no deletion |

GB/MB above are decimal. There are 960 million coordinate iterations per level. The two four-byte coordinate operands give 7.68 GB per sweep, **not measured DRAM bytes**: pivot caching, repeated object caching, coalescing, shared loads, page movement and compiler lowering remain unknown. The input payload itself is 3.84 GB. Min/max/abs/sign tests, nominal pow lowering and loop/address overhead are not included in the six directed-source-intrinsic count; it is not an instruction/throughput ledger.

Relative to the scoring stage alone, C2 adds the 5.76-billion directed intrinsic calls and two-million roots; relative to B0's **combined pipeline**, it merely moves them. C2 does not remove the full second arithmetic stream. Interleaving safe operations may increase registers, reduce residency or induce spills; no resource or speed claim follows from operand sharing.

## Whole rebuild and lifetime

Five levels remove 38,400,000,000 coordinate operand bytes in the proposed shared traversal and add 160,000,000 endpoint read/write bytes. Their **net source-operand tally only** is 38,240,000,000 B saved before other work; this is not a bandwidth forecast, actual memory traffic, or a claim that C2 is faster. Peak sidecar payload is **16 MB**, reused after each level is consumed, not an 80 MB/5M-pair cache. Separate eight-byte-aligned lower/upper arrays have no per-element padding; allocation metadata and alignment rounding remain unknown.

Native key array: 8,000,000 B. Persistent physical order: 4,000,000 B. Its existing `id_list[s]` enables physical-row-indexed endpoint gathers; no extra endpoint permutation or owner map is necessary. Sorted-slot order loads are 4 MB per complete gather traversal; B0 also loads the physical order for refit, so this is not automatically new traffic. Randomized endpoint gather locality remains a cost uncertainty.

Final bounds: `2*111111*8 = 1,777,776 B`, persistent and common. B0 refit shared lower/upper scratch is 4,096 B per node block; C2 register/shared/segmented reduction scratch depends on the unimplemented mapping and is not asserted zero. Native sort scratch is unknown and kept common because key/value types and algorithm stay unchanged. An API-based segmented reduction could add offset/scratch allocations; the strong control instead permits split-local consumption of existing descriptors.

## Bound stage is not the whole refresh wrapper

B0 has one post-build numeric refit launch per rebuild and a following device synchronization (`numeric.cuh:82`). C2 removes that **distance-refit kernel**, but bound reductions/readiness still have to occur before publication and before sidecar overwrite. Split-local fusion can avoid separate reduction launches; a separate per-level reducer may add launches. Existing score/split synchronizations and host-observable `thrust::reduce` are not automatically removed. Do not claim a fixed total launch or synchronization delta.

`refresh_bounds` also synchronizes, releases/allocates bound state and validates final structure. Native nodes/empty/order D2H payload is `20*111111 + 4*111111 + 4*1000000 = 6,666,664 B`; its host vectors add seen/cover, totaling 14,666,664 payload bytes. Retain checks and epoch/base guards. `update.cuh` subsequently performs region/live refresh; no deletion is claimed for those. Diagnostic/audit copies are conditional and outside this core accounting.

Native split boundary remains 111,110 coordinate-pair tasks (106,665,600 D960 coordinate iterations) per rebuild, common to B0/C2/Z. Its float accumulator differs from scoring's double accumulator; do not substitute the score key or interpret its small overlap as permission to remove it.

**B1 Z minus strong C2: zero normalized dependency or required payload delta.** Execution-specific register, launch or layout effects are unknown, not measured wins. No milliseconds, occupancy estimate, roofline speedup or acceptance threshold is calculated in this record. [Machine counts](evidence/COSTS.json) are independently recomputed by the validator.
