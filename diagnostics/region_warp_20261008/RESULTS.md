# REGION_WARP: completed bounded mapping experiment

## Decision and scope

**Warp-per-leaf mapping improves both regional SERIAL controls, but does not demonstrate an end-to-end win over PAR_STRONG. Stop this mapping trial without expanding seeds or budgets.**

The paired trace ratios are SPLIT_SERIAL/SPLIT_WARP 1.03663x and FUSED_SERIAL/FUSED_WARP 1.03317x (six wins each). These correspond to 3.53% and 3.21% lower complete-trace latency, respectively. After mapping is shared, FUSED has a small 1.00295x increment over SPLIT (four wins, lower95 1.00029) on this fixed trajectory only. PAR_STRONG/FUSED_WARP is 1.00104x with CI95 [0.99612, 1.00575], three wins and an order-direction reversal; superiority over the strong baseline is unconfirmed.

Frozen seed2026100431, N1000/D128, integer-valued FP32, B1, radius0: 10000 range queries +1000 physical-row reinsertions +1000 live-rank deletions, 50 rebuilds. This is a small dynamic correctness/performance trace, **not** the N1M static final10000 campaign and not a Faiss/CAGRA comparison. No historical median is used as a denominator. Target: one isolated RTX PRO 6000 Blackwell Server 96GiB (SM120), CUDA 13.1.115, driver590.48.01, NUMA3.

Primary: continuous 12000-event Host-ready/ACK time, complete returned results, paid refresh/rebuild and final release/drain. Setup+trace includes input/output allocation, cold build and initial plan; CUDA context initialization and post-timing output/audit are separate. Nested maintenance intervals must not be added again.

## Complete-trace and setup results

Each row is the median of six fresh formal processes. The inferential ratios below are paired geometric ratios, not ratios of these medians.

| Mode | Trace median (s) | Setup+trace median (s) |
|---|---:|---:|
| PAR_STRONG | 13.924399 | 14.015188 |
| SPLIT_SERIAL | 14.444815 | 14.547607 |
| FUSED_SERIAL | 14.367278 | 14.468699 |
| SPLIT_WARP | 13.949703 | 14.040888 |
| FUSED_WARP | 13.928709 | 14.020213 |

Six registered orders: ABCDE, EDCBA, BDAEC, CEADB, CAEBD, DBEAC; every pair has 3/3 ordering. A=PAR_STRONG, B=SPLIT_SERIAL, C=FUSED_SERIAL, D=SPLIT_WARP, E=FUSED_WARP. All 30 required formal processes completed; there are no failed/replaced/selected primary runs.

## Three-account paired comparisons

Baseline time / candidate time; >1 favors the candidate. CI95: 20000 paired bootstrap resamples, seed202610081022. Intervals quantify run variability on this one fixed trace, not dataset or seed generalization.

| Baseline / candidate | Trace ratio | CI95 | Wins /6 | Baseline before | Baseline after | Setup+trace ratio (CI95) |
|---|---:|---|---:|---:|---:|---|
| SPLIT_SERIAL/SPLIT_WARP | 1.036634 | [1.034162, 1.039399] | 6 | 1.039353 | 1.033922 | 1.037070 [1.034677, 1.039579] |
| FUSED_SERIAL/FUSED_WARP | 1.033165 | [1.031483, 1.034813] | 6 | 1.032108 | 1.034224 | 1.033957 [1.031731, 1.036137] |
| SPLIT_WARP/FUSED_WARP | 1.002949 | [1.000290, 1.005629] | 4 | 1.004294 | 1.001607 | 1.003054 [1.000475, 1.005656] |
| PAR_STRONG/FUSED_WARP | 1.001039 | [0.996124, 1.005746] | 3 | 0.997475 | 1.004616 | 1.001542 [0.996044, 1.006529] |
| PAR_STRONG/SPLIT_WARP | 0.998095 | [0.992618, 1.003680] | 3 | 1.000198 | 0.995997 | 0.998493 [0.992447, 1.004727] |
| SPLIT_SERIAL/FUSED_SERIAL | 1.006317 | [1.003829, 1.008917] | 6 | 1.006507 | 1.006126 | 1.006073 [1.002945, 1.009076] |

## Every retained formal trace time

