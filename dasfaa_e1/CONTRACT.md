# E1 true-arrival dynamic maintenance contract — frozen v1

Frozen before any task-owned GPU execution or measured result. The shared
COMMON/E1 contracts and revision plan remain unchanged. Their hashes, source
pins and exact data hashes are in SOURCE_INPUT_PINS.json and
evidence/input_audit.json. This experiment branch is
`experiments/gtspp-dasfaa-e1-true-arrival-20261026`; no merge is authorized.

## Scope and provenance

Use one RTX PRO 6000 Blackwell (sm_120), CUDA 13.1, driver 590.48.01.
Recheck actual state under the existing device advisory lock and a task lock.
No foreign signals or GPU setting changes. The source start for P is archival
`GTS_hei_lea_ada_input_prune_update`: it contains
`ensureUpdateSearchWorkspace`, `collectLeafNodesSingleQuery` and a buffer-only
`MAX_IN_SIZE` path. It has no leaf direct insertion. Its B value is a configurable
constant, NOT an already implemented online estimator. The Proposition controller
must be added explicitly. G starts at archival `GTS/SourceCode/GTS`, retaining
its allocator-heavy update query path and native blocking reconstruction with
B=10. Compare `GTS_incremental` and GTSPP main for provenance; neither's direct
insertion is admitted to the executable. Never modify the archive.

## Input gate, before results

| Dataset | Corpus rows | Arrival rows | Native queries | Feature-overlap rows | Input gate |
|---|---:|---:|---:|---:|---|
| sift | 1000000 | 100000 | 10000 | 0 | input-pass |
| gist | 1000000 | 100000 | 1000 | 17 | input-contract-blocked |
| deep | 1000000 | 100000 | 10000 | 42 | input-contract-blocked |
| tloc | 1000000 | 100000 | 1000 | 1000 | input-contract-blocked |
| word | 611756 | 61175 | 1000 | 1000 | input-contract-blocked |
| protein | 52799 | 5279 | 1000 | 3547 | input-contract-blocked |
| chembl | 50000 | 5000 | 1000 | 1110 | input-contract-blocked |

The arrival permutation is NumPy PCG64(seed=20261026), first floor(N/10)
rows as arrivals, remainder as initial base. IDs are unique and never recycled.
Native query payloads must have no identical features in either split; +0/-0
are equal. Corpus text is byte-preserving Latin-1, not UTF-8 transcoded.
No rows, queries, workload ratios, thresholds or arms may be silently replaced.
Overlap is input-contract-blocked, not a correctness result. A user-approved
input change requires a dated AMENDMENTS entry and new hashes before running.
Capacity-infeasible workloads remain in the matrix; never shorten traces or
recycle arrival IDs. Full matrix is the Cartesian product in input_audit.json:
7 datasets, random/skew, 10K/100K operations, 442/811/181, k8 plus k10 for L2.
SIFT/T-loc 1M-operation traces are P1. P-approx, cosine and H are optional/P2.

Skew order: SIFT/GIST/Deep use k-means k=64, fixed seed, cluster index then
original permutation rank; T-loc uses 64x64 equal-width cells per coordinate
(min/max over corpus), row-major cell ID then permutation rank; Word/Protein
use length then bytewise lexical order, original row ID breaks ties; ChEMBL
uses popcount then original permutation rank. Random arrival order is the
frozen permutation. Operations use exact counts, then PCG64-shuffle; deletes
sample uniformly from current live IDs. Fail rather than return fewer than k.
Required snapshots advance once per accepted mutation. Native queries cycle
through a seeded permutation if trace needs more query events than query rows.

## Arms and interface

G: archival GTS with true external payload/ID interface, B=10.
G+B*: same implementation as G with measured Proposition B.
P: archival C1 workspace/single-query path plus measured B, C2 disabled.
D: append-only resident GPU payloads and authoritative stable-ID delete bitmap,
exact scan + complete top-k host-ready output. Use rolling-row edit distance,
flat L2 and bit Tanimoto. Record changes relative to E3; static parity is a
required delivery gate, not assumed before E3 is available.

Insertion writes only payload/delta state, never tree/leaf metadata. Query
unions tree candidates and exact delta scan, filtering the single authoritative
stable-ID bitmap; no duplicate IDs. Rebuild consolidates live tree and delta,
blocks the triggering insertion at delta length >=B, includes that cost in its
operation and separately in stall. Deleted delta rows do not become active on
rebuild. The immutable IDs survive physical compaction. Reject duplicate/new-ID
violations before device mutation. An automatic static check must reject any
leaf routing/padding or metadata write in the insert function/call graph.

