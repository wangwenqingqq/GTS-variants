# Original GTS experiment deliveries and evidence alignment

## Direct R/T/P short-workflow closure (2026-10-10)

[Direct R/T/P results](artifacts/external_closure/RTP_RESULTS.md) close the internal
cumulative and strengthened-reference gap with 18 fresh, balanced processes on
FP32 GIST **N1M/D960/B1/K8**, 336 events (128 range, 128 kNN, 40 inserts,
40 deletes, two actual rebuilds). Complete ordered outputs and all state
transitions match the exhaustive-qualified parent. Direct paired workflow gains
are **R/P 13.423096×**, **T/P 6.448319×**, and **R/T 2.081643×**; all three
95% intervals exceed 1 and all six pairs favor the candidate.

R includes common numerical/safety repairs and is not untouched original GTS;
T and P both use strengthened TILED construction. These are fixed-query internal
short-workflow results, not an external win, a coalescing-only attribution or
100k/1B admission. Five bridge qualifiers and 18 primaries were added; external
static B remains at zero primaries. The 96 B context-symbol limitation and
GPU_TREE native membership blocker remain. No paper content was published.

## External controls: Stage A qualification (2026-10-10)

[Stage A results](artifacts/external_closure/A_RESULTS.md) add complete GPU range
qualification on two GIST1M/D960 snapshots, disjoint-query CPU leaf512 selection,
and an explicitly labeled inclusive CPU Flat adapter. Author GPU_TREE remains
blocked by native kNN membership failure; ownership/reuse and bounded safety
results are retained separately. Twenty GPU qualifiers, no new primary timings.
At this Stage A checkpoint, external static rankings and direct R/T/P gains were
pending. The later direct internal result is linked above; external B is still open.


## Same-semantics build tiling: submission B/internal C (2026-10-09)

[Build-distance tiles](artifacts/build_distance_tiles/README.md) passes22
qualification processes and12 fresh direction-balanced primary processes on
original FP32 GIST N1M/D960/B1/K8,336 events with two actual rebuilds. Against
fresh PAR+FULL/original build mapping, paired workflow gain is **8.029943×**
(95% interval **[7.955661,8.104259]**); all six pairs favor tiling and complete
ordered outputs match. All112 original GPU functions are identical; only one
scoring mapping function is added. See [complete boundaries and raw pairs](artifacts/build_distance_tiles/REBUILD_E2E_RESULTS.md).

This is engineering baseline strengthening,not novel distance-work elimination,
untouched-GTS/external superiority,leak-clean/default or100k/1B admission. The
96B context-symbol issue and external tree/scan gates remain open. The earlier
PAR and static Flat counterevidence are not multiplied or discarded.

## Rebuild localization and CPU/GPU baseline admission (2026-10-09)

[Submission A](artifacts/rebuild_tree_baselines/README.md) adds two real-rebuild
NSYS diagnostics and six native CPU static diagnostics on original FP32 GIST
N1M/D960. Shallow pivot-distance kernels dominate the captured build; all384
complete CPU query-quality checks pass. CPU Flat is faster than the fixed-leaf
KD/Ball diagnostics. MVPT/GPU_TREE concrete source/output/reuse gaps remain
explicit. This is **not** a new tiled-kernel or dynamic end-to-end gain; earlier
phase-B18 primary processes remain unchanged. B/C were pending at this A
checkpoint; the later internal delivery is linked above. External formal C
comparisons remain pending.

## Scoped unified search/update integration (2026-10-09)

[The unified B1 artifact](artifacts/unified_search_update/README.md) now uses one
original-GTS live base, tombstones, reference buffer and rebuild loop for exact
kNN plus PAR range queries and serialized updates.31 guarded processes passed
full-output and state checks, including K8/K32 mixed10k traces and4 sanitizer
runs. The fresh legacy-PAR regression screen passed: paired warm-trace ratio
1.000430,95% interval[0.996224,1.005527], three alternating pairs (2/1 order
split). This is non-regression, **not a measured speedup**.

This is a **synthetic N1000/D128/B1 scoped integration**, not paper-wide GTSPP
or arbitrary-vector/large-N/external-comparison admission. Each mixed10k trace
contains5k range and5k kNN. The unpruned FULL control was faster in the single
K8 mixed comparison; that adverse observation is retained, not relabeled as a
cutoff gain. See [results and limits](artifacts/unified_search_update/RESULTS.md)
and the [redundancy-to-end-to-end ledger](artifacts/unified_search_update/CLAIMS.md).
The2026-10-07 statement below records the older static-contract checkpoint;
its global comparison admission remains unchanged by this bounded integration.

## Scoped PAR range/update reproduction (2026-10-08)

[The standalone PAR module recipe](artifacts/par_range_update/README.md) fetches
pinned original GTS, regenerates the exact N1000/D128/B1 synthetic inputs, builds
the qualified same-source executor, and checks complete serialized query/update
results with an independent CPU oracle and guarded sanitizer runs. Its default
entry uses PAR_STRONG, with NATIVE retained as a correctness control.
This is **not** unified GTSPP, arbitrary new-vector ingestion, or an external
kNN comparison; the separate static admission status below is unchanged.
See the [redundancy/mechanism/module/impact/end-to-end ledger](artifacts/par_range_update/CLAIMS.md).

