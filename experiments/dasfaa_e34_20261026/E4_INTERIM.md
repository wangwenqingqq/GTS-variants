# E4 intermediate report — post-incident continuation

Updated 2026-10-26 02:24 UTC. **Status: operational HOLD before formal timing; crossover, ratios/CI and slopes remain unknown.**

No result from the three incident epochs is used. The corrected diagnostic epoch completed eight bounded sanitizer/complete-ID gates, then was stopped intentionally for a full-output timing-contract clarification. This is not a guard97/98, fail-fast3, NVML-timeout, or failed-SSH restart. No formal six-pair timing began and no full-scale result is reported.

## Decision requiring explicit user direction

1. **Complete output:** the carried-over P harness copies k IDs to host but frees native k-distance output without materializing it on host. Native FAISS S returns distances and IDs. Do not label these identical complete-result payloads. Approval was requested to append a correction, create a fresh ID+distance harness/build, and repeat independent gates before timing. The current STOP remains set; no replacement epoch is automatically created.
2. **Deep value isolation:** first1000 public queries overlap base feature values. Approval was requested for deterministic source-order filtering against the largest20M prefix, then new1000-query/oracle hashes. No changed query set is presumed authorized.

## Fresh bounded hardware evidence

All rows below use N=2000,k=8 and the newly generated independent exhaustive CPU FP64 oracle. Recall is candidate-ID tie-aware recall, not validation of P distance-field delivery. Q1024 returns1024 rows with24 repeated queries. Zero invalid/duplicate IDs in every completed row.

| Arm | memcheck | synccheck | Tie-aware recall | Scope |
|---|---|---|---|---|
| P, approved correctness patch/C2-off | Q1/32/1024:0 errors | Q1/32/1024:0 errors | 1.00000000 in all6 runs | bounded ID outputs only |
| S, native FAISS Flat64 + CPU FP64 refinement | Q1/32:0 errors; Q1024 not run | not run | 1.00000000 in both runs | bounded ID outputs only |
| G | not run | not run | unavailable | compile-only; native arena int32 risk |

The last completed receipt reports the owned process exited0 and no foreign compute process was observed during its30-second-resolution admission/settling samples. The controller exited1 at the explicit STOP check before its next GPU launch; no PID or GPU setting was changed. Process/settling wall time is not query latency.

## Complete requested E4 vector matrix

Every Q is retained. Latency units would be host-ready batch milliseconds; none are eligible yet. P/S CI, crossover and fitted slopes are unavailable, not zero and not story B.

| Family/source | N | Q | P state/ms | S state/ms | P/S [95% CI] | Query/base value matches |
|---|---:|---:|---|---|---|---:|
| tloc/real | 1000000 | 1 | not run: output-contract hold | not run: output-contract hold | unavailable | 0 |
| tloc/real | 1000000 | 32 | not run: output-contract hold | not run: output-contract hold | unavailable | 0 |
| tloc/real | 1000000 | 1024 | not run: output-contract hold | not run: output-contract hold | unavailable | 0 |
| tloc/real | 3000000 | 1 | not run: output-contract hold | not run: output-contract hold | unavailable | 0 |
| tloc/real | 3000000 | 32 | not run: output-contract hold | not run: output-contract hold | unavailable | 0 |
| tloc/real | 3000000 | 1024 | not run: output-contract hold | not run: output-contract hold | unavailable | 0 |
| tloc/real | 10000000 | 1 | not run: output-contract hold | not run: output-contract hold | unavailable | 0 |
| tloc/real | 10000000 | 32 | not run: output-contract hold | not run: output-contract hold | unavailable | 0 |
| tloc/real | 10000000 | 1024 | not run: output-contract hold | not run: output-contract hold | unavailable | 0 |
| tloc/synthetic | 30000000 | 1 | policy-infeasible: N>10M; not run | not run: output-contract hold | unavailable | 0 |
| tloc/synthetic | 30000000 | 32 | policy-infeasible: N>10M; not run | not run: output-contract hold | unavailable | 0 |
| tloc/synthetic | 30000000 | 1024 | policy-infeasible: N>10M; not run | not run: output-contract hold | unavailable | 0 |
| tloc/synthetic | 100000000 | 1 | policy-infeasible: N>10M; not run | not run: output-contract hold | unavailable | 0 |
| tloc/synthetic | 100000000 | 32 | policy-infeasible: N>10M; not run | not run: output-contract hold | unavailable | 0 |
| tloc/synthetic | 100000000 | 1024 | policy-infeasible: N>10M; not run | not run: output-contract hold | unavailable | 0 |
| deep/real | 1000000 | 1 | not run: value-isolation failed | not run: value-isolation failed | unavailable | 16 |
| deep/real | 1000000 | 32 | not run: value-isolation failed | not run: value-isolation failed | unavailable | 16 |
| deep/real | 1000000 | 1024 | not run: value-isolation failed | not run: value-isolation failed | unavailable | 16 |
| deep/real | 3000000 | 1 | not run: value-isolation failed | not run: value-isolation failed | unavailable | 63 |
| deep/real | 3000000 | 32 | not run: value-isolation failed | not run: value-isolation failed | unavailable | 63 |
| deep/real | 3000000 | 1024 | not run: value-isolation failed | not run: value-isolation failed | unavailable | 63 |
| deep/real | 10000000 | 1 | not run: value-isolation failed | not run: value-isolation failed | unavailable | 201 |
| deep/real | 10000000 | 32 | not run: value-isolation failed | not run: value-isolation failed | unavailable | 201 |
| deep/real | 10000000 | 1024 | not run: value-isolation failed | not run: value-isolation failed | unavailable | 201 |
| deep/real | 20000000 | 1 | policy-infeasible: N>10M; not run | not run: value-isolation failed | unavailable | 379 |
| deep/real | 20000000 | 32 | policy-infeasible: N>10M; not run | not run: value-isolation failed | unavailable | 379 |
| deep/real | 20000000 | 1024 | policy-infeasible: N>10M; not run | not run: value-isolation failed | unavailable | 379 |

