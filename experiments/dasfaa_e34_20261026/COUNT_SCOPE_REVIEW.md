# P work-counter scope review

Reviewed 2026-10-26 UTC, read-only after vector epoch initialization. No frozen
source, evaluator, workload, or run artifact was changed for this review. This
is a source-attribution audit, not an independent runtime counter measurement.

## Verdict

The existing WORK sites cover all **explicit query-to-pivot and
query-to-indexed-object metric evaluations** on the declared external-vector
full-ID L2 kNN path. They also cover every candidate `(query, leaf-node)`
processing-block invocation on that path. There is no identified missing
query-distance evaluation site in this specific call graph.

The Word harness's native-ID full-ID kNN path is covered by the corresponding
ID-query sites, provided the harness continues to use appended query IDs
`N+i` outside the indexed `[0,N)` range. This is a source-level coverage
finding; a Word counter binary and successful full-output run are separate,
not-yet-established gates.

Do **not** describe these counters as total end-to-end work, unique leaves,
per-batch work, tree-build work, FLOPs, instruction counts, or measured DRAM
traffic. Those broader scopes are incomplete/unmeasured. Current counters are
aggregates over a complete query pass, not per-batch observations.

## Provenance checked locally

- Original P search header SHA256:
  `2268650537923903819c84245ca0b05050636cab59508d114a4033e952cce278`.
- Approved patch plus WORK-only header, reconstructed with `adapt.corrected`:
  `1cf8ec247dc36f087b610dfae296b8c29a5a7b3c0a2f777bb26fb815cd442052`.
- This header hash matches the downloaded build manifest for
  `corrected_20261026T013932.417102Z`, build ID
  `508d02b2d5b73aa08080d1fc6514a9a1af150c88708999ad16a3b500ac6600af`.
- Adapter SHA256:
  `165860a65b517387278d1926b496697e6be9e50efd95ad83d2a67118bc3e9cb5`.
- Vector harness SHA256:
  `aeea431516a1677fe307c982773fb0faf2da42b2751d0a28e427a21f3d075b2c`.
- Downloaded manifest records `tree_count` SHA256
  `bee426753372b17ecae60d7b94953bb3743ecd7685c0ee179ea39d960944d83e`.
  This review did not re-download or execute that binary.

## Exact instrumented sites

Line numbers below refer to the reconstructed patched+WORK header, not to an
unpatched archive or a future build.

| Site | Instrumented line | Counter | Exact event |
|---|---:|---|---|
| `getDisPQVec` | 1027 | `WORK(0,1)` | One active query/pivot distance evaluation; immediately after the active-parent/nonempty-node guard and before `dis_q=0` and the metric branch. |
| `dataProcessKnnVec` | 682 | `WORK(1,1)` | One launched candidate-leaf processing block, counted by `tid==0`, before the padded-object loop. |
| `dataProcessKnnVec` | 690 | `WORK(0,1); WORK(2,1)` | One real indexed-object distance evaluation, after `did < node.size && node.is_leaf == 1`; padding slots are not counted. |
| `getDisPQ` | 911 | `WORK(0,1)` | Native-ID equivalent of the active query/pivot event; used by Word. |
| `dataProcessKnn` | 561 | `WORK(1,1)` | Native-ID candidate-leaf block invocation; used by Word. |
| `dataProcessKnn` | 569 | `WORK(0,1); WORK(2,1)` | Native-ID real indexed-object event; used by Word. |
| `dataProcessRnn` | 445 | `WORK(0,1); WORK(2,1)` | A range-query site, not reached by either declared kNN harness. Its presence does not make range-query coverage complete. |

Thus `distance_calls = pivot evaluations + leaf-object evaluations`,
`leaf_distances = leaf-object evaluations`, and
`distance_calls - leaf_distances = pivot evaluations` on these declared paths.
The difference is an attribution derived from the two counters, not a
separately collected counter.

## Vector call graph and excluded operations

`tree_bench.cu` passes a `float* query` plus `int* output` to the full-ID
external-vector `searchIndexKnnV2` overload (archive entry at line 2104).
Its metric-evaluating kernel calls are `getDisPQVec` for active pivots and
`dataProcessKnnVec` for real objects in candidate leaves. Both are covered.

