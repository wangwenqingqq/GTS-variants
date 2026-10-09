# Stage A results — qualified controls and retained blockers

**No new end-to-end gain is claimed.** This checkpoint implements baseline
ownership/full delivery, complete GPU range recovery and CPU development freeze.
The supplied 84-static/18-internal primary matrix has **not started**.

## Dataset and process scope

- Target: original FP32 **GIST N=1,000,000, D=960**, B1, K8, radius bits
  `0x3f34a3d8`; initial and first-rebuilt occurrence-preserving snapshots.
- 32 complete range queries/snapshot for the GPU scan; 32 kNN plus 32 range
  queries/snapshot for the inclusive CPU Flat adapter. Independent exhaustive
  ordered-FP64 membership and scale-1 squared-field tolerance 5e-5 passed.
- GPU: RTX PRO 6000 Blackwell Server 96GB, CUDA13.1/SM120. 20
  guarded qualification processes including failures; **0 new primaries**.
  Foreign GPU work was not signalled or reconfigured. This is not a full-leak
  or sustained-workload qualification, and the older 96B limitation remains.
- CPU: six completed development processes and one retained precondition failure
  before native work. Existing sklearn1.6.1 / Faiss1.15.1, one native thread.
  Shared-host CPU/NUMA placement is retained privately, not claimed exclusive.

## Admission table

| Method / identity | Actual result | Admission for next static stage |
|---|---|---|
| CPU_KD / CPU_BALL | Both selected **leaf512** on independent coordinates; all64 selected-development answers correct; all leaf choices passed N0/1/7/513, ties/duplicates and32 B1 repeats | Freeze leaf512; native FP64 representation and preparation costs must remain charged |
| CPU_FLAT native | Fixed target diagnostics previously passed, but new radius-zero/exact-boundary tests expose strict native range semantics | Do not silently call it inclusive |
| CPU_FLAT_INCLUSIVE_ADAPT | Strict native comparator gets first FP32 threshold above squared radius; scores/tolerance unchanged; boundaries and both million-row snapshots pass | Explicitly name the adapter; kNN remains native |
| GPU_RANGE_COMPLETE | Recovered cuVS26.8.1 FP32 L2Unexpanded route plus complete CUB filter/compact/D2H; N0/1/7/513/4096 edge/reuse and3 sanitizer tools pass; both target snapshots pass | Range only, not Faiss finite top-K; freeze formal observer/timing source before B |
| GPU_TREE native-search wrapper | PNUM8/K8; eight valid fields but only **6/8 true neighbors** on preregistered N4096/D17 duplicate-occurrence case; squared-field error1.16e-7 | **Blocked**, not a performance loss or all-GPU-tree claim |
| GPU_TREE ownership adapter | Same first-call full bytes and selected-tree counts; one build/32 B1 calls; kNN retains the same failure | Lifecycle repair does not repair semantics |
| GPU_TREE_SAFE_ADAPT | Additionally guards one unused tail read; bounded N4096 range outputs unchanged and mem/race/sync pass | Bounded range safety only, not full GPU_TREE or N1M admission |
| CPU_MVPT | Existing exact provenance/full-output gap remains | Not executed or replaced with a weak invented baseline |

The author's GPU-Tree is not original G-PICS. No complete third-party source is
redistributed; `prepare_tree.py` consumes exactly hashed user-supplied headers.
Native PNUM5 cannot serve K8 safely through the inspected Kth partition-bound
access; PNUM8 was registered before experiments, not selected from timing.

## CPU development freeze (not a formal ranking)

32 new coordinate hashes were excluded from both registered static query sets,
with two snapshot/data identities independently rebound. Seed2026101001.
Equal-count complete Host-ready kNN+range cost selects one leaf per tree.
FP32→FP64 preparation and construction were **not** used for leaf selection,
and must be separately reported in the formal lifecycle table.

| Method | Leaf | 32 kNN +32 range development pass, seconds |
|---|---:|---:|
| CPU_KD | 32 | 98.517700 |
| CPU_BALL | 128 | 68.499506 |
| CPU_KD | 512 | 69.855025 |
| CPU_BALL | 32 | 69.309134 |
| CPU_KD | 128 | 75.104631 |
| CPU_BALL | 512 | 67.255470 |

Only one development process per setting was requested; this is neither a
statistical speedup nor a claim of universally optimal tree parameters.
The existing32 static queries are already observed diagnostics, not held-out
cross-dataset generalization tests.

## Ownership fixes and negative evidence

1. Search freed tree topology metadata needed by subsequent calls. The reuse
   adapter moves those frees to index release and frees query filter temporaries.
2. Construction overwrites root-pointer table entries. Releasing that mutable
   table as allocation owners caused the first wrapper release failure. Original
   allocation pointers are now captured before construction and freed once.
3. Memcheck found `mergeRoot` reading node_sum_prefix[total_tree_num] after its
   final consumed root. The separately labeled safety overlay guards only that
   unused next-iteration load. It does not repair the native kNN membership bug.
4. The CPU harness first failed its non-overwrite precondition because logs shared
   an output prefix. That invocation measured no native work; logs were separated
   and all six development runs were registered afresh. Nothing was rerun to win.

All failures, native/safety identities, raw outputs and guard receipts are
retained. See [proof summary](evidence/A_RESULTS.json),
[build identities](evidence/BUILD_IDENTITIES.json), [ownership](OWNERSHIP.md) and
[remaining gates](NEXT_GATES.md). The private complete proof hash is
`fadfcb19246203ab798eabac8287d68fa6992cfdb123d2acbcee19c0e3bc099a`.

Next: freeze the actual six admitted static entrypoints/cost observers, then
execute the supplied balanced matrix and the separate functional bridge for T.
The direct R/P and strengthened-baseline T/P tables remain missing. No historical
ratio multiplication, global default, paper novelty or dynamic external win is
inferred from this checkpoint.

## Final audit binding

Publication review found and closed fail-open completeness and small-K>N field
checking gaps. The real20 GPU receipts were complete; none was discarded or rerun.
The original numerical proof above remains immutable. A separate admission binding
in the sanitized summary requires every expected receipt/guard/output/source and
binary identity. New CPU rechecks validate all three leaves, four N values,
32 repeats and five task/radius cases: **3840 KD/Ball +1920 inclusive Flat rows**,
all passing, including delivered kNN fields and ordering. Negative regression
fixtures reject missing/invalid receipts, incomplete matrices, stale sources,
NaN, wrong-length and misordered small-N fields. This adds no performance claim.

Four adapters also compiled from the clean deliverable source; see
[evidence/CLEAN_BUILD.json](evidence/CLEAN_BUILD.json). These compile-only binary
hashes are distinct from the measured hashes, not silently substituted for them.
