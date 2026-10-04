# GTS execution recovery: workflow attribution and real 10k comparisons

Date: 2026-10-04. **Plan only; this document does not certify new implementation or GPU execution.**

## 1. Decision and immutable anchors

Resume the requested verification without turning native Faiss numerical repair into the project. Pin actual query candidates, finish the missing original-workflow attribution, and collect native IVF/CAGRA comparisons on held-out 10k queries. A static scan executor is not automatically an integrated tree/update system.

This amends execution roles, failure isolation, and collection-versus-admission gates in [PLAN_10K.md](PLAN_10K.md), frozen at `480bc7dbdfaf6ff7048bc810d29f6b4aecbf2e16`; its SHA-256 remains `0f48f8c8c4a21165d4593ddbab5324d7be9b67f44b9205fd95899ed6efcdfb5a`. Preserve that file and all previous failures. Dataset/shape/count, strict oracle, field tolerance, warmup, full output, six rounds, tails, and sustained requirements remain in force.

| Anchor | Published state / use |
|---|---|
| [Latest execution](https://github.com/wangwenqingqq/GTS-variants/tree/86cb65f1347d7e7d2269c04636aa52c3ef6a5f84/diagnostics/next_campaign_20261004) | `86cb65f1347d7e7d2269c04636aa52c3ef6a5f84`: qualification/diagnosis; zero formal static processes |
| [P7 sources](https://github.com/wangwenqingqq/GTS-variants/tree/7bce3679c3e32e77fa25cf7842805926509e1412/diagnostics/unified_knn_e2e_20261003) | Published source `7bce367`; search implementation `d65c6e41effad67dde8ae1f1f68e656562607817` |
| [Results](https://github.com/wangwenqingqq/GTS-variants/blob/86cb65f1347d7e7d2269c04636aa52c3ef6a5f84/diagnostics/next_campaign_20261004/RESULTS.md) | GIST/K8/B32 developer1024; native Flat rejected; CAGRA32 diagnostic is not its development grid |
| [Operator inventory](https://github.com/wangwenqingqq/GTS-variants/blob/86cb65f1347d7e7d2269c04636aa52c3ef6a5f84/diagnostics/next_campaign_20261004/OPERATOR_INVENTORY.md) | Extend this ledger, not a parallel evidence framework |

Published evidence is not live host admission. Recheck remote source, inputs, active users/processes, environment, and GPU before execution. Use any currently idle admitted single GPU, preserve other jobs/settings, and keep each paired campaign on the same physical GPU with one lock. Private paths, device identifiers and process details belong in the private execution card.

## 2. P0: pin roles and repair the controller without GPU work

### Actual candidate identities

| Role | Starting entry | Boundary |
|---|---|---|
| Original static baseline | Original search plus declared full-ID/capacity/output adapter | Preserve original arithmetic; not a byte-identical upstream binary |
| Tree kNN candidate | P7 `O_MASK` | Tree mask, seed cutoff, verification and complete topK |
| Scan kNN control | P7 `O_BOUND` | Whole-database object traversal/early exit; no tree-mask pruning |
| Full scan control | P7 `O_FULL` | Same selector/output without cutoff early exit |
| Range candidate | Existing qualified P4 entry, after identity/contract closure | Separate range entry; do not substitute kNN |
| Native update baseline | Original U0 entry with declared `rnum[0]=0` repair | Physical-row reinsertion, live-rank deletion, serialized multiset |
| Integrated update candidate | None certified at this checkpoint | Unavailable; not a prerequisite for static verification |

Record source/build/binary/input hashes, caller, output semantics, and setup/maintenance costs for each role. A development-selected tree/scan dispatch needs an explicit frozen rule and charged dispatch/refresh. Keep both tree and scan evidence; a scan win is not tree-pruning evidence. Do not label any static entry a unified range/kNN/update keeper.

### Minimal harness changes

Reuse `campaign10k.py`, `continue10k.py`, `hook_control.py`, and existing analyzers; no new framework, dependency, or search-algorithm change just to reach10k.

1. Replace the complete-mode assertion as a **global campaign exception** with a persisted per-method/per-shape quality decision. Preserve failed audits and outputs; never convert them into passes.
2. Make IVF/CAGRA development independently schedulable. Flat strict-quality failure must not block them, other datasets, range diagnosis, or legal update attribution.
3. Check every formal ANN process against its frozen reachable target anchors. An unreachable target's highest-quality point remains `diagnostic_only`, not target-admitted.
4. Retained growth above64 MiB must fail stability admission, not just set an unused Boolean. Keep the common80 GiB device cap on the previously used96 GiB model; re-register a common cap if hardware changes.
5. Separate `collection_complete`, `candidate_stable`, and strict/target-quality admission. A collected matrix can contain rejected diagnostic baselines; missing required external executions keep comparison completion pending.
6. Resume checks cover source/scripts, binary, command, data/index/graph, query/oracle, and observer mode. Hashing only the Python interpreter cannot identify its measured script. Earlier receipts can support exact-scope qualification, not a new timing process after drift.
7. Finish hook-on/off controls before final timing, including original and native adapters and representative fast B1/B32/bulk paths. Require hash-identical outputs. Native strict-quality rejection must not block observer-cost diagnosis. Keep coarse snapshots in the declared formal timer only after cost is quantified/disclosed. Material method-dependent overhead blocks that timer's admission until repaired; no guessed subtraction or silent removal of required window evidence.

**Small runnable check to implement:** one standard-library CPU-only regression with mocked receipts/audits: rejected Flat remains recorded while independent CAGRA is schedulable; wrong candidate blocks promotion; missed ANN target is ineligible; unreachable100% stays diagnostic; excessive memory growth rejects stability; changed script invalidates cached admission; missing required rows cannot yield accepted-comparison status.

**Exit:** inspected diff, passing CPU-only check, versioned admission policy, role cards, and runnable actual commands. The current published `pipeline` must not be blindly resumed before repair. This plan does not invent unsupported CLI switches.

## 3. Failure policy and numerical contract

| Event | Required action |
|---|---|
| Foreign GPU activity, CUDA/runtime error, invalid capacity, corrupt input, identity loss/drift | Stop affected task-owned collection and retain receipts; never signal foreign jobs |
| Candidate wrong result | Stop that candidate's admission/promotion; localize first failure; independent admitted work can continue |
| Native library fails strict membership or field tolerance | Preserve native time/quality as rejected diagnostic evidence; exclude from strict complete-quality table; continue independent methods |
| ANN misses a reachable frozen target | Retain process, mark target ineligible; no final-set tuning or favorable rerun selection |
| Target unreachable on development | Freeze highest-quality legal diagnostic point; retain attainable target comparisons |
| Stability failure | No stable label for affected entry/shape; retain slow valid observations |

The strict oracle remains independent explicit-RN FP64 squared L2, no FMA, exact kth-boundary ties. Full membership and `abs(delivered_distance**2-reference_squared) <= 5e-5*max(1,reference_squared)` remain unchanged. Native FP32 outputs retain their arithmetic label. Native quality frontiers and strict complete-quality tables are separate; no ratio combines native time with another adapter's refined quality.

Do not continue tuning finite-overfetch `FAISS_FLAT_REF64` in this campaign. Retain its GIST pass and small96 failure. A different numerical adapter or precision policy requires a separate contract, not a hidden baseline repair.

## 4. P1: fill missing original-workflow attribution

Reuse the78 bounded qualification processes,12 static NSYS traces, eight NCU reports, and three U10 correctness traces where hashes/contracts match. Requalify changed entries; do not rerun unchanged evidence merely to populate another report.

| Missing question | Minimum next collection | Required evidence |
|---|---|---|
| Useful CPU computation versus driver wait/polling | Inspect existing stacks/query CPU deltas; bounded replacement only for unresolved sites | User/system CPU, thread distribution, API wait, GPU union, copies and host gaps separately; unresolved symbols stay unresolved |
| Distance arithmetic versus memory traffic | Actual measured-pass launch/work ledger for original `dataProcessKnn` and matching control | Query/object/coordinate counts, early exits, requests/sectors, L2/DRAM bytes, FP64 instructions/stalls, registers/spills, same-scope stage time |
| Cold construction cost | One legal representative original build per dataset if existing evidence lacks it | Pivot distances, sort/permutation, allocations, topology/coverage, Host-ready build time; load and build separate |
| Insert/delete/compaction/rebuild cost | Lean full-output U0 timed adapter; bridge one registered seed before the other two | Exact state/IDs/fields/operations/rebuild counts; observer printing outside timer |
| Redundant state maintenance | Existing legal base/buffer deletion, prefix, merge, compaction/reset/rebuild replay | Actual counts and state/version transitions; safe invalidation required for reuse |

Select actual query-pass kernels, not an unspecified first warmup match. Different iterative launches are not equal work. Physical bytes and sector ratios must be normalized by actual coordinate/object work; high FP64 activity alone does not prove a compute-only bottleneck.

The lean U0 adapter retains every operation and full result delivery. Use bounded output buffering or an equivalent full-output path; write files and validate after timing. Record query/insert/delete/rebuild ACK latency p50/p95/p99/max, total trace wall time, maintenance, peak memory and final drain. Compare full outputs to the preserved oracle and observer entry; qualify adapter overhead before admitted timing.

U10 remains N1000/D128, three registered seeds, each with10k queries +1000 inserts +1000 deletes +50 threshold rebuilds. It diagnoses native multiset operations, not N1M dynamic throughput, new-vector arrivals, stable external IDs, or concurrency. Missing real-arrival APIs do not block native diagnosis.

**Exit:** every original inventory row has a trace/source identity and `measured`, `not executed`, `unsupported`, or `pending` status. Pending runtime rows mean the whole-workflow audit is incomplete. Never add overlapping inclusive CPU wait and GPU time.

## 5. P1: native development, independently of a new optimization

This lane can run once identities and the repaired controller qualify; it need not wait for an integrated update system or a successful new optimization.

- GIST N1M/D960 and Deep N1M/D96; K8/K32, B1/B32. Preserve original GTS, tree/scan/full controls, native Flat, native IVF and native CAGRA.
- Registered developer1024 seeds `2026100411/12`; separate bulk-development10k seeds `2026100413/14`. Verify hashes/exclusions; old receipts are qualification evidence only at matching identities.
- IVF: nlist1024/4096; legal nprobe16/64/128/256/512/1024/2048. Retain all-list nlist1024/nprobe1024 and actual quality.
- CAGRA: pinned graph degree64/intermediate128; `itopk_size {64,128,256,512,1024}`, `search_width {1,2,4}`, installed legal algorithm/default iteration policy. Two developer passes per shape/configuration. Retain failures and the highest-quality point if100% is unreachable.
- Select99%,99.9%, empirical100% on development only. Preserve unrounded recall, worst query, complete-query fraction, missing/invalid/duplicate IDs, and field validity.
- Bulk: all10k inputs ready; native chunks32/128/512/2048/8192/single10000 when legal. Validate actual large-chunk quality on bulk-development10k, including native auto-dispatch. Audit batch-dependent parameter re-selection; a matched-only config subset does not establish a global native optimum. GTS/P7 supported B32 chunking remains an explicit limitation.

**Exit:** two-pass IVF/CAGRA receipts on all development shapes and frozen matched/bulk policies. Native Flat repair is not an exit requirement; its diagnostic quality remains visible.

## 6. P2: one cheap claim-relevant mechanism control

Choose at most one missing control from the workflow evidence; reuse existing P4/P7 controls first. Link the nearest overlap and cheap novelty falsification test from the existing N0 ledger before any new mechanism. A subsumed idea is not rescued by routine engineering; novelty failure does not cancel requested external verification.

| Control | Invariants / decisive check |
|---|---|
| Address-only coalescing | Same query tile, object/coordinate work, arithmetic, early exits, selector and launch work; include packing/refresh; lower sector amplification plus Host-ready benefit |
| Cross-query reuse/intermediate elimination | Identify eliminated reads/writes and added shared/register/selection costs; full outputs unchanged; do not call it pure coalescing |
| Prefix/workspace/state reuse | Same legal state and invalidation/version rules; include update/rebuild refresh and final drain |
| CPU wait policy, only if stack evidence supports it | Same GPU work/results; CPU savings reported separately, not automatic end-to-end acceleration |

Start with development Q128 and six fresh alternating A/B and B/A process pairs on the selected shape, including its adverse B1/B32 boundary where relevant. Profile only to discriminate mechanisms. Retain target, workload, keeper, costs, effect, diagnosis and reopen condition for rejection. If no attributable Host-ready benefit appears, freeze qualified existing controls and continue10k; no broad optimization sweep.

FP32-versus-FP64 replacement is a separate precision experiment, not address-only optimization. No Tensor Core tree restructuring or new insertion system is scheduled.

## 7. P2: real held-out10k static comparisons

1. Freeze source/binaries, index/graph, candidates/dispatch, native configs/chunks, observers, order, estimator, exclusions, memory and calibrated timeouts.
2. Verify final seeds `2026100421/22` remain unused in live state. Generate10,000 unique IDs per dataset after policy freeze, disjoint from historical/development/bulk-development queries. If another campaign consumed them, preregister a new generation and expanded exclusions; never tune on any final set.
3. First formal slice: **GIST and Deep K8/B32**, every required method, **six fresh-process rounds**, including native IVF/CAGRA.
4. Complete K32/B32, then K8/K32/B1: **eight matched shapes total**. B32 means312 full32 batches + one16-query tail, not10016 padded queries.
5. Complete **four bulk dataset/K shapes**, six rounds each, using frozen per-method chunk/config policies. Report amortized throughput, not matched request latency.

Use eight separate development warmups per actual full/tail shape. Re-measure comparators in the same campaign with balanced before/after order and shape rotation. Host-ready timing includes gather/H2D, seed, tree/scan, verification, selection/merge, runtime allocation, conversion, full IDs/fields D2H and synchronization. Cold load/layout/build/refit/capture/warmup has a separate true total; maintenance is never hidden.

Preserve every process/batch. Primary estimator: paired log-ratio geometric mean, seeded bootstrap95; also marginal medians, p10/median/p90, wins and order split. Robust win: lower speed-ratio confidence bound >1.03 and at least5/6 wins; registered non-regression band1.03. At most two predeclared contaminated-pair replacements. Slow valid samples and real quality failures are not contamination.

All formal processes retain full per-query output audits, tail/batch times, and near1k-window quality/throughput/CPU/RSS/device memory evidence under the qualified observer contract. Growth>64 MiB rejects stability; throughput decline>10% between the first/last2k in at least two rounds requires diagnosis. Do not convert missing allocation/launch/copy counters into zero.

**Tables:** strict complete-quality rows; native quality/latency frontiers with target eligibility; rejected/diagnostic rows; tree-versus-scan controls; cold cost/memory/window/tail stability. A minimum recall target is not equal achieved quality. Lead with external results, including losses; never multiply historical component ratios.

**Exit:** all mandatory native methods executed, eight matched/four bulk conditions collected or named incomplete, every process audited, candidate stability and target/strict admission separately decided. Collection alone never earns a stable label.

## 8. P3: close range, sustained behavior and native update evidence

- **R10:** five existing conditions: GIST half/normal B32, Deep normal B32, Tloc B1/B32. Frozen radii, held-out10k, six rounds, complete variable-length IDs/fields and FN/FP oracle. Fix/qualify the original range parser's16-tail limitation first; never silently use10016. Native CAGRA kNN is not an exact range API; any wrapper requires its own contract/full cost.
- **30k sustained:** three consecutive10k passes in one process on GIST/K8/B32 for the selected static candidate, native Flat, IVF_ALL, high-quality CAGRA: registered order, reverse, registered permutation. Full outputs and1k windows mandatory. A rejected native row remains diagnostic, not qualified by repetition.
- **Native update timing:** finish the lean adapter bridge and three-seed original-stage ledger. If an actual update candidate qualifies, use the same three traces with six fresh paired rounds and all maintenance/final drain. Otherwise report original attribution only, no invented dynamic speedup.
- **Real arrivals:** conditional on implemented new-vector ingestion, stable IDs, legal capacity/coverage, deletion, serialized visibility and maintenance. Do not silently add an integration project as a prerequisite for static verification.

## 9. Operational checkpoints, budget and deliverables

At each transition state the exact missing claim/evidence, why existing receipts cannot answer it, and strongest competing explanation. Append existing ledgers; do not build a second framework.

Before every GPU phase, fill the private card: host/task-owned path, source/build/binary, environment, live users/processes/GPU and lock, data/index/query/trace hashes, N/D/Q/K/B/tail, numerical/output/ID/visibility contract, warmup/order/timer, actual command, logs, owned PID, timeout, do-not-touch list, stop/drain/rollback and expected validation. Do not reserve a remembered GPU or change shared clocks/driver settings.

The published GIST/K8/B32 original1024 pass was321.237s. Linear scaling forecasts about52.3 minutes per original10k pass, or5.23 GPU-hours for its six rounds alone; this is not measured10k. The older original-only eight-shape forecast was about25 GPU-hours, excluding development, other methods, profiling, bulk, range and sustained work. Re-estimate from the repaired screen and checkpoint the budget before expensive collection. Stage work without reducing queries/shapes/six-round acceptance. No fixed finish date or current GPU availability is asserted.

| Order | Deliverable | Meaning |
|---|---|---|
| 1 | Role cards + minimal controller diff + CPU-only regression + observer-cost decision | Runnable recovery, not new performance evidence |
| 2 | Missing query/build/update ledger + lean U0 output bridge | Original-workflow attribution; remaining holes named |
| 3 | Two-pass IVF/CAGRA development + frozen policies | Comparison proceeds without repairing Flat |
| 4 | One claim-relevant cheap control, or no-new-change decision | Attributed evidence/negative result, not novelty by default |
| 5 | First GIST/Deep K8/B32 six-round10k slice, then eight matched/four bulk conditions | Same-campaign external verification at declared quality |
| 6 | R10,30k sustained, native timing/conditional candidate comparison | Separate range/stability/native-workflow gates |

Publish only reviewed technical code/contracts/results to the corresponding repository. Raw data/indexes/profiler captures/outputs stay external with manifests/hashes; no private manuscript or device configuration. Final delivery lists role commit/binary, validation scope, rejected results, remaining gates and independently verified remote state.