2026-10-07最新状态：K10 matched/bulk采集完成834/834进程；本合同静态O_MASK稳定；整体`comparison_admitted=false`，统一search/update候选不存在。六轮统计已闭合，R10、30k与全冷总计仍未完成。

- [按资格分类的六轮结果与四笔账](diagnostics/next_campaign_20261004/K10_QUALIFIED_RESULTS.md)
- [每个方法、每对方法的比较资格与具体原因](diagnostics/next_campaign_20261004/K10_COMPARISON_STATUS.json)
- [剩余门槛与实际候选身份](diagnostics/next_campaign_20261004/CLOSURE.md)

八个matched条件中，O_MASK相对原始适配器的累计warm改善为46.956–76.846倍；树前置相对O_BOUND没有任何条件达到预登记稳健胜出门槛，B1全部回退。合格外部对照含更快结果，均保留，不把原始适配器的大倍率归因于纯coalescing或整合GTS++。

在已有NumPy环境下一键重建三份报告（纯CPU，不运行GPU）：

```bash
python3 diagnostics/next_campaign_20261004/summarize_k10.py
python3 diagnostics/next_campaign_20261004/test_recovery_cpu.py
```

分析固定5b145bc的834行和冻结策略；校验完整六轮、身份及替代轮来源。22项CPU回归覆盖拒收、缺轮、计时失败、窗口未知和错误配对。下面的早期轮次仍保留其历史状态。

This publication branch contains only task-owned experiment deliveries. It has
a fresh, standalone commit chain and does not inherit older repository traces,
data or history. Existing repository branches, history and visibility are not
changed. This is not a remediation of any exposure in older public history;
affected credentials still require revocation or rotation by their holder.

## Round 1: original GTS versus native GPU Faiss-IVF

- [Results](diagnostics/native_knn_faiss_ivf_20261003/RESULTS.md)
- [Reproduction and validation scope](diagnostics/native_knn_faiss_ivf_20261003/README.md)
- [Claim/evidence ledger](diagnostics/native_knn_faiss_ivf_20261003/EVIDENCE_LEDGER.md)

The frozen development-selected 100% points miss final100% on all eight shapes.
The later fixed all-list IVF control reaches100% tie-aware recall, with a
non-paired timing comparison and deterministic tie-breaking exception on GIST.
No production GTS++ improvement is measured here.

## Round 2: original GTS baseline recheck

- [Results](diagnostics/original_gts_compare_20261003/RESULTS.md)
- [Replay and pending comparator identity](diagnostics/original_gts_compare_20261003/README.md)

Four single-process original-GTS checks pass full-ID/field validation at K8,
B1/32, GIST/Deep1M and32 already-seen queries. This is a baseline-only pilot;
an optimized comparator had not yet been measured at that checkpoint. The
later P7 static executor and U0 update validation are linked below; neither is
a unified range/kNN/update keeper.

## Next campaign: mandatory 10,000-query comparisons

- [Detailed 10k stability and complete-workflow experiment plan](diagnostics/next_campaign_20261004/PLAN_10K.md)
- [Later P7 static kNN evidence](https://github.com/wangwenqingqq/GTS-variants/blob/7bce3679c3e32e77fa25cf7842805926509e1412/diagnostics/unified_knn_e2e_20261003/RESULTS.md)
- [Later original-GTS U0 update evidence](https://github.com/wangwenqingqq/GTS-variants/blob/7bce3679c3e32e77fa25cf7842805926509e1412/diagnostics/claim_closure_20261003/RESULTS.md)

该计划现已完成K10 matched/bulk采集及按资格分类的统计：139个冻结配置组，每组六个fresh进程；52组完整质量与计时联合可比，67组ANN、20组其余拒收/未覆盖。90个合格局部方法对不改变全局未准入状态。原生Flat/IVF/CAGRA的失败配置和诊断时间没有删除；范围持续性、30k及完整工作流剩余门槛见最新CLOSURE。静态查询、原生逻辑多重集更新与新向量到达仍为不同合同。

## Evidence alignment: query and update lifecycle

- [Extended P4 evidence ledger](diagnostics/batch_tree_inheritance_20261002/EVIDENCE_LEDGER.md)
- [Curated-source provenance](diagnostics/batch_tree_inheritance_20261002/CONVERGENCE_SOURCE.json)

This extension links existing public reports, retains external counterevidence
and version-specific qualification gates, and does not add a new GPU run.
Mechanism experiments are complete at their registered scopes; a unified
search/update candidate is not complete.

## Publication provenance

[PUBLICATION.json](PUBLICATION.json) identifies the original local checkpoint
and exported path. Experimental sources, contracts, numeric results, curated
evidence and collection hash manifests are preserved; only publication-status
prose is adjusted for this standalone branch.

Original GTS is attributed to [ZJU-DAILY/GTS](https://github.com/ZJU-DAILY/GTS),
revision `3bac1b725e92e98e3b69d5cb79ad9c56ccb5e639`. Upstream headers are not
redistributed by these directories; preparation verifies caller-supplied source
against pinned hashes. Existing rights are preserved and no new license is
imposed on upstream or derived source. Dataset/index/result binaries and raw
profiler environment captures are excluded. Replay the delivered fixed queries;
new development campaigns may need the prior-query inventory recorded in their
metadata and must not silently change exclusions.
