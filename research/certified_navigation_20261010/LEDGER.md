# Append-only experiment ledger

## 2026-10-10 — source and query freeze

Experiment: `gts_20261010_certified_navigation_rnfp64_b1`.
Eight upstream source pins passed. The selected executor has current-layer
pivot thresholds but no persistent distinct cross-layer witnesses and no
pivot-to-leaf memo. Exact tree ownership audit passed for GIST 1M x 960.
Development 32 and formal 256 query IDs were frozen disjoint from one another
and the explicitly inventoried prior fixture lists; the inventory does not
certify absence from undisclosed historical query files.

## 2026-10-10 — CPU-only work model (partial)

`evidence/CPU_MODEL_RECEIPT.json`, `query_work_model.csv`, and
`threshold_model.csv` retain the model. This computes canonical pivot distances
and replays original *raw FP32* split intervals. It does not compute leaf
answers, validate GPU execution, certify these raw bounds, or measure latency.
Memo is idealized at the pivot-to-leaf boundary. 32 actual development queries:
G0 mean 947977.5 leaf objects, G2 947775.3125. Mean per-query fractional leaf
saving 0.00022155065765. Replaying G0's upper timeline in G2 restores G0 visits
in this model. Candidate effect is tiny, not absent; positive in 21/32 queries.
No timing or universal GPU-tree claim is permitted from this model.

## 2026-10-10 — build and hardware admission

Original GTS was preserved byte-for-byte. Generated isolated overlays and an
independent exhaustive reference compiled for sm_120a/CUDA 13.1 with FMA off.
Initial generator-anchor and relocated nvcc header failures were retained
privately; neither is a CUDA correctness or performance observation.

GPU 0 had a foreign process. GPU 1 was explicitly approved but concurrently
occupied by a separate GTS campaign. The user then approved physical GPU 2 and
freshly measured four controls. GPU 2 was idle at preflight, but a new VLLM
worker occupied it before admission. The two-sided-starttime guard refused
launch; **no oracle or tree GPU query ran in that attempt**, no foreign process
was signaled. Admission failure retained as `e1_v3`/runner log in private
scratch. Formal budget remains 0/24.

Prototype v3 had a needlessly serial common threshold selector. Before any
GPU tree sample, v4 restored G0/G1's original O(1) Kth read after the native
pivot sort; only G2/G3 pay the persistent candidate insertion cost. This is a
pre-measurement baseline-identity correction, not a changed result or gate.
Six CPU regression checks passed, including source/anchor drift, exact leaf
ownership rejection, result protocol rejection and guard PID-reuse cases.

Current status: source/ownership built; CUDA correctness unvalidated; E1 GPU
work/timing pending exclusive hardware; E2 full boundary/invalidation matrix
not passed; E3 not admitted; E4 not started. GPU 3 authorization requested after
fresh GPU 2 occupation. Preserve this status until a separate live receipt
changes it.

## 2026-10-10 — physical GPU 7 admission and first E1 receipt

GPU 3 was also occupied by the same new VLLM tensor-parallel job. The user
explicitly authorized selecting a freshly idle device from physical GPU 4/5/7.
GPU 7 / NUMA 3 passed live checks. One existing guard held both shared advisory
locks throughout all E1 processes; no foreign activity, clean completion.

v4 E1: all four full outputs matched the separate GPU exhaustive reference
bitwise on 32 queries; G0/G1 and G2/G3 complete recorded visit/upper/candidate
traces matched. G2 replaying G0 upper values restored G0 visits. A separately
compiled scalar CPU exhaustive reference independently matched the same full
result bytes. 35 small reference queries also matched Python ordered-FP64 and
exact-rational rank checks (reference-only, not native-tree E2).

Preliminary v4 diagnostic totals: G0/G1/G2/G3 coordinate updates were
29493222720 / 29176068480 / 29486222400 / 29169161280. Leaf calls were
30376910 / 30376910 / 30369720 / 30369720. These are measured CUDA counts.
All original widened split intervals passed full coverage (0 disabled nodes).
These v4 samples remain retained and are not pooled with final v6 timing.

Audit found a remaining upstream finite-infinity sentinel at initialization.
Although 10000 exceeds all distances in the frozen [0,2], D960 envelope and
first two levels never prune, the required witness invariant calls for literal
+infinity until K valid witnesses. v6 corrects initialization and skips invalid
Kth sentinels uniformly; all four E1 modes are freshly remeasured. No formal
samples have been used and no previous raw sample is rewritten.

The first v4 default memcheck reported four `cuLibraryGetKernel` symbol-not-found
API errors during CUDA context initialization, before geometry/query work.
The run was stopped, not labeled sanitizer clean; no memory-error waiver is
assumed. Its outer guard also failed final receipt writing because the passed
program name was not an absolute path; ownership logs and raw failure remain
private. Subsequent guarded commands use absolute executable paths. API/tool
localization and profiler evidence remain diagnostic-only; E2 is not admitted.

## 2026-10-10 — v6 E1 final (measured scope; not promoted)

v6 binary `9c4d7310ab6d6e04e1bebcad4c1d491174f3c0a73a6a715c29882be4929d0dd1`.
Four modes freshly run under one GPU 7/NUMA 3 lock. Full ID and FP64 score bytes
match both independent GPU and scalar CPU exhaustive references. Literal
+infinity before K witnesses is now recorded as null in the trace. Finite
upper bounds begin at level 3. The common initializer correction leaves all
v4/v6 query-work counts and result bytes identical in the frozen dataset.

