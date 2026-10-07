# 恢复执行：10K 静态采集完成，整体比较仍未准入

执行依据为 [EXECUTION_RECOVERY.md](EXECUTION_RECOVERY.md)，原 [PLAN_10K.md](PLAN_10K.md) 内容及 SHA 保持不变。真实 GPU 工作固定在同一张 RTX PRO 6000 Blackwell Server 96 GiB，使用原有双锁及外来进程检查。未改变检索 kernel、共享设备设置或数值合同。本报告不宣称整个计划已完成。

## 当前状态

截至2026-10-07北京时间11:23，正式 K10 matched/bulk 矩阵已完成 **834/834 个 fresh 进程，每进程10000查询**。GIST1M/D960、Deep1M/D96的K8/K32、B1/B32共八个 matched 条件，以及两数据集×两种K的四个独立 bulk 条件，均完成六轮。正式种子0421/22在开发策略冻结后生成，没有使用正式结果改参数。

原始完成决定为 `collection_complete=true`、`candidate_stable=true`、**`comparison_admitted=false`**。candidate_stable仅适用于本合同中的静态 O_MASK 行及其已检查门槛；不能推广为动态更新、并发、所有查询或外部基线优势。完成摘要与冻结身份见 [K10_COMPLETION](evidence/recovery/K10_COMPLETION.json)，全部834行的时延、质量、资格和哈希见 [K10_FORMAL_ROWS](evidence/recovery/K10_FORMAL_ROWS.json)。六轮配对统计报告尚未生成，本次不发布新的加速倍率或置信区间。

| 项目 | 实际完成范围 | 准入结论 |
|---|---|---|
| 原静态观察器成本 | 18 条件 × 6 fresh pairs × on/off，216 个进程 | 14 条件通过，4 条件拒收；没有全局 admitted 标记 |
| Lean U10 桥接 | seed0431 全12000事件、10000查询、51棵树、102000 ancestor/member 检查 | 与保留 observer 的全部 IDs/FP32 字段一致 |
| Lean U10 memcheck | seed0431 全轨迹与全部输出 | runtime valid；ERROR SUMMARY: 0 errors |
| Lean U10 成本/计时 | 三seed，每seed六对 fresh on/off，共36进程 | 三seed全部通过输出 hash 与 ≤3% 上界 |
| 原版合法冷建树 | GIST1M/D960、Deep1M/D96，各一棵真实新树 | 完整排列、覆盖、容量、父区间；各32条后续查询严格通过 |
| 实际 query-pass NCU | O_FULL/O_BOUND/O_MASK/GTS_ORIG 各一个指定距离 launch；四份补充直接工作计数已采集 | post-warm NVTX 范围；直接计数的校准和工作量归一化仍待完成 |
| 原生更新 NSYS | seed0431 全12000事件、10000查询；输出重新审查 | attribution only，不能替代主计时 |
| Native matched development | 两数据集、K8/K32、B1/B32，IVF/CAGRA 两遍全网格，448 行 | 已收集；严格/target 质量逐配置保留 |
| Native bulk development | 独立开发10000，六种 chunk、两遍全网格，1344行；另72行 bulk 控制 | 已完成并冻结独立 bulk 策略；不是正式集 |
| 正式 K10 matched/bulk | 八个 matched 与四个 bulk 条件，各六轮，834进程 | 采集完成；整体比较未准入 |
| R10、30k | 范围查询矩阵、单进程三次连续10000查询 | 未完成 |

### 正式 K10 逐方法门槛

| 方法 | 进程数 | 完整成员/字段通过 | 内存增长通过 | 计时有资格 | 已观测吞吐下降超过10% | 吞吐窗口不可测 |
|---|---:|---:|---:|---:|---:|---:|
| CAGRA | 198 | 0 | 198 | 0 | 35 | 60 |
| FAISS_FLAT | 72 | 30 | 72 | 48 | 0 | 18 |
| GTS_ORIG | 72 | 72 | 72 | 72 | 0 | 0 |
| IVF_ALL | 72 | 36 | 72 | 48 | 0 | 0 |
| IVF_APPROX | 204 | 6 | 204 | 0 | 0 | 12 |
| O_BOUND | 72 | 72 | 72 | 72 | 0 | 0 |
| O_FULL | 72 | 72 | 72 | 48 | 0 | 0 |
| O_MASK | 72 | 72 | 72 | 72 | 0 | 0 |

834项均为 actual_Q=10000、runtime valid，内存增长门槛通过，采样设备已用内存不超过注册80 GiB上限。采样设备已用值不是任务独占分配或瞬时峰值。O_MASK的72项完整输出、计时资格与当前稳定性门槛全部通过；CAGRA的35项吞吐下降保留为该方法的诊断，不能称所有方法均稳定。另90项大chunk原生调用内部无法观测首/尾2k吞吐，保留不可测状态，不计作通过；bulk各方法使用各自冻结chunk，四个bulk条件不代表共同B值。

整体仍有 **474项计时未资格化、96项未达冻结召回目标、474项严格完整质量拒收**；三组不是同一集合。计时未资格化既包含注册代表成本对照失败，也包含 method/config/tile 没有合格代表对照，不能把474项都解释为实际观测开销超标。O_FULL的B1、Flat/IVF_ALL的部分bulk条件没有计时资格。ANN的99%/99.9%目标通过与严格100%成员/字段通过分开记录；目标标签共348 admitted、96 missed_target、102 diagnostic_only，不把开发阶段不可达目标因正式集偶然通过改判。

