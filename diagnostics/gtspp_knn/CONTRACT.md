# GTSPP kNN operator campaign — 2026-09-23

## Phase 1: freeze before baseline measurement

Parent: f895d51 (accepted bounded RNN aggregation overlay). Native GTSPP source
pins remain diagnostics/cpu_io/SOURCE_PINS.json. Never replace the source tree.
This is ordinary operator engineering, not a new top-k/reduction novelty claim.
RNN's full-segment integer reduction does not describe kNN: mergeResKnn reads one
kth item; mergeResKnnIds copies k already-sorted items. The preceding global
sort may contain more material redundant work. Measure before choosing B.

Host: same admitted RTX PRO 6000 Blackwell Server Edition server, CUDA13.1.115,
driver590.48.01, GCC13.3. The user explicitly authorized physical GPU5 for this
round because GPU0 was occupied. Use only GPU5, verified UUID, an advisory
/tmp/gtspp_gpu5.lock and pre/post idle snapshots; do not disturb other devices,
processes or driver settings. sudo NCU only under existing task authorization,
clock-control none/cache-control none, bounded timeout. Remote scratch and a
separate branch only. Build/provenance logs and failed attempts are preserved.

Workload: same pinned SIFT first N65,536, 128D FP32 integer coordinates[0,255],
Q32/128, k10/100; smoke N2,000/Q32/k10. Queries are floor(i*N/Q), self included.
Primary return contract: complete top-k IDs and distances. Verify each ID's
squared distance, nondecreasing order, unique IDs and the exact full-table top-k
squared-distance multiset (ties may use any qualifying ID). Native encoded-key
float output must agree with sqrt(exact squared distance) within 1e-3 absolute.
Also verify the scalar-kth overload and vector-query overloads on the same
queries. These are bounded self-vector queries, not held-out ANN recall evidence.
Pruning mode is explicitly fixed to 0 (no learned residual), equally in A/B,
so calibration/learned-approximation changes cannot masquerade as speedup.

Native dynamic height, padding, C3 node path, 4 GiB workspace budget, candidate
construction, distance arithmetic, result encoding, CPU default wait policy and
all synchronizations remain. Common driver changes only stage clocks/NVTX,
debug-print suppression, native update_disk reset for every call, CPU result
collection and final cleanup. Complete warm query timing includes allocation,
all GPU/CPU operators, waits, output delivery and cleanup; excludes input,
full-table oracle, build, learned calibration and three warmup queries. No
full-program-startup, all-tree, insertion, arbitrary-float or production claim.

Preflight: source-pin/instrumentation checks, baseline correctness on smoke and
all four main shapes; memcheck and synccheck on smoke/primary; scoped primary
NSYS plus stage timings. Profiling before full gates is diagnostic-only.
Stop optimization on an unresolved correctness/sanitizer failure. Append any
candidate contract and design/role/ready graph BEFORE implementing it.

Choose the dominant material operator, not its name. A copy-only coalescing
candidate must not be presented as a full-query improvement from fewer sectors
alone. Any replacement of full sorting must preserve all native top-k output
semantics, ties, candidate sets and scalar-kth paths. Price extra workspace,
metadata, packing and launches inside the end-to-end denominator.

## Acceptance for a subsequent candidate

Required: all four primary shapes plus smoke, all four overloads on smoke and
primary, independent oracle, source invariants, memcheck/synccheck A/B on smoke
and primary and B smoke racecheck/initcheck for shared handoffs. Stress each
variant for 64 queries on two endpoint shapes, each output checked.
Six matched fresh-process pairs per main shape with AB/BA alternating, one
checked cold query, three checked warmups and eight retained queries/process.
Primary estimator: paired geometric ratio of process-median complete-query wall
times, seed0 10k-bootstrap 95%CI, lower bound>1.02 and B wins>=5/6 pairs.
Report every shape, p10/median/p90, marginal medians, order split, main-thread CPU
and stage fractions. Do not select favorable observations. Sustained64-query
batches on two endpoints, three alternating pairs; preallocated result-history
copies included in timer, correctness afterward; require lower CI>=1.00.

