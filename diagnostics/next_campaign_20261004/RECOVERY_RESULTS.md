# 恢复执行：已测证据与未完成门槛

执行依据为 [EXECUTION_RECOVERY.md](EXECUTION_RECOVERY.md)，原 [PLAN_10K.md](PLAN_10K.md) 内容及 SHA 保持不变。真实 GPU 工作固定在同一张 RTX PRO 6000 Blackwell Server 96 GiB，使用原有双锁及外来进程检查。未改变检索 kernel、共享设备设置或数值合同。本报告不宣称整个计划已完成。

## 当前状态

| 项目 | 实际完成范围 | 准入结论 |
|---|---|---|
| 原静态观察器成本 | 18 条件 × 6 fresh pairs × on/off，216 个进程 | 14 条件通过，4 条件拒收；没有全局 admitted 标记 |
| Lean U10 桥接 | seed0431 全12000事件、10000查询、51棵树、102000 ancestor/member 检查 | 与保留 observer 的全部 IDs/FP32 字段一致 |
| Lean U10 memcheck | seed0431 全轨迹与全部输出 | runtime valid；ERROR SUMMARY: 0 errors |
| Lean U10 成本/计时 | 三seed，每seed六对 fresh on/off，共36进程 | 三seed全部通过输出 hash 与 ≤3% 上界 |
| 原版合法冷建树 | GIST1M/D960、Deep1M/D96，各一棵真实新树 | 完整排列、覆盖、容量、父区间；各32条后续查询严格通过 |
| 实际 query-pass NCU | O_FULL/O_BOUND/O_MASK/GTS_ORIG 各一个指定距离 launch | post-warm NVTX 范围；动态坐标直接计数仍待补齐 |
| 原生更新 NSYS | seed0431 全12000事件、10000查询；输出重新审查 | attribution only，不能替代主计时 |
| Native matched development | 两数据集、K8/K32、B1/B32，IVF/CAGRA 两遍全网格，448 行 | 已收集；严格/target 质量逐配置保留 |
| Native bulk development | 独立开发10000，六种 chunk、两遍全网格 | 正在执行；不是正式集 |
| 正式10k、R10、30k | 正式0421/22尚未生成；零正式静态进程 | pending |

测量入口 SHA：静态优化 `70520e34a97b155a0aeffa58d0b1c851684a6be4cd4fd71b170099da64cfae17`；原版静态 full-output `40c1cf9b1f0d855a4d4c1cd55a6e4916af90fc0ca75e18b5d8be372ba5dc2075`；lean U10 `f96746e38adabd9ff1dc511202bd5e4782c83101db31b2fe86e3af8c695c18ad`。详见 [lean source manifest](evidence/recovery/U10_LEAN_SOURCE.json)。15个相关 GPU kernel body 的源码比较相同；变化限于声明的 `rnum[0]=0`、Host 输出/观察/ACK 与错误检查。

## 观察器失败没有转为通过

[216进程摘要](evidence/recovery/HOOK_CONTROL_COMPLETE.json) 保留全部六对比例。Deep Flat B10000 的点估计为1.00864，上95为1.04977：不能证明开销低于3%，也不能据此断言真实开销必然超过3%。未删慢样本、重复抽样挑结果或减去猜测开销。

Deep CAGRA B1/B32/B10000 的原始 on/off 输出 hash 均不一致；B32 开销上界另为1.22192。CPU检查首对原始输出发现同距离并列排序/边界选择差异，其中部分完整 tie-aware 质量通过，bulk还有未达完整召回的进程。输出 hash 失败仍然失败，不能用 tie-aware 质量通过代替观察器合同。

`execution-recovery-v2` 的最小控制器补丁把成本决定保留到方法/config/tile：已结束的失败对照不自动重跑；未资格化计时只能作为诊断行，阻止 comparison_admitted。配置改变或测量入口/观察器源码改变不能继承成本资格。12项标准库 CPU 回归通过。该治理补丁在本报告时仅完成 CPU 验证，当前运行阶段仍使用其已登记脚本快照；不得在活动测量中覆盖脚本。

## 原生更新计时与边界

[u10_trace.hpp](u10_trace.hpp) 只增加有界 Host 收集器：[u10_native.py](u10_native.py) 从固定八份原始源码生成和编译适配器。每次查询交付完整 IDs/FP32 字段，两种 observer 模式都执行相同 ACK fences 和 D2H；文件写入在计时后，树打印仅用于独立 correctness bridge。cold/load/output-buffer setup、最终 drain、CPU user/system 与八个阶段分别保存。

每seed仍为 N1000/D128、10000 query、1000 insert、1000 delete、50 threshold rebuild。三seed共10030351项交付结果，在每个 fresh 进程均逐项核对。成本上95分别为1.004605、1.006568、1.006288，原始完整输出/查询元数据 hash 全部一致。桥接和 sanitizer 的时延不进入性能摘要。

下表对六个 on 进程分别计算百分位后取中位数；trace 是六进程中位数，单位 ms。全部36进程与每项 p50/p95/p99/max/维护/内存见 [timed rows](evidence/recovery/U10_LEAN_TIMED_ROWS.json)，不挑最快轮。

