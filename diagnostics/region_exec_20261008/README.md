# REGION_EXEC 原型

原生 range/update 有界子树执行实验；上游 `ZJU-DAILY/GTS@3bac1b725e92e98e3b69d5cb79ad9c56ccb5e639`，已资格化 lean 适配器来自 `ab742e2`。首个提交实现 NATIVE/PAR_STRONG 同入口桥接，尚无融合性能结论。

N1000/D128/B1/L2。U10 输入值是整数，原配置 `#define short float` 实际存储 float；保留原配置、float 累加、维度次序、pow、边界及对象自身分支。新路径仅支持此冻结接口，其他距离合同明确拒绝。

`PAR_STRONG` 一 block/parent、实际 pid 共享；当前层父标记只读，独立下一层输出。规范槽按终端叶编号和叶内顺序，共同稳定收集；原缓冲、live-rank、重数、删除和串行 ACK 保持。CPU RegionPlan 在初建及实际重建后通过计入成本的 D2H/规划/H2D 重建，初建单列，重建嵌入触发 insert。

`PAR_BRIDGE_CHECK.json`：两半径 × 两模式，小型 57-event/19-query mixed trace，每模式完整多重集/FP32/更新状态/6034 祖先成员校验通过；两模式有序输出逐字节一致。`test_plan.cpp` 独立覆盖对象255/256/257、非空节点127/128/129、root leaf和超预算叶 fallback。开发耗时不是正式性能证据。

执行文件位于用户指定 ANNS 目录；复用原 U10 输入、独立 CPU oracle 与设备独占 guard，不修改任何历史证据。

四模式原型已实现并通过新资格检查：`REGION_BRIDGE_CHECK.json` 中两半径的四模式输出逐字节一致；三个新模式的逐节点/pivot/叶/对象计算集合在两个小 mixed trace 完全相同（`WORK_*.json`）。SPLIT/FUSED 共用模板内的局部遍历，只改变叶表全局交接/块内核验。

`STRUCTURAL.json`：9种拓扑×6种状态×2模式，覆盖预算、提前叶、空节点、root leaf、过大叶同语义 fallback、deleted pivot、stale epoch、可见容量错误。原 mixed trace 两模式各有 memcheck/racecheck/synccheck，结构矩阵三种 sanitizer 均通过。一个 racecheck 报告格式解析错误已保留并只重新审核原输出，未重跑该 GPU 进程（`HARNESS_FORMAT_FIX.json`）。

首轮性能仅固定 seed0431、四模式×六 fresh 进程；先做新身份观察器开销控制。主表尚未产生，不能以小型开发轨迹时延作收益结论。CPU 规划、传输、分配、完整输出与 ACK 均在相应成本边界中；三种新模式保留相同密集节点工作区及 N 级最终 hit/distance/collector，不声称消除全部物化。

## 2026-10-08 closure

The paragraphs above retain the earlier implementation checkpoint. The first
24-process primary campaign is now complete: see [RESULTS.md](RESULTS.md).
PAR_STRONG improves the native workflow; both region variants are slower than
PAR_STRONG, and direct fusion benefit is inconclusive. No seed/budget expansion
or fusion promotion follows this result.

The authoritative measured v2 identity and all raw process summaries are under
[evidence/v2](evidence/v2). Older root-level PAR/REGION manifests are historical
qualification records, not the v2 primary binary identity.
The published cleanup now matches the immutable measured source. The handoff
also closes the PAR sanitizer gap, verifies all 10k work sets, adds diagnostic
profiles and independently replays all 72 process outputs against an integer
multiset oracle. Follow [REPRODUCE.md](REPRODUCE.md); no primary run was replayed.
