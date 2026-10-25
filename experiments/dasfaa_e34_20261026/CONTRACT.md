# E3/E4 frozen experiment contract

Registered 2026-10-25 UTC, before any GPU benchmark execution. This contract
implements the externally supplied COMMON, E4, and E3 protocols; those originals
are read-only. All subsequent changes are append-only in AMENDMENTS.md.

## Scope and frozen questions

E4 is first: compare C2-off GTS++ P against S on every N and Q below. E3 follows
with all nine original dataset instances, G/P/S, k=8, and k=10 additionally for
L2; Q=1,32 and the full original query count. No workload can be removed after
results. Missing/gated loads stay visible with their exact state.

E4 crossover exists only when the process-paired geometric mean P/S < 1,
its two-sided 95% CI upper bound < 1, S passes complete-output correctness,
and P tie-aware recall >= 0.999. Report the smallest measured qualifying N per
family/Q. If the required feasible matrix is complete and no point qualifies,
the result is story B. Incomplete or correctness-failed comparisons are unknown,
not proof of no crossover. Extrapolation is labeled and never replaces an
infeasible N or a measured conclusion.

## Inputs, queries and provenance

DATA_MANIFEST.json is part of this freeze and binds every source file, generated
file and individual N-prefix SHA256. It contains no measured result. Headered
little-endian float32 vectors preserve the actual archived float32 inputs.

| Family | N | Source |
|---|---|---|
| 2D L2 | 1M,3M,10M | Real archived T-loc 10M prefixes |
| 2D L2 | 30M,100M | Synthetic fitted 64-component Gaussian mixture |
| Deep L2 (96D) | 1M,3M,10M,20M | Official archived Deep-1B 100M prefix |
| Word edit | 61K,150K,300K,611K | Archived 611,756-row corpus, seed 20261026 |

Real 2D queries are the first 1,000 rows of the separate T-loc 1M source; exact
float32 coordinate overlap with the entire 10M base is rejected. Real prefixes
share these same queries. Synthetic queries use seed 20261027, separately from
base seed 20261026. Deep uses the first 1,000 official public queries. A full
CPU scan additionally detects zero-distance duplicates; any shared value is
reported, and source identity stays disjoint. No query is indexed.

No larger real spatial corpus was located in the authorized user's data tree.
Synthetic mixture cluster count=64, fit sample=32,768 (seed 20261026), Lloyd
iterations=20, component weights and full covariance matrices are frozen in
mixture.json. This matches a spatial-cluster approximation, not a claim of
identical T-loc density. Report the real/synthetic boundary prominently.

Word uses a fixed permutation: first 1,000 disjoint rows are query, next N index.
The 611K prefix fits after holding out queries. Full hash and length manifest
must be appended before the Word GPU phase. P1 versioned protein L<=100,256 and
P2 larger ChEMBL are optional; do not substitute synthetic strings. Optional E4
G and E3 P-approx are not required and remain explicitly not run unless appended
before that phase. E3 uses dataset query counts 1000,1000,1000,100,10000,10000,
1000,1000,1000 for T-loc1M,T-loc10M,Word,Vector,Deep,SIFT,GIST,Protein,ChEMBL.
E3 exact input hashes are a separate append-only phase freeze before E3 runs.

## Arms and disclosed source adapters

P is the archived buffer-only GTS++ implementation, using its full-ID
searchIndexKnnV2 API and native external-vector query overload, C2 mode=0.
No direct insertion or update runs occur in E4. Original sources are copied,
never edited in place. Source-original, adapted source and binary manifests are
stored separately. No pruning, distance expression or count approximation is
introduced. Before results, static inspection found inclusive qe passed to
half-open leaf consumers. The scratch-only adapter changes five `le=qe` leaf
boundaries to `le=qe+1`; this is a disclosed complete-output correctness repair,
not an optimization. It cannot be described as untouched archived P. The
harness frees the archived API's returned res_dis after each invocation, inside
the timer. Internal native allocations remain timed; no hidden workspace or
batch serialization is substituted.

S uses real native FAISS 1.15.1 GpuIndexFlatL2, built with GPU=ON and CUDA
architectures=120. Existing user-local compiled library is reused read-only;
no proxy is called FAISS. Config: device logical0, FP32 storage/accumulation,
useFloat16=false, native (non-cuVS) backend, 512 MiB temp memory. S requests
64 native candidates and explicitly reranks those candidates by CPU FP64 direct
differences to deliver 8 IDs. Candidate copies, reranking and full output are
inside the host-ready timer. This precision adapter is predeclared because
norm-dot cancellation can break close spatial rankings; it is not a proof of
universal exactness. Every required query must independently pass the exhaustive
CPU oracle. A failed load is correctness-failed, not replaced or retuned.
Report this column as native FAISS Flat + FP64 candidate refinement, not plain
unmodified FAISS-k8. L2/cosine prefer this native implementation in E3; edit scan
will reuse the existing rolling-row distance implementation; Tanimoto uses
2048-bit popcount. String/bit adapters require append-only source freeze first.

