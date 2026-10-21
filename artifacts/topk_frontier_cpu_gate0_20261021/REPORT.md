# Dynamic exact top-k: deletion/frontier CPU Gate0

**Threshold expansion is observed;ordinary saved-frontier repair matches the future-threshold oracle in the tested fixed-tree/cached-score family.** Decision: `LOCAL_REPAIR_NEAR_RESTRICTED_ORACLE`;next boundary: `STOP_FIXED_TREE_REPAIR_FAMILY`. Novelty remains `NOT_ADMITTED`;full native strong-baseline performance admission is `NOT_EVALUATED`. This is not a negative result for every dynamic top-k or cross-query proof mechanism.

## Corrected question and frozen task

The parent fixed-radius pivot experiment did not test this question. Here an unchanged metric lower bound remains valid,but its old decision `LB>old_tau` can cease to exclude a node after deletion raises the kth distance. Reopened decisions,candidate resurrection,and actual result replacements are counted separately.

Both primary populations use N=4096 reference occurrences and64 disjoint external queries. Each of k=1,4,16,64 occurs16 times,with exactly1360 returned rows per state. This is an exact top-k batch join,not a full self-join. Duplicate values remain distinct source IDs;ties use `(integer edit distance,source ID)`,and only strict `LB>tau` prunes. Words' parent source has611756 rows;DNA has1000000 GRCh38-derived108bp windows,not original GTS DNA. These are source populations,not the measured4096-row index.

Four independently reset atomic-delete episodes are frozen from initial answers:random256,targeted256,union of all old top-k answers,and a random deletion matching that union size. Targeted deletion is adversarial/synthetic and uses only old outputs,not future ranks. All online methods deduplicate affected queries through the same reverse postings;there is no weak per-deleted-item repair baseline.

## Main evidence:pressure is real,but future tau saves no further distance calls

Counts below are over64 queries. `Affected / tau up` separates membership changes from actual distance-threshold rises. `Reopened nodes / unknown pairs` counts old-cut nodes satisfying `old_tau<LB<=new_tau` and live pairs with previously uncomputed scores.

| Dataset | Episode | Deleted rows | Affected / tau up | True replacements | Reopened nodes / unknown pairs | Root-restart calls | Retained / threshold-oracle calls | k+32 reserve calls |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Words | TARGET256 | 256 | 64 / 19 | 390 | 330 / 7189 | 225357 | 6980 / 6980 | 0 |
| Words | DRAIN_OLD_TOPK | 998 | 64 / 33 | 1360 | 405 / 7957 | 183832 | 7825 / 7825 | 10 |
| DNA_GRCh38_chr1_108 | TARGET256 | 256 | 64 / 41 | 382 | 2 / 85 | 244910 | 85 / 85 | 0 |
| DNA_GRCh38_chr1_108 | DRAIN_OLD_TOPK | 1092 | 64 / 56 | 1360 | 2 / 65 | 193664 | 65 / 65 | 0 |

All1360 old result relations disappear in each DRAIN episode. Therefore this is not the earlier near-no-change fixed-radius test. Words also has cross-query node overlap:405 reopened entries map to230 distinct node IDs,67 shared by multiple queries. Candidate-pair overlap is8018 live pairs across those entries,7957 previously unscored pairs and3097 distinct unknown reference IDs. These are different query-conditioned bounds/scores;node/data ID overlap is not automatically one reusable distance computation.

Across all eight dataset/episode cells,RETAIN_FRONTIER and its future-threshold oracle have identical repair distance counts,not merely within the frozen10% near-oracle tolerance. The online method never receives future tau. The oracle uses the same tree,initial score cache,frontier cut and safe lower bounds;only true final tau is supplied after every online output finishes. It is not a global batch-plan oracle or an arbitrary-representation lower bound.

## Material cache and oracle limits

Initial RETAIN_FRONTIER already evaluates233975/262144=89.2544% of all Words query-reference pairs,and262055/262144=99.9660% for DNA. Initial persistent search-container payload is2219392/2283392 bytes,respectively,excluding tree,reverse postings,raw strings and transient ranking buffers. This is small-N,cache-rich evidence;no bounded-memory or full-self-join scaling claim follows.