| Round / registered order | PAR_STRONG ms | SPLIT_SERIAL ms | FUSED_SERIAL ms | SPLIT_WARP ms | FUSED_WARP ms |
|---|---:|---:|---:|---:|---:|
| 1 / ABCDE | 14003.402558 | 14466.447224 | 14354.705206 | 13940.864167 | 13931.064502 |
| 2 / EDCBA | 14021.788285 | 14400.108755 | 14379.850348 | 13908.376924 | 13926.354272 |
| 3 / BDAEC | 13877.675616 | 14565.931642 | 14455.698755 | 14036.835880 | 13967.321488 |
| 4 / CEADB | 13970.052213 | 14423.183388 | 14343.283239 | 13942.817554 | 13851.101570 |
| 5 / CAEBD | 13878.744984 | 14555.673405 | 14391.265702 | 13959.946031 | 13966.812040 |
| 6 / DBEAC | 13834.993561 | 14402.656785 | 14343.618540 | 13956.588305 | 13856.649721 |

## Admitted tails and nested maintenance

All five new observer identities passed six alternating on/off pairs (60 separate fresh processes), with exact output identity and upper95 overhead <=1.03. No old observer qualification was inherited. Formal tails/stages are therefore admitted. Values below are medians of the six per-process p99/sum values, not pooled percentiles. Raw per-process values remain in SUPPLEMENT.json and FORMAL_ROWS.json.

| Mode | Query p99 ms | Insert p99 ms | Delete p99 ms | Rebuild p99 ms | Rebuild sum ms | Rebuild refresh sum ms |
|---|---:|---:|---:|---:|---:|---:|
| PAR_STRONG | 2.870043 | 4.977048 | 2.502264 | 6.682659 | 247.997346 | 9.010208 |
| SPLIT_SERIAL | 2.885670 | 5.110247 | 2.830154 | 7.768918 | 251.365690 | 8.994711 |
| FUSED_SERIAL | 2.870116 | 5.109301 | 2.763294 | 6.659939 | 247.011275 | 8.876663 |
| SPLIT_WARP | 2.872914 | 4.858108 | 2.501480 | 6.476429 | 243.389146 | 8.897140 |
| FUSED_WARP | 2.866969 | 4.903079 | 2.473787 | 7.003521 | 249.454262 | 8.876225 |

The FUSED_WARP median rebuild p99 is 7.003521ms versus FUSED_SERIAL 6.659939ms and PAR_STRONG 6.682659ms. Its rebuild sum is 249.454262ms versus 247.011275ms and 247.997346ms. These descriptive maintenance regressions are retained; no stable tail improvement or new maintenance mechanism is claimed. Refresh sums exclude initial refresh and are nested in paid rebuilds.

| Observer mode | On/off geometric cost | CI95 | Admitted |
|---|---:|---|---|
| PAR_STRONG | 1.002660 | [0.994872, 1.013059] | yes |
| SPLIT_SERIAL | 1.000543 | [1.000050, 1.001307] | yes |
| FUSED_SERIAL | 0.998876 | [0.996489, 1.001350] | yes |
| SPLIT_WARP | 0.998844 | [0.993417, 1.003607] | yes |
| FUSED_WARP | 1.003502 | [0.999797, 1.006793] | yes |

## CPU and memory inventory

| Mode | CPU user+system s | Sampled device peak GiB | Region peak owned bytes | Region allocations | Region transferred bytes |
|---|---:|---:|---:|---:|---:|
| PAR_STRONG | 13.495278 | 13.191162 | 18908 | 765 | 601596 |
| SPLIT_SERIAL | 13.998363 | 13.197021 | 18908 | 765 | 601596 |
| FUSED_SERIAL | 13.917841 | 13.191162 | 18908 | 765 | 601596 |
| SPLIT_WARP | 13.518252 | 13.198975 | 18908 | 765 | 601596 |
| FUSED_WARP | 13.498261 | 13.197021 | 18908 | 765 | 601596 |

CPU demand remains approximately one core-equivalent (about 13.5 CPU seconds per 13.9s trace); the mapping does not remove CPU orchestration or alter allocation/transfer counts. Rusage is CPU consumption, **not measured CPU waiting time**. The reductions relative to SERIAL are compatible with a shorter device critical path, but this campaign does not separately attribute driver busy-wait or instruction/memory stalls. Sampled device peak includes the existing runtime/workspace; it is not analytical index storage. Region accounting excludes that legacy workspace.

## Opportunity, mechanism and correctness

