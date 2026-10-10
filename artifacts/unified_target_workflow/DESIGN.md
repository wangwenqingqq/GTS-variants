# Target-size qualification design (phase A)

Status: implementation in progress; no target performance evidence.

## Frozen boundary

The base is GTS-variants `0033cb2d1934768411ed1806c6729108f412c1e7`.
The pinned original GTS build/update owner and existing PAR / FULL / BOUND
mechanisms remain in use. A separate overlay preserves historical sources and
results. Required shapes are D128 regression and GIST N1M/D960/B1/K8 only.
A is staged original GTS with common numeric and safety repairs, not untouched
native GTS. B adds PAR; C changes FULL to BOUND. No WARP/FUSED routing is added.

## Capacity and ownership

Preflight replays events to determine the maximum physical base plus insertion
buffer. Capacity is rounded to 32 once; an unexpected growth rejects the run.
The native update loop owns compaction, tombstones, buffer, and rebuilds. kNN
owns only its mirror and two recursive Top-K scratch buffers, each
ceil(capacity/256)*allocated_K. All allocation products use checked size_t
arithmetic. The original fixed tree height is raised to the minimum height
whose largest leaf is at most MAX_SIZE; old small defaults remain.

Host answers grow on demand under a fixed 1 GiB combined ID/field budget.
Every field is retained and copied before ACK. Budget exhaustion rejects the
whole trace, never truncates it. File writing follows timing. Long traces are
not admitted until their actual output budget / equal consumption is qualified.
Host vector growth/copy costs are inside the event trace.

## Numeric design and ready graph

Input is finite original FP32. Object verification uses the existing ordered
FP64 RN subtraction, multiplication and dimension-ordered addition, no FMA.
Membership compares squared sums, not rounded FP32 square roots.
The output conversion is RN sqrt followed by RN conversion to FP32.

The fixed historical strict_l2.cuh has the compatible ordered reference
function and member-refit pattern, but its hardcoded outward padding is not
carried into the new bounds. Directed FP64 subtraction, squaring, accumulation
and sqrt enclose the true norm of every actual node member. For finite FP32
operands all nonzero intermediates are normal finite FP64. With u=2^-53,
reference_sum >= true_squared_distance*(1-u)^(D+3). A downward-rounded product
alpha <= (1-u)^(D+3) therefore gives a conservative allowed true radius
sqrt_up(cutoff_RN/alpha). Directed upper additions implement exclusion;
uncertain nodes survive. No fitted epsilon is used.

Each refit CTA owns one node, with 256 member lanes and two shared reductions.
The base/order remain read-only. Refit completion -> publish bounds/base epoch
-> PAR plan refresh when required -> kNN repack -> ACK. Query launch checks
base pointer, dimensions, physical size, and epoch. Deleted pivot rows are not
removed until actual rebuild. All lanes participate in refit reduction barriers;
there is no asynchronous handoff or tensor-core path.

Persistent live sets: common lower/upper arrays (16*node_count bytes); PAR-only
plan and query workspace; kNN FP32 AoSoA32 mirror, double scores/cutoff, live
rank/mask arrays, two Neighbor buffers and K outputs. Rebuild temporarily owns
old/new data and tree state; paid copies/refit/repack remain inside ACK.

## Gate / reject rules

CPU exhaustive small-output comparison and A/B/C ordered equality precede
bounded sanitizer runs. Then N65536 transition and N1M real rebuild smoke,
with independent chunked reference and boundary cross-checks. Missing numeric,
coverage, lifecycle or capacity proof blocks the 18-process campaign. No
compilation or narrow smoke test is described as target qualification, speedup,
default selection, or novelty.

## Current P cost/ownership closure (2026-10-10, submission A)

The present keeper is PAR_STRONG/FULL/TILED, not the old staged implementation.
The five-part chain and measured bounds are in
`../build_distance_tiles/CLAIMS.md`. Existing process
records are reused by `../external_closure/pe_costs.py`; no old primaries are rerun.

| State / work | CPU responsibility | GPU responsibility | Invalidation / publication |
|---|---|---|---|
| Original FP32 multiset and insertion buffer | one serial event owner, ACK order | tombstones, buffer merge, stable compaction, original threshold10 rebuild | insertion/deletion changes live set; rebuild changes base pointer/epoch |
| TILED construction | original level control and tile geometry | per-object same-arithmetic distances, original sort/partition | actual rebuild only; publish after construction completion |
| Safe member intervals | allocate/refit fence and epoch check | directed FP64 member norms and min/max bounds | any rebuilt membership/pivot invalidates bounds; refit before queries |
| PAR plan | D2H metadata, make_plan, allocations/H2D | parent-group traversal, actual-pivot reuse, leaves and complete verification | base/tree epoch change; plan publish after bounds |
| FULL kNN mirror and visibility | capacity/epoch checks | AoSoA repack on rebuild; live prefix/mask/buffer publish per query; all live distances and Top-K | geometry invalidates mirror; every update can invalidate visibility |
| Full output | retain all fields and IDs before ACK, release service at end | compact, prefix/ID conversion, D2H | new query requires new output; no truncation |

