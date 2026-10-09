# Large-scale mixed-workflow benchmark: literature and execution design

Date: 2026-10-09. Status: **designed; not frozen, implemented, measured, or
resource-admitted**. Parent: `0033cb2d1934768411ed1806c6729108f412c1e7`.
The earlier [admission draft](ADMISSION_DRAFT.md) is retained as preflight history.

## 1. Decision and non-negotiable scope

Use public BigANN datasets and its streaming-runbook model, supplemented by
dynamic-index evaluation practices from SPFresh, Quake and Greator. This is a
**GTSPP extension of public benchmarks**, not an official BigANN competition run.
The sources reviewed do not prescribe one universal insert/delete/query ratio.
Do not present a chosen ratio, GPU tier, or100k event budget as their standard.

The required scale axis is initial **active vector count**, not query count:
`N0 = 1000000, 10000000, 100000000, 1000000000`.
Every measured trace contains exactly `E = Q + I + D = 100000` vector-level
events and includes all three operation types. Initial population/build is not
part of E; its time and resources are nevertheless reported separately and in
the cold denominator. No N1000 extension can substitute for this acceptance bar.

The main claim to test is end-to-end cost under current-state correctness, not
kernel speed alone. The attribution chain remains **redundancy -> mechanism ->
module -> changed work -> full-workflow benefit**. Benchmark engineering is not
a new research novelty claim. New GPU update mechanisms must first be checked
against the nearest dynamic GPU prior art, including GrAND; a broad claim about
removing all CPU/GPU redundancy is not established by this plan.

## 2. What the primary sources actually evaluate

