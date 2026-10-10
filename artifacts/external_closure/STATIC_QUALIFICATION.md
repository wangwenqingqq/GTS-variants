# External static B: qualified Host-ready adapters

Historical checkpoint3aac39e; see [later authorized recovery](STATIC_RECOVERY.md)
for current execution status. The qualification/failure records below are unchanged.

**The new adapters pass six GPU qualification processes and an independent
stricter offline recheck. This is not an external speedup result.** The 72-process
formal matrix was launched after admission and stopped after4 passed processes
and one CPU Flat environment failure before construction. No complete static
ranking is published at this checkpoint.

## What changed

P previously selected an already device-resident database query. The formal
interface now submits the same Host FP32 vector on every call, charging its H2D
copy inside the query timer. One extra non-indexed row does not change N or tree
membership. Native GPU Flat and complete GPU range also start from Host input.
No GPU kernel was optimized or changed in this delivery.

All methods build once. Each supported task has eight warmups followed by a
continuous pass of 32 B1 calls. Full IDs and FP32 Euclidean fields must be ready
on Host. Preparation, construction, warmup and owned-resource release are
recorded separately. External native-squared observers remain charged; no
observer cost is subtracted. Serialization and later client consumption/release
of retained answers are outside the service timer.

## Gates actually passed

| Qualification | Shape | Complete delivered queries | Outcome |
|---|---|---:|---|
| P memcheck | N4096/D128 |80|Full membership/fields and zero declared errors|
| P racecheck | N4096/D128 |80|Full membership/fields and zero errors/warnings|
| P synccheck | N4096/D128 |80|Full membership/fields and zero declared errors|
| P initial snapshot | N1,000,000/D960 |80|Full membership/fields and state|
| P first-rebuilt snapshot | N1,000,000/D960 |80|Full membership/fields and state|
| Complete range memcheck | N4096/D128 |40|Full membership/fields and zero declared errors|

P preserves all **113 GPU functions / 76,152 normalized instructions** of the
admitted parent. Complete range preserves all **5 functions / 3,280 normalized
instructions**. This static identity is separate from runtime correctness,
sanitizer and timing evidence.

The original resource-wrapper attempt failed before CUDA because a standalone
time executable was missing. Its registration, command and logs remain intact;
it consumes one slot. The standard-library replacement changed no native
algorithm, query set, precision or timing boundary. Counters are **25 prior +
1 retained failure +6 successful =32/32 GPU qualification attempts**. There is
no remaining automatic GPU qualifier allowance.

The subsequent offline checker binds all six actual guard directories (including
failed attempts without receipts), exact registrations/inputs/build/source,
device/placement, commands and payloads. It additionally rejects negative or
nonfinite Euclidean fields and descending kNN fields. Existing R2 outputs pass
this stronger R3 check with **zero GPU reruns**. R1/R2 execution sources remain
immutable and distinct from the current verifier; compiled source registration
uses the R1 contract, while the successful runtime uses the explicit R2 recovery.

## Formal matrix scope — not a completed result

- Original FP32 GIST: **N1M, D960, B1, K8**, radius bits `0x3f34a3d8`, initial and
  first-rebuilt snapshots. Previously observed diagnostic queries, not held out.
- P: PAR_STRONG/FULL/TILED; KD/Ball: native FP64, development-selected leaf512,
  one native thread. CPU Flat is **CPU_FLAT_INCLUSIVE_ADAPT**, not raw-native
  inclusive range. GPU Flat kNN uses native Faiss FP32; range uses cuVS FP32 plus
  inclusive filter, CUB compaction and complete delivery.
- Six admitted methods x two snapshots x six frozen balanced permutations =
  **72 planned external primary processes**, plus18 completed internal primaries
  =90/102 if all complete. Failed attempts are retained, never replaced to win.
- Same isolated single RTX PRO 6000 Blackwell, CUDA13.1/SM120; shared CPU host,
  fixed NUMA placement. Foreign jobs and clocks/power settings are unchanged.
- `static_results.py` is the fail-closed offline analyzer for a future COMPLETE
  matrix. Its complete72-row real-evidence path has **not yet been exercised**.
  It must not emit partial-row rankings. Paired ratios compare comparator/P,
  bootstrap20,000 with seed2026101002; both order strata and >=5/6 wins are required.
- Both-task lifecycle, when reported, is preparation + build + measured kNN pass
  + measured range pass + release. It excludes warmup, parsing and context setup;
  it is **not fresh-process wall time**. Single-task GPU baselines cannot be
  silently compared against this dual-task sum.

GPU_TREE remains blocked by native membership failure; MVPT provenance/full
output remains unavailable. The original96 B managed context-symbol issue is
unresolved. No production/leak-clean, dynamic superiority, novelty,100k/1B or
new10k-workflow claim follows from these gates. The private manuscript is unchanged.

See [sanitized bound evidence](evidence/STATIC_QUALIFICATION.json),
[effective runtime contract](STATIC_CONTRACT.json), [retained original contract](STATIC_CONTRACT_R1.json),
[attempts](STATIC_ATTEMPTS.md), and [measurement design](STATIC_DESIGN.md).

## Primary stop, not a completed external comparison

The first four processes passed: CPU Ball, GPU Flat kNN, P, complete GPU range.
The fifth, CPU Flat, used the CPU-tree interpreter, which has sklearn but not
Faiss, and failed on import before building an index or returning any query.
This is a launcher dependency-routing omission, not a membership failure or a
native timing observation. The guard stopped the entire matrix as registered.
The known Faiss interpreter also lacks threadpoolctl, so merely changing the
interpreter without correcting the unnecessary CPU Flat dependency is not enough.
No package was installed or upgraded.

All5 attempts are retained:4 valid partial observations +1 failed, cumulative
**23/102 primary attempts** including18 internal. There is no COMPLETE proof,
no six-round interval, and no formal speedup ranking. The partial data remain
[available with exact identities](evidence/STATIC_STOPPED.json), not discarded
for having an unfavorable direction. Resume requires a separately acknowledged
bounded recovery, preserving all old observations and the failed invocation.

### Prepared dependency repair — not resumed

`STATIC_CPU_ENV_FIX.patch` is an **unapplied** two-file repair: route CPU Flat to
its existing qualified Faiss interpreter and restrict threadpoolctl to KD/Ball.
CPU Flat uses the native Faiss OpenMP setter/getter to enforce one thread. No
native distance/index/query code or timer is changed. Dry-run application and
Python compilation pass; the corrected native timing driver has not been run.
`static_preflight.py` successfully imports and checks the existing tree and Faiss
versions/API/thread control, without data, index build, query or CUDA allocation.
This is dependency evidence only. Original R3 sources and output identities stay
intact. Applying the patch and resuming require a separate recovery registration,
source binding and the explicitly requested exception to the no-replacement rule.