两次外来GPU活动使原运行 runtime invalid，按登记规则替换了**整个受影响的数据集/形状/轮次**：Deep/K8/B32第一轮11项、GIST/K8/B32第三轮12项。811项保留原 measurement label，23项明确保存 `__contamination1/2` 标签及登记SHA。原始有效部分、失败receipt和输出仍保留在外部证据中，没有第三次替换。

发布前逐项核对冻结计划、actual measurement label 的receipt/audit与完整结果文件SHA，检查全部834项query/oracle身份及测量身份中的文件哈希；校验结果见完成摘要。这是采集后的文件一致性检查，没有重测GPU、重新调参或替代独立oracle计算。

测量入口 SHA：静态优化 `70520e34a97b155a0aeffa58d0b1c851684a6be4cd4fd71b170099da64cfae17`；原版静态 full-output `40c1cf9b1f0d855a4d4c1cd55a6e4916af90fc0ca75e18b5d8be372ba5dc2075`；lean U10 `f96746e38adabd9ff1dc511202bd5e4782c83101db31b2fe86e3af8c695c18ad`。详见 [lean source manifest](evidence/recovery/U10_LEAN_SOURCE.json)。15个相关 GPU kernel body 的源码比较相同；变化限于声明的 `rnum[0]=0`、Host 输出/观察/ACK 与错误检查。

## 观察器失败没有转为通过

[216进程摘要](evidence/recovery/HOOK_CONTROL_COMPLETE.json) 保留全部六对比例。Deep Flat B10000 的点估计为1.00864，上95为1.04977：不能证明开销低于3%，也不能据此断言真实开销必然超过3%。未删慢样本、重复抽样挑结果或减去猜测开销。

Deep CAGRA B1/B32/B10000 的原始 on/off 输出 hash 均不一致；B32 开销上界另为1.22192。CPU检查首对原始输出发现同距离并列排序/边界选择差异，其中部分完整 tie-aware 质量通过，bulk还有未达完整召回的进程。输出 hash 失败仍然失败，不能用 tie-aware 质量通过代替观察器合同。

`execution-recovery-v2` 的最小控制器补丁把成本决定保留到方法/config/tile：已结束的失败对照不自动重跑；未资格化计时只能作为诊断行，阻止 comparison_admitted。配置改变或测量入口/观察器源码改变不能继承成本资格。12项标准库 CPU 回归通过。开发网格和控制筛选结束、无活动测量子进程时，已部署审查提交 `ddae6c1` 并冻结正式源快照。路径迁移只规范化同文件别名且保留哈希检查；检索源码与静态二进制未改变，执行代码已迁入 ANNS 工作目录。

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

[实际pass NCU](evidence/recovery/PASS_COUNTER_STATUS.json) 与 [physical counters](evidence/recovery/PASS_PHYSICAL_COUNTERS.json) 修正了之前只选warmup的范围问题。full默认报告只有DMUL per-cycle执行率；补充四份直接工作计数已经采集，但O_BOUND/O_MASK早停实际坐标数及原版迭代工作的校准尚未闭合，所以当前不发布每坐标byte或纯访存合并贡献。补采样只针对这个缺口，保持同一二进制/查询与post-warm范围。

## 开发质量与剩余工作

[两遍IVF/CAGRA网格](evidence/recovery/PUBLICATION.json) 包含全448行的时延与未四舍五入聚合质量，逐查询recall和原始IDs/字段留在外部文件；raw/curated hashes分开。选择只使用注册dev1024，不使用正式种子。

GIST上CAGRA的经验100%目标在两种K及B中均不可达，保留最高质量诊断点；Deep是否达到完整门槛随K/B改变。Deep IVF K32即便接近/达到成员召回，也不能忽略字段/完整结果合同。任何正式集上的偶然通过不得把development_unreachable改为target-admitted。bulk已完成独立六chunk筛选并冻结策略，没有以matched参数代替bulk开发。448行matched、1344行native bulk、48行筛选与72行bulk控制的原始文件SHA和行数也保存在完成摘要中；未将开发结果混入834行正式矩阵。

剩余工作为六轮配对统计报告、R10范围查询矩阵、30k单进程连续性、直接计数校准，以及全冷总计/逐窗口归因等未闭合工作流项。静态K10采集完成不代替这些门槛，未资格化计时和未达质量目标的外部点仍留在诊断范围，不进入同质量正式速度结论。

没有新增优化机制。本次增加静态K10完整采集和受限稳定性证据，并保留原生更新与构建归因；不足以恢复任何常规prefix缓存/coalescing的新颖性或端到端收益主张。正式逐窗口质量/计数的派生报告和全工作流剩余runtime行仍未完成。

公开摘要的私有路径/GPU标识/PID已移除；完整原始输出、receipt、源码快照、index和profiler留在任务私有执行目录。[PUBLICATION](evidence/recovery/PUBLICATION.json) 保留每份原始/规范化SHA，未把规范化摘要冒充原文件。
