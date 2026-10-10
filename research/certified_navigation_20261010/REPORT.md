# E1 result: low reuse headroom, weak candidate effect

**The two proposed mechanisms do not justify promotion on this original-tree
GIST snapshot.** Memo removes only 1.075346% of coordinate updates. Persistent
distinct cross-layer witnesses remove only 0.023669% of leaf-object calls.
The prototype's serial candidate maintenance adds substantial device time.
This is a bounded E1 stop decision, not a universal negative GPU-tree result.
E2 is incomplete; formal E3 consumed **0/24** processes. No production change
or paper performance/novelty claim is promoted.

## 1. What was actually measured

Repaired original `searchIndexKnnV2` retains the native tree, per-level pivot
sorts, node tests, Host stack and leaf verification. G0 includes the common
ordered RN FP64 score, conservative interval, capacity and complete-output
repairs. G1 adds only query-local pivot memo. G2 adds a distinct persistent
cross-layer real-candidate set, not the already-existing per-level pivot
threshold. G3 combines them. There is no CUDA Graph, fusion, learned model or
replacement full scan in the online path.

GIST N1M/D960, K8/B1, 32 frozen development queries, self-inclusive `(score,id)`
ranking, one admitted physical GPU 7/NUMA 3 for all modes. The full source,
query, tree, binary and hardware/software identities are pinned. Independent
GPU and scalar CPU exhaustive references are separate from all online modes.

The final v7 byte-initialization correction was applied uniformly and all four
modes were freshly remeasured. It leaves v6 work CSVs and complete results
unchanged. Older samples/failures remain independent, never pooled into v7.

## 2. Work evidence

All totals are over the same 32 queries. Coordinate updates are software
counters for completed ordered-distance loops, not hardware DRAM traffic.

| Mode | Full distance computations | Coordinate updates | Coordinates saved vs G0 | Leaf-object calls | Leaves saved vs G0 |
|---|---:|---:|---:|---:|---:|
| G0 | 30,722,107 | 29,493,222,720 | — | 30,376,910 | — |
| G1 memo | 30,391,738 | 29,176,068,480 | 1.075346% | 30,376,910 | 0% |
| G2 candidates | 30,714,815 | 29,486,222,400 | 0.023735% | 30,369,720 | 0.023669% |
| G3 both | 30,384,543 | 29,169,161,280 | 1.098766% | 30,369,720 | 0.023669% |

G0 averages **949,278.4375 leaf objects/query (94.927844% of N)**. G1 records
32 pivot-to-pivot hits and 330,337 pivot-to-leaf hits in the entire pass; the
underlying tree has 11,100 eligible pivot slots but 11,099 distinct rows if
all regions are visited. Memo preserves exact visit bitsets and threshold
trajectories. G2/G3 also preserve each other's exact bitsets; replaying G0's
upper timeline in G2 restores G0's visits. Thus G2's tiny nonzero visit change
is attributable to its upper-bound trajectory, not altered input arithmetic.

Candidates improve the final upper mean from 1.286552 to 1.283944, while the
independent true Kth-distance mean is 1.150832. Neither G0 nor G2 reaches
U <= 1.01 U* on any of these 32 queries. This does not establish a partition
limit or prove that a stronger region certificate is effective: E1-O was not
run, and candidate quality, bound slack and region granularity are not fully
disentangled. The coordinate fraction is **not an upper bound on latency
improvement** because distance invocations can have different costs.

## 3. Timing and mechanism attribution

These are **one uninstrumented diagnostic process per mode**, reverse order
G3/G2/G1/G0, one fixed development warmup, no paired interval. The denominator
is resident-query-ID submission through complete K IDs/FP64 scores Host-ready;
it is not the plan's full external Host-vector E3 denominator. All per-query
allocation, clearing, candidate work, sorting, synchronization and copies are
charged. Context/file load and tree coverage setup are separately recorded.

| Mode | 32-query diagnostic total (ms) | Per-process query p50 (ms) | p95 (ms) |
|---|---:|---:|---:|
| G0 | 925.438587 | 27.218402 | 37.258825 |
| G1 | 920.598571 | 26.642150 | 35.627753 |
| G2 | 1578.714066 | 48.570921 | 58.175948 |
| G3 | 1568.954307 | 47.983138 | 54.727786 |

No robust G1 win is claimed. Its final nominal change is about 0.52%; earlier
v4 had the opposite sign. Version-specific observations remain retained.

A separate NSYS first-two-query run supports an implementation-level cost
explanation, not a formal ranking:

