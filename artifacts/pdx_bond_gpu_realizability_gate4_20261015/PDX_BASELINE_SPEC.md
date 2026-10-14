# Source-exact reconstruction and explicit contract adaptation

**This is an adversarial baseline, not a novelty claim.** The official publication
implementation is the `sigmod` branch at
`fdc62f2d22b3793060abf633cb5407438c7f739b`, not the evolved `main` layout.
Source hashes and immutable links are in SOURCES.json. No upstream code is
executed or redistributed here. The reimplementation reads the existing raw
FP32 data through the preserved diagnostic harness.

## 1. Query priority and aggregation

The relevant official routines are
[GetDimensionsAccessOrder, lines223–305](https://github.com/cwida/PDX/blob/fdc62f2d22b3793060abf633cb5407438c7f739b/include/pdx/pdxearch.hpp#L223-L305)
and [global mean construction, line157](https://github.com/cwida/PDX/blob/fdc62f2d22b3793060abf633cb5407438c7f739b/python/pdxearch/index_base.py#L157).
Use the global original-database FP32 mean, not survivor/nonhit statistics:

`mu = data.mean(axis=0, dtype=FP32)`

Each coordinate priority is the absolute FP32 subtraction `abs(q[d]-mu[d])`.
Each zone rank is its sequential FP32 priority sum divided by its length
(double division, rounded back to FP32). This is **not squared distance**,
variance, second moment, or our prior moment score. The per-dimension
`DISTANCE_TO_MEANS` path provides the same underlying absolute-deviation criterion.

## 2. Actual zone schedule, not an invented full rank sort

The native comparator uses descending zone rank, with no secondary tie key.
Take the top3 zones using `std::partial_sort`; then physically sort the selected
IDs ascending and the remaining27 IDs ascending. Visit those two groups in
that order, with coordinates ascending inside each zone. Ties inherit the
frozen standard-library algorithm; retain observed orders and cutoff ties.
The expression `ceil(zones.size()/8)` uses integer division first, so30 zones
select3, **not4**. Do not substitute a full descending order of all30 zones.

## 3. Confirmed fixed32 boundary adaptation

The upstream last interval is `[928,959)`, exclusive of959. Dimension959 remains
at the final initialized order slot. Thus its literal output still covers all
960 dimensions; this is **not proof of a missing coordinate or an unsafe search**.
It does not, however, form30 complete32-dimensional zones.

The human confirmed the following single adaptation on2026-10-15, before any
population measurement: use `[32*z,32*(z+1))` for every zone, preserving the
official3-zone selection, score, and two-group physical schedule. This is a
**fixed32 contract adaptation, not a byte-for-byte upstream transplant**.
The upstream automatic zone width depends on CPU vector-group size; the present
plan fixes32 explicitly. No group-size or ordering sweep is admitted.

## 4. Exact predicate and authority

The [official predicates](https://github.com/cwida/PDX/blob/fdc62f2d22b3793060abf633cb5407438c7f739b/include/pdx/pdxearch.hpp#L540-L566)
retain candidates whose partial distance is below the current kNN threshold.
The frozen **range** contract instead includes equality: original-coordinate
ordered-FP64 full score `<=T`. Its safe rejection is a **strict** partial-sum
comparison against the outward guard in NUMERICS.md. A reordered partial
sum is not accepted as an original-order full score.
All32M original full scores are recomputed and checked bitwise against the
preserved authority during this diagnostic. This validation work is not a
search implementation or a free GPU output path.

## 5. Warmup and active positions

[PDX paper, §4–5, PDF pages11–12](https://ir.cwi.nl/pub/35044/35044.pdf), and
[official Start/Warmup/Prune](https://github.com/cwida/PDX/blob/fdc62f2d22b3793060abf633cb5407438c7f739b/include/pdx/pdxearch.hpp#L568-L670),
describe first-group full evaluation to initialize a kNN threshold, dense
warmup before sparse positional pruning, and a surviving-position array.
Gate4 already has a fixed range threshold. It preserves the planned
128/256/512/960 staged compaction rather than reproducing the CPU scheduler.
The CPU logical diagnostic checks after each coordinate within the zone order;
source accounting separately rounds reads to the four frozen stages.

## 6. Layout, preprocessing, and update scope

The [official index writer](https://github.com/cwida/PDX/blob/fdc62f2d22b3793060abf633cb5407438c7f739b/python/pdxearch/index_base.py#L155-L205)
stores static groups in a vertically transposed layout. The
[BOND wrapper](https://github.com/cwida/PDX/blob/fdc62f2d22b3793060abf633cb5407438c7f739b/include/pdx/bond.hpp)
does not rotate the query. Gate4 defaults to the single raw FP32 representation;
any necessary alternative layout, conversion, or maintenance must be charged.
The mean is static preprocessing; online priority, sort, and order transfer
must be inside future Host-ready timing, with no cached test orders.
No dynamic implementation or update-benefit claim is admitted this round.

[BOND, §4.3–5.1, PDF page5](https://ir.cwi.nl/pub/10425/10425D.pdf) supplies the
historical partial-distance and ordering context. Its stronger sum-statistic
bounds and decreasing-query criterion are not silently substituted for PDX's
absolute-distance-to-means zone path.