Collect same-round NSYS and NCU A/B for the selected operator after validation;
retain exact runtime functions, binary/SASS hashes, resources, load requests /
sectors, cache/DRAM bytes, warp participation, scheduler/stalls. Replay timing is
not the public latency. CPU synchronization API durations overlap GPU work and
cannot be added to kernel time. Missing production gates bound a prototype.

## Phase 2 amendment — before candidate implementation

Phase-1 primary Q128/k100: clean median query32.963 ms, leaf14.898 ms (about45%),
result-sort4.791 ms, result-copy0.820 ms (about2.5%). Scoped NSYS confirms the
leaf kernel itself14.857/14.900/14.904 ms; result-copy0.965/0.844/0.848 ms.
All primary/smoke and four overload checks pass, as do A memcheck/synccheck.
Choose leaf L2 ownership, not the small final copy. No RNN integer reduction is
transplanted into kNN, and no top-k algorithm/ordering change is claimed.

A: native dataProcessKnn / dataProcessKnnVec, one thread per point, serial128D.
B: add an L2-only warp-cooperative fast path to BOTH shared leaf kernels; retain
native fallbacks for other metrics. Same grid (one CTA/leaf-query candidate),
512 threads/CTA, tree, node/pivot kernels, candidate slots, disk bounds, IDs,
encoded keys, output stores and sorting/copy kernels. Sixteen warps/CTA stride
through MAX_SIZE=20 points. Lanes load coordinates lane+32*j and accumulate
FP64 partial sums of the unchanged FP32 squared differences; five full-mask
warp shuffles combine partials. Lane0 performs native sqrtf/threshold and writes
one original ID/distance/key tuple. Self distance remains0. Invalid slots retain
ID=-1 and INFI_DIS. No new shared memory, CTA barrier, allocation or CPU wait.

Design: target sm_120 scalar load/add/shuffle, not tensor cores. A warp owns one
point partial; register live set is node metadata, query/point bases, bounds,
one FP64 partial and loop coordinate. The partial dies at lane0 finalization;
ID/distance/key die at their stores. No cross-warp handoff/reusable asynchronous
object. Ready graph: original candidate-production synchronization -> contiguous
vector loads -> lane partials -> five shuffles -> lane0 sqrt/threshold/stores ->
original kernel-completion synchronization -> unchanged full sort and top-k copy.
All 32 lanes of every participating warp enter every shuffle, including the
ragged second round (only four whole warps process points16..19).

For the frozen integer vectors, each squared difference and every possible
partial sum are exact integers <=128*255^2=8,323,200. FP64 summation regrouping
is exact and sqrtf input is identical; arbitrary floating inputs are outside
the validated contract. No precision reduction is introduced.

Expected useful work: same coordinates/distances; additional shuffle/metadata
work, fewer serial per-lane accumulation steps. Movement hypothesis: adjacent
lanes use adjacent AoS coordinates, fewer sectors per useful byte. Control cost:
more active warps and shuffle dependencies, unchanged CTA count and host waits.
This is a coupled ownership/coalescing/reduction change, not pure coalescing.
Static resources/stack/local traffic must be audited; legacy edit-distance
fallback may retain a large static stack despite not executing in L2 mode.

Keep source invariant checks and every original acceptance gate. NCU targets
one measured dataProcessKnn launch, not mergeResKnnIds. Preserve raw preflight
binaries separately. Build fresh final A/B with one identical driver. If the
same-contract full-query or sustained gate fails, do not promote this candidate.

Validation-only refinement before performance collection: explicitly reject
nonfinite returned top-k distances and check returned float ordering explicitly (the earlier `abs(error)>tol` expression
alone would not reject NaN). Preserve the initial gate round and rebuild both
final variants before repeating all final gates; no timing result from an older
driver is promoted. Kernel/candidate math is unchanged by this oracle hardening.

## Conditional geometry control C — predeclared before implementation

Initial correctness-only A/B samples show B's leaf about19.51 ms versus A14.86
ms, despite the intended contiguous reads. These are not acceptance estimates;
finish and retain the complete B512 campaign. The source suggests a competing
cost: sixteen active warps per leaf CTA, including padded slots and metadata,
versus native's at most20 active point threads. Test one bounded geometry control,
C64, only after B512 collection finishes. No concurrent builds during timing.