G1 saves 1.075346% coordinate updates, with identical visits. G2 saves
0.023735% coordinate updates and 0.023669% leaf calls. G0 visits on average
949278.4375 / 1000000 leaf instances (94.9278%). G3 saves 1.098766% coordinate
updates; its visits match G2. G0 upper replay in G2 again restores G0 visits.
No DRAM-traffic or bandwidth claim is made from these software counters.

One reverse-order, uninstrumented diagnostic process per mode (G3,G2,G1,G0):
G0 932.696709 ms, G1 901.412060 ms, G2 1575.850244 ms, G3 1564.038097 ms,
for the 32-query pass. This denominator starts with a resident-data query ID,
not a complete external Host vector. No paired CI, formal ranking or >=10%
promotion. v4 G1 had the opposite timing sign; retain it without pooling
versions, and do not call the v6 G1 nominal 3.35% change a robust win.

Decision: **LOW_REUSE_HEADROOM** and **WEAK_CANDIDATE_EFFECT** for this exact
original-tree GIST snapshot/query sample. Stop before E3/E4 or parameter sweeps.
The serial cross-layer insertion prototype's slowdown is implementation-level,
not proof that all candidate implementations or all GPU trees are slow. Reopen
memo/candidates only with a different frozen tree/workload showing substantially
more repetition or avoidable visits, or a new non-incremental mechanism.

E2 remains incomplete: native small/N<K cases, cache-capacity controls, dynamic
storage invalidation, adversarial boundary/stress matrix and strict API sanitizer
gate are not passed. Formal budget remains **0/24**. E1-O eight-query ideal-region
diagnosis is deferred because the first reuse/candidate mechanism has a clear
low-headroom exit; no stronger-certificate, partition-limit or external-ranking
conclusion is drawn.

## 2026-10-10 — v6 initcheck failure; uniform correction pending

API-reporting-disabled memcheck completed G0/G3 on the first two dev queries
with zero reported memory errors. Initcheck then reported uninitialized 8-byte
reads at the upper half of 16-byte NavKey elements in CUB ThreadLoad. The old
key was `double score; int id;` with four implicit padding bytes. The probe hit
its 600-second timeout; its sanitizer subreaper/query child survived parent
termination. Both exact owned processes were subsequently stopped after UID,
command and process-starttime checks; no foreign process was signaled.
The whole probe is invalid, not a sanitizer pass. Logs remain unchanged.

v7 makes the padding an explicit zero-initialized reserved integer for every
mode, and adds diagnostic-only exact per-node visit bitsets. Bounded probes
now stop their own subprocess group on timeout and retain a failed receipt.
This is a common representation fix, not a memo/candidate optimization. Fresh
four-mode E1 and differential sanitizer evidence are required; no v6 timing is
pooled into a v7 comparator. Full E2 and E3 admission remain blocked.

## 2026-10-10 — v7 final diagnostic and bounded tool localization

v7 binary `cf89d346c1f70e495f4fc235fc60c87e51de29f04ed1cc870dd129e76253a769`.
Fresh four-mode E1 under one GPU 7/NUMA 3 guard: all work CSVs and complete
result bytes match v6. Exact per-node visit bitsets match G0/G1 and G2/G3;
G2 with G0 upper replay restores every recorded G0 visit bit. G0 witness-ID
provenance and the full native-tree E2 matrix remain separate missing gates.

Uninstrumented diagnostic totals G0/G1/G2/G3: 925.438587 / 920.598571 /
1578.714066 / 1568.954307 ms, 32-query resident-ID pass. One reverse-order
process each, no paired confidence or promotion; prior timing retained, not
pooled. The ~0.52% nominal G1 change is not a robust win.

A fresh whole-guard-valid first-two-query probe reports zero memory/init/sync
errors for G0 and G3, explicitly with API-error reporting disabled. All six
sanitizer and two NSYS full results match the corresponding independent
reference subset bitwise. The old v6 initcheck failure stays failed. A no-query
plain API smoke has zero default-memcheck errors; the identical smoke plus
unmodified original GTS headers reports two cuLibraryGetKernel NOT_FOUND(500)
errors. This localizes a pre-query original-header/tool boundary; it does not
establish a harmless waiver or pass strict API admission.

NSYS diagnostic G0/G3 two-query ranges: 71.472619 / 109.858721 ms; 140 kernels
in either mode. nav_update inclusive GPU durations 0.791 / 41.491 ms explain
most of the added range time in this serial candidate prototype. G0 has 38
cudaDeviceSynchronize and 66 cudaStreamSynchronize calls. Runtime API spans
mostly contain GPU waiting, not a measured CPU-computation percentage. No CPU
utilization samples or NCU hardware DRAM/coalescing counters were collected.

Final decision remains LOW_REUSE_HEADROOM / WEAK_CANDIDATE_EFFECT on this
snapshot. E2 incomplete, E3 0/24, E1-O and E4 not run. No production keeper or
paper novelty is promoted. Next possible branch is a separately frozen small
same-U region-truth/interval diagnostic, not a larger memo parameter search.

## 2026-10-10 — delivery audit checkpoint

Fresh generation from the staged full repository matches every compiled v7
input byte. Eight CPU checks pass, including exact-visit-bitset rejection and
a check that an unused profiles-only branch is removed. The second read-only
audit found that branch would reference a non-created memcheck output; it was
never used in a measurement. Removing it does not change the fixed successful
six-sanitizer/two-profile workflow, CUDA inputs, binary or raw evidence.

Publication set is task-owned source plus curated diagnostics only. Full
publication-base ancestry was independently scanned: the only path-pattern
hit is an existing redaction-regex literal, not a real private path. Unrelated
old refs are not added to the new branch or rewritten. No credentials, private
host paths/UUIDs, raw conversations, dataset or original source copies are in
the outgoing set. Final Git/remote verification is a separate delivery receipt.