## Addressing feasibility

No int32 address widening is allowed. Flattened vector coordinate expressions
`object_id * D + j` are signed int32: N*D <= 2^31-1 is a conservative address
limit. Thus 2D N<=1,073,741,823; Deep96 N<=22,369,621; SIFT128 N<=16,777,215;
GIST960 N<=2,236,962; cosine300 N<=7,158,278; 2048 scalar-bit representation
N<=1,048,575. String stride M=109 gives N<=19,702,602, also requiring length<M
because archived DP arrays include the terminal row. Tree order=10, leaf
capacity=20; node-count powers and size/index fields must independently fit
int32. The P query arena is natively capped at 4 GiB / sizeof(double), with
chunking, not a new address-width extension. All requested E4 vector Ns pass
the coordinate bound, subject to actual tree-memory/runtime checks. An
address bound is not a tested capacity guarantee. G's fixed default height is
not evidence that its native leaf capacity covers large N; its height/output
adapter will be documented separately before the E3 phase.

## Correctness and sanitizer gates

Independent CPU oracle exhaustively computes every FP64 explicit L2 difference
for every query and N; it never reuses GPU or preexisting top-k GT. Oracle
returns 10 neighbors so k8/k10 are available. Audit every returned ID and its
true FP64 distance, not only API-reported distance fields. Require distance <=
CPU kth distance*(1+1e-5), distinct IDs and valid active IDs. Keep raw outputs.
P and S are timed only on loads passing this complete-output gate; P's actual
recall is always reported and never described as exact merely because C2 is
off. A nonzero mismatch is correctness-failed and that load is not replaced.
Any resulting absence of a comparison is unknown, not story B.

Run compute-sanitizer memcheck and synccheck on bounded real-input subsets
(before accepting timings) for each delivered kernel family, plus changing
queries/repeated invocations. Instrumented builds are separate; no atomic
counts enter timed binaries. Counts: actual pivot/object distance calls,
candidate leaf invocations, logical S scan bytes Q*N*D*4 (not claimed as measured
DRAM bytes). Counts with incomplete instrumentation stay explicitly incomplete.

## Timing, batching, GPU admission, statistics

Hardware is one live-admitted RTX PRO 6000 Blackwell UUID per complete epoch;
CUDA13.1, driver590.48.01, clocks/power unchanged. Reuse the existing
/tmp/gtspp_gpu<index>.lock advisory lock read-only and hold a separate task
campaign lock. Recheck idle before each process, monitor foreign PIDs during,
and wait for trailing NVML utilization to settle after exit. No foreign process
is signaled. On contamination retain/invalidate the entire epoch and restart
the full six-pair schedule on a freshly admitted UUID; never pool epochs.

Host steady-clock/perf_counter surrounds complete host query materialization,
H2D input, native GPU computation, synchronization, all result copies, and
required output refinement. Dataset ingestion/index build/cache-load, first
correctness pass, and one warmup batch are separately recorded. Index cache
is only a build-time artifact, with source/data/config/hash identity, and no
query result is cached. Graph capture is absent (zero), not hidden.

E4 Q=1,32,1024. There are 1,000 unique held-out queries. Q1024 is exactly those
1,000 followed by their first24 again, including duplicate work in latency;
there are not 1,024 independent queries. Q1 processes all1,000. Q32 processes
31 full batches and one final8; all outputs are checked, but the frozen Q32
batch-latency estimator uses only full32 batches (the final8 is retained as a
separate ragged batch). No Q is a serial bundle unless explicitly labeled.

For each load, six independent fresh processes per arm, paired by round, in
PS,SP,PS,SP,PS,SP order. Each process has one excluded complete-output first
pass, one excluded warmup batch, and three retained full-query passes. The
process value is the arithmetic mean of complete full-Q batch latencies.
Primary ratio = exp(mean(log(P_i/S_i))), two-sided Student-t CI with df=5,
t_0.975=2.5705818356. Retain each batch, process order and epoch. Also report
process wins, order split, p10/median/p90 and marginal median ratio. No optional
stopping, estimator selection, or resampling of unfavorable batches.

Fit OLS log(process latency) vs log(N), separately by arm, family and Q using
complete eligible loads; report the N set. Real and synthetic 2D slopes must be
separate (3 real points and 2 synthetic points). A pooled 2D slope, if shown,
is labeled distribution-confounded and not used to establish crossover. Fewer
than2 valid N values means slope unavailable, not zero. A failed P/S comparison
cannot be rescued by extrapolation.

## Delivery

Push task-owned curated artifacts to the preexisting experiment repository,
branch experiments/gtspp-dasfaa-e34-scan-crossover-20261026, never merge main.
Check exact publish set/history and remote branch SHA, then independently
re-download the remote files and verify hashes. Large raw data/binaries stay
outside Git with hashes. E4 interim report first, Word follows; E3 remains a
separate clearly tracked matrix. No paper novelty/priority claim is authorized
by crossover alone; a nearest-prior-art audit would still be needed for any
"first" wording in the eventual manuscript.