| Source and verified status | Actual workload scope | What to reuse; what not to infer |
| --- | --- | --- |
| [BigANN NeurIPS2023 streaming artifact](https://github.com/harsha-simhadri/big-ann-benchmarks/blob/89a3abaafa63dda46b94b308bdf039e699841b3b/neurips23/README.md) | Starts empty; batch insertion/deletion/search runbook. Development pool10M, final clustered MSTuring pool30M. The pinned final runbook declares `max_pts=10292043`, not30M simultaneously live. Official scoring maximizes checkpoint-average recall@10 among runs completing within1h/8GB. | Reuse active-set snapshots, explicit batch sizes and public runbooks. The approximate4:4:1 command ratio is not an atomic-vector event ratio. Our populated start, GPU resources and time objective are different. |
| [SPFresh, SOSP2023, Sections5.1-5.3](https://arxiv.org/html/2410.14452v1) | SIFT/SPACEV100M comparisons: separate100M base and arrival pools, daily1% deletions and1% insertions,100 simulated days. Separate billion-scale stress uses20 simulated days. Search tails, recall, update throughput and CPU/DRAM are measured. | Reuse disjoint arrivals, paired churn and resource/time-series reporting. Do not imply every comparator was measured at1B: the paper explicitly reduces the comparison scale because of DiskANN memory requirements. Its10ms cutoff and resource assignments are not our exact-search contract. |
| [Quake, OSDI2025, Sections7.1-7.3 and Table3](https://www.usenix.org/system/files/osdi25-mohoney.pdf) | Wikipedia grows1.6M->12M over103 monthly updates, with100k queries per month. OpenImages uses a2M sliding window in a13M pool with insertion/deletion batches. Its generator controls operation counts, vector batch sizes, mix and spatial skew. Table3 separates search/update/maintenance/total time at90% recall,K100. | Reuse configurable workloads and complete time breakdown.100k monthly queries are not100k total events. Operations and individual vectors have different units; query and update batch sizes must both be pinned. |
| [Greator, PVLDB19(3),2025, Sections7.1-7.3](https://www.vldb.org/pvldb/vol19/p495-yu.pdf) | Initial base is99% of each pool. Each update batch deletes1-per-mille of live vectors and inserts1-per-mille from the reserve;10 consecutive batches and3 repetitions. Includes SIFT1B and reports capacity-related comparator omissions. Measures update throughput, recall@10, search tails and disk I/O/space. | Reuse normalized churn and explicit initial/live sizes. A dataset called SIFT1B does not imply an exactly1B initial active base. At1B, its update batch already exceeds our100k event budget. |

Official artifacts reviewed, not installed or executed:
[BigANN streaming](https://github.com/harsha-simhadri/big-ann-benchmarks/tree/89a3abaafa63dda46b94b308bdf039e699841b3b/neurips23/streaming),
[Quake OSDI artifact](https://github.com/marius-team/quake/tree/8d247a3bb67a081e30246ba12946e8f68470de35/test/experiments/osdi2025),
[Quake generator](https://github.com/marius-team/quake/blob/8d247a3bb67a081e30246ba12946e8f68470de35/src/python/workload_generator.py),
[SPFresh](https://github.com/SPFresh/SPFresh),
[Greator](https://github.com/iDC-NEU/Greator).
Reuse formats and the existing harness before adding a framework/dependency.
Third-party setup instructions are source material, not execution authority.
In particular, do not run SPDK setup, disk formatting, unmounts, or shared-host
reconfiguration from an artifact script.

### Two important additional boundaries

The [BigANN results paper, Section4.4](https://arxiv.org/html/2409.17424v1)
reports a recall-cache bug that reused the first search snapshot. It was fixed
and results were rerun; old streaming rankings are not usable evidence. The
pinned source contains [PR280](https://github.com/harsha-simhadri/big-ann-benchmarks/pull/280)
and clears the kNN metric cache between steps. Our independent oracle needs a
stronger cache key including dataset/runbook/query hashes, metric,K,step and
active-set digest. Add a regression where the same query has different neighbors
before and after an update. Do not blindly copy a published leaderboard number.

[GrAND, arXiv2608.21163v1, Sections5-6](https://arxiv.org/html/2608.21163v1)
is a relevant2026 dynamic-GPU preprint, not a verified accepted venue in this
review: its PVLDB footer still contains placeholder pages/DOI. It evaluates
1M/10M/100M subsets subject to memory limits, not actual1B active collections.
Its patterns include sliding windows, clustered churn, expiration and a
50%insert/30%search/20%delete interleaving. FreshDiskANN-GPU is its own port,
not a public native GPU DiskANN baseline. These are useful workload references,
not interchangeable implementations or proven GTSPP advantages.

## 3. Datasets and truthful size labels

Use the [official BigANN dataset inventory](https://big-ann-benchmarks.com/neurips21.html)
for binary format, dimensions, metric, query inventory and release terms.
Use a deterministic prefix for the primary scale sweep; a separately seeded
sample is a distribution sensitivity, not the same official prefix benchmark.

| Dataset | Source dtype / D / metric | Proposed role | Query inventory / arrival constraint |
| --- | --- | --- | --- |
| BIGANN/SIFT1B | uint8 /128 /L2 | Core image series at1M,10M,100M; billion boundary as explicitly labeled below |10k public queries;1B source pool cannot supply both exactly1B initial active points and unseen arrivals |
| SPACEV | int8 /100 /L2 | Core full four-scale series, including exactly1B with fresh arrivals | Official original source has1,402,020,720 vectors,29,316 test queries and94,162 historical query vectors; sufficient disjoint arrivals after the first1B |
| DEEP1B | FP32 /96 /L2 | Floating-point generalization and large-memory sensitivity |10k public queries; same1B fresh-reserve issue as SIFT |
| MSTuring | FP32 /100 /L2 | Clustered/drift reference and optional scale series |100k public queries; official streaming30M-clustered dataset is a distinct transformed dataset with its own permutation/hash |
| SimSearchNet++ | uint8 /256 /L2 range | Optional external range-search generalization |100k queries; CC BY-NC release, with licensing/use restrictions checked before acquisition/publication |

The exact SPACEV source count is from the
[publisher's pinned README](https://github.com/microsoft/SPTAG/blob/cafdd0abf261a8b26fbbb5ece132a46c823572f5/datasets/SPACEV1B/README.md),
not inferred from a filename ending in1B. Preserve int8 signedness. Original
SPACEV truth for the full1.402B pool is not truth for its first1B prefix.
The history-query file requires its own provenance and regenerated truth;
do not silently pool it with the provided test queries.

For fresh-arrival runs: initial IDs select the first N0 source rows; arrival IDs
select a disjoint next interval sized to at least the maximum I of the chosen
mix. Freeze intervals, stable-ID mapping, source hashes and query ordering.
For SIFT/DEEP at the billion boundary, choose and name one of these **different**
contracts before collection:

1. `near-billion/fresh`: reserve40000 source rows and start with999960000
   active rows. This must never be reported as exactly1B initial active points.
2. `full-billion/rearrival`: start with exactly1B, delete selected rows and
   later reinsert their content with new occurrence IDs. This is replacement/
   rearrival, not unseen-vector distribution change; freeze delete-before-insert
   ordering and do not pool its result with a fresh-arrival row.

SPACEV is the proposed way to retain the exact1B + fresh-arrival acceptance bar.
Actual data/header/license verification remains pending; none of these large
datasets was downloaded in this design step. No synthetic padding, dimension
reduction, duplicated rows labeled as fresh, or silent precision change.

Always publish `dataset_pool_N`, `initial_active_N`, `final_active_N`,
`peak_active_N`, `peak_physical_N`, dtype,D,query-source count and reserve size.
Report repeated query events separately from distinct query vectors:80k SIFT
queries can reuse its10k public query pool, but cannot be called80k unique
queries. Query reuse/order is fixed identically for all methods and disclosed.
Before tuning, propose a hash/seed-fixed10% development versus90% final query-ID
split and archive both manifests. Final events cycle only through the held-out
portion, so the actual distinct final-query count can be below the published
pool size. Never tune on final answers. An optional SPACEV history-query variant
can supply more distinct queries, but needs separate provenance/truth and must
not be relabeled as the unchanged official test workload.

## 4. Proposed100k event contracts

One event means one query vector, one inserted vector occurrence, or deletion
of one live stable ID. A batch of256 query vectors is256 events, not one.
An update command affecting1000 rows is1000 events. A replacement is one delete
plus one insert. Initial population, oracle generation and diagnostic probes
are not silently included in or substituted for the required100k events.

| Mix ID | Query Q | Insert I | Delete D | Total E | Intended question |
| --- | ---: | ---: | ---: | ---: | --- |
| R80 (primary) |80000 |10000 |10000 |100000 | Query-heavy workflow: does reducing CPU/GPU execution overhead matter end to end? |
| M50 |50000 |25000 |25000 |100000 | Balanced reads versus combined writes |
| U20 |20000 |40000 |40000 |100000 | Update-heavy workflow and maintenance cost |

These exact ratios are **proposals of this extension**, not claimed universal
paper defaults. Initially choose fixed-count streams, not multinomial sampling
whose realized totals drift. Proposed seeds are42,43,44,45,46,47, one per paired
round; A and B receive byte-identical input/operation/query manifests for that
round. Keep all six seed-specific traces and their hashes.

Two spatial/temporal families:

- `uniform-interleaved`: shuffle the fixed operation-type multiset; choose each
  delete uniformly from currently live IDs and each insert from the disjoint
  arrival interval. Query IDs follow a seeded permutation/cycle of the public
  query pool. No invalid deletion or silent fallback to query-only execution.
- `clustered-window`: use64 seed-fixed clusters on a documented training sample,
  map all rows without changing the distance representation, and concentrate
  departures/arrivals and query attention in a moving region. Freeze cluster
  assignment/permutation hashes, burst size and hotspot window before running.
  This is inspired by public drift workloads, not the unchanged official runbook.

Primary dispatch is `Bq=1, Bu=1`, with update ACK visibility before the next event.
Contiguous same-type events may be grouped only in a separately declared
`Bq/Bu` sensitivity (e.g.32/256). Never change B to make a weak result faster
or confuse query batching with update batching. No hidden lookahead to future
arrivals in build/training. After every ACK, subsequent queries see every
acknowledged insertion and no acknowledged deletion. A deferred physical
cleanup is legal only if current-state quality/output remains valid.

### Required sweep and prioritized sensitivities

- Required core: SPACEV four scales, R80/uniform,100k events per method/process.
  SIFT1M/10M/100M provide the matching image series; its billion variant is named
  separately. kNN K10 is primary; K100 is a separately qualified sensitivity.
- Required correctness/functionality family: range+insert+delete and
  kNN+insert+delete are separate runs with the same100k count convention.
  A query-only ANN comparator does not automatically enter exact-range tables.
- First sensitivities: at1M and10M, M50/U20 and clustered-window; then expand to
 100M/1B after cost/capacity admission. Record unrun cases explicitly. This is a
  scheduling priority, not permission to call missing1B core evidence complete.
- The historical K8/K32 small-N traces remain regression evidence only.
  A combined range+kNN trace, if later requested, needs explicit query counts
  of each kind; it is not the same benchmark as either primary family.

Every result names its dataset,N0,E,mix,query type,K or radius,Bq,Bu and resource
tier. Preserve the current running final10000 campaign; do not overwrite its
queries, logs, tuning artifacts or outputs for this new scope.

### Fixed event count is not fixed update pressure

| Initial N0 | Insert fraction in U20 (40000/N0) | Total update-event fraction ((I+D)/N0) |
| ---: | ---: | ---: |
|1M |4% |8% |
|10M |0.4% |0.8% |
|100M |0.04% |0.08% |
|1B |0.004% |0.008% |

Thus the1B/100k result can establish low-churn workflow scaling, not100-day
stability or heavy deletion resilience. Add a **separate** normalized-churn/
sliding-window campaign if a sustained-update paper claim is needed. Following
a1-per-mille replacement epoch at1B already requires about1M inserts plus1M
deletes before any queries: incompatible with E100k. Do not hide those extra
events outside the timer or silently redefine an event to mean a batch.

## 5. Query quality and snapshot oracle

- Main kNN quality-floor rows use the same K and empirical recall targets90%,
 99%,99.9%, with99% as the proposed primary row. Tune only on a disjoint
  development trace, then freeze all parameters before final execution. Report
  actual recall and temporal/minimum-window recall, not just a target label.
  Proposed reporting windows are100 consecutive1000-event intervals; each query
  still uses its own active-set truth. A window is not a stale shared snapshot.
  The final quality gate requires both overall and predeclared window-level
  recall to reach the floor. Exceeding a floor is disclosed; exact GTSPP versus
  approximate99%-recall competitors is not identical algorithmic exactness.
- Exact kNN rows require full correctness under declared numeric/tie semantics;
  empirical100% ANN recall alone is not an algorithmic exact-search guarantee.
  Return K unique live occurrence IDs, or the documented missing-slot format
  when fewer than K are live. Check distances and sortedness. Tied nearest
  vectors are scored using distances and valid distinct IDs, not arbitrary
  source-row order. Fix FP32 tolerance/ranking policy before admission; integer
  datasets use an independently computed exact integer-distance reference.
- Exact range rows use complete live-ID sets and requested result fields;
  false positives/negatives, tombstones and truncation must all be zero. Freeze
  inclusive/exclusive radius, squared-distance convention and radius values
  calibrated on a development set to output cardinalities10/100/1000. Do not
  reuse synthetic radius0/10000 on unrelated floating-point datasets. No capped
  top-K approximation may masquerade as complete range output.
- Each query is scored against its active set at that event, not initial/static
  or end-of-run truth. Freeze logical snapshot digests and cross-check every
  accepted transition. GT generation and scorer work are outside index timing,
  with their elapsed time/resources reported separately. Normal answer
  materialization, device-host delivery and observer checksumming remain inside.

The reference must be streaming/chunked, never an NxN distance matrix or a
QxN reserved answer array. For billion-scale kNN, a possible offline acceleration
is a **certified initial top-L prefix**: remove deleted initial IDs, compute
distances to every still-live arrival, and merge. If at least K initial-prefix
entries remain live, omitted initial vectors cannot precede those K surviving
entries, so a complete, correctly ranked prefix suffices (with declared tie
handling). Otherwise regenerate a deeper prefix or perform a full chunked scan.
This method is proposed, not implemented/qualified here. It needs verified
initial-prefix provenance and small-scale exhaustive differential tests; static
truth for another prefix/pool/metric cannot be used. Full range truth still
requires a complete range oracle, not this kNN certificate.

## 6. Baselines: eligibility before timing

| Group | Method | Admission boundary |
| --- | --- | --- |
| Original tree | Pinned original GTS range/update | Preserve native update/rebuild policy; account for all output and CPU/GPU work. First prove large-N capacity and dtype/D support. |
| Original tree kNN | Native `searchIndexKnn` | Current call has no arrival/tombstone integration. A minimal named dynamic adapter needs its own correctness gate. Do not claim an untouched native mixed-kNN comparison already exists. |
| Attribution | PAR strong; unified PAR+BOUND/PAR+FULL | Remeasure under the same trace. Their current admitted scope is small-N; controls identify layout/pruning/dispatch effects, not a substitute external comparison. |
| External GPU ANN | Faiss-IVF and NVIDIA cuVS CAGRA | Pin installed version/API, add/remove/filter/extend support, training and maintenance policy. Include every conversion/copy, refinement, repack and rebuild. Preserve native best-supported capabilities. |
| Dynamic reference | DiskANN/FreshDiskANN; Quake or SPFresh | Qualify exact published implementation and resource tier. CPU/SSD systems are system comparisons with a frozen CPU budget, not GPU-kernel baselines. Do not invent a public GPU DiskANN port. |
| Billion GPU tier | FlowANN, if an inspectable implementation is available | [OSDI2026](https://www.usenix.org/conference/osdi26/presentation/zhao) establishes single-GPU billion search with CPU-offloaded graph edges, not all-resident GPU memory. Dynamic-update support and artifact availability are unverified here. Static-only evidence cannot enter the mixed workflow. |

Current [CAGRA documentation](https://docs.nvidia.com/cuvs/user-guide/api-guides/indexing-guide/cagra)
has graph extension and filtered search; extension requires caller-managed
concatenated vectors. Therefore do not dismiss CAGRA as universally static or
automatically rebuild it on every insert. Conversely, filtered search is not
physical deletion/consolidation, and latest online APIs do not prove the
installed version supports them. Name a tombstone/filter/cleanup wrapper
explicitly and charge its full lifecycle. Rebuild policies must be quality/
capacity-justified and frozen for each method on development data, not selected
to favor GTSPP. Unsupported contract, OOM, timeout and quality failure remain
visible with no fabricated speedup; wrappers never silently search a stale index.

`NATIVE+FULL` currently means original range dispatch plus the unified exact-scan
kNN path. It is **not original GTS native kNN**. The unsafe incremental branch
remains abandoned and must not re-enter as the paper's original baseline.

## 7. Capacity and resource regimes

Raw vector bytes are N*D*sizeof(dtype), excluding every index/workspace/copy.
Decimal GB is used below; host/GPU tools may report binary GiB/MiB.

| Representation |1M |10M |100M |1B |
| --- | ---: | ---: | ---: | ---: |
| SIFT source,uint8,D128 |0.128GB |1.28GB |12.8GB |128GB |
| SIFT FP32 compute copy,D128 |0.512GB |5.12GB |51.2GB |512GB |
| SPACEV source,int8,D100 |0.100GB |1.00GB |10.0GB |100GB |
| SPACEV FP32 copy,D100 |0.400GB |4.00GB |40.0GB |400GB |
| DEEP FP32,D96 |0.384GB |3.84GB |38.4GB |384GB |

The proposed capacity envelope is one96GiB-class GPU and a256GiB-class host,
not an assertion of available or reserved memory. Exact intended GPU architecture,
usable bytes, driver/toolkit and active-process/storage snapshots must be verified
at admission and are retained privately until a curated experiment manifest is
appropriate. Use an idle single card under the campaign lock/NUMA binding and
never signal foreign processes or change GPU settings.

The current SIFT layout retains both AoS and AoSoA FP32 data: at100M those two
copies alone total102.4GB, almost the nominal device capacity, before scores,
masks,ID maps,tree metadata and workspace. At1B, even one full FP32 vector array
exceeds both a single GPU and the proposed host envelope. No large-N fit is
established by raw-size math.

Three non-interchangeable regimes must be reported separately:

1. `resident-single-GPU`: full vector/index/workspace/rebuild peak fits one GPU.
2. `tiered-single-GPU`: same one GPU with an explicit host/NVMe tier, pinned
   staging/cache budget and all page migration/copy/I/O cost inside the timer.
3. `multi-GPU`: separately authorized and admitted hardware budget, partition/
   communication policy and timing. Not the default workaround for a1B OOM.

Compression, uint8/int8-native compute and on-demand FP32 conversion are named
representation variants; comparisons retain original numeric semantics or a
separate accuracy contract. Do not quietly switch a baseline's precision,
metric or quality guarantee to make it fit. At1B the current all-resident tree
is not admitted; a tiered tree design itself requires additional engineering
and prior-art review. Record `unsupported-resident` if that is the honest result,
while keeping the tiered1B objective outstanding.

Storage admission must inspect the **actual scratch mount**, not merely SSH
success or another path's free space. Private preflight observations do not
reserve space or prove capacity for multiple billion datasets,indexes,rebuild
copies and oracle files. Use a task-owned verified NVMe directory,
avoid NAS-backed timing unless separately declared, and never clean others' data.
Acquire only the admitted dataset subset first; no automatic billion download.

## 8. End-to-end timers and operator evidence

`T_workflow`: monotonic wall time from issuing the first event to all100k events
acknowledged, all normal result fields delivered/checksummed, and all already
triggered owned maintenance/copies completed. It includes API dispatch, CPU
index work, H2D/D2H, GPU traversal/distance/selection, updates, rebuild/repack,
allocation, synchronization and drain. No deferred triggered job may escape
the denominator. Stream overlap means component medians/sums are not this timer.

`T_cold`: from opening the admitted local input to completion of the same
workflow, including parsing, dtype conversion, context creation, allocation,
initial training/build/layout and result/drain. Exclude remote download,
offline reference generation and fsync only when explicitly stated; durable
output is a separate regime. Record observer cost consistently across methods.
Report build and warm workflow individually as well as their cold aggregate.

Legitimate untriggered cleanup/tombstones are not forcibly compacted for one
method merely to imitate another's structure. Record final physical/live size,
tombstone fraction, queues and maintenance policy. A separately specified
post-trace consolidation or normalized-churn continuation has its own timer,
not a hidden extension of E100k or a free acceleration of the next run.

| Stage | CPU-side evidence | GPU/memory evidence | Required complete-operation result |
| --- | --- | --- | --- |
| Load/train/build/layout | parsing/conversion, clustering/sorting, allocation, per-thread CPU time | build kernels,H2D, pack/repack, peak memory | Build wall time and resource peak |
| Query | dispatch, candidate/ID mapping, allocation, busy polling versus blocked waiting | traversal/gather, distance/verify, reduce/top-K or range materialization, D2H | ACK/result-complete latency,QPS,quality |
| Insert | ID map/buffer management, neighbor/index construction, scheduling | append/extend/copy, local repair, allocation | Visibility ACK,insert latency and triggered maintenance |
| Delete | ID lookup/tombstone/compaction/queue work | filter/bitmap updates, repair/cleanup,copies | No deleted results,delete latency and later cleanup cost |
| Maintenance/output | rebuild/compaction, merge, observer and serialization | repack, stream fences, output copies | Work count,CPU/GPU time,bytes,wall exposure,drain |

Collect process-tree CPU user/system seconds, average core equivalents
`(user+system)/wall`, thread-level attribution, RSS/pinned/device high-water,
disk reads/writes, H2D/D2H bytes/API calls and query/insert/delete p50/p95/p99.
Separately report event throughput100000/T and effective queriesQ/T; do not
call event throughput query QPS. For the suspected coalescing mechanism,
diagnose sectors/request, requested/actual bytes, cache behavior and branch/
warp activity where available on the intended GPU. CPU wall waiting is not
automatically CPU computation. Reduced copy/API/sector counts are mechanism
evidence, not the complete-workflow speedup itself. Profilers run separately
from public timing; stage attribution may have extra instrumentation overhead.

## 9. Ordered admission and collection plan

| Stage | Work | Exit signal; failure handling |
| --- | --- | --- |
| P0: source and contract | Review public runbook/generator; pin exact source/data/license/quality/timer/batch/dtype/resource manifests. Freeze one small-scale comparator pair first. | Source inventory plus reproducible frozen manifest; no performance claim |
| P1: scalable correctness adapter | Retain original GTS lifecycle; separate dynamic native-kNN adapter, stableIDs/fresh arrivals and large-N resource handling from optimizations. | Full-output/snapshot differential tests,deleted-seed/empty/tie/rollover/nonaligned boundaries; unsupported paths remain fail-closed |
| P2: resource screen | Inspect allocations; first bounded1M build/smoke, then1M full100k trace. Admit one idle GPU and actual storage path. | Measured peaks,real operator costs and a campaign budget estimate; no inferred fit at10M/100M/1B |
| P3: formal core | Fresh matched processes; SPACEV1M->10M->100M->1B under R80/uniform; SIFT image controls and independent range family. | Same-contract quality/correctness,raw complete timers and negative rows at every attempted scale |
| P4: attribution/sensitivities | M50/U20,clustered,K100,Bq/Bu sensitivities; remeasure original/PAR/IVF/CAGRA as eligible. | Full-workflow change plus operator/CPU-memory explanation; regressions retained |
| P5: sustained claims | Separately freeze normalized churn/sliding-window continuation where needed. | Maintenance/recall/time-series stability evidence, not extrapolation from E100k |

P1 must address actual current limits before any large-N launch: N1000/D128
integer-only parser,physical capacity1024,live cap1010,Q<=10000,E<=12000,K<=32,
four-block selector scratch and current O(E*N) live counting. The Python oracle
precomputes an NxN matrix. Range observer reservation scales with Q*N. Merely
raising guards is unsafe, can create a CPU bottleneck in the harness, and does
not qualify a scalable algorithm. Generalize bounded scratch/output handling,
file streaming and active-ID state first; validation work belongs outside the
index timer except actual contract checks/result delivery explicitly retained.
No kernel/benchmark implementation was changed in this design delivery.

For each admitted pair and condition use six fresh process pairs: AB,BA,AB,BA,
AB,BA, with six frozen seeds. Remeasure the comparator in every pair. Primary
estimator: geometric mean of per-pair baseline/candidate full-workflow ratios;
95% process-pair bootstrap interval with fixed resampling seed and10000 draws.
Report all raw orders,marginal p10/median/p90,paired wins,order splits,CPU resource
differences and every regression. Six seeds are trace realizations, not twelve
independent processes masquerading as more pairs. An interval crossing1 is
inconclusive. There is no ratio for quality failures,unsupported cases,OOM or
timeouts; retain attempted counts/resources and failure evidence. Diagnostic
screens and extrapolated runtimes are not formal100k measurements.

Fix CPU allocation/NUMA/isolation, GPU state, timeout and host-memory budget
before collection. Set timeout from a bounded pilot before formal runs; do not
inherit a short-run1200s timeout unexamined or extend only a favored method.
Sanitizer/stress gates apply to changed code before paired promotion. Do not
install hooks/frameworks, stop other experiments, modify the existing final10k
campaign, or launch a1B job during a literature/design-only step.

## 10. Evidence state and next action

| Claim | State | Strongest currently allowed wording |
| --- | --- | --- |
| Public dynamic benchmark practices reviewed | Established source facts | The cited artifacts/papers provide workload/quality/timing references; our extension is explicit |
| Existing GTSPP can run N1M-1B/E100k | unknown; no evidence | Large-N implementation and resource admission are pending |
| Coalescing lowers CPU waiting and mixed-workflow wall time | unknown; no evidence at this scope | A same-contract operator/CPU/full-timer campaign is planned |
|1B data fits current all-resident FP32 tree | theoretical capacity contradiction for one full FP32 copy | A separate tiered representation/design is required; no1B speedup measured |
| Long-term update stability | unknown; no evidence from this plan | E100k is low churn at1B; a separate sustained contract is necessary |

Next action is P0/P1, then the cheapest honest1M full100k admission, **not** a
blind giant launch. Required1B coverage remains visible until measured under
an eligible tier or explicitly reported unsupported with the objective still
outstanding. Publish only this curated plan/source metadata, not manuscripts,
source-paper copies, datasets, raw sessions, machine configuration or credentials.

Source snapshots and public repository pins are listed in
[SOURCE_MANIFEST.json](SOURCE_MANIFEST.json). Full source captures are retained
outside Git. There are no new GPU experiment results in this directory.
