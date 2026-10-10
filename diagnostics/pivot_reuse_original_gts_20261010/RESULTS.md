# Original GTS pivot reuse: final fixed-contract evidence

**Distance reuse works, but a net host-ready speedup is not confirmed.** The
predeclared paired G0/G1 time ratio is **1.003294**, with 95% paired-bootstrap
interval **[0.998207, 1.009474]** and G1 wins in **4/6** pairs. The interval
crosses parity; no extra round, favorable replacement or production promotion
was made. G2 was already present in original GTS, so G3 collapses to G1.

## Frozen scope and denominator

Pinned original GTS kNN, GIST1M x960 FP32 resident input, original double L2
arithmetic, K8, sequential B1, self-inclusive domain, same tree/pivots/1GiB
workspace and complete Host ID/distance outputs. Each of12 fresh processes runs
one continuous256-query pass after two warmup queries. Query cache allocation,
reset, lookup/write/read, traversal, sort, output/free and synchronization are
included; data/index/mapping setup, warmup, independent oracle and file writing
are excluded and reported separately. These are in-dataset query IDs with
resident vectors, not a fresh external-vector upload or rebuild-per-query test.

All measurements are new on the user-authorized physical GPU1/NUMA0. GPU0's
existing service was untouched; GPU1 admission locks and foreign-process checks
pass for every process. The host is shared and CPU binding is not CPU exclusivity.
The bootstrap represents fixed-query-set process variation, not distribution or
hardware generalization. IDs exclude15,984 known historical IDs from396 files;
unknown/generic prior histories may be missing, so they are not universally unseen.

## Complete confirmation: all six pairs

Time is the complete256-query pass in seconds. Ratio>1 favors G1.

| Round | Actual order | G0 seconds | G1 seconds | G0/G1 |
|---|---|---:|---:|---:|
| 1 | G0 -> G1 | 91.232873 | 89.729748 | 1.016752 |
| 2 | G1 -> G0 | 92.174386 | 91.469773 | 1.007703 |
| 3 | G1 -> G0 | 92.144398 | 92.207093 | 0.999320 |
| 4 | G0 -> G1 | 92.286285 | 92.163920 | 1.001328 |
| 5 | G1 -> G0 | 89.737434 | 90.235395 | 0.994482 |
| 6 | G0 -> G1 | 89.730051 | 89.700331 | 1.000331 |

| Statistic | G0 | G1 |
|---|---:|---:|
| p10 / median / p90, seconds | 89.733742 /91.688635 /92.230336 | 89.715039 /90.852584 /92.185506 |
| Arithmetic mean, seconds | 91.217571 | 90.917710 |
| Geometric mean, seconds | 91.210859 | 90.911407 |

Primary paired geometric ratio:1.003294 [0.998207,1.009474], bootstrap20,000,
seed202610101333. Marginal median ratio:1.009202, **not** the promotion estimator.
G0-first ratio:1.006109; G1-first ratio:1.000487. All12 full-result audits have
independent exhaustive tie-aware and deterministic recall1.0, complete slots,
correct signed/sorted fields and frozen distance tolerances. Every round's G0/G1
full result binaries are bit-identical. See `FORMAL_ROUNDS.csv`, `SUMMARY.json`
and hash-bound receipts in `VALIDATION.json`; there were zero formal replacements.

## Redundancy -> mechanism -> module -> effect -> complete cost

1. **Redundancy.** Original GTS already shares a pivot among sibling nodes,
   saves the full double distance and uses encountered pivot distances to tighten
   the kNN bound. G2 is deleted rather than manufactured by weakening G0. The
   real gap is pivot-object recomputation at leaves and one cross-level alias.
2. **Mechanism.** G1 caches original full double distances by query/object ID.
   Equal-vector different IDs remain distinct. Arithmetic/rounding, disk filter,
   bound, node priority and traversal decisions remain unchanged.
3. **Module.** An immutable4,000,000-byte object-to-pivot map is index setup.
   Each query allocates44,440 bytes of validity and88,880 bytes of double cache,
   clears validity and frees both:133,320 bytes of extra logical query capacity,
   plus the static map. Formal mapping setup ranges4.34794-6.60137 ms, reported
   per process rather than silently amortized. No Graph/layout/precision change.
4. **Measured effect, fixed32 diagnostic only.** G0 executes28,442,203,200
   distance dimensions; G1 executes28,138,250,880:303,952,320 fewer,
   **1.068666579%**. G1 avoids316,585 leaf and32 cross-level pivot recomputations.
   All316,617 hit bridges are bit-identical. Both modes test3,365,870 nodes,
   pass3,262,461 nodes, and visit2,929,074 leaves and29,290,740 valid leaf objects.
   Neither visits nor the first-bound formation point changes. Counts are not extrapolated
   to the different256-query confirmation set.
