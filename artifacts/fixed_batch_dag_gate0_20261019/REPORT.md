# Fixed batches: simple sharing versus a restricted oracle

## 1. Strongest result and material exception

**Simple shared access has not consumed all finite-chain opportunity at B2/B4;
B8 still has a wide certified interval and fails to establish a win over the
batched full-scan source control.** No GPU, service-latency or new-index claim
follows from these offline values.

| B | Independent GB/query | Strong simple GB/query | Oracle cost interval GB/query | Extra saving vs strong simple | Batched full scan GB/query |
|---:|---:|---:|---:|---:|---:|
| 2 | 0.814114808 | 0.753396888 | 0.671067576–0.671067576 | 10.9277%–10.9277% | 1.920003960 |
| 4 | 0.814114808 | 0.706752120 | 0.541218968–0.541218968 | 23.4217%–23.4217% | 0.960003960 |
| 8 | 0.814114808 | 0.617970648 | 0.340882040–0.603455032 | 2.3489%–44.8385% | 0.480003960 |

The strongest predeclared simple envelope is the minimum of PREFIX_TRIE,
GREEDY_FANOUT and GREEDY_LOOKAHEAD per entire batch. It is an optimistic posthoc
control, not an online chooser. In this population **GREEDY_FANOUT itself attains
that envelope in all28 batches**, so no unimplemented selector is needed for
these particular values. The frozen primary remains GREEDY_LOOKAHEAD; its labels
are retained separately rather than silently selecting a better primary.

The oracle interval is [certified lower source cost, feasible upper source cost].
The corresponding saving interval reverses these endpoints. B2/B4 endpoints
coincide; B8 endpoints must never be reported as one measured optimum.

## 2. Redundancy → mechanism → module → role → end-to-end evidence

| Redundancy or tension | Mechanism/module | Role | Complete-service evidence |
|---|---|---|---|
| Repeated physical-tile requests across queries | Data-centric frontier sharing in solver.cpp | One tile emission feeds all ready matching chains | UNKNOWN |
| Shared reads versus divergent proof orders | Prefix trie, two greedy schedules, bounded A* | Measure residual source-read opportunity | CPU source model only |
| Full-score authority after reordered filtering | Immediate per-sector original-order terminal pass | Charge terminal rereads, no free coordinate retention | Model, not a new verifier run |
| Predicted access compatibility and recipe reuse | None implemented | Not tested; fixed batches only | UNKNOWN |

A query signature, plan cache, DAG name or bitmask does not establish novelty.
The nearest shared-execution, dual-tree and GPU data-centric prior art is retained
in PRIOR_ART.md. The authorized CPU falsification is not novelty admission.

## 3. Population and inherited numerical authority

The immutable source is GIST1M, N=1,000,000, D=960 FP32, 3.84GB raw coordinates.
All32 inherited queries and the exact inclusive range threshold are unchanged.
Every query is drawn from the database in the earlier diagnostic; self-matches
are not removed. They are **development probes**, not32 new held-out requests,
production arrival logs, or evidence of compatibility stability across time.

The parent PDX CPU campaign preserved32M per-query/candidate guarded first-crossing
counts and dimension orders. All64 consumed safe/order files match the parent's
public SHA256/size manifest; histograms, zone boundaries and logical query IDs
are rechecked. The complete parent RESULTS identity matches the published
recovery authority, not just its self-reported correctness flags.

No new distances or output fields are evaluated. We inherit the parent's guard
for rounded nonnegative FP64 terms relative to its ordered-FP64 authority, and
never reorder terms within one query. We only change how different query chains
are interleaved. This preserves the declared certificate arithmetic abstractly;
it is not a new GPU numerical qualification or an exact-result benchmark.

## 4. Frozen physical access and state model

Each database sector contains eight adjacent candidate rows. A physical tile is
one32-coordinate zone of that sector:32 coordinate-major sectors ×32B =1024B.
Thus sharing requires the same snapshot, candidate sector and dimension zone,
not merely the same dimension number on different candidates.

This is a **hypothetical single coordinate-major representation**, not measured
accesses of the existing row-major GPU program. Transposition/build/update cost
and alternative layouts are not priced as free service work; they are unmeasured
and outside this fixed resident-snapshot model. There is one3.84GB database, not
a hidden second raw vector copy.

Each point checks the inherited guarded proof at32-coordinate boundaries. Its
zone count is ceil(first_safe_crossing/32). A query's sector chain stops at the
maximum of its eight point depths. Point masks allow earlier points to stop
arithmetic, while source sectors still fetch all eight values. For every sharing
schedule the per-query coordinate-operation count is unchanged.

For each sector, all B filter chains finish, an original-order terminal pass
immediately follows, then state is released. Any point with rounded depth30 is
conservatively verified, including some last-zone rejectable nonhits. This is an
explicit protocol, not unavoidable work. A terminal sector costs960×32B;
shared schedules pay once across their terminal queries, independent execution
pays per query-sector. No last-filter-tile reuse or cross-sector caching is free.
The full-scan control is one original-order batched pass, with no second terminal
pass; its query-coordinate arithmetic is much larger.

