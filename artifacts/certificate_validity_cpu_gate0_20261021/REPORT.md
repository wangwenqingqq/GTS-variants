# Certificate validity: CPU premise falsification

**Decision: BASELINE_SUFFICIENT_FOR_VALIDITY.** Ordinary identity-preserving pivot columns handle the declared updates without recomputing unchanged surviving object-pivot distances. Novelty remains NOT_ADMITTED;the full5x/10x strong-baseline performance gate is NOT_EVALUATED. This does not admit another index or CUDA implementation.

## Frozen scope and source finding

Two primary CPU targets,Words and GRCh38-derived DNA108,each4096 initial objects,32 deleted,32 appended,4 retained pivots,32 independent calibration queries and64 evaluation queries. All pivot database members are deleted deliberately;their copied immutable values remain. Original populations are611756/1000000,not benchmarked sizes. No TLoc,protected GIST held-out,query-ball/annulus or GPU execution.

Read-only original GTS update source hashes match the retained source snapshot. The code marks base deletions,searches a separate insertion buffer,and reconstructs when MAX_IN_SIZE=10 fills. It does not rebuild on every delete and does not state that all old object-pivot proofs become invalid. Source range/identity map is in evidence/GTS_SOURCE_INSPECTION.json. Source commit identity itself was not freshly verified;the upstream reference commit and exact inspected hashes are distinguished.

## Calibration,target and achieved selectivity

Radii are nearest-rank quantiles from32 calibration queries against the4096 initial rows,fully frozen before evaluation. Ties are inclusive;integer edit radii are not interpolated. Calibration/evaluation queries are disjoint and exclude both earlier parent query sets. Self-matches imply a minimum1/4096=0.024414% hit fraction,so the0.01% target cannot be achieved on this subset. It is retained,not tuned or renamed.

| Dataset | Target selectivity | Frozen radius | Calibration achieved | Initial evaluation achieved | Initial output triples |
|---|---:|---:|---:|---:|---:|
| Words | 0.01% | 0 | 0.024414% | 0.024414% | 64 |
| Words | 0.10% | 4 | 0.119019% | 0.208282% | 546 |
| Words | 1.00% | 6 | 2.602386% | 4.036713% | 10582 |
| DNA_GRCh38_chr1_108 | 0.01% | 0 | 0.024414% | 0.024414% | 64 |
| DNA_GRCh38_chr1_108 | 0.10% | 49 | 0.161743% | 0.233078% | 611 |
| DNA_GRCh38_chr1_108 | 1.00% | 52 | 1.243591% | 1.132202% | 2968 |

## Certificate construction and maintenance

Both datasets require16384 initial point-pivot distances. After deleting32,16256 live certificate entries remain and are retained unchanged;32 dense sidecar rows move,copying128 certificate entries. After appending32,only128 new point-pivot distances are calculated. Raw string copying is represented by immutable authority IDs,not physically executed or timed. These are semantic/cache-maintenance observations,not native full update ACKs.

| Dataset | State | Ordinary maintenance metric calls | Weak full-recompute calls | Cached-GTS snapshot build calls |
|---|---|---:|---:|---:|
| Words | Initial | 16384 | 16384 | 13398 |
| Words | Delete32 | 0 | 16256 | 13302 |
| Words | Append32 | 128 | 16384 | 13398 |
| DNA_GRCh38_chr1_108 | Initial | 16384 | 16384 | 13398 |
| DNA_GRCh38_chr1_108 | Delete32 | 0 | 16256 | 13302 |
| DNA_GRCh38_chr1_108 | Append32 | 128 | 16384 | 13398 |

The weak full-recompute variant repeats the same correct query algorithm and is deliberately excluded from research admission. Huge maintenance ratios against it are not new mechanism evidence. GTS snapshot construction is also not native GTS update behavior. No B+tree/SFC/RAF implementation is benchmarked or mislabeled SPB-tree.

## Validity is not pruning utility

Initial-snapshot complete batch costs below include query-pivot distances and all candidate verification;Quickjoin includes partition distances. Scalar pivot comparisons are separately visible,not declared free. All methods return identical full triples.

| Dataset | Radius | Pivot metric calls | Pivot scalar bound checks | Cached-GTS metric calls | Quickjoin-family metric calls | Output triples |
|---|---:|---:|---:|---:|---:|---:|
| Words | 0 | 1044 | 302937 | 7707 | 38993 | 64 |
| Words | 4 | 152427 | 787564 | 207286 | 427396 | 546 |
| Words | 6 | 206293 | 918202 | 244970 | 453037 | 10582 |
| DNA_GRCh38_chr1_108 | 0 | 332 | 290948 | 2051 | 36537 | 64 |
| DNA_GRCh38_chr1_108 | 49 | 262144 | 1048192 | 269094 | 525067 | 611 |
| DNA_GRCh38_chr1_108 | 52 | 262145 | 1048195 | 269094 | 525287 | 2968 |

Across every nonzero-radius state,the best metric-call reduction factor versus cached GTS is only 1.3599x,below5x even before charging scalar-filter,construction and update overhead. This is not a tail-latency estimator or a new algorithm claim. Radius0 can reduce metric calls more,but is a known exact-match special case with large scalar scanning work;an exact-match hash/dictionary is an additional strong comparator,not measured here. Do not select that corner to revive the proposal.

DNA at radii49/52 verifies essentially the whole live population despite valid certificates. Under these four untuned pivots,correct local maintenance does not yield useful strong pruning. This does not prove every pivot choice or representation fails;it does remove global certificate invalidation as an automatic explanation for the observed query cost.

## Cost and quality boundaries

- All24 build/update rows and72 query rows are retained,including query compute+materialization and complete20-byte/triple serialization times/bytes. They are single fixed-order CPU observations,no paired speedup or p95/p99 claim. Output timing closes the file but does not fsync.
- Complete outputs pass native comparison against exhaustive reference and read-only Python member/score/byte equality checks on every state.581 independent DP pairs qualify the shared edit kernel;full references are not independent arithmetic rederivations.
- Native code rederives98048 live certificate entries in diagnostic checks,outside method work. The zero old-pair count concerns incremental maintenance only;each query/radius still pays64*4 query-pivot distances.
- Immutable owner handling is implemented;block-envelope and generation examples are only mathematical witnesses,not block-maintenance/version-aware rejection implementations. Mutable-object,changed-metric,concurrency and production validity are not admitted.
- All CPU worker limits passed. One local prepopulation self-test failure caught the maintenance-call counter bug;it was fixed and refrozen before data calibration. No population failure,retry or source change after observed results.

## Decision and next boundary

Keep ordinary incremental maintenance as a strong simple control. Do not implement a new certificate system on the unsupported assumption that all old distances must be recomputed. Missing native SPB/AV-tree/RECAST comparisons are unknown,not defeated baselines. A full performance Gate0 must first state a genuinely distinct dependency/mechanism and then freeze5x minimum/10x strong work-or-tail criteria against all applicable admitted strong controls,including construction,updates,queries and identical complete output. No such campaign or CUDA job is started here.
