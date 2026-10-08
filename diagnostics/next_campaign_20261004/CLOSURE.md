# 统计闭合后的剩余门槛

## 2026-10-08 本轮闭合结果

提交 A 已完成[工作量与流量归因](REDUNDANCY_ATTRIBUTION.md)：Full/Bound/Mask 同工作域计数对齐，Bound/Mask 少算 46.72%/48.15%；纯 coalescing 因果仍不支持。18 个既有 U10 on 进程的八阶段账及一个独立 profile 的选定分配预算已闭合。

提交 B 已完成[原生范围查询—更新工作区生命周期小桥接](INTEGRATION_RESULT.md)。同一新二进制 U_BASE/U_LIFE 只改变 11 个内部工作区的容量/寿命，24 个正式进程与全部输出核验通过；两条轨迹时延下降约 3.41%/3.00%。第二条 trace/setup+trace 的 CI 下界未过 1.03，insert p99 配对比中位数增加 3.58%，按事前登记停止第三 seed，不晋升 keeper。新观察器资格、边界/sanitizer 与两份小 profile 分列，全部六轮和负门槛保留。

原生小桥接已经存在；**静态 P7 kNN 与原生更新的统一候选仍不存在**。Graph/AoSoA 为 N/A；完整任务分配峰值、CPU useful time、UVM/合并访存因果、R10/30k/全冷、任意新向量/N1M 动态/并发及外部动态比较仍未闭合。未改原 834 行和 K10 合格结果，不自动启动这些任务。实际代码/输入/输出身份见 [CANDIDATE_MANIFEST.json](CANDIDATE_MANIFEST.json) 与[完整技术结果](evidence/recovery/U_LIFE_BRIDGE_RESULTS.json)。

## 2026-10-07 统计闭合时的记录

以下内容保留该次提交的状态与排序；其中四计数与唯一生命周期小桥接的后续状态以上述 2026-10-08 记录为准。它们不改变历史 K10 准入，也没有形成统一搜索—更新总倍率。

基点 `5b145bceabbc7aa544e6d6ff25657403ea92e151`；834行/139配置组/12条件已做纯CPU六轮统计；全局comparison_admitted仍false。未运行新的GPU任务。

## 当前实际实现身份

统一search/update候选**不存在**。静态kNN使用P7派生O_MASK/O_BOUND，search commit `d65c6e41effad67dde8ae1f1f68e656562607817`、parent `7bce3679c3e32e77fa25cf7842805926509e1412`；O_MASK二进制`70520e34a97b155a0aeffa58d0b1c851684a6be4cd4fd71b170099da64cfae17`。树mask、seed cutoff、完整验证/topK及Graph/AoSoA均限于该静态入口。

原生范围更新使用独立lean U10入口`f96746e38adabd9ff1dc511202bd5e4782c83101db31b2fe86e3af8c695c18ad`，保留原insert/delete/buffer occupancy-triggered整理重建及live-rank多重集。N1000/D128物理行重插入、串行立即可见性已测；不是稳定外部ID、任意新向量、并发或N1M动态。没有把静态AoSoA、树界refit或Graph刷新接入这个更新入口；更新后的静态副本/工作区/Graph刷新与发布时机未桥接。静态range的历史P4/P5入口仍为独立合同，不能与K10 topK输出互换。

资源复用、Tloc阶段连续性、P4/P5范围候选组织及U10-prefix归因仍是独立证据；未自动合入一个keeper。有限overfetch REF64及旧direct-insert不晋升。不存在整合GTS++搜索—更新端到端倍率，历史静态与更新倍率不相乘。

| 优先级 | 缺口/实际状态 | 影响的主张 | 下一步及证据来源 |
|---|---|---|---|
| P0 已完成 | K10每行资格、每组六轮、全部子比较和三类表 | 累计静态改善、树额外净收益、合格外部竞争 | 一键重建本报告；使用已有834行，不重跑GPU |
| P1 | 444行method/config/tile未覆盖；18行继承hash失败；12行继承成本上界未过 | 外部frontier或必要O_FULL对照计时 | 先依据具体受阻比较登记最小缺失控制；已结束失败不自动重跑，新身份不回填旧834行 |
| P1 | 外部成员失败与仅字段失败分别保留，ANN目标失败不删 | 同质量精确竞争；native速度仍是竞争信号 | 复用当前oracle/audit及既有Flat定位；不放宽容差、不以有限候选精算恢复旧native、不开混合精度项目 |
| P1 | O_BOUND/O_MASK的逐条件净收益与负例已列；不是全形状树优势 | 树前置的实际贡献和 keeper 选择 | 不根据正式结果补选dispatch；维持冻结候选/控制，负例保留 |
| P1 | 四份直接工作计数已采集，核名/launch/查询/单位与校准未闭合 | 工作减少、每坐标bytes；纯coalescing尚未证明 | 下一提交先分析既有query-pass NCU和直接计数；范围不匹配则不除，不默认新NCU |
| P2 | 搜索—更新统一候选不存在，静态副本/界/工作区/Graph刷新未桥接 | 整合系统真实存在、总维护/查询收益 | 先CANDIDATE_MANIFEST；按已有阶段预算选择一个兼容组件，再做更新前query→insert→立即query→delete→query→一次rebuild→重查小桥接；确需新源码/小GPU测量 |
| P2 | U10是独立原生有界基线，prefix约139.6ms/18.6s instrumented trace，尚未缓存 | 更新等待与维护收益 | 重复次数不代替预算；组件桥接确有净收益后复用登记U10轨迹，维护/layout/Graph/final drain全计时，rebuild不重复相加 |
| P2 原计划未完成 | R10范围10k、单进程三次10k持续性 | 长范围完整交付、连续状态稳定 | 不能从本次静态kNN six fresh rounds推得；候选身份后按具体论文主张恢复登记测量 |
| P2 原计划未完成 | 全冷总计、逐窗口质量派生、allocation/copy/CPU有用工作剩余归因 | 完整工作流端到端、CPU等待/PCIe/coalescing因果 | 先复用保存的raw输出、profile与冷阶段；缺失context/layout/Graph/warm证据才登记最小新测量，不加重叠区间 |

## method/config/tile缺口排序

完整明细见K10_COMPARISON_STATUS.json的method_config_tile_gaps，或合格结果报告C表。六轮完整质量已通过、未被开发目标诊断边界阻挡且缺少tile成本控制的必要外部点为：bulk:Deep:K8 IVF_ALL B2048 {"nlist":1024,"nprobe":1024}。这不准许事后改写旧834行资格；只有论文确需该bulk对照时才登记新的补充控制/计时身份。其他native质量或目标失败不能只补计时控制后恢复完整质量比较。

O_FULL/B1未覆盖只阻挡额外full-scan消融，不阻挡已合格的GTS_ORIG/O_BOUND/O_MASK主比较。CAGRA已失败的hash控制和Flat已失败的成本控制不自动重跑；其余ANN参数未覆盖与数值/目标失败分别保留。native全部实测速率是竞争信号，未准入时仍不提供正式倍率。

这些优先级是采集后的工作排序，不是改写原统计合同或追加事前登记。首次统计提交不包含新kernel、精度修复、R10/30k或新10K任务。