| Actual query-region leaf bucket | Query-regions | Candidate objects | Non-self distance evaluations |
|---|---:|---:|---:|
| 0 | 89868 | 0 | 0 |
| 1 | 8805 | 88050 | 79312 |
| 2-8 | 1327 | 26540 | 25203 |
| >8 | 0 | 0 | 0 |

100000 query-regions across 10000 queries and 51 epochs. Multi-leaf regions account for 25203/104515 = 24.1142% of actual base-tree distance evaluations, **not 24.1% of elapsed time**. Candidate objects include deleted/self slots; actual evaluations exclude both. One missing-mapping diagnostic exactly matches the retained parent work stream. No radius/query filtering was introduced.

The repaired bounded 8-leaf x20-object microcheck gives geometric SERIAL/WARP 3.66548x. This is one process with six direction-balanced CUDA-event batch pairs (512 launches/batch), not six independent primary processes and not complete workflow speed. The first periodic fixture is retained but excluded; the new deterministic random-integer fixture has only intentional row0/1 duplication. No primary process used the periodic fixture.

Uniform nl0 returns; nl1 retains the full-CTA leaf function. For nl>=2, warp w owns leaves w,w+8,... and lane l owns objects l,l+32,... . One thread retains the complete ascending-dimension native pow/FP32 computation, self/deletion semantics and canonical output slot. Shared query/leaves are published before entry; warp-specific loops have no CTA barrier. SPLIT and FUSED call the same helper, isolating mapping from fusion.

19 budget-legal direct geometries (nl0/1/7/8/9; size1/20/32/33; ragged sizes), three over-budget combinations excluded rather than truncated; repeated reuse, deletion, two radii and actual owner probes. Original topology/state/update/fallback/stale/capacity checks, memcheck/racecheck/synccheck and all five full counter trajectories pass. Node/pivot/leaf/object streams are identical, including 104515 actual base distance evaluations. The independent integer live-multiset replay checked 900000 query outputs across 30 formal +60 observer processes, exact ordered IDs/FP32 fields and all guard receipts. GPU0 and other services were not signaled or reconfigured.

## Main executable static kernel resources

| Kernel | Registers/thread | Stack bytes | Shared bytes | Local bytes |
|---|---:|---:|---:|---:|
| FUSED_SERIAL traversal+verification | 52 | 40 | 3088 | 0 |
| FUSED_WARP traversal+verification | 48 | 40 | 3088 | 0 |
| SPLIT_SERIAL verification | 50 | 0 | 1536 | 0 |
| SPLIT_WARP verification | 52 | 0 | 1536 | 0 |
| Common SPLIT traversal | 50 | 40 | 3088 | 0 |
| PAR_STRONG verification | 44 | 0 | 1536 | 0 |

cuobjdump inventory from the new measured main executable, not the micro binary. These are static resources, not achieved occupancy or evidence of a coalescing change. No NCU/NSYS measurement is added here; no DRAM-sector, warp-efficiency or CPU-wait causal claim is made. The parent ptxas/cuobjdump shared-memory accounting difference is not resolved by this experiment.

## Evidence, negative outcome and next action

All primary/observer rounds, qualification, exact work hashes, repair history and independent audits are retained in evidence/v2. Raw/portable hashes are separately recorded in PUBLICATION_QUALIFICATION.json and PUBLICATION_RESULTS.json; raw inputs, full output arrays and host/device identities remain in external task-owned storage. Measured binary SHA256: c63b9cb0507ffe8f4912e5e64d134a764a466a9b9bb70b7d67b9260bdd7ef474.

The rejected claim is that this mapping/fusion intervention demonstrates superiority over the strong parallel baseline. The same-contract regional controls improve, but the strong-baseline CI crosses 1; median FUSED_WARP trace is 13.928709s against PAR_STRONG 13.924399s. The order split changes the apparent direction, and maintenance p99 is not uniformly better. Retain PAR_STRONG as the keeper; retain WARP as a regional attribution improvement, not a promoted global winner. No parameter/seed expansion or limited confirmation is automatically registered. Reopen only under a separate contract with a distinct mechanism and reproducible strong-baseline end-to-end advantage, including maintenance/tails. Generic warp ownership and this small gain are not a paper novelty contribution.

The clean commit-A source archive was independently rebuilt after all formal timing completed. Its exact main-source/controller/test identities match the measured snapshot; three normal structural/direct smoke processes plus native/five-mode mixed-update output checks pass. This new build is not a remeasurement, not a new sanitizer admission and not a selected-function SASS-identity claim. See ARTIFACT_CHECK.json.
