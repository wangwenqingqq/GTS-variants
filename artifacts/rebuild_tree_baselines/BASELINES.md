# Baseline capability and admission ledger

**This is a real execution/blocker ledger, not a list of assumed competitors.**
Static comparisons and dynamic workflows remain separate. All new CPU jobs use
the two already-registered GIST N1M/D960 snapshots, B1/K8 and radius bits
`0x3f34a3d8`; the second snapshot retains distinct duplicate occurrences. See
`BASELINE_RESULTS.md` for the actual six diagnostic processes and quality gates.

| Identity | Representation / D960 | Complete range / kNN | Native insert/delete | Execution and admission in this submission |
|---|---|---|---|---|
| CPU_KD | scikit-learn 1.6.1 KDTree; original FP32 coordinates exactly promoted to FP64; D960 executed | Native `query_radius` / `query`; all IDs and fields retained | Immutable fitted index; no required native update API qualified | Two fresh diagnostic processes; fixed leaf_size 128, single native thread; not six-round formal or dynamic |
| CPU_BALL | scikit-learn 1.6.1 BallTree; same FP64 promotion; D960 executed | Native complete `query_radius` / `query` | Same qualification boundary as KD | Two fresh diagnostic processes; same settings and scope |
| CPU_FLAT | Faiss 1.15.1 CPU IndexFlatL2; FP32; D960 executed | Native complete `range_search` / `search` | Library supports add/remove, but shifting row/occurrence semantics not qualified for this dynamic trace | Two fresh diagnostic processes; OpenMP 1; CPU index, not GPU or a tree |
| CPU_MVPT | SISAP MVP-tree implementation cited by GTS; source/provenance not qualified | Historical implementation identity and full field/ID delivery unresolved | Required native update interface not qualified | **Blocked** pending identifiable source/license and complete-result adapter; no new run or fabricated timing |
| GTS_ORIG | Pinned original ancestor, FP32 distance arithmetic; existing complete-output kNN adapter increases height capacity | Existing native kNN adapter; original complete range on these two snapshots not newly qualified | Original buffer/rebuild streaming path exists; exact mixed-task adapter/numerics must be labeled | Existing evidence retained, **not a fresh two-snapshot result**; do not relabel repaired A as untouched original |
| GTS_REPAIRED_A | Common numeric/safe-bound repairs; staged range + integrated FULL backend | Phase-B full 336-event membership/field proof retained; fresh profile prefix/warmup byte-identical | Qualified phase-B 40 insert/40 delete/2 rebuild internal contract | One new NSYS diagnostic, **not another primary timing round** |
| GPU_TREE | Pinned author-adapted multi-MVP/G-PICS strategy; `#define short float` makes the configured numeric input FP32; runtime D loops | Source has native range and kNN arrays; complete Host-ready B1 reuse adapter **not qualified** | No required insert/delete path found in inspected program | **Source-audited / not executed**; ownership, result delivery, original numerics, capacity and license gates remain |
| GPU_FLAT_KNN | Frozen native Faiss GPU FlatL2, FP32, no cuVS | Native kNN; do **not** infer complete range from finite top-K | Native/update-adapter occurrence semantics not admitted here | Phase-B two-snapshot B1K8 complete/tolerant quality and faster results retained; no fresh timing in this submission |
| GPU_COMPLETE_RANGE_SCAN | Separate complete range executor requested by the supplied plan, not finite top-K | Historical executor referenced in that plan; exact source/executable identity and two-snapshot requalification not closed here | Not a tree or a qualified dynamic system | **Pending**; previous kNN Flat results do not fill this row |
| GTSPP_B0 | Current PAR+FULL, threshold 10 | Existing qualified phase-B internal workload | Same repaired visibility/rebuild contract | One new B NSYS diagnostic; old 18 primary runs preserved |
| GTSPP_B1 | B0 + proposed build-distance tiling | No new implementation or qualification | Must preserve B0 state and output contract | **Not implemented / not timed**; advance only through submission-B gates |

## Actual source audit and blockers

