# GTS: next experiment plan — 10,000-query stability and complete-workflow attribution

Date: 2026-10-04 (Asia/Shanghai)
Status: **PLAN ONLY. No GPU experiment, implementation promotion, or new measured result is recorded by this document.**
Delivery scope: public experimental protocol; no manuscript or private project metadata.

## 1. Decision and mandatory scope

Run a genuinely frozen stable query version on **10,000 distinct queries per dataset**, against **original GTS, native GPU Faiss Flat, native GPU Faiss-IVF, and native CAGRA**. Keep range and kNN separate. Independently audit every operator in query, insert, delete, compaction, and rebuild. Do not revive the abandoned direct-insertion incremental implementation.

The largest ratio against original GTS is not the acceptance criterion. The questions are:

1. Does the qualified version sustain its quality and complete-output contract over 10k queries without state leakage, memory growth, or unexplained tail stalls?
2. Does it have an advantage against the strongest **quality-admitted external comparator**, especially Flat/IVF/CAGRA?
3. Which measured CPU work, CPU waiting, synchronization, GPU coordinate computation, and physical memory traffic explains the remaining gap?
4. Can an attributable change improve the complete Host-ready query or complete operation trace, after including its added work and maintenance?

There is no unified range/kNN/update keeper today. “Stable” is a qualification to earn for an exact entry and shape set, not a name for the latest diagnostic branch. A static stable result does not certify updates or fresh-vector arrivals.

### Required comparison protocols

| Protocol | Submission contract | Required query count | Purpose |
|---|---|---:|---|
| K10-MATCHED | Sequential Host-ready B1 requests, or successive ready B32 batches | 10,000 per dataset/shape/process | Compare the existing P7 contract; expose CPU/control and tail behavior |
| K10-BULK | All 10,000 requests ready together; each method uses its frozen best legal chunking policy | 10,000 per dataset/K/process | Compare realistic bulk throughput without handicapping native libraries |
| R10 | Independently registered exact L2 range queries and complete variable-length outputs | 10,000 per admitted workload/process | Validate the actual range contribution, not a kNN substitution |
| U10-NATIVE | Legal native logical-multiset operations, with 10,000 query events | 10,000 query events plus updates | Long correctness and original-workflow attribution; not fresh arrivals |
| U10-ARRIVAL | Stable external IDs, new vectors, serialized visibility, and full maintenance | 10,000 query events plus updates | Conditional integrated update evaluation; unavailable until the API/keeper qualifies |

CAGRA is **mandatory in both static kNN protocols**, not a follow-up or optional appendix. A missing executable comparator is an incomplete comparison, not an admitted performance result.

## 2. Live evidence checkpoint and corrections

Evidence was read at `wangwenqingqq/GTS-variants@7bce3679c3e32e77fa25cf7842805926509e1412`, branch `experiments/unified-knn-p7-20261003`. This plan does not assert current remote GPU availability.

| Evidence | Established scope | Consequence for this plan |
|---|---|---|
| P7 R2 | 516 formal processes; 288 complete-mode processes pass per-query tie-aware quality and full fields on 256 queries | Useful bridge evidence, not 10k stability or a dynamic keeper |
| OPT-KNN-P7 | Implementation `d65c6e41effad67dde8ae1f1f68e656562607817`; binary `1a6a63ecd452dda0b67ab6140e394a60c21b9f04280e4643f00b7749a53d0e92` | Preserve as the immutable static comparator; qualify any new build independently |
| Tree-mask ablation | Every B1 mask case is slower than O_BOUND; GIST/B32 small point gains have intervals crossing 1; Deep/B32 slightly regresses | O_MASK is an ablation, not an automatically selected universal keeper |
| Native comparators | Flat leads the complete B32 cases; Deep/B1 is an exception where the optimized executor beats Flat but not IVF_ALL | Report external leadership and workload exceptions, not only GTS speedup |
| P7 R1 | Input H2D and Graph ordering was not guaranteed | R1 formal samples remain invalid; never reuse them in K10 |
| U0 | Original empty-buffer stale `rnum` failure reproduced; one-line reset passes 17 legal cases/69 complete-ID checkpoints | Keep original and repaired identities separate; extend correctness before timing new updates |
| U0 capacity | N1990 fixed-height fixture rejected; separately registered legal N2000 fixture passes | N <= 2000 is not a blanket legality certificate |
| Native IDs | Insert/query uses physical rows; delete uses current live rank; output is live multiset rank | Do not call native reinsertion new-vector arrival or rank deletion stable-ID deletion |
| NCU | Four supplemental P7 calls rejected before launch; physical DRAM/sectors/instruction counts unavailable | Collect new diagnostic counters; do not infer physical coalescing from wall time |
| Historical allocation/rebuild chains | Complete provenance not recovered; main-result claims retired | Do not restore historical headline values through this campaign |
| Unified keeper | Shared update invalidation and ingestion protocol absent | U10-ARRIVAL performance remains conditional; static K10 need not wait for it |

Primary evidence links:

- [P7 results](https://github.com/wangwenqingqq/GTS-variants/blob/7bce3679c3e32e77fa25cf7842805926509e1412/diagnostics/unified_knn_e2e_20261003/RESULTS.md)
- [P7 identity](https://github.com/wangwenqingqq/GTS-variants/blob/7bce3679c3e32e77fa25cf7842805926509e1412/diagnostics/unified_knn_e2e_20261003/evidence/IDENTITY.json)
- [P7 completion receipt](https://github.com/wangwenqingqq/GTS-variants/blob/7bce3679c3e32e77fa25cf7842805926509e1412/diagnostics/unified_knn_e2e_20261003/evidence/COMPLETE.json)
- [U0 results](https://github.com/wangwenqingqq/GTS-variants/blob/7bce3679c3e32e77fa25cf7842805926509e1412/diagnostics/claim_closure_20261003/RESULTS.md)
- [Compatibility decision](https://github.com/wangwenqingqq/GTS-variants/blob/7bce3679c3e32e77fa25cf7842805926509e1412/diagnostics/claim_closure_20261003/C0.md)
- [Retired historical claims](https://github.com/wangwenqingqq/GTS-variants/blob/7bce3679c3e32e77fa25cf7842805926509e1412/diagnostics/claim_closure_20261003/R0.md)

The frozen design contract and an intermediate identity status are snapshots, not final completion receipts. Resolve actual execution state using R2 receipts, source/binary hashes, formal records, and the completion artifact together.

## 3. N0: novelty gate before a new research mechanism

Write a one-page problem/mechanism/claim matrix before implementing another optimization. Check nearest primary sources rather than claiming that GPU trees have a universal problem:

| Primary source | Relevant precedent | Boundary to check |
|---|---|---|
| [Original GTS](https://arxiv.org/abs/2404.00966) and [code](https://github.com/ZJU-DAILY/GTS) | GPU metric-tree organization, pivot pruning, query and update workflow | What is already implemented, including parent-pivot reuse in kNN? |
| [G-PICS](https://cse.usf.edu/~tuy/pub/SSDBM18.pdf) | Concurrent spatial queries, leaf-grouped query processing and updates | Generic grouping/reuse cannot stand alone as new; metric/high-D tree distinctions need evidence |
| [Harmonia](https://www.ece.lsu.edu/lpeng/papers/ppopp-19.pdf) | GPU-aware tree layout and traversal | B+tree key search differs from metric search; generic compact layout is precedent, not an external similarity-search baseline |
| [Faiss GPU paper](https://arxiv.org/abs/1702.08734) and [official GPU guide](https://github.com/facebookresearch/faiss/wiki/Faiss-on-the-GPU) | Efficient selection, memory hierarchy, scratch reuse, batching and streams | Compare native distance plus topK and sensible scratch resources, not an artificially allocation-heavy wrapper |
| [CAGRA](https://arxiv.org/abs/2308.15136) and [official implementation guide](https://github.com/NVIDIA/cuvs/blob/main/fern/pages/neighbors/cagra.md) | GPU graph-based ANN with small- and large-batch search | Approximation and observed quality must not be conflated with an exact completeness guarantee |
| [MVGpuBTree](https://github.com/owensgroup/MVGpuBTree) | GPU-resident updates and snapshot/visibility mechanisms | Not a same-task high-dimensional similarity comparator; relevant to novelty of update-residency claims |
| [GrAND](https://arxiv.org/abs/2608.21163) | Dynamic GPU ANN graphs and elimination of redundant maintenance work | Recent dynamic graph precedent; examine overlap before claiming generic batched update redundancy removal |

N0 deliverable: nearest overlap, one non-incremental mechanism if it exists, strongest alternative explanation, and the cheapest falsification control. If the mechanism is subsumed without a decisive same-contract distinction, stop that research direction. Do not rescue it by packaging or a small ratio against an inefficient original baseline.

This research stop rule does **not** silently cancel the user's requested 10k stable-version comparison. K10 remains useful verification even if the proposed novelty fails; do not present routine engineering verification as a new contribution.

## 4. F0: freeze versions and qualify “stable”

### Separate identities

| Label | Role | Required qualification |
|---|---|---|
| GTS_ORIG_FULL | Pinned original static search plus declared full-output/capacity/loader adapter | Preserve original search/arithmetic; include actual complete-output work in timing |
| GTS_UPDATE_RESET | Pinned original native update plus the localized `rnum[0]=0` repair | Legal capacities, full membership/fields, and native rank semantics; not a new algorithm |
| OPT_KNN_STABLE | Qualified static executor derived from P7 R2 | Commit/source/binary hashes; all K/B/tail, stream, sanitizer and long-state gates |
| O_FULL / O_BOUND / O_MASK | Mechanism controls sharing the same selector/output contract | Do not combine historical independent ratios; keep every rejected shape |
| RANGE_STABLE | Qualified P4-derived static range entry | Separate range membership, arithmetic, radius, delivery and source identity |
| UPDATE_CANDIDATE | Future integrated keeper only after an actual entry exists | New-vector ingestion, stable IDs and all invalidation/maintenance gates |

Use O_BOUND as the **provisional** static kNN default because the existing O_MASK results do not establish a universal gain. Select the final policy on development queries only. Retain O_MASK and O_FULL as ablations even when neither becomes the default. If a dispatch policy is proposed, freeze its rule before final-query generation and include dispatch cost.

### Qualification sequence

1. Reuse the current source and harness; inspect exact callers and changed flow.
2. High-entropy and tied/duplicate fixtures: K8/K32, B1/B32, N and D boundaries, zero distance, legal capacity, and ragged query batches.
3. Graph/eager differential check; H2D -> computation/Graph -> final D2H must have explicit stream/event ordering. Pointer/capacity changes must invalidate or update the graph.
4. memcheck and synccheck for new/changed paths; initcheck/racecheck where the change creates the relevant risk. Silent sanitizer output never replaces membership tests.
5. At least 100 alternating query/shape/pointer-reuse cycles on bounded fixtures; deterministic output hashes where the tie contract allows them; no state leakage.
6. Q=1024 development stability screen with full outputs. This is qualification, not the requested formal K10 measurement.
7. Freeze implementation, binary, index, query generator, output bridge, legal parameters, order table and statistics before final10k generation.

The measured P7 executors read variable query counts. OPT-KNN-P7 already captures each actual batch shape, including a ragged tail; native code also uses actual batch lengths. The campaign still names final256 files and the analyzer hardcodes 256 in throughput formulas. **Change orchestration/analysis minimally, not the search algorithm solely to reach 10k.** Independently verify the original adapter's tail and output length.

No invented `--queries 10000` command is advertised as implemented. A runnable 10k command is a deliverable of F0, after the actual parser/paths have been changed and tested.

## 5. K10 data, queries, quality and outputs

### Mandatory static matrix

| Dataset | N | D | K | Matched B | Final unique queries |
|---|---:|---:|---|---|---:|
| GIST | 1,000,000 | 960 | 8, 32 | 1, 32 | 10,000 |
| Deep | 1,000,000 | 96 | 8, 32 | 1, 32 | 10,000 |

This produces **eight matched shapes**, each with six independent formal process rounds per configuration. Both datasets and both batch sizes remain mandatory, including cases unfavorable to the tree mask.

### Query isolation

- Primary bridge: in-database, self-inclusive L2, matching P7. A self object is eligible, not forced through tied duplicates.
- Use fresh development1024 per dataset, excluding all previously used query IDs. Proposed development seeds: GIST `2026100411`, Deep `2026100412`.
- Reserve a separate bulk-development10k unique pool (GIST `2026100413`, Deep `2026100414`) for actual large-chunk/10k-call quality and chunk-policy selection, disjoint from the1024 and historical query inventories. A1024-query call cannot establish the best8192/10k call policy. This additional developer cost is budgeted separately; the fixed-policy original adapter does not need a redundant full bulk tuning sweep.
- Generate **10,000 unique final IDs without replacement after all tuning freezes**, excluding the accumulated pilot/development/bulk-development/old-final query inventory. Proposed final seeds: GIST `2026100421`, Deep `2026100422`. Register generator and exclusion-inventory hashes before generation.
- Persist exact IDs, order, data fingerprints, seeds and final fixtures. Reuse the identical final fixture in every method, K/B shape and round. No repetition of final256 to manufacture Q10k.
- Warmup queries are separate: eight development batches per actual batch shape, including the16-query tail shape; for bulk, eight calls/chunks drawn from the separate bulk-development pool under its chosen chunking policy and a bounded warmup of each actual tail shape. Warmup may reuse its registered development inputs; formal10k may not repeat them. No warmup on final10k. Extend the existing two-batch warmup loops as orchestration changes and validate warm-input length, rather than silently keeping different warmup counts across methods.
- If a code/config change occurs after looking at final quality/timing, retain that failed revision and use a new preregistered final set for a retuned candidate. No final-set retuning.
- A later external-vector / exclude-self K10 task needs a common input API, independently frozen external queries and complete topK recomputation. Merely removing the returned self slot does not implement exclude-self K.

### Full quality gate, on all 10,000 queries

- Independent explicit-RN FP64 squared L2 reference, no FMA, with exact kth-boundary ties. The reference does not call the candidate and does not supply cutoffs to timed search.
- Exactly K distinct valid original IDs per query, finite nonnegative Euclidean FP32 fields, and nondecreasing distance order.
- Retain deterministic-ID recall and **exact-boundary tie-aware Recall@K** separately.
- Original/optimized/Flat/IVF_ALL complete modes must pass every query's full membership gate. Field gate follows P7: `abs(delivered_distance**2 - reference_squared) <= 5e-5 * max(1, reference_squared)`; this does not relax membership.
- Approximate points report unrounded mean recall, worst-query recall, complete-query fraction, missing-ID counts and field validity. Every process must satisfy its registered minimum target.
- A 100% point requires zero misses across all 10k queries, not rounding a mean. It remains **empirical 100% on this set**, not a completeness proof for ANN graphs.
- Compute oracle outputs outside timing in bounded chunks; audit every delivered ID/field. Do not reduce final correctness to a random sample because Q is larger.
- Keep a bounded FP64 score workspace: a Q10k x N1M dense score array is 80 GB and is unnecessary. Existing B32 scores occupy 256 MB; reuse chunked reference/selection logic and save only required reference outputs and tie information.

At B32, **10,000 = 312 full batches + 16 real tail queries**. Capture/use the actual tail shape, validate exactly 10k outputs, and report its timing separately. Do not replace the workload with 10,016 queries or hide padded work.

## 6. Mandatory native Flat, IVF and CAGRA protocol

### Fixed roles

| Comparator | API / identity | Quality role |
|---|---|---|
| Native Flat | `GpuIndexFlatL2.search`, FP32 storage, actual installed Faiss build pinned | Complete-search external baseline, subject to empirical membership/field qualification |
| IVF_ALL | `GpuIndexIVFFlat`, nlist=1024, nprobe=1024, no scan cap/PQ | Complete-scan IVF control; not relabeled as Flat |
| IVF_ANN | Native `GpuIndexIVFFlat.search` with frozen legal nlist/nprobe | 99%, 99.9%, empirical 100% targets |
| CAGRA_ANN | Native cuVS CAGRA search, frozen graph, native K outputs | 99%, 99.9%, empirical 100% targets; mandatory on every shape |

Record actual installed versions, shared-library/source hashes, build algorithms, graph/index hashes, training inputs, RNG state, search algorithm, workspace and streams. P7's versions are starting provenance, not evidence of the next host's installed state. Do not silently replace Faiss's native backend with cuVS and still label the two as independent implementations.

### Development-only selection

- Start with the P7 frozen index/graph and legal configurations to establish a query-count bridge. Reuse the graph if its identity and inputs qualify; do not silently rebuild a different graph between methods/rounds.
- IVF grid: nlist `{1024,4096}`, nprobe `{16,64,128,256,512,1024,2048}`, limited to nprobe <= nlist and actual backend limits. FP32, no PQ, no artificial scan cap. Training sample/seed/hash fixed.
- CAGRA initial graph degree64 and intermediate degree128, as in P7; build method and full frozen graph hash recorded. Search grid: `itopk_size {64,128,256,512,1024}`, `search_width {1,2,4}`, legal installed search algorithms; retain default/auto iteration policy and actual selected algorithm. Do not impose a low iteration cap to make it appear fast.
- Two development passes on the same fresh1024 fixture; choose the fastest configuration satisfying a target in **both** passes, with a deterministic tie-breaker. Freeze all choices before final10k.
- Duplicate selected configurations run once and can serve multiple labeled targets. A configuration that misses a target on final10k stays in the table as failed; it is not retuned.
- If no CAGRA development configuration reaches empirical100%, record “development target unreachable” and still run the frozen highest-quality legal CAGRA point on final10k as a diagnostic. The native 99%/99.9% CAGRA comparisons remain mandatory where reachable.
- CAGRA technical failure is retained with exact command/status and leaves the comparator pending, not omitted. Do not label that shape's comparison complete without the required native CAGRA evidence.

### Quality comparison, not a misleading same-recall slogan

Publish native latency/recall frontiers and separate target tables at 99%, 99.9%, and empirical100%. Each row reports **actual achieved quality** and gate eligibility. A minimum99% target is not equality with a 100% method. Label a direct “equal-achieved-quality” speed ratio only where the predeclared quality convention genuinely matches; otherwise report target-qualified frontiers and absolute values.

Native K output is the primary protocol. An optional overfetch plus exact-refinement variant must have a new label and include candidate generation, gathering, recomputation, selection, conversion, D2H and synchronization in its timer. Never pair refined recall with native CAGRA/IVF time. Do not substitute radius-derived pseudo-kNN for the API.

### Two batch regimes

1. **K10-MATCHED:** all methods receive the same B1 or B32 ready-submission contract, including the actual16-query tail. Report that constraint explicitly.
2. **K10-BULK:** all10k inputs are ready. On the separate bulk-development10k pool choose each native method's best legal chunk size from `{32,128,512,2048,8192}` plus a single10k call when supported and memory-admissible. Validate the actual bulk algorithm/configuration on that entire development pool before freezing; native auto-dispatch can change with batch shape. Candidate/GTS may use their supported internal chunking; if they cannot batch beyond32, retain that limitation rather than forcing native libraries down to32. Freeze policies before final generation. Include every query-input/output bridge and final Host-ready completion. Bulk per-query amortization is not request latency.

The official Faiss guide emphasizes batching and scratch reuse. Keep sensible resource memory; do not disable scratch allocation or force repeated setup only for a comparator. Record peak persistent and temporary memory for each method; enforce a preregistered, common device-memory admission limit after inspecting the actual GPU. Dataset/layout/index storage and workspace are reported separately.

Python/C++ control cost stays in the actual end-to-end entry timer. Also provide a device-ready diagnostic scope and, if host-language overhead is materially dominant, a minimal equivalent native entry control. Do not compare a Python-controlled system with a C++ system as if the difference were a tree-kernel result.

## 7. K10 measurement, statistics and stability admission

### Timing scopes

- **Warm Host-ready pass, primary:** before the first input submission until all10k final IDs/fields have reached Host. Includes query packing/gather/H2D, seed/topK, tree/mask, verification, sorting/selection/merge, runtime allocations/frees, output conversion, D2H, waits, and fallback.
- **Cold total, separate:** data load/transfer, layout, training/build/load, bound refit, graph capture, warmup, then query pass. Report a true total and each stage; do not add overlapping intervals. Build and load are separate operations.
- **GPU-ready / device stages, diagnostic:** record with equivalent ordered device timing; never substitute these for Host-ready comparisons.
- No oracle work, validation/file writes or profiler replay in the public query timer. Persist output/timing after the timer; all output delivery itself remains included.

### Formal process design

- Six independent fresh-process rounds for every mandatory matched shape and every frozen configuration, plus six bulk rounds per dataset/K/configuration.
- Reuse P7's rotated/reversed complete-mode order; add native ANN points with a frozen balanced schedule and record realized order. Rotate shape order across rounds. Serialize all collection on one admitted idle GPU with one task lock.
- At least three numerator-before and three numerator-after rounds for each primary keeper/comparator pair; validate schedule before running. Original-GTS runs are long, so retain monitoring/thermal/order records rather than pretending all rows ran simultaneously.
- Save all raw pass and batch observations, not just percentiles. Six processes are the independent units for the primary bootstrap;10k correlated requests are not10k independent replicates.
- Primary comparison: paired process log-ratio geometric mean with seeded bootstrap95, raw round ratios, wins and order split. Also report marginal median ratio, process p10/median/p90, and complete-pass time.
- Predeclared robust performance-win threshold: lower95% bound >1.03 and at least5/6 process wins for the claimed shape/quality pair. Smaller effects are retained as inconclusive/practically small, not silently promoted. This is a per-shape gate, not an all-shape statement.
- Per-shape non-regression acceptance for a replacement keeper: upper95% bound of candidate/keeper latency <=1.03, zero quality failures, and all declared stability gates. Otherwise retain separate shape routing or do not promote.
- Use predetermined contamination rules: CUDA/runtime failure, capacity rejection, foreign GPU activity, lost evidence, undeclared revision/contract drift. A slow valid sample is not contamination. Retain rejected rows and repeat the affected complete paired round, not just the slow side; at most two replacement rounds before declaring incomplete evidence.

### Long-run metrics

For all formal runs save:

- Total10k wall time, QPS, amortized cost, batch p50/p95/p99 and maximum.
- B1 request latency percentiles; B32 **batch** percentiles. Do not divide a batch percentile by32 and call it request latency.
- Per1k-query window quality, throughput, CPU user/system time, RSS, device memory, allocation/free counts, launch counts, copies and synchronization counts. Avoid high-frequency instrumentation in formal timing; compare overhead if an in-process hook is added.
- First-versus-last windows, tail shape, invalid IDs, stale-state failures, output hashes, CUDA status and progress.
- CPU busy-core equivalents for the query scope = query-scoped user+system CPU-time delta / the same query wall-time interval; report thread distribution. Do not divide cold-setup CPU time by warm-query wall time. CPU API wait duration is a different quantity.

Proposed stability gate: no mismatch/runtime failure; no growing outstanding allocations; at most64 MiB retained-memory increase after warmup over the10k pass unless a documented bounded lazy allocation is registered before final runs. If the last2k throughput is >10% lower than the first2k in two or more uncontaminated rounds, retain the drift and investigate; do not declare a sustained stable version from the overall median alone. Clock/thermal drift is a diagnosis, not automatic evidence of a memory leak.

After the main matrix, run three consecutive10k passes in one process on GIST/K8/B32 for OPT_KNN_STABLE, Flat, IVF_ALL and the frozen high-quality CAGRA point. The first is the preregistered input order, the second reversed, the third a preregistered permutation. No retuning; verify all outputs and record pass/window behavior. This30k sustained test supplements, not replaces, the10k fresh-process matrix. Repeat on a shape that shows a drift or boundary failure under a new registered diagnostic.

## 8. A0/A1: complete query/insert/delete operator census

Create a source-to-runtime operator inventory before selective NCU collection. Every row must be marked `measured`, `not executed in this trace`, `unsupported`, or `pending`, with the exact entry/shape. Do not silently drop a cold/update operator because the static query trace does not execute it.

| Workflow stage | CPU evidence | GPU / memory evidence | Attributable candidate/control and validity condition |
|---|---|---|---|
| File/load/input preparation | Parsing, packing, user/system CPU, cold wall time | H2D/D2D bytes, pinned/pageable input | Reuse input representation; cold work not folded into warm-query attribution |
| Initial allocation and resource setup | Allocation API and library resource creation | Managed/device allocation sizes and lifetime | Reasonable reusable capacity control; preserve numeric/search semantics |
| Construction pivot distances | Host dispatch/control | Exact selected construction kernels, coordinate work, traffic | Mapping/reuse only with unchanged topology/member coverage |
| Construction sort/permutation | Library invocation vs actual CPU execution | Device sort, scan, D2D, key/index writes | Do not call host-invoked GPU sort CPU computation |
| Query input/gather | Host ID/vector packing and submission | H2D, gather reads, stream/event dependency | Common input contract; all bridge costs timed |
| Tree query-pivot evaluation | Layer/queue scheduling | Warp addresses, actual pivot IDs, reuse, bounds work | Share only identical pivot identity and unchanged version/bound certificate |
| kNN seed distances/topK/cutoff | Seed dispatch and control | Seed scans, selection/merge, cutoff writes | All work timed; no oracle threshold or deleted seed ID |
| Tree flags/frontiers/masks | Count reads and next-layer control | Clear, counts, prefix, masks/list/task construction | Same candidate set; include any added materialization cost |
| Leaf/object validation | Submission and wait | `dataProcessKnn` and actual range kernels; dimensions, sectors, DRAM, FP32/FP64/SFU | Same arithmetic/quality; separate work reduction from address coalescing |
| Early exit | No hindsight skip | Coordinates executed, divergence, cutoff tests and mask misses | Identical cutoff semantics; all survivor outputs unchanged |
| Result counting/prefix | Host count feedback and scheduling | Counts, scan, atomics, state reset | Remove only a dead dependency; actual-length output dependency cannot be discarded |
| topK/sort/merge | Actual CPU selection if any | Selected device sort/selector kernels, score writes and rereads | Register same fields/ties; include complete selector and workspace cost |
| Output conversion/delivery | Copy submission, actual Host completion | ID conversion, square-root fields, count D2H, result D2H | Deliver all K or all valid range outputs; no hidden padding/fields |
| Read-only native update query | Per-query allocation and loop control | Tree+buffer search, deletion prefix, `mergeTotalResult` | Reset buffer count; unchanged native multiset state across queries |
| Buffered insertion | Native append and threshold bookkeeping | Managed count/list accesses, copy if any | Existing-row native reinsertion is not fresh-vector ingestion |
| Base deletion lookup | Read returned rank/location, write tombstone | Full bitmap prefix and `findIdx` | Preserve live-rank semantics and versioned lookup |
| Buffer deletion | Branch, decrement and bookkeeping | Bitmap clear/copy/prefix, `mergeInResult` | Valid compaction/order; empty-buffer and duplicate boundaries |
| Tombstone filtering/prefix reuse | Version check, cache lifetime | Prefix/bitmap traffic and following query work | Reuse only when deletion version and object ordering are unchanged |
| Compaction | Allocate, read new size, release old state | Copy, scan, `getNewData`, ID/map movement | No dropped/resurrected member; atomic generation publication |
| Tree rebuild | Trigger/pause/publish cost | Construction distances, sort, topology and bound updates | Charge complete rebuild; legal capacities and every-member coverage |
| AoSoA/layout refresh | Allocation/packing bookkeeping | Repack bytes, mapping/bound refit | Rebuild invalidates old layout, permutation, masks and seeds |
| Graph/resource refresh | Update or recapture, pointer lifetime | Graph dependency/order, new addresses/shapes | No launch against freed/stale data or old capacity |
| Cleanup/deferred maintenance | Free/destroy and possible waits | Outstanding work and leak high-water marks | Include deferred work in full-trace denominator and explicit final drain |

Trace actual current entry points; the original stage names are a starting inventory, not proof that a specific runtime kernel executed. Match loaded function names and binary hashes. Recover SASS/resource metadata for hotspot kernels when needed; static instructions alone do not prove executed work.

### CPU work versus waiting

Collect independent NSYS developer traces for representative B1/B32 kNN, sparse/dense range, delete-to-empty-buffer, threshold rebuild, and mixed traces. Include NVTX ownership/stage ranges, CUDA APIs, copies, GPU work and host scheduling. Collect task-local CPU stack samples/per-thread CPU time with permitted existing tools; if CPU samples or UVM fault tracing are unavailable, mark the attribution unknown instead of interpreting API time as computation.

Separate parsing/packing, scheduling, allocation, CPU instructions, busy polling, blocked wait, driver work, H2D/D2H, actual managed migration/faults, and GPU idle gaps. Managed allocation alone proves neither migration nor PCIe dominance. Inclusive API wait overlaps GPU execution; never sum both to invent total cost.

### NCU recovery and bounded diagnosis

Read the installed `ncu --help`/supported metric list first. Smoke-test one bounded launch with compatible output options; confirm a nonempty kernel report before starting a profile matrix. Preserve the old prelaunch CLI failures. Do not change shared driver/permission/clock settings.

Use development32/128-query traces, not the10k formal passes. Profile the actual hot distance, seed, mask, prefix, selector, update and construction kernels. Collect matching request/sector and byte totals (L1/L2/DRAM as supported), load/store instruction families, predicated-on participants, registers, local/spill/shared bytes, occupancy/waves, active/eligible warps, and major stall sites. Freeze replay/cache options and record unsupported counters explicitly.

Normalizations: physical bytes per accepted query and per actual coordinate update; sectors per request; candidate/member counts; mask/score traffic; selector reads/writes; GPU stage time. Higher bandwidth utilization alone is not better coalescing. A fewer-coordinate result is work elimination, not automatically an address-only improvement.

## 9. A2: cheapest one-mechanism controls, then complete remeasurement

Run controls only after A0/A1 identifies a material cost. Rank by possible critical-path benefit and cost. Pure coalescing as a standalone contribution was previously canceled; diagnostic collection does not resurrect it. An address-only optimization may still be evaluated as engineering when the hotspot data supports it.

| Hypothesis | Smallest control | Required invariant | Reject/reopen condition |
|---|---|---|---|
| Repeated per-query allocation/clear creates CPU/GPU gaps | Reuse identical capacity; separately clear only provably active extent | Same arithmetic/candidates/outputs and required initialization | Lower allocation count without Host-ready improvement is not a speed claim; reopen only with a new identified gap |
| Busy CPU polling wastes CPU, not GPU work | Process-local wait-mode control, set before context creation | Same device work, sync semantics and output | CPU reduction may be useful but no throughput claim if wall time does not improve; tail regression retained |
| Host-device control feedback limits GPU readiness | Remove one demonstrated dead count/readback or use dependency-equivalent device control | Consumer no longer needs count; completion/output proof | No arbitrary cross-block fusion or weakened completion |
| Managed metadata migration is material | Device-resident metadata plus explicit bounded scalar transfer | Identical state and visibility; transfer timed | No migration counters means unknown cause; do not label all managed memory bad |
| Hot loads are strided/uncoalesced | Address/layout-only mapping control on one selected operator | Same query tile, coordinates, candidates, arithmetic, selector, launch work | If work/reuse also changes, label composite mechanism; charge packing/update maintenance |
| Dense full-score matrix/selector dominates | Reuse native selection capability or minimal bounded streaming topK | Same complete IDs, distance fields, ties and quality | Source feasibility is not runtime correctness; score-byte reduction must improve full output scope |
| Read-only queries repeat deletion prefix | Cache prefix with deletion/order generation | Exact same tombstones, ranks and output | Every base/buffer delete, compaction/rebuild invalidates as appropriate |
| Rebuild policy overwhelms updates | Reasonable-buffer repaired baseline, selected on development trace | Same admitted arrival/visibility/task and quality | Fewer rebuilds alone not enough; include query delta scan and final drain |

If two changes genuinely share a required producer-consumer contract, preregister a2x2 or equivalent interaction control; do not multiply separate speedups. Keep current static code immutable while testing a candidate in a task-owned copy.

Each control starts on bounded developer cases, then passes correctness, sanitizer and stream/Graph stress. A direction-balanced short timer may select the next candidate, but **formal promotion requires the affected10k Host-ready comparison** against the immutable keeper and the external comparator remeasured in the same new campaign.

## 10. R10: range stability, separately from native kNN

Before execution fix the exact P4 keeper and original full-output adapter. Retain both positive and adverse cases:

- GIST1M x960D, B32, sparse/half-radius and normal-radius policies from the registered range contract: two workloads.
- Deep1M x96D, B32, normal-radius policy: one workload.
- Tloc1M x2D, the registered radius policy at B1/B32, including the shallow/single-query boundary: two workloads.
- Q=10,000 unique held-out IDs per admitted workload, radii fixed as exact values/policies on development only, and six process rounds. Register any range-query exclusions separately from K10.

These are five mandatory range workloads. Copy the actual registered radius values/bit patterns and modes into the execution contract at F0; the labels “half” and “normal” are not executable radius definitions. If an original full-output adapter fails membership, arithmetic or capacity admission, retain that failure and the unresolved comparator row rather than reporting an inequivalent speed ratio.

Compare original qualified range, repaired/tuned conventional range, RANGE_STABLE, and a strong common-semantics batch scan. Reuse qualified existing external range controls when their actual input/membership/field/output gates pass. Include every count, valid-length prefix, full result field and D2H; report result bytes/cardinality and memory peak. Process queries in bounded batches so a dense10k result set cannot silently cause truncation or OOM. Any capacity rejection remains a rejection, not an omitted slow row.

**CAGRA is a native kNN comparator, not a native exact range API.** For a requested range comparison use a separately labeled CAGRA candidate-generation plus range-filter/refinement adapter, with its overfetch/capacity policy frozen on development data and all work timed. Measure full range FN/FP against the independent oracle on every query. Preserve missed objects/unsupported capacities; do not use a sampled recall or truncated output to place it in an exact-range table. An empirical full-output pass does not make the wrapper algorithmically complete.

Do not make R10 wait for a unified update implementation, and do not combine R10/kNN numbers in one speedup. R10 is the stability/scale check for the currently evidenced range mechanism.

## 11. U10: native long replay, then conditional real arrivals

### U10-NATIVE: mandatory workflow diagnosis, bounded semantics

Start from the legal native N1000,D128 fixture and the repaired original plus a timed full-output adapter. Observation prints and offline audits are excluded from timing; required output materialization/delivery is not. Hash its source/bin separately from the U0 observation binary. Preserve the unrepaired original empty-buffer counterexample separately; do not force a known-wrong baseline into a performance leaderboard.

Proposed long trace: **100 cycles, each with10 native deletions,10 native reinserts and100 query events**. Thus Q=10,000, inserts=1,000, deletes=1,000, events=12,000. Alternate50 base-maintenance cycles with50 buffer-empty cycles. In a base-maintenance cycle, perform10 legal base-delete/reinsert pairs; current pending-buffer occupancy reaches10 on the final insertion and triggers the registered native rebuild. In a buffer-empty cycle, perform10 insert-then-delete-that-buffer-occurrence pairs, returning the buffer to zero after each pair without reaching the threshold. Both cycle types start/end at1,000 live occurrences with an empty buffer. Choose legal rows/ranks with the oracle; never infer a stable external ID from a live rank.

Use `query -> update1 -> query -> update2 -> query` for each pair (three checkpoints per pair =30 queries/cycle), plus70 registered unchanged-state queries, for exactly100 queries/cycle. Preserve diversity with frozen query/rank choices. This planned trace has50 threshold rebuilds under the registered policy; validate the actual count and coverage. **The trigger is current pending-buffer occupancy reaching10, not global cumulative insertion count.** Freeze scheduling, row/rank selection, radii, expected prefixes and trace hashes before execution. Validate every constructed tree's capacity/coverage rather than assuming legality from total N.

Use three preregistered trace seeds and six fresh-process paired rounds when evaluating a candidate's performance. Full native multiset/rank oracle on every query; correct byte fields and state checkpoints on every update/rebuild boundary. If no admitted update candidate exists, execute correctness and original-stage diagnosis only; do not manufacture a unified performance comparison.

Counter/attribution rows: allocation/free, buffer bookkeeping, base lookup, bitmap prefix, buffer compaction, tree+buffer query, merge, tombstones, data compaction, construction sort, rebuild, publish, and final drain. Record query/insert/delete/rebuild latency p50/p95/p99/max, total trace wall time, cumulative maintenance, buffer/dead-object sizes, ID validity and memory high-water marks. Rare rebuild pauses must remain visible even if they do not enter p99.

The native trace inserts copies of current physical rows and deletes live ranks. It is not new-vector arrival, not stable-ID idempotent deletion, and not a representative million-object dynamic speed result.

### U10-ARRIVAL: conditional integration gate

Do not launch until the same actual keeper provides range/kNN queries, new FP32 vector ingestion, stable external IDs, legal deletion, serialized ACK visibility and maintenance. Its complete manifest must cover:

- Shared object store/permutation, AoSoA data, ID maps and tombstone generation.
- Insert-buffer publication and new-vector visibility after ACK.
- Deleted seeds and refreshed kNN cutoff/selection state.
- Refitted ancestor coverage and masks/frontiers after rebuild.
- Workspace capacity, addresses, graph update/recapture and safe release of old state.

Initial real-arrival replay: N=10,000 base objects **only if admitted by the registered tree construction**, disjoint new-vector pool, stable-ID oracle, Q=10,000 plus1,000 inserts and1,000 deletes, three seeds. One uniform trace and one clustered/skewed trace; use the same operations, metric, quality and visibility for every comparator. Scale to N1M only after correctness, capacity and maintenance admission, using a separately frozen trace.

Compare against repaired original with a **separately declared new-vector ingestion adapter**, and a reasonable-buffer conventional baseline. Buffer policy is selected on a disjoint development trace; original ten-item threshold alone is too weak an update comparator. Include all buffer queries, compaction/repack/bound refresh/rebuild, ID remap, graph recreation and required final consolidation/drain. No background or deferred work disappears from the complete trace denominator.

Native Flat/IVF/CAGRA update participation needs an installed-API audit. If native delete/new-vector/visibility is unsupported, expose an explicit wrapper/rebuild route and charge all work; do not invent an API or reuse a static graph while deleted IDs remain eligible. The new GrAND dynamic graph work is prior-art/possible comparator research, not a silently substituted native CAGRA baseline. No concurrency claim is made by the serialized trace.

## 12. Execution order, deliverables and stop rules

| Priority | Experiment | Missing evidence / question | Deliverable / next gate |
|---|---|---|---|
| P0 | N0 + F0 | Novelty boundary and runnable stable version | Overlap matrix; source/bin/index/output identities; smoke/tail/sanitizer/Graph receipts |
| P0 | A0/A1 | Actual CPU work/wait and physical GPU traffic | Complete operator inventory; representative NSYS/CPU stacks; valid bounded NCU reports |
| P1 | K10-MATCHED | Sustained original/optimized/Flat/IVF/**CAGRA** comparison | Eight shapes, actual10k, six rounds, full quality/raw order, windows and tails |
| P1 | K10-BULK | Best native batching on a10k ready workload | Frozen per-method policies, external latency/quality frontiers, memory and cold costs |
| P1 | R10 |10k validation of the existing range mechanism | Qualified range main table, full output traffic and adverse cases |
| P1 | U10-NATIVE | Longer original query/insert/delete correctness and attribution |12k-event native traces, all10k query outputs and complete maintenance accounting |
| P2 | A2 | Which single change improves the measured critical path? | Attributable controls, negative results, affected10k remeasurement |
| P2 | U10-ARRIVAL | Integrated real-arrival semantics and complete dynamic benefit | Conditional keeper/adapters, full trace vs reasonable-buffer and admitted external update routes |

F0/A0 can progress without starting the costly matrix. Start matched B32/K8 GIST+Deep as the first formal slice, then remaining B32/K32, then all B1. All required shapes remain in the acceptance checklist. If research novelty fails, preserve the K10 requested verification while stopping unrelated bespoke optimization. Profiling and formal timing are never concurrent.

### Cost checkpoint — forecast, not a measured10k result

Linear scaling of the P7 original-GTS256-query medians suggests approximately53 minutes for one GIST/K8/B32 original10k pass, and approximately60 minutes for GIST/K8/B1. Original GTS alone across all eight shapes and six rounds projects to about25 GPU-hours. Other methods, oracle generation, development, cold setup, bulk, range, updates and profiling add cost. Runtime distribution/queries may change, so re-estimate after the1024 developer screen and fill actual per-process limits; do not report forecasts as timing results.

This cost motivates staging, not replacing10k by256 or omitting the original comparison. No calendar completion promise or GPU reservation is implied. Native CAGRA work is budgeted in both kNN matrices from the beginning.

### Per-run execution card

```text
Experiment / exact evidence gap / planned claim boundary:
Host and task-owned code/scratch paths:
Source, branch/commit, binary SHA-256 and build command:
Comparator/candidate entry and adapter identity:
Data/index/query/trace SHA-256, N/D/Q/K/B/tail:
Metric, arithmetic, ties, fields, IDs and visibility:
Installed environment, GPU model/UUID, driver/toolkit/library:
Process CPU affinity, NUMA placement and library thread-pool settings:
Live users/processes, idle single-GPU admission and lock:
Do-not-touch processes/services; no shared clock/driver changes:
Warmup, process order, estimator, scope and memory admission:
Actual command, raw output path, owned PID/process group:
Progress interval, calibrated timeout, stop/drain/rollback:
Correctness, sanitizer, stress, complete-output and evidence gates:
```

Use any currently idle admitted single GPU, not a fixed GPU0 or remembered GPU7. Select once for a campaign and keep each comparison on that physical GPU; switching GPUs requires a separately matched campaign. Never signal another user's processes. Stop only task-owned work on wrong results, invalid capacity, CUDA failure, foreign activity, lost identity/evidence or undeclared semantic drift. Retain the first failing boundary and every rejected sample.

### Required durable evidence

- Contract with source/bin/data/index/queries/trace, library identity and actual hardware, stored before measurement.
- Raw realized schedule and every process/batch result, including rejected/failed configurations.
- Complete10k IDs/fields or hashed externally stored bundles plus independent oracle receipts; no summary-only correctness claim.
- Separate NSYS/CPU/NCU manifests, selected kernel identity, counter status and overhead/denominator notes.
- CSV/JSON tables generated from raw records: latency/recall frontiers, matched and bulk, windows/tails, cold setup/memory, workflow accounting and ablations.
- Append the existing evidence ledger; statuses distinguish measured, partial, unknown, unvalidated, inconclusive and rejected. Record implementation decision, mechanism decision and thesis impact separately.
- Every negative result names target, workload, keeper, failed mechanism, added costs, measured effect, diagnosis and a falsifiable reopen condition.
- Curated technical reports/code go to the matching project after publication review; large raw data/indexes/profiler state remain external with hashes. No private paper, credentials, conversations or device configuration in the public artifact.

## 13. Completion checklist

- [ ] One qualified static query keeper is pinned; no diagnostic HEAD relabeled as a unified system.
- [ ] Mandatory original GTS, native Flat, native IVF and native CAGRA paths are all executable or their exact unresolved failures are stated.
- [ ] Fresh10k unique queries per dataset; no repeated256-query surrogate; final sets never tune parameters.
- [ ] All eight matched shapes and all four bulk dataset/K shapes have complete six-round evidence, or named incomplete rows remain pending.
- [ ] Every complete-mode query passes full membership/fields; ANN targets and actual recall remain distinct.
- [ ] Actual16-query tails, full10k delivery and process/order/quality receipts retained.
- [ ] Window/tail/memory/CPU stability and the additional30k sustained control are evaluated.
- [ ] Query/insert/delete/compaction/rebuild operator inventory has no unlabeled holes.
- [ ] CPU computation/wait, actual copies/migration and GPU work are separated; no overlapping-time sum.
- [ ] Coalescing/work-elimination claims have appropriate causal controls, or remain explicitly unknown/narrow.
- [ ] Range and dynamic results have their own contracts; native CAGRA kNN is not mislabeled as exact range or dynamic API support.
- [ ] New-arrival dynamic work is admitted only after a real keeper and explicit external-ID/ingestion/visibility protocol.
- [ ] Final decisions lead with external evidence, material exceptions and retained negative results, not original-only headline speedups.

This checklist is a plan, not a completed experimental receipt. The next executable delivery must supply the actual commands, identities and qualification outputs before launching the formal matrix.