5. **Complete cost.** The six-pair result is inconclusive, despite lower thread-level
   arithmetic counts. Retain G0 as keeper; retain G1 only as a research diagnostic.
   The current experiment does not demonstrate that its savings cover all costs.

### Logical work is not physical traffic or warp-issued arithmetic

Fixed32 G1 has29,627,327 logical map lookups,2,532,936 cache-read payload bytes and
4,038,660 payload/tag-write bytes. These are source-level operations, **not DRAM/L2
traffic**; validity reads, memset and allocator metadata are not included. G0_count
also maintains diagnostic tags for uniqueness; these are not present in formal G0.
Instrumentation time and intentionally duplicated bridges never enter the ratio.

A post-collection CPU screen finds every leaf has10 objects, with at most2 evaluated
pivot IDs in a leaf. Even the optimistic all-pivots cache plus the self-distance shortcut leaves
at least7 uncached objects per leaf. The original512-thread leaf CTA has its10 object
threads in one warp: no visited leaf can skip the entire distance loop merely by
reusing these pivots. Thus thread-level saved dimensions need not translate into
fewer warp loop executions. This is a **static/inferred SIMD explanation**, not a
measured SASS-instruction or causal latency result; see `WARP_REUSE_SCREEN.json`.

Static resources: getDisPQ registers G0=50/G1=52; leaf registers48/48. Both retain
47,528-byte stack declarations and zero static SHARED/LOCAL allocation. This is not
an occupancy or no-runtime-local-traffic certificate.

## Query-only NSYS attribution: diagnostic, not another latency result

The same uninstrumented binaries and fixed32 queries were profiled after formal
completion. Both complete result sets still pass and are bit-identical.

| Query-range diagnostic | G0 | G1 |
|---|---:|---:|
| Kernel launches | 1,792 (56/query) | 1,792 (56/query) |
| cudaDeviceSynchronize calls | 576 | 576 |
| cudaMalloc /cudaFree /cudaMemset calls | 672 /736 /32 | 736 /800 /64 |
| Recorded GPU-work temporal coverage | 96.782% | 96.871% |
| Leaf-kernel inclusive duration, ms | 9,987.763340 | 9,988.451160 |
| Pivot-kernel inclusive duration, ms | 774.398494 | 774.175486 |

G1 adds exactly64 malloc,64 free and32 validity-memset calls for32 queries. Leaf
kernels occupy about88.9% of the captured Host query range in both profiles; the
many small operators do not imply that launches dominate this1M workload. Recorded
GPU coverage is high, **not SM utilization**. cudaDeviceSynchronize inclusive time
is about10.83 seconds and overlaps GPU execution: it cannot be called10.83 seconds
of CPU arithmetic. No CPU-sampling, NCU traffic or isolated cache-module timer was
collected. We therefore do not causally blame allocator cost, CPU compute or cache
lookup alone for the inconclusive net result. Full tables/hashes: `PROFILE_RESULT.json`.

## Qualification and preserved faults

Final guarded binaries pass fixed32 full-output checks, primitive bridges and
memcheck/racecheck/synccheck for the cache component and one real query. A separate
post-confirmation suite passes N4097 at D96/960, K1/2/7/8/9/31/32, including the
nine-identical-vector distinct-ID K-boundary ties and self queries. Last-allocated-
nonempty-leaf self queries also pass; GPU leaves execute in parallel, so this is not
a total visit-order proof. N4, B32 and K33 are explicitly rejected by both binaries.

**Original root-leaf N<K variable-cardinality search remains unsupported and
uncertified**, not passed by the four-object cache unit or negative-admission test.
Arbitrary long-unfilled/visit-order trees, in-process index replacement, concurrent
batches, alias-edited indexes, updates and Graphs remain outside the certificate.

Initial unguarded diagnostics, the clean-but-partial sanitizer orchestration fault,
pre-freeze fixes and a profiler wrapper argv TypeError before process launch are
preserved. The corrected profile collection used a separate scratch; it replaced
no formal observation. Raw archive SHA and1,120 portable file hashes are in
`RAW_MANIFEST.json`; the20MiB archive and raw binaries/NSYS files remain outside Git.

## Decision and reopen condition

- **Implementation:** admitted static B1 checks pass; broader qualification is partial.
- **Mechanism:** repeated thread-level arithmetic is measured and removed; existing
  candidate-bound use is not a new contribution. Net benefit is inconclusive.
- **Thesis:** no novelty, external superiority or dynamic-update benefit established.
- **Action:** do not migrate/promote this cache as a GTS++ acceleration contribution
  on this evidence. A defensible next test should address measured leaf execution
  geometry or another independently evidenced bottleneck. Reopen reuse only with
  a preregistered regime that plausibly eliminates whole SIMD work or has much more
  repeated distance work, while keeping all management costs and exact outputs.
