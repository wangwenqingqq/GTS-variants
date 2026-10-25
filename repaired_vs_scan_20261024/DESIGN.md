# Implementation/ownership card before formal measurements

Target: RTX PRO 6000 Blackwell sm_120, CUDA 13.1.115, driver 590.48.01.
This describes the composed implementation; it is not a performance result.
Dataset/query/radius/output contracts remain in CONTRACT.md and AMENDMENTS.md.

## Roles, layouts, and work

| Arm | Query dispatch | Distance work | Result handling |
|---|---|---|---|
| A | Serial calls to pinned original Update path | Original full-table Words DP / original float32 L2 | Original allocation/count/scan/projection, CPU canonicalization |
| R | Serial batch-one Graph replays | Same leaf arithmetic; multi-CTA node traversal | Fixed workspace, parallel candidate reduction/scan, fused stable selection/projection, fixed-capacity D2H |
| S | Native flattened Q*N grid, 128 threads/CTA | Existing rolling-row exact edit kernel / flat 2D float32 L2 | Native CUB flagged selection, actual-count full output D2H; input order is already canonical |
| X | Native ArborX CUDA BVH with Q predicates | Native double 2D geometric predicates on float32 source coordinates; float32 output-distance projection | Native CRS output, complete projected IDs/distances D2H, CPU canonicalization |

A/R native output is checked byte-for-byte before canonicalization. Every arm's
public complete ID/distance/count output is independently checked against the
frozen CPU oracle outside the timer. Q is a serial host bundle for A/R, native
batching for S/X; the serial A denominator is not the old V2 Q32 batch timing.
The optional 32-coordinate L2 early-stop rule cannot help 2D and is not added.

Words uses 109-byte original string slots, lengths <=40. A/R retain the original
M*M integer DP local array. S uses two uint16 rows of length 41. No precision,
fast-math, model, metric or radius tuning is hidden in the composition.

## Buffer ownership and ready/overwrite graph

- R owns one nonblocking stream, one executable Graph, a pinned query ID/count,
  and device flags/candidates/raw hits/output/CUB workspace. Capacity is derived
  from the actual original tree node count; leaf slots are nodes*20.
- The Graph sequence is input copy -> initialize flags -> per-level node walk
  then parent update -> candidate reduction/scan/merge -> leaf payload -> deletion
  prefix -> stable fused selector -> full capacity D2H -> stream synchronization.
- Node CTAs own disjoint child flags. Each level completes before parent flags
  are cleared and the next level is launched. Candidate leaf CTAs own disjoint
  20-slot payload segments; the stream edge precedes selector reads.
- The fused 512-thread selector owns CUB BlockScan scratch. All lanes release
  scratch at each tile's block barrier; a register carry preserves stable order.
- The host rewrites R's pinned query ID only after the previous replay's stream
  synchronization. No buffer or CUB temporary storage is overwritten before its
  last consumer and D2H complete. Capture/instantiate/setup are outside timing.
- S owns a stream, pinned query IDs/count, Q*N flags and raw/selected Hit arrays,
  plus preallocated CUB selection storage. Kernel, selection and count copy share
  the stream; selected output is copied only after the count synchronization.
- Native ArborX/Kokkos owns its BVH and CRS buffers. Queries upload from pinned
  host memory. Native predicates/CRS complete before distance projection and
  output copies; host output is ready before the timer stops.
- A retains original allocation, scalar count and synchronization behavior;
  scratch-only zero-CTA launch guarding is the disclosed empty-query adapter.

## State and traffic hypotheses (not measured wins)

R removes device-side scalar counting stages and launch/allocation control cost,
not point-distance work. Multi-CTA traversal exposes independent nodes but does
not reduce their arithmetic. Fixed-capacity Graph delivery adds/retains transfer
and inactive-grid costs: for 111111 nodes, 2222220 ID/distance slots require
17777764 output bytes per query including count, even for a sparse result.
These are source-derived capacity bytes, not measured DRAM/PCIe traffic.

S's persistent raw/selected/flag storage is 17*Q*N bytes plus CUB workspace and
input. It does not construct a metric tree. The largest tested product is
1,024,000,000 items, below signed-int indexing limits. Native large batching is
not disabled to accommodate R. S/X actual-count output copies are charged.

Static compiler/resource reports, correctness, bounded memcheck/synccheck,
changing-ID Graph replays, separate instrumented work, and six matched process
rounds are distinct gates. Static stack/occupancy is not an end-to-end result.

## Counter interpretation

A/R measure node and leaf metric calls, exact DP update cells or coordinates,
candidate leaf CTAs, and active payload lanes / launched leaf lanes (including
R's inactive-capacity CTAs). S counts actual point calls/cells/coordinates and
active / launched scan lanes. Counts are reset per complete bundle.

Native ArborX's indexable getter is invoked at native primitive-predicate tests;
its instrumented version counts those calls, including separate native count/fill
traversals, not unique points. Output-distance projections are counted separately.
Internal AABB bounds are not point-metric calls. A comparable launched-payload
thread denominator is unavailable for native BVH traversal and is explicitly
null, never fabricated as SM occupancy or inferred from point counts.