Native legacy update APIs are range-only/count-oriented. Any adapter required
to produce external-query complete kNN (candidate delivery, initial bound,
filtering and top-k) must be explicitly documented before public timing; it
cannot be represented as an unchanged native dynamic kNN API. Archive distance
and pruning arithmetic are not optimization targets. Missing metric support
must be named, never treated as all-zero distances.

## Correctness and sanitizer gates

Smoke: real corpus-derived disjoint FEATURE sets, 10K base, 2K arrivals,
1K queries, 5K exact 4:4:2 events, k8, seeds 20261026/27/28, all seven datasets.
The smoke split is a dedicated deduplicated sample, not a substitute full load.
Record its source-row maps and hashes before GPU execution. Every arm must
have zero invalid, duplicate, deleted or out-of-active IDs and no stale snapshot.
D requires zero tie-aware misses. Independently compute CPU active-set oracle
at every query, retaining complete output. CPU L2 is FP64 Euclidean, edit is
integer Levenshtein, Tanimoto is 1-intersection/union (empty/empty=0).
Accept returned distance <= oracle kth distance*(1+1e-5), require k IDs.
Record P/G Recall@k and diagnose every non-tie miss: inherited pruning versus
new delta/delete/rebuild bug. New bugs block timing until fixed; retained failed
attempts are not replaced. No exactness claim for G or P; apply COMMON's
correctness-failed/no-timing rule to failed exact-required workload rows.
Before timing, validate each full trace once in every arm against the independent
per-event oracle. Bounded memcheck and synccheck are mandatory. No CPU proxy
may be labelled a native GPU tree or native library.

## B* calibration and validation

Measure T_rebuild(n) and c_naive on the admitted UUID before workload timing.
T_rebuild: 3 fresh process builds, median complete blocking build wall time.
c_naive: 3 fresh processes, delta lengths 100/1000/10000, 10 independent query
payloads each; slope of median complete scan wall seconds versus length, clamp
negative slope as calibration-failed rather than invent a constant. Edit and
Tanimoto are measured directly, never inferred from L2 dimension.
Bhat=ceil(min(sqrt(2*Ni*T_rebuild/(Ns*c_naive)),Ni)), at least 1.
G+B* and P use the SAME premeasured Bhat per dataset/ratio/length. Do not choose
B by observing the timed trace. The literal trigger >=B is retained, including
B=Ni; any finite-trace discontinuity in the old model must be reported, not hidden.
Validate on SIFT/GIST/Word, 100K/442/random, B in
{10,100,300,1000,2000,5000,10000,20000,infinity}; infinity never rebuilds.
Report predicted B, empirical optimum, curve, counts and stalls on this GPU only.

## Timing and statistics

Scope is complete host-ready operation: payload input, GPU compute, synchronization,
complete result return. Initial tree build, capture and warmup are separate.
No correctness/oracle/log serialization inside the timed interval; preallocate
raw observation storage and write it after trace completion. Instrumented build
is separate (distance calls, candidate leaves, scan bytes), never used for timing.
After gates pass, six fresh-process paired rounds per load with balanced orders:
G,B,P,D; D,P,B,G; B,G,D,P; P,D,G,B; G,P,D,B; B,D,P,G.
Use the same GPU UUID for the full epoch, record clocks/power/process telemetry.
Foreign activity invalidates the entire epoch's performance observations; retain
and restart all six rounds after re-admission. Treat post-exit utilization-only
NVML tails as settling, not automatically foreign application ownership.

Per dataset report each arm's trace wall time/ops-s and each operation's
p50/p95/p99, rebuild counts/stalls, delta history, full per-query Recall@k and
invalid/missing counts. Ratio P/G means time(G)/time(P), P/(G+B*) means
time(G+B*)/time(P), P/D means time(D)/time(P). Report exp(mean paired log ratio)
and Student-t df5 95% interval on the six process-pair logs. Headline across
datasets is the median, never the maximum; no cross-order pooling.

## Frozen decisions

1. Retain C3' as main contribution iff P/G >=2 on at least 4 of 7 datasets
   at 100K/442/random/k8. Missing datasets do not pass or fail by extrapolation.
2. Retain C1 as separate contribution iff dataset median P/(G+B*) >=1.2;
   otherwise minor implementation optimization. Missing evidence is undecided.
3. Report D honestly; if D wins every load, record support for story B.
4. Skew gets a separate table, never an average with random.

## Delivery

Append only to AMENDMENTS.md after this commit; never edit this contract.
Publish task-owned code/manifests/curated evidence to the designated branch,
not raw data, credentials or host configuration. Retain full raw records in the
private experiment workspace. Verify remote SHA, download published files and
compare hashes. Mark implementation, correctness, sanitizer, timing, E3 parity
and upload states separately. Uncompleted required and optional items remain
explicitly uncompleted. No paper-facing performance claim before required gates.
