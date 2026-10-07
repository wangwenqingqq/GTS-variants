# Original GTS experiment deliveries and evidence alignment

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