Moreover,the missing-new-output-pair floor is **zero in all eight episodes** for the retained cache:all final replacements were already scored during initialization. Consequently,when continuation initializes its heap from all surviving cached scores,its provisional top-k and numerical tau already equal the true final top-k/tau in every episode. The algorithm does not receive future truth,but the future-tau oracle supplies **no additional numerical cutoff information in these samples**. This gate therefore does not create an uncached replacement/unknown-threshold discovery stress case. The extra6980/7825 and85/65 calls in the targeted cases certify that unseen points cannot displace those known candidates. A stronger,new certificate might avoid some such proof work;the future-tau oracle does not bound that possibility. Ordinary k+32 reserve and full-score/rank caches already avoid most/all repair metric calls here,but their initialization and storage are charged.

## Complete lifecycle work,not a repair-only speedup

Each lifecycle means index construction+initial query+one independent atomic deletion/repair+initial and final complete output. Metric-call totals are deterministic work proxies,not elapsed-time speedups. Native serialization writes54400 bytes per lifecycle and is timed separately;scalar bounds,heap/rank/cache work,reverse-posting setup and tombstone application are retained in raw counters/instrumented CPU timings.

| Dataset | Episode | Root restart | Retained | k+32 reserve | Full rank cache | Seeded Quickjoin | Root / best ordinary |
|---|---|---:|---:|---:|---:|---:|---:|
| Words | TARGET256 | 472730 | 254353 | 263374 | 262144 | 1420343 | 1.8586x |
| Words | DRAIN_OLD_TOPK | 431205 | 255198 | 263384 | 262144 | 1283260 | 1.6897x |
| DNA_GRCh38_chr1_108 | TARGET256 | 520363 | 275538 | 275542 | 262144 | 1450708 | 1.9850x |
| DNA_GRCh38_chr1_108 | DRAIN_OLD_TOPK | 469117 | 275518 | 275542 | 262144 | 1284774 | 1.7895x |

No new candidate is implemented or promoted. Large repair-only ratios against root restart or Quickjoin are benefits of ordinary caching/continuation,not GTS++ novelty. Even root restart versus the strongest ordinary lifecycle is only1.69–1.99x in these targeted cells;this is not an end-to-end or tail-latency claim. All method/case and per-k counts remain in results/,including random controls and regressions.

## Validation and custody

- Two single-thread nice10 population processes,one remote fixture process,zero population failures/retries,and zero GPU starts. Shared users/processes and GPU settings were untouched.
- All60 complete method output streams(81600 triples) byte-equal their ten exhaustive reference streams. Every member,score,order,live ID and cardinality is checked. Reference and methods share the Myers edit primitive;581 DP qualification pairs and independent Python DP rederivation of5803 distinct emitted query-object scores passed. The latter is not a second all-pair membership oracle.
- Source,input,selection,binary,argv,raw-file census and frozen-query construction were rechecked read-only. Raw-output corruption and injected-failure copies were rejected. Data-free checks additionally reject altered publication copies.
- Raw source,input,full outputs and logs remain outside Git in durable custody,with source/binary hashes,raw seal,131-member archive manifest and archive receipt published as metadata. No raw string data or credentials are redistributed.
- Instrumented CPU time is a single fixed-order observation on a shared host. Telemetry writes and some container copies are included. Oracle setup is borrowed from the retained baseline,and oracle mutation/lookup timing is not an online ACK. No confidence interval,p95/p99,physical-memory traffic or GPU speedup is claimed.

## Method and reopening boundaries

The ten-way layout and Quickjoin helper are own pinned CPU reimplementations/adapters,not original executables. Saved-frontier continuation is an ordinary tombstone metric-tree control,not a native SPB/AV-tree/HDR implementation. Native GTS update timing and native SPB/HDR comparisons remain unknown. Raw immutable payloads are retained rather than moved/reclaimed;these are not complete production update ACKs.

Stop further engineering of this **tested fixed-tree,cache-rich,future-threshold-repair configuration** under the frozen gate. The frozen STOP_FIXED_TREE_REPAIR_FAMILY label is limited to that contract,not all trees or cache budgets. The observation of threshold expansion is positive evidence for the corrected phenomenon,but it does not establish novelty or justify CUDA. Reopening requires an explicitly different memory/workload/certificate contract,a distinct future-blind mechanism,and charged5x minimum/10x strong advantage over applicable strongest ordinary controls. Do not use this result to close all low-cache,full-self-join or cross-query-certificate problems,or to reopen classical query-ball/annulus traversal by renaming it.