The observed high CPU time is not itself repeated CPU arithmetic. Host waits,
allocation, plan generation, transfer and actual arithmetic must remain separate
hypotheses; inclusive Host intervals include GPU dependencies.

### Candidate reuse lifetimes and added costs

* `parent_groups::radius_upper(radius,d)`: same radius/d in every active parent
  CTA; current D960 executes963 directed multiplies per invocation. The separate
  probe counted1,006,009 calls for one parameter pair, implying968,786,667 source
  multiplications. Isolated time is **unknown**; containing parent kernel811.499ms
  includes traversal/distances and an extra diagnostic atomic. Correct reuse
  would compute the same GPU function once per valid
  radius/d epoch, publish before traversal, then load the value; radius/d changes
  invalidate it. Added scalar storage, kernel/launch/fence, argument/load and
  refresh costs must be charged. Whole query.tree is only a loose ceiling, not
  removable work. Do not implement merely because hoisting is easy; not novel.
* Live prefix/mask/order is regenerated at each FULL kNN query; range merge and
  deletion also use prefix scans. Unchanged tombstone/buffer state permits reuse,
  but insert/delete/base compaction invalidate the dependent subset. Current
  invocation counts and constituent time beyond the inclusive boundaries are
  unknown. Any update-version check/cache adds ownership, refresh and memory.
* Member refit computes actual membership bounds after each rebuild. Membership
  and pivot changes mean an old bound cannot simply be reused. Three total refits
  (setup plus two updates) are necessary in the current correctness design;
  the fraction safely avoidable under another representation is unknown.
* Compaction copies a full old vector allocation before stable live compaction.
  The two actual rebuilds repeat this stage, but changed state means they are not
  identical work. Avoiding the temporary copy needs a legal out-of-place lifetime
  or another update representation, with old/new overlap and peak memory priced.
* FULL kNN performs required exact distances/selection on each different query.
  A full stage is not evidence of redundant distances. Cross-query reuse requires
  identical operand pairs and invalidation proof, neither currently measured.

### Logical external interface (submission B, now qualified)

The separately registered P/E adapter uses immutable Host query/insert vectors
and occurrence IDs. A CPU replay freezes the old physical trajectory before any
comparison. P receives11 nonindexed request rows (10 live insertion slots plus
one query slot); these are retained through the unchanged native compaction.
A timed Fenwick map converts stable live ranks to occurrence IDs. All original
GPU kernel bodies, PAR/FULL/TILED dispatch and actual threshold10 remain fixed.

E reuses Faiss `bfKnn` and its native `runL2Norm`, with cached norms; cuVS range
uses the same dense live vector allocation. Insert copies one vector and computes
one native norm. Delete swaps the last live vector/norm and updates two Host ID
maps. No inactive row reaches selection, no fixed-K postfilter, no forced tree,
no second vector dataset. This is an explicitly labeled dynamic adapter, not a
native Faiss update benchmark or a new research mechanism. Eleven qualification
processes and all12 formal jobs passed; the first correct bounded P sample was
admitted offline after correcting a cumulative-build-count checker error, not
rerun. Every original GPU function remains compiled-identical. The complete
[result](../external_closure/PE_RESULTS.md) rejects a current dynamic P advantage:
paired E/P0.202847, P0/6 wins. Setup+trace is only a service-setup sensitivity
(E client ledger reservation is outside that secondary sum); the continuous
primary trace remains as registered. No10K expansion or private paper edit.

### Single selected next cost question (submission C2, design only)

The independent diagnostic attributes1793.454ms to range leaf verification,
1199.096ms to tiled rebuild distances,844.275ms to FULL verification and811.499ms
to parent groups. These are perturbed GPU durations, not formal trace intervals.
Choose only range reject-suffix arithmetic for a bounded causal question: after
a strict ordered partial FP64 squared distance exceeds the unchanged cutoff,
nonnegative remaining terms cannot restore membership. A32-coordinate gate
would reuse the existing kNN early-termination principle, preserve accepted field
bits and avoid changes to candidates/traversal/layout. Count eligible/skipped
coordinates before any timing claim; charge divergence/control/register costs.
No cross-query state is cached; a new query/radius/object invalidates each proof.
This is established partial-distance elimination, not novelty. Even the whole
leaf-stage budget cannot alone close the external gap. Detailed kill tests and
separately registered reopen gates are in[PE_DECISION](../external_closure/PE_DECISION.md).