| Diagnostic item, two queries | G0 | G3 |
|---|---:|---:|
| Query NVTX range (ms) | 71.472619 | 109.858721 |
| Kernel count | 140 | 140 |
| nav_update inclusive GPU duration (ms) | 0.791212 | 41.491257 |
| Leaf dataProcessKnn inclusive GPU duration (ms) | 41.075165 | 40.831662 |
| Recorded GPU-work temporal coverage | 71.882056% | 83.751687% |
| cudaDeviceSynchronize calls | 38 | 38 |
| cudaStreamSynchronize calls | 66 | 66 |

The added ~40.7 ms nav_update duration corresponds to most of the added
~38.4 ms range time. In this implementation G2/G3 insert candidates on one
thread, whereas G0/G1 retain an O(1) Kth read after the existing level sort.
Parallelizing that insertion might remove this prototype's cost; it would
not by itself create more avoided leaf work or establish research novelty.

The trace has 70 kernel launches/query, 19 device and 33 stream synchronization
calls/query. G0's CUDA API union occupies 62.100216 ms of its 71.472619 ms
range, largely including GPU waits. **This is not a measured CPU-computation
percentage or CPU utilization.** Temporal GPU coverage is not SM utilization.
Unified migration events total 491,520 bytes in each direction for G0 and
532,480 for G3 over two queries; these are trace-recorded migrations, not
hardware DRAM bytes, total cache traffic or proof of a unified-memory cause.
The whole E1 campaign's 200ms device-memory samples range from 67 to 18,298 MiB
including setup and the oracle; this is not a query-only allocator peak.
No NCU coalescing, occupancy, instruction or DRAM evidence was collected.

## 4. Correctness and unresolved gates

Full K IDs, FP64 score bytes and order match both independent exhaustive
references for every development query in all four modes and the G0-upper
replay. Original widened split intervals cover every object's declared region
in setup; zero bounds were disabled. Exact per-node visit bitsets are verified,
not merely equal non-cryptographic digests. Eight CPU source/protocol/ownership/
guard/trace checks pass, and 35 small *reference-only* queries match ordered
FP64 plus exact-rational rank checks. These do not complete native-tree E2.

The first v6 initcheck reported uninitialized reads in CUB's whole-NavKey load:
`double score; int id` left four implicit padding bytes undefined. v7 makes
those bytes an explicit zero-initialized integer. First-two-query G0/G3
memcheck, initcheck and synccheck now report zero errors and full results match
the reference subset. **API reporting was explicitly disabled in these six
runs**, so this is only a memory/init/sync subset, not a strict sanitizer pass.

Default memcheck of a plain no-query API smoke passes. The same smoke including
unmodified original GTS headers reports two cuLibraryGetKernel
CUDA_ERROR_NOT_FOUND(500) errors before any query/memo. This localizes a common
pre-query boundary but does not prove the errors harmless; strict API admission
remains unresolved. The older timeout/failure and its exact-owned orphan
cleanup are retained. No foreign process was stopped.

Missing: native empty/N<K/tie/boundary/adversarial matrix, cache-capacity and
storage-invalidation controls, race/stress/rollover gates where applicable,
full G0 finite-upper witness-ID provenance, per-boundary device timestamps,
strict API sanitizer gate, full Host-vector submission and formal paired E3.
There is no E4 certificate or new external GPU-tree/scan comparison.

## 5. Decision and reopen condition

* **Implementation:** diagnostic-only, not a promoted keeper. The serial
  candidate insertion is costly; default API admission is unresolved.
* **Mechanism:** LOW_REUSE_HEADROOM / WEAK_CANDIDATE_EFFECT on this tree/query
  sample. Do not spend the 24-process formal budget or sweep memo parameters
  to rescue this memo/candidate-only direction.
* **Thesis:** no novelty promotion. Original GTS already uses pivot thresholds;
  generic memo and top-K witnesses are established techniques. A defensible
  new direction requires a different, non-incremental mechanism plus decisive
  same-contract evidence, not packaging or a small diagnostic timing change.

Reopen reuse/candidates only with a newly frozen tree/workload showing
substantially more repetitions or avoidable visits. If studying region
representation next, first freeze an eight-query same-U region-truth/interval
cost diagnosis to distinguish bound slack from region granularity; do not
label it a stronger certificate or launch a new large ranking beforehand.
No conclusion here applies automatically to all GPU trees, other dimensionality,
batching, arbitrary external queries or dynamic updates.