| Seed/半径 | trace总计 | query p50 / p95 / p99 | insert p50 / p99 | delete p50 / p99 | rebuild p50 / p99 |
|---|---:|---:|---:|---:|---:|
| 0431 / 0 | 17470.832 | 1.375 / 3.431 / 5.077 | 0.01784 / 4.923 | 0.07210 / 1.397 | 4.808 / 5.235 |
| 0432 / 10000 | 18780.445 | 1.493 / 3.632 / 5.123 | 0.01814 / 4.970 | 0.07013 / 1.570 | 4.804 / 5.509 |
| 0433 / 512 | 18855.986 | 1.501 / 3.629 / 5.124 | 0.01838 / 4.946 | 0.07173 / 1.695 | 4.813 / 5.650 |

rebuild 是 insert 内子区间，不能再加到 insert 或 trace。50次重建造成 insert 尾部跳升；不能只引用未触发重建的 p50。trace 含最终 drain、完整交付与已资格化观察；不含冷加载/初建/Host 输出预分配和计时后的文件写入。所有 on 进程 sampled device-used 最大14237302784 bytes，Host 输出容量80800000 bytes；前者为 cudaMemGetInfo 的全设备已用值，不是任务独占分配或瞬时精确峰值。

这是原生物理行重插入/live-rank 删除/串行多重集的归因，没有更新候选、更新加速倍率、N1M dynamic、真实新向量或并发保证。

## 构建与 CPU 等待

[Cold attribution](evidence/recovery/COLD_ATTRIBUTION.json) 的 constructor NVTX 区间：GIST22726.105 ms，GPU kernel union22705.232 ms；Deep2330.580 ms，GPU union2308.076 ms。每棵实际树height6、100000叶、5000000 pivot-object距离、111110边界距离、5次全N排序。GIST构建中getPivotDis累计22647.682 ms，Deep为2300.440 ms。是有 profiler 的代表构建，不是六轮无观测性能分母。

适配器 index_setup 另含覆盖审查与cache写出，不能将其当纯constructor时间。完整N1M排列/区间通过不等于穷举所有成员的度量区间证明；本次后续query质量仅32条。输入load/constructor/审查写cache仍分开，包含context/layout/graph/warmup的全冷总计尚未闭合。

[U10 NSYS](evidence/recovery/U10_NSYSTEMS.json) 的 full trace18575.558 ms、GPU kernel union12293.360 ms。leaf-IP samples主要在未解析libcuda/VDso及profiler；不得将全部CPU user时间称为有用CPU计算，也不得把未解析IP指认为确定的等待函数。原静态32-query证据仍显示99.879%区间覆盖GPU工作，inclusive同步等待与GPU时间重叠。

[实际pass NCU](evidence/recovery/PASS_COUNTER_STATUS.json) 与 [physical counters](evidence/recovery/PASS_PHYSICAL_COUNTERS.json) 修正了之前只选warmup的范围问题。full默认报告只有DMUL per-cycle执行率；O_BOUND/O_MASK早停实际坐标数及原版迭代工作尚未直接闭合，所以当前不发布每坐标byte或纯访存合并贡献。补采样只针对这个缺口，保持同一二进制/查询与post-warm范围。

## 开发质量与下一阶段

[两遍IVF/CAGRA网格](evidence/recovery/PUBLICATION.json) 包含全448行的时延与未四舍五入聚合质量，逐查询recall和原始IDs/字段留在外部文件；raw/curated hashes分开。选择只使用注册dev1024，不使用正式种子。

GIST上CAGRA的经验100%目标在两种K及B中均不可达，保留最高质量诊断点；Deep是否达到完整门槛随K/B改变。Deep IVF K32即便接近/达到成员召回，也不能忽略字段/完整结果合同。任何正式集上的偶然通过不得把development_unreachable改为target-admitted。bulk还需实际六chunk全参数筛选，不能用matched参数声称全局最优。

下一阶段串行排队：补直接指令计数 → 完整48控制筛选 → bulk控制与冻结策略 → 观察器逐方法决定/安全源快照转换 → 正式集生成及首GIST/Deep K8/B32六轮。原版GIST1024既有321.237s意味着10k约52.3分钟/轮、仅该形状六轮约5.23 GPU-hours；旧八形状原版约25 GPU-hours，均为预测，另有大chunk八次预热、全native网格及其他方法成本。保持查询数、尾16及六轮，不能为赶进度缩样本。

没有新增优化机制。本次完成原生更新与构建的归因，不足以恢复任何常规prefix缓存/coalescing的新颖性或端到端收益主张。R10解析尾批次、30k单进程连续性、正式逐窗口质量/计数和全工作流剩余runtime行仍未完成。

公开摘要的私有路径/GPU标识/PID已移除；完整原始输出、receipt、源码快照、index和profiler留在任务私有执行目录。[PUBLICATION](evidence/recovery/PUBLICATION.json) 保留每份原始/规范化SHA，未把规范化摘要冒充原文件。