The source pin is `ZJU-DAILY/GTS@3bac1b725e92e98e3b69d5cb79ad9c56ccb5e639`.
The author's [README](https://github.com/ZJU-DAILY/GTS/blob/3bac1b725e92e98e3b69d5cb79ad9c56ccb5e639/README.md)
identifies SISAP CPU baselines and its own adaptation of G-PICS. This does not
make GPU_TREE original G-PICS or justify statements about every GPU tree.
`evidence/UPSTREAM_SOURCE_AUDIT.json` records the inspected file hashes and
the non-truncated recursive source tree. No LICENSE/COPYING/COPYRIGHT-named
file was found in that pinned tree. This is a provenance/publication gap, not
an assertion of infringement or proof that the algorithm cannot run. Only
hashes and audit findings are published here, not additional third-party code.

GPU_TREE `src/main.cu` builds once, calls `search()` for a query batch and prints
average search time. Its `search.cuh` frees build-time `isSatisfied`, `tree_num`,
`tree_sum_prefix` and `node_sum_prefix` within the search path (both task
branches). Consequently, simply repeating 32 B1 calls on the same build is not
a qualified adapter. Batch-32 execution cannot be silently called B1 latency.
The display helpers address only the last five queries and are not called
by the inspected search path; their existence is not complete Host-ready output proof.
Native arrays must be retained and fully delivered before the timer ends, with
ownership/reuse and all capacity bounds checked. `DNUM=500` is the per-tree
partition capacity; it is **not** automatically a global range-result cap. The
correspondence between partitions, candidate counters and complete output
allocation still needs validation rather than assumption.

A local `MVPT/mvpt.cpp` was found, but it has no recovered upstream/version/
license binding; its range interface returns a count rather than all IDs and
fields. An older wrapper is also not proof of SISAP provenance. Neither is
renamed into a mature qualified baseline, and no weak replacement is written.
The cited SISAP library URL could not be retrieved during this audit. Reopen
when identifiable source/permission and complete output interfaces are available.

## Fairness and remaining formal gates

CPU diagnostics use one native thread, a common NUMA node and original query
coordinates; no auto algorithm or batching. Actual library threadpools are
recorded. The CPU has Xeon Gold 6530 processors, 128 logical CPUs and four NUMA
nodes. GPU diagnostics use an idle RTX PRO 6000 Blackwell Server 96GB with
live-verified device-local NUMA placement, driver 590.48.01/CUDA 13.1; NSYS 2025.5.2.266. Foreign jobs and shared
settings were left unchanged. Single-thread latency is **not** multi-core CPU
throughput. Sklearn's float64 representation and its memory/preparation cost
are charged and exposed; CPU Flat keeps FP32. No new environment was installed.

Six-round external timing remains conditional on capability/quality admission,
leaf-size development freeze on separate queries (32/128/512 candidates), and
an exact process-budget/order registration. A static index enters the dynamic
table only after a labeled complete buffer/tombstone/rebuild adapter or required
native update interfaces pass. Cross-policy replay requires frozen query/insert
vectors and distinct deletion occurrence IDs; bare physical row/live-rank
numbers are not a common workload after different maintenance policies.

ANN IVF/HNSW/CAGRA remain separate quality-latency evidence, not substitutes for
exact trees. No 10k/final10000 job, old primary matrix or long campaign was
restarted by this submission. No global fastest-CPU/GPU-tree claim is admitted.

## Later checkpoint: external-closure Stage A (2026-10-10)

[The new admission results](../external_closure/A_RESULTS.md) supersede the
pending GPU-tree/range recovery and fixed-leaf status **for this later scope**;
older diagnostics retain their original identities. GPU complete range passes
both original GIST N1M/D960 snapshots. KD/Ball select leaf512 on disjoint
32-coordinate development queries. A separately named CPU Flat inclusive-boundary
adapter passes edges and both snapshots. GPU_TREE remains excluded: native kNN
returns only 6/8 true neighbors on a preregistered N4096/D17 case, while ownership/reuse and
bounded safety-overlay range results are retained separately. MVPT remains open.
No new external formal timing or direct R/T/P cumulative table has run yet.