### Feasibility and provenance

- P/G never run N>10M. Preserve the mandated `infeasible: workspace chunking (tree_h=8)` policy label; the incident measured tree_h8 at30M, not at every excluded N. No20M Deep tree was built to test an exception. Coordinate int32 bounds do not override the safety cap.
- Real T-loc1/3/10M prefixes and synthetic fitted-mixture30/100M inputs passed hashes and exact-value separation. Deep1/3/10/20M has16/63/201/379 matching base rows; the issue is the held-out split, not measured tree recall.
- All full input and prefix hashes were independently rechecked after the stop and matched the initial verification. Existing vector oracle payloads are complete, sorted, finite, unique-ID and distance-consistent; this structural check is not a newly exhaustive recomputation of every full-scale oracle.
- P archived header22686505… plus exact approved patch; compiled search1cf8ec24… has WORK macros only, with native leaf endpoints. Timed binary8db22e4c…; counted binarybee42675…. G originalb7a9c719… plus approved patch/output observer compiled tof10a854d… but was not launched.
- Native G assigns half free GPU bytes/8 to signed `int size_a`; a near-idle96GiB GPU can exceed that slot capacity. This is source-derived, not a measured G failure. No widening, memory-pressure trick, or workspace workaround was used.
- Counts have a static scope audit but no runtime count process completed. Q32 counts would cover the full1000-query pass including ragged8, not the full32-batch latency denominator. Logical S bytes are not DRAM measurements.

## Word preparation and E3 status

Word fixed permutation/query identities were preserved. The source has611756 rows, seven non-ASCII-byte rows, no embedded NUL, max length32. Native byte/LF/strlen semantics are retained; no byte is ignored or Unicode-normalized. Query/index value matches are0 at all feasible scales.

| Word N | CPU oracle (1000 queries) | GPU correctness/sanitizer/timing |
|---:|---|---|
| 61000 | newly generated under guard,OMP_NUM_THREADS=16 configured;120000 bytes | not run |
| 150000 | newly generated under guard,OMP_NUM_THREADS=16 configured;120000 bytes | not run |
| 300000 | newly generated under guard,OMP_NUM_THREADS=16 configured;120000 bytes | not run |
| 611000 | infeasible after holdout: only610756 indexed source rows available | not run; no substitute N |

Word P/time/count and CPU-oracle binaries compiled. The Word phase runner and JIT binary provenance were locally reviewed/tested only; no operational freeze or GPU approval follows from those tests. E3 remains wholly unmeasured; its full nine-dataset/k/Q inventory is retained in E3_PROGRESS.md. Custom Tanimoto scan/oracle/auditor passed10 CPU-only tests; this is not GPU evidence. P/G metric8 support is absent in the approved source and remains unresolved. Optional long-protein/ChEMBL gradients and G remain uncompleted. C2/P-approx are not run.

## Evidence and review

- `evidence/resume_20261026/HARDWARE_GATES.json`: all8 fresh bounded gate records and raw-log hashes.
- `INPUT_CHECK.json` / `INPUT_CHECK_FINAL.json`: stable full input/prefix/oracle identity and isolation failures.
- `BUILD_SUMMARY.json`, `POSTSTOP_ARTIFACT_HASHES.json`, `RUNTIME_SUMMARY.json`, `WORD_MANIFEST.json`: source/binary/input provenance.
- `RAW_ARCHIVE.json`: SHA2560b46b02587c05a2880bd5bf6dd77abb307cf4da7c98ec1c582ee5830b434ca0d for the retained232KiB raw archive, including guard JSONL/receipts/outputs. Raw host-local command paths and data are not published.
- `INTEGRITY_REVIEW.md`, `INTEGRITY_WORD_REVIEW.md`, `COUNT_SCOPE_REVIEW.md`: independent code/scope review, not final performance acceptance.

## Next authorized action

Wait for the two explicit contract decisions above. Preserve STOP and every old/new diagnostic artifact. If authorized, append the decisions with time/reason, freeze new output/query artifacts in Git, then run fresh bounded/full correctness gates and all six same-UUID alternating pairs. Never reuse diagnostic sanitizer wall times or incident epochs as latency. Finish vectorE4 before Word/E3. Before any future high-memory launch, estimate peak RSS and coordinate the shared one-job-above8GiB limit; passing the16GiB guard alone does not establish that concurrency condition. No novel/first claim, no extrapolated crossover, and no story B is supported by this partial record.