- `labelCNode` propagates candidate state without computing distances.
- `nodeProcessKnn` reuses stored pivot distances and applies lower bounds;
  its residual-pruning function is C2-off. It does not evaluate a new raw
  query/object metric distance.
- `updateDisK`, query/leaf merging, initialization, sorting, scans, reductions,
  output merging, transfers and synchronization do not perform an additional
  raw query/object metric evaluation. They are not distance-counter events.
- Tree construction (`getPivotDis` and related build operations) is before the
  counter reset and has no WORK sites. Its distances are intentionally absent.
- CPU oracle, CPU output audit and S's FP64 refinement are separate processes
  or arms and are not included in P's counters.

A candidate-leaf event counts an actual processing-block invocation, not a
unique leaf-node ID. Revisited leaf/query pairs count again. Because the
candidate-leaf counter is before the object-validity guard, a launched block
with no eligible object still counts once. This is appropriate for invocation
counts, not a claim about nonempty unique leaf visits.

## Word native-ID path

`edit_tree_bench.cu` appends each batch's query strings after the indexed N
strings, while `info[1]` remains N. It passes `qids[i]=N+i` and full output IDs to
the native-ID full-ID `searchIndexKnnV2` overload (archive entry at line 1860).
That overload calls `getDisPQ` and `dataProcessKnn`, both instrumented above.
The actual edit-distance recurrence, including the zero-length shortcut, is
one metric evaluation per reached WORK site, not one event per DP cell.

`dataProcessKnn` has an indexed self-query shortcut after its WORK site. It is
not reachable with the declared Word interface: indexed object IDs are below N
and batch query IDs are at least N. Reusing this counter for in-index native-ID
queries would require explicitly distinguishing a trivial self-result from a
computed metric evaluation; this review does not authorize that broader use.

## Denominator and normalization

The vector runner creates count tasks with `reps=0` and `warm=0`. The harness
resets counters after building the index, executes the complete first output
pass, then reads the counters. Consequently:

- Q=1: one complete 1,000-query pass; counters aggregate 1,000 batches.
- Q=32: one complete 1,000-query pass, including 31 full batches and final
  ragged batch of 8. Counters include that ragged batch.
- Q=1024: one batch of 1,024 rows: 1,000 unique held-out queries plus the first
  24 repeated. Counters include the repeated work.

Report raw totals with these denominators. Per-query means may divide by
1,000, 1,000 and 1,024 respectively. Q=32 aggregate counts cannot be exactly
converted to the timing estimator's average **full-32 batch** work because
there is no counter snapshot separating the final 8 queries. Do not silently
pair `total/31` or `total*32/1000` with that estimator as an exact quantity.
For future nonzero warm/reps instrumentation runs, verify the counter reset
location again rather than assuming the count-task denominator.

## S scan-byte scope

`scan.py` reports `logical_scan_bytes_per_batch = Q*N*D*4` for float32 vectors.
This is a declared logical base-vector-read volume for a full-Q batch. The
ragged final Q=32 batch has logical volume `8*N*D*4`; it is not a full32 batch.
For one complete first pass, use `1000*N*D*4` at Q=1 or32 and
`1024*N*D*4` at Q=1024.

This is not measured DRAM traffic. It excludes native FAISS's temporary,
selection and repeated memory accesses, result/input traffic, and CPU FP64
candidate-refinement traffic. No profiler or hardware byte counter was
collected by this review. Do not equate this logical S denominator with a
measured P/S memory-traffic ratio.

## Publication boundary

Allowed wording: "A separate instrumented build counted query-time pivot and
leaf-object metric evaluations and candidate-leaf processing invocations;
counts cover a complete 1,000-query pass (1,024 rows in wrapped Q1024). S byte
counts are logical float32 base-vector scan volumes, not measured DRAM bytes."

The source coverage finding alone is not a correctness gate, a count-run
success, a sanitizer result or a performance claim. Required runtime count
artifacts remain subject to the same independent full-output audit and frozen
source/binary identity gates as the rest of the campaign.