C keeps B's warp-per-point math/output but uses64 threads (two whole warps) per
leaf CTA. Warp point stride is blockDim.x/32 rather than16. All four kNN overloads
use this leaf launch width; every other launch remains512/native. Grid/candidate
slots unchanged; ten whole-warp point rounds cover20 slots. MAX_SIZE20 and L2
integer workload are frozen. No general metric/shape admission is implied.
No shared memory/barrier; register and ready ownership unchanged, more sequential
points per warp versus more simultaneously resident independent leaf CTAs.
Expected tradeoff: fewer per-CTA metadata/warp overheads and more resident leaf
CTAs, paid by longer warp point loops. This is a block-geometry control on the
same coalesced algorithm, not a new mathematical method or free-work reduction.

Run C64 in a separate immutable collection with A/native and B/C64 comparator
roles; preserve B512 separately as rejected/inconclusive/accepted according to
its own gates. Remeasure A with C64 in the same round; never reuse B512's A times.
Every declared correctness/sanitizer/stress/fresh-pair/sustained/profiler gate
applies independently. Do not tune more geometries from favorable samples in
this task. Final promotion requires all four required short-query gates and
both sustained endpoints. If neither B512 nor C64 passes, report that result
and leave the source keeper unchanged.

Analysis-only clarification after B512 collection: the complete source-PC ledger
reconciles exactly with `sass__inst_executed_per_opcode` for both variants.
B512's separately collected hardware `smsp__inst_executed.sum` exceeds that
SASS-patched total by0.624%. Preserve both totals and the unresolved gap; do not
force cross-collector equality or normalize the source ledger to hardware.
Replace the incorrect cross-collector assertion with exact source/opcode
reconciliation. No correctness, timing, confidence or acceptance gate changes.

## Store-ownership control D64 — before implementation

The completed B512 campaign fails all four short-query gates and both sustained
endpoints. NCU's global-load sectors fall1,272,531,693 ->538,387,512, but global
store sectors rise18,496,740 ->73,986,960 (4x). Its source-correlated global-store
warp instructions rise3,699,348 ->73,986,960 (20x): one lane/warp stores one point
rather than one warp storing adjacent points. C64's correctness-only primary
leaf is still about18ms. Preserve the entire C64 geometry campaign before this
new control; do not mistake reading improvements for whole-operator success.

D64 keeps C64's64-thread CTAs, two warp owners, grid, coordinate accumulation and
all host/output contracts. Change only the post-reduction handoff: each warp's
lane0 publishes the ID and FP64 squared-distance sum to shared arrays[20]. After
one unconditional CTA barrier, threads0..19 each own one point, perform the
native sqrtf/disk-threshold/encoded-key calculation and write adjacent tuples
to the unchanged three global SoA result arrays. Invalid point ID=-1 still
produces INFI_DIS, without sqrt. This coalesces result stores and batches scalar
finalization across lanes, instead of executing it with one active lane/warp.
No new global scratch, allocation, kernel launch or host synchronization.

Shared live set:20 ints plus20 doubles=240 bytes, written once by a unique
producer and consumed once after the single barrier. Full CTA enters L2 helper
uniformly and reaches the barrier even for empty/invalid/padded nodes. Each
shared slot has exactly one writer; slots remain live through the post-loop
barrier then die after thread-owned global stores. Ready graph:
loads -> FP64 warp sums -> lane0 shared publication -> full-CTA barrier ->
thread0..19 sqrt/threshold/encoded stores -> original completion -> native sort.
Shared arrays are contiguous; no custom swizzle or asynchronous reuse. Double
access wavefront/bank behavior and extra barrier cost must be measured.
Registers retain only query metadata across the barrier; FP64 warp partials die
at publication. Same exact integer arithmetic/FP32 sqrt result as A/B/C.

Expected: restore coalesced global stores and reduce sparse-lane finalization
instructions, paid by240 shared bytes, shared traffic and one CTA barrier.
This is a store/finalization ownership control, not another geometry search.
Run one separate A/native versus B/D64 same-round campaign after C64 completes.
Require the identical full32gates,64-query stresses, four6-pair matrices, scoped
profilers and two sustained endpoints. No further candidate is planned here;
if D64 does not pass, keep the native keeper and report bounded negative or
inconclusive evidence rather than relaxing the acceptance threshold.
