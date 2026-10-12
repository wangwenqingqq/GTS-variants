# Numeric contract and lifetime audit

All locations below refer to the 25-file frozen keeper source pinned in INPUT_MANIFEST, not a remembered upstream implementation. No device source was changed in this task.

| Property | TILED scoring | nodeSplit boundary | numeric refit |
|---|---|---|---|
| Input | FP32 (`short` macro aliases float) | same FP32 | same FP32 explicitly promoted to double |
| Subtract | FP32 expression before pow | FP32 expression before pow | explicit FP64 `__dsub_rd` / `__dsub_ru` |
| Accumulation | `double result`; ordinary addition / pow expression | `float result`, rounded at updates | explicit directed FP64 mul and add for both endpoints |
| Root transform | nominal pow(sum,0.5) | nominal pow(sum,0.5), float storage | `__dsqrt_rd` and `__dsqrt_ru` |
| Output | FP64 key: distance/10000 + owner bid*100 | FP32 TN.min_dis | per-pair [lo,hi], reduced into node min(lo)/max(hi) |
| Numeric consumer contract | sorting key | legacy boundary scalar | conservative FP64 interval safety certificate |
| FMA / generated pow | compiler lowering/overload/exact SASS not resolved here | same uncertainty | explicit directed intrinsics in source, not a SASS-throughput claim |

Source arithmetic differences alone establish a producer/consumer contract mismatch. Inverting sorting-key encoding cannot recover FP32 subtraction rounding, accumulation information or the two interval endpoints. This does not establish that every actual nominal number differs, and does not disprove an analytically widened interval or a redesigned arithmetic producer. Those are different contracts requiring separate qualification.

SAME_NUMERIC=0 under the frozen arithmetic/representation definition. Nonself pairs are classified INCOMPATIBLE under that definition, not as measured numerical failures. Self pairs analytically permit a trivial `[0,0]` conversion and are included only as an optimistic admitted-category ceiling. Original refit capture supplies node extrema, not individual endpoint pairs: empirical per-pair value comparison is UNKNOWN. No invented nominal/refit value sample or error histogram is reported.

## Value lifetimes

`indexConstru` allocates a single N-double dis_list, scores and sorts it, then overwrites it at the next level. It does not retain prior levels' outputs. In-place sort moves keys with rows but introduces no persistent pair mapping. At return it frees dis_list, pid_list and split_list. `update.cuh` calls target::refresh_bounds only after indexConstru returns; refresh_bounds releases/allocates its own bounds and recomputes them. Therefore scoring value survival to refit is NO. Last-level keys existed transiently, but are also freed before the consumer.

Boundary TN.min_dis persists through the node tree and matches the captured later tree bits. This lifetime is YES for that scalar, not for every scoring pair and not for a numeric interval certificate. At most it provides a nominal boundary value, not both min/max interval extrema.

See SOURCE_LOCATIONS.json for hashes and exact one-based locations. This is source-flow evidence, not a newly collected memory allocator trace or performance profile.