Live per-sector arithmetic state is B×8×8 bytes of FP64 partials plus B bytes of
candidate masks, and one1024B tile buffer. Query coordinates (3840B/query), order
inputs (120B/query), scheduler positions/queues and actual state traffic are
separate. Modeled resident quantities are not measured GPU registers, spills,
occupancy or DRAM. No all-N query-state matrix or global terminal queue is assumed.

## 5. Strong simple schedules and oracle scope

PREFIX_TRIE recursively shares identical current prefixes and never reunites
branches. GREEDY_FANOUT chooses the ready zone serving most queries, ties by zone
ID. GREEDY_LOOKAHEAD first maximizes the same fanout and then scores proximity in
the known full per-query orders. Neither greedy score consults future rejection
depths: active/finished status is revealed only when the simulated prefix ends.
The lookahead heuristic regresses against fanout here; sophistication is not
proof that it is the stronger control.

The restricted oracle solves a shortest-common-supersequence problem for these
fixed sector chains. A state is the vector of per-query prefix positions. One
transition reads a ready zone once and advances every ready matching query.
Serving these extra consumers is weakly dominant for source-read count because
per-query arithmetic/work and future chains are fixed. The oracle never chooses
a new certificate order, prefetches nonready coordinates, retains multiple tiles,
shares across sectors/snapshots, or removes query-specific arithmetic.

A* uses two admissible bounds: the union of remaining zone symbols and the exact
pairwise SCS bound at the initial state. Initial feasible witnesses are both
frozen greedy schedules plus an eager-serve-all normalization of the trie. Full
future chain lengths are free to the oracle only; it is not an online algorithm.
The new mechanism question includes whether this information can be obtained
cheaply, and is unanswered by the oracle.

The cap is4096 expanded states/context and2,000,000/batch. At a cap, the minimum
open frontier bound and a complete feasible witness remain a certified interval.
No unresolved interval is relabeled optimal. All identical chain-length contexts
are deduplicated, but their physical sectors remain frequency-weighted.

| B | Unique contexts | Exact-cost sectors / all batch-sectors | Expanded A* states |
|---:|---:|---:|---:|
| 2 | 1956 | 2000000 / 2000000 | 19055 |
| 4 | 22446 | 1000000 / 1000000 | 994390 |
| 8 | 293405 | 32061 / 500000 | 8000000 |

## 6. What the gap means, and what it does not

Primary source cost includes filter tile reads, the declared terminal pass and
query/order inputs. Its remaining-read ratio is shared/independent; smaller is
better. Additional headroom versus a simple cost C is bounded by
(C−oracle_feasible_upper)/C through (C−oracle_certified_lower)/C.
Filter-only gaps are also retained, so fixed terminal fees cannot conceal a gap.
These are exact finite-population arithmetic, not confidence intervals.

- B2: the strongest simple schedule leaves10.9277% additional source saving.
- B4: it leaves23.4217%, with all sector optima established.
- B8: only2.3489% additional saving is demonstrated;44.8385% is an optimistic
  maximum. Only6.4122% of weighted sector cases have exact optima. Further oracle
  work or a better feasible schedule is needed before claiming material B8 gap.
- B8 strong simple0.617970648GB/query exceeds batched full scan0.480003960.
  Best feasible oracle0.603455032 also exceeds it. Lower bound0.340882040 does
  not establish a realizable full-scan win. Full scan and pruning have different
  arithmetic costs, so byte comparisons are not latency rankings.

The original primary LOOKAHEAD reports larger gaps, including16.1089% proven at
B8. This is **not** the gap against the strongest simple control. Both primary
results and the adversarial envelope are published; headline claims use the
stronger comparison.

## 7. Correctness, execution and retained preparation diagnostics

28/28 CPU population processes pass, maximum four workers, nice10 enforced and
recorded, no failed population process or automatic retry. Zero GPU starts.
Existing sources/results/data and confidential manuscript remain untouched.
One GCC syntax preflight succeeded with three formatting warnings; newline-only
fixes were placed in a new execution-source snapshot before any population
solver target. Earlier snapshots and diagnostic logs are retained. Before that,
read-only audit strengthened niceness checks and bounded-search fixtures.
The original contract, derivation and input identities are never rewritten.

Independent fixtures check1344 oracle brackets,36 exhaustive word-enumeration
comparisons,152 strict oracle wins,60 bounded-search branches, shared budget
exhaustion, empty/reconvergent chains and four malformed-input rejections.
Every real context and complete feasible witness is independently replayed.
The post-run binder closes frozen inputs/sources→build→qualification→28 starts,
commands, logs, successful exits and output hashes→statistics. It regenerates
all inputs/results byte-identically and rebuilds the diagnostic binary identically.
No population solver or GPU target is rerun by that closure.

## 8. Decision

**A finite-chain gap survives the predeclared simple controls at B2/B4; B8 versus
the strongest control remains unresolved.** This justifies retaining the
opportunity question, not building a recipe index or starting GPU work now.

The next missing evidence is a future-blind inexpensive policy that captures the
gap against strong sharing and full scan, followed by generalization beyond the
32 development queries. Signature extraction, planning, masks/partial spills,
actual coalescing/cache effects, final outputs, updates and service/SLA costs
remain unknown. Ordinary SCS heuristics and data-centric GPU precedents remain
strong competing explanations. No new research mechanism is admitted.
