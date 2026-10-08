# P4 证据账本

> 2026-10-07当前K10状态与六轮统计见[合格结果](../next_campaign_20261004/K10_QUALIFIED_RESULTS.md)及本文件末尾补记；早期停止/恢复记录保留其历史口径。

本轮以 `wangwenqingqq/GTS-variants@43463278fa1f2b7b8e6e36ff224e5c640036963e` 为冻结起点。历史证据保留原实验口径，不能与本轮收益相乘。

| 机制 | 历史来源与观测 | 本轮继承与检验 | 新语义 |
|---|---|---|---|
| 旧 GTS、`pow` 算术 | [距离路径报告](https://github.com/wangwenqingqq/GTS-variants/blob/8cf31c448b968398207fe5a5eb358121be64c134/diagnostics/arithmetic_path_boundary_20260928/REPORT.md)：固定工作量回放中 `pow` 很贵；该比值不是端到端收益 | 使用同一显式顺序 FP64 参考算术，并与旧 strict FR 完整输出比较 | 无 |
| 树拓扑、向外边界、C4/C1 | 同一报告：Tloc C4 正向，Deep C1 几乎不剪枝；GIST 单查询结果依半径变化 | 冻结原树 dump，父复用仅在实际 pivot ID 相同时生效；GIST 候选集合与旧 strict_walk 逐位置相同 | 有：批量树前缀与候选掩码 |
| 父 pivot 复用 | 旧树遍历中的共享 pivot 是同一查询内的距离复用；兄弟节点按同一 pivot 划分并非重复计算 | 每组核对 pivot ID 后算一次完整距离区间；账本记录 pivot 次数 | 无 |
| GPU Graph 与输出整理 | [Tloc 融合结果](https://github.com/wangwenqingqq/GTS-variants/blob/8cf31c448b968398207fe5a5eb358121be64c134/diagnostics/traversal_count_combo_20260924/TLOC_RESULTS.md)：去掉重复计数在当时单查询路径有收益 | P4 共用 P0–P3 的 Graph、稳定收集和两阶段有效长度 D2H | 无 |
| AoSoA32、跨查询对象复用、早退 | [P0–P3 报告](https://github.com/wangwenqingqq/GTS-variants/blob/8cf31c448b968398207fe5a5eb358121be64c134/diagnostics/batch_exact_highdim_20261001/RESULTS.md)，提交 `43463278fa1f2b7b8e6e36ff224e5c640036963e`：GIST/Deep B=32 的 TILE 相对 GRID 有正向收益，GIST 全命中早退不占优 | 同一新二进制内重测 SCAN_L/E；树模式共用布局、算术和输出，不能把旧收益另乘一遍 | 无 |
| `C_ID`、`C_MASK`、`C_TASK` | 历史没有与强批量 SCAN 在同一执行器内比较这三种组织 | 本轮唯一新增对照；三者使用完全相同的树候选集合，逐字节核对输出 | 有：候选组织方式 |

本轮最终计时、候选账本、profiler、源码/数据/query 哈希和原始收据索引见 [RESULTS.md](https://github.com/wangwenqingqq/GTS-variants/blob/8cf31c448b968398207fe5a5eb358121be64c134/diagnostics/batch_tree_inheritance_20261002/RESULTS.md) 与 [PREFLIGHT.json](https://github.com/wangwenqingqq/GTS-variants/blob/8cf31c448b968398207fe5a5eb358121be64c134/diagnostics/batch_tree_inheritance_20261002/PREFLIGHT.json)。

## 2026-10-03 convergence extension

**Status:** existing measurements were aligned with source identities; no new
GPU experiment was run. Mechanism experiments are complete at their registered
scopes; the integrated search/update version is not complete. This extension
continues P4's ledger rather than introducing a parallel evidence system.

### Candidate and comparator identity

- Original comparator: `ZJU-DAILY/GTS@3bac1b725e92e98e3b69d5cb79ad9c56ccb5e639`.
  The eight GTS CUDA files were locally rehashed against the existing manifest.
  Native range counts/kth distances are distinct from complete host-ID output.
- Recent original kNN adapter: measured binary
  `2871b26adf8b1109795291ffb0ff8645390365d89a20ec41ac3d6a239a27043c`;
  fixed MAX_H6, 1 GiB workspace, FP32 input loader and full-ID observation.
  It is not an untouched published executable.
- P4 static component: source snapshot
  `8cf31c448b968398207fe5a5eb358121be64c134`, measured binary
  `36adb09b490d124591e78f0332e0dd0c114ee8f621018b82ae7be3d8dd491c77`.
  `p4_bench.cu:10–161` shares P0–P3 object order, AoSoA32, explicit sequential
  FP64, Graph and stable full-result delivery; it adds static tree/mask/task
  organization. It contains no update loop or optimized kNN entry.
- Tloc count-removal binary and driver are separate. No current commit/hash
  represents a unified production query/update candidate. Root historical
  `include/src` remains incremental and is not the active original comparator.

### E1–E6 disposition and claim boundaries

| ID / proposed claim | Result and code entry | Verified scope / disposition | Missing or prohibited |
|---|---|---|---|
| E1 / resource lifetime | Original `update.cuh:341–348,589–628` contains transient query/result allocations | Source-established lifecycle traffic; no current qualified resource-only or complete-sequence measurement is registered here. | Historical claims require separately authorized provenance before reuse; no numerical implementation change may masquerade as allocation-only. |
| E2 / C2 phase continuity | [Fixed Tloc report](https://github.com/wangwenqingqq/GTS-variants/blob/f16d09a4e8a32ab8afff3b1b92221a5e447725a0/diagnostics/traversal_count_combo_20260924/TLOC_RESULTS.md), `prepare.py:18–40`; E/R/Q 3.809/1.228/0.929 ms | Four alternating process rounds, same binary **GPU6** (`TLOC_EVIDENCE.json`); R/Q full-output and memcheck/synccheck gates. Separate Graph driver, not production integration. | Not all fusion/coalescing, not P4 integration or dynamic throughput. P alone is bimodal and wins only 2/4. |
| E3 / C1 explicit reuse | [Fixed P0–P3 report](https://github.com/wangwenqingqq/GTS-variants/blob/43463278fa1f2b7b8e6e36ff224e5c640036963e/diagnostics/batch_exact_highdim_20261001/RESULTS.md), common `Batch` executor | Development GIST full-dimensional DRAM 122.9→61.5 GB; separately qualified final B32 Host-ready benefit. Same AoSoA32 in GRID/TILE. | Not pure layout/coalescing; read halving is not time halving; do not multiply with P4. |
| E4 / C1 candidate organization | This P4 report; `batch_tree_prefix.cuh:11–47`, `batch_candidate_tasks.cuh:7–101`, `p4_bench.cu` | GIST half B32 SCAN_E/C_MASK_E 1775.1/1521.8 ms per1024 queries, paired ratio1.16657; common candidates/collector. Positive Tloc B32; Deep, full-output GIST and Tloc B1 negative. | No universal ANN/index advantage; C_TASK's small additional gain is not a distinct major contribution. |
| E5 / maintenance attribution | Original `update.cuh:493–539`, `tree.cuh:361–383` contains buffer-triggered compaction/rebuild | Source-established maintenance amplification; reasonable-buffer comparator and complete operation costs required. | No current rebuild speedup claim; duplicate base-ID insertion cannot certify new arrivals. |
| E6 / C3 state safety | Public original-workflow preparation separates abandoned direct insertion from original buffering | Prepared probes are inputs/expectations; current candidate sequential visibility and external IDs are unclosed. | No transferred legacy bug/fix status, no certification from insert ACK, and no GPU result from expected counts. |

### External kNN counterevidence and cost ownership

The [native comparison](https://github.com/wangwenqingqq/GTS-variants/blob/8d300725eb0d9e1fd99213109b85cdff9b260b13/diagnostics/native_knn_faiss_ivf_20261003/RESULTS.md)
retains all failed frozen100% quality points. Later native all-list IVF1024/1024
reaches100% tie-aware recall on eight shapes; six-process Host-ready medians are
63.6–140.2× shorter than the original adapter. This is a **non-paired
supplement**, uses `GpuIndexIVFFlat` rather than a Flat API benchmark, and has
admissible GIST boundary ties rather than deterministic-ID parity. No optimized
GTS++ or update result follows. The [original-only pilot](https://github.com/wangwenqingqq/GTS-variants/blob/957ccf0b3592cebf2aeb49678a58f2c9379ed363/diagnostics/original_gts_compare_20261003/RESULTS.md)
does not fill that missing candidate.

In the GIST K8/B32 diagnostic, `dataProcessKnn` occupies99.087% of the recorded
query interval and GPU temporal work covers99.866%. Actual ordinary D2H/UVM
activity is small. The small Words query-only update trace instead has temporal
gaps and mostly one-block launches. Host synchronization overlaps GPU work;
neither trace establishes CPU distance arithmetic, bulk PCIe dominance, or a
universal GPU-tree bottleneck. Host-invoked `thrust::device` sorts/scans are GPU
work.

### Novelty and next evidence gate

[P5 complete-range evidence](https://github.com/wangwenqingqq/GTS-variants/blob/06570cd2e2857684984e43289d645b2b54903ae6/diagnostics/external_mask_validation_20261002/RESULTS.md)
also remains admitted at its own contract. P5 GIST half
B32 records C_MASK_E1526.3, SCAN_E1773.8 and qualified cuVS FP64 LIB64_U4786.4
ms per1024-query pass, paired ratios1.162/3.135. Deep's qualified LIB64_X is
faster; FP32 membership and GIST expanded-distance field failures are retained.
The same masked kernel's real/all candidate control establishes pruning
attribution, not coalescing-only benefit.
[P6 capability evidence](https://github.com/wangwenqingqq/GTS-variants/blob/f16d09a4e8a32ab8afff3b1b92221a5e447725a0/diagnostics/cagra_ivf_range_comparison_20261002/RESULTS.md)
retains the tested native GPU top-k/range
capabilities and K2048 capacity bound do not turn a truncated candidate result
into complete range output. Its custom full-bucket scan/reorder is not native
Faiss range performance. These frozen sets differ from P4; no cross-campaign
timing substitution is permitted.

Primary G-PICS leaf registration/reuse, Harmonia compact/query-organized GPU
trees, and MVGpuBTree device snapshots remain nearest mechanism precedents.
Generic pooling, batching, coalescing and GPU residency are not standalone new
contributions. A unified non-incremental thesis is not yet established.

Priority: close candidate/contract compatibility; recover or retire E1/E5;
check retained original update-prefix oracles before any new U0 tests; run an
integrated complete-query/sequence bridge only when a keeper exists. A
coalescing-specific experiment is conditional on retaining that claim, not
required to preserve the measured reuse/count-removal statements. Every new
run must identify one section, claim and missing qualifying evidence. No global
historical rerun or new optimization direction is authorized by this ledger.

## 2026-10-04 10K首轮执行补记

按固定计划480bc7执行；[本轮报告](../next_campaign_20261004/RESULTS.md)与hash外部完整bundle保留首个失败。未生成正式静态10K；下列开发/有界证据不替代计划的六轮主表。

| 项目 | 实际证据/契约 | 结果与状态 | 实现决定、机制决定、论文影响 |
|---|---|---|---|
| F0 bounded | P7派生适配器；78进程、24对eager/Graph、600复用cycles、16sanitizers、16条真实tail；完整CPU oracle | passed，bounded；1024/10K长稳定性未完成 | 保留控制，不晋升static stable或统一keeper |
| U10-NATIVE | N1000/D128、三预登记seed，每条10000 queries/1000 inserts/1000 deletes/50 rebuild，原U0观察bin | 30000查询、10030351字段项、153实际树、306000 ancestor/member检查全过；FN/FP/重复/非法ID全0 | 修补长正确性证据；无完整计时、新到达/稳定ID/并发/N1M动态主张 |
| 静态开发准入 | 新GIST1024/K8/B32；GTS_ORIG/O_FULL/IVF_ALL/O_BOUND全部成员/字段通过 | Native Flat漏1个成员，worst7/8，另1个自距字段超容差；CPU全1M复核，rejected | 按wrong-result停止；零正式10K进程，强基线比较仍不完整 |
| optional Flat REF64 | Native取64+RN-FP64精算+topK+全部Host-ready工作计时 | 同GIST1024通过231.328ms；memcheck32通过；small96资格13/48成员失败、worst0，rejected | 不晋升、不替代原native失败；有限候选精算不可宣称通用完整 |
| A0/A1静态 | 12NSYS+8实际NCU，全部诊断32输出独立核对；CPU/API/GPU并集分开 | measured；距离FP64管线指标85%左右；UVM fault存在但迁移bytes未知 | 支持后续距离路径归因；未证明新coalescing/精度机制端到端收益 |
| K10/R10/动态计时 | matched/bulk剩余形状、CAGRA网格、R10、30K sustained、更新timed adapter | pending；U10-ARRIVAL not admitted | 完整计划与统一keeper尚未达成，失败和未完成项保留 |

## 2026-10-04 execution recovery 补记

按 [恢复合同](../next_campaign_20261004/EXECUTION_RECOVERY.md)继续独立原生比较；首轮 Flat/REF64 的质量失败与全部历史口径保留，原全局停止规则修订为局部质量/计时拒收。当前仍没有正式10k结果或统一query/update keeper。

| 缺口 | 新取得的实际证据 | 边界与决定 |
|---|---|---|
| 原生更新完整计时 | Lean full-output binary `f96746e38adabd9ff1dc511202bd5e4782c83101db31b2fe86e3af8c695c18ad`；三seed×六fresh on/off pairs；全部事件/结果通过；成本上95≤1.006568 | N1000物理行重插入/live-rank/串行多重集；无新到达/并发/N1M动态倍率。桥接打印及memcheck不进性能摘要 |
| 观察器成本 | 18条件216进程，14通过、4拒收；Flat bulk上95为1.04977，CAGRA raw hash不一致 | 不删样本或减猜测开销；未资格化计时仅diagnostic，独立方法继续；全比较准入仍pending |
| 合法冷建树 | GIST/Deep各N1M真实构建；5000000 pivot-object距离、5次全N排序；完整排列/容量/覆盖通过；32条query输出通过 | NSYS constructor/GPU union与含审查/cache写出的index_setup分开；不是全N1M度量区间穷举 |
| 实际查询pass计数 | 四指定距离launch在post-warm `formal.query_pass`内采NCU | full默认只有DMUL per-cycle率；直接动态工作计数仍待补，不能据85% FP64指标宣称compute-only或纯coalescing |
| 独立原生开发 | IVF/CAGRA matched 两遍全网格448行已收集，未四舍五入质量保留；bulk10k全网格正在执行 | GIST CAGRA经验100%不可达，最高点保留diagnostic；正式种子未生成，无完整主表 |
| A2机制选择 | U10 query-prefix scan/init实际GPU累计139.598ms，整条instrumented trace18575.558ms；尚未实现缓存 | 存在源级重复状态维护，不据重复次数推端到端倍率；常规prefix缓存不足以开启新颖性主张，当前no-new-change |

源码、完整聚合数据、原始/curated hash映射与剩余门槛见 [RECOVERY_RESULTS](../next_campaign_20261004/RECOVERY_RESULTS.md)。治理补丁12项CPU回归通过；活动GPU阶段保持已登记脚本，安全切换安排在拥有的阶段drain之后。后续控制筛选、冻结和正式矩阵仍按完整查询数、真实16尾批次和六轮，原版旧约25GPU-hours仅为预算预测。

## 2026-10-07 K10统计闭合补记

上述2026-10-04停止/恢复文字保留历史状态；最新[合格结果](../next_campaign_20261004/K10_QUALIFIED_RESULTS.md)、[逐方法/逐对资格](../next_campaign_20261004/K10_COMPARISON_STATUS.json)和[剩余门槛](../next_campaign_20261004/CLOSURE.md)替代其“零正式进程/统计pending”作为当前状态。本补记只分析5b145bc已采集834行，不增加GPU任务、修改算法、改查询或调参。

| 账目/主张 | 现有正式证据 | 资格与决定 | 尚未证明 |
|---|---|---|---|
| 原始GTS/O_BOUND累计执行改善 | 八个matched条件，每组六fresh进程；配对几何比48.758–75.185 | 全部完整成员/字段及计时合格；多项执行差异共同贡献 | 不是纯coalescing贡献，不是与其他历史倍数的乘积 |
| 原始GTS/O_MASK完整静态候选 | 八个matched条件比46.956–76.846；另四bulk条件六轮，原始输出/身份已核对 | 静态本合同稳定；不覆盖动态更新 | 不含cold/layout/refit/Graph成本，不是统一GTS++总加速 |
| O_BOUND/O_MASK树额外净收益 | 核对同二进制、seed4096/depth/数据/树/输出；GIST/B32约1.8–2.2%，Deep/B32轻微回退，B1时延增加3.84–13.90% | matched 0/8达到下95>1.03且至少5/6 wins；bulk 0/4；负例保留 | 没有全形状树优势；不得依据final收益新增dispatch |
| 合格外部/O_MASK | 八个matched合格点，2个O_MASK较快、6个外部较快；全部合格IVF_ALL点更快 | 每组必须六轮联合质量+计时合格，完整保留最快外部竞争信号 | bulk无合格外部速度结论；ANN未资格化时间只诊断 |
| 整体采集与准入 | 834/834、139组六轮、12条件；52A/67B/20C，90个合格局部方法对 | collection_complete=true，静态candidate_stable=true，comparison_admitted=false | 局部有价值不等于全表准入 |
| 失败/未知保存 | 444计时未覆盖、18行继承hash失败、12行继承成本上界未过；474完整成员失败，24兼有字段失败；96目标未达；90吞吐窗口不可测 | 不丢失败轮、不重复已失败成本对照，不把未知当零；污染替代两完整轮使用实际labels | 3%上界未通过不能证明实际开销必然>3% |
| 统一search/update候选 | 静态P7 O_MASK与原生lean U10仍为不同二进制/状态入口 | 明确不存在；原生N1000重插入/live-rank/串行边界保留 | 未桥接更新后的AoSoA/树界/工作区/Graph刷新、任意新向量或并发 |

统计量和门槛沿原冻结合同；seed20261003/20000重采样继承P7实现，K10冻结未单列，明确为采集后公开的实现参数。六进程只刻画固定查询集运行波动，不证明跨分布泛化。剩余R10/30k、全冷总计、逐窗口派生与物理工作计数校准不删；先复用已有计数，不默认新NCU。新增summarize_k10.py可一键重建三类表，22项CPU回归验证缺轮/重复/失败轮/错误替代配对/同B及未知窗口等边界。

## 2026-10-08 机制归因与唯一生命周期候选

[归因报告](../next_campaign_20261004/REDUNDANCY_ATTRIBUTION.md)仅分析既有计数，0个新增GPU任务。三个优化模式的同源/同输入/同launch、SASS与本次Full校准对齐：GIST N1M/D960/Q32的Full/Bound/Mask分别30.720/16.369/15.929十亿坐标，Bound/Mask少算46.72%/48.15%，单位坐标DRAM读取未下降。只能支持少算与源码显式共享读取，不能把静态累计倍率归为纯coalescing；原版pow路径、单次迭代launch不做等工作相除。动态shared steps/拒绝前后配对数保留未知。

18个U10 on进程（每seed六个）的query.tree占比中位84.347%/85.026%/85.183%，逐进程八阶段原值完整保留。另一个已有NSYS的query.tree内110,000次显式内部申请+110,000次释放API包含预算612.809ms；必要kernel/标量反馈/初始化与所有等待区间分别解释，不把包含时间当净可省。

[候选manifest](../next_campaign_20261004/CANDIDATE_MANIFEST.json)登记唯一U_LIFE_BRIDGE，尚未实现/计时；仅复用原生range/update内部11个工作区，保持Managed/Device类别、计算与所有屏障，外部结果和Thrust分配不动。先正确性与新身份观察器资格，再固定seed0431六对；无完整流程可信收益即停止扩展。静态P7未整合，R10/30k/全冷及扩大动态能力仍pending，原834行与K10合格结果未修改。
