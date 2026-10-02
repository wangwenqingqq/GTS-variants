# P4：浅层树接入强批量精确范围查询

**结论。** 在同一块 pro6000-8 RTX PRO 6000 Blackwell、同一新二进制和完整 ID+距离交付口径下，GIST-1M×960D 的半径减半查询中，四层树加掩码相对强批量扫描有稳定净收益：B=8 为 **1.104×**，B=32 为 **1.167×**；紧凑块任务分别为 **1.108×** 和 **1.172×**。普通半径的 B=32 收益只有约 1%–2%，低于预定 1.03× 区分门槛；全命中没有收益。Deep-1M×96D 的一层树没有超过扫描。Tloc-1M×2D 的四层树在 B=32 快约 1.45×，但 B=1 变慢。因而这是受数据、半径和批量约束的精确范围查询组件，不能称为通用 ANN 索引加速。

本报告记录上传的 [PLAN.md](PLAN.md) 与 [CONTRACT.yaml](CONTRACT.yaml) 的**实测结果**；两份设计附件原有 `DESIGN_ONLY` 标记仍表示编写时的状态。冻结起点是 `wangwenqingqq/GTS-variants@43463278fa1f2b7b8e6e36ff224e5c640036963e`，未修改 GTS 生产路径，也未向上游仓库提交。[PREFLIGHT.json](PREFLIGHT.json) 保存哈希和环境，[EVIDENCE_LEDGER.md](EVIDENCE_LEDGER.md) 区分历史机制与新增证据。

## 同口径端到端结果

所有模式共用 AoSoA32、512 线程、Q_T=2、顺序 FP64、CUDA Graph、稳定输出收集和按实际结果长度回传；B=1 沿用 Q_T=1 语义。`L` 算满全部维度，`E` 每 32 维做一次安全早退。`SCAN` 是本轮同二进制内重测的强批量扫描；`C_ID` 为每查询稳定候选位置列表，`C_MASK` 保留原数据块并按掩码核验，`C_TASK` 将并集非空的数据块压缩为任务。三条树路径使用相同的静态树、边界和候选集合。时间从提交已就绪的批查询到主机收到本批**全部有效 ID 和 float32 距离**，包括树遍历、候选组织、清零、GPU 核、计数反馈、有效结果 D2H 和同步；不含冷载入、布局构建、静态 refit、Graph 捕获或在线凑批。

下表是各条件六个独立进程的 **1024 条查询总 Host-ready 时间中位数**，单位 ms；不是一条查询的响应延迟。每进程先预热 8 个开发批次，最终查询顺序与配对不变，模式顺序和批次遍历顺序轮换。

| 模式 | GIST half B8 | GIST half B32 | GIST normal B32 | GIST all B32 |
|---|---:|---:|---:|---:|
| SCAN_L | 5722.4 | 5683.7 | 5702.9 | **6010.6** |
| C_ID_L | 4920.9 | 4805.6 | 6024.8 | 6622.9 |
| C_MASK_L | 4665.3 | 4484.1 | 5507.7 | 6035.9 |
| C_TASK_L | 5831.2 | 5682.4 | 6235.6 | 6620.5 |
| SCAN_E | 1826.1 | 1775.1 | 4563.4 | 6039.1 |
| C_ID_E | 2038.0 | 1915.3 | 5831.1 | 7915.6 |
| C_MASK_E | 1653.9 | 1521.8 | 4519.9 | 6112.7 |
| C_TASK_E | **1647.3** | **1515.3** | **4493.3** | 6075.5 |

同轮 `SCAN_E/C_MASK_E` 在 GIST half B8、B32 的配对中位比值分别为 **1.10435×**、**1.16657×**，六轮范围 `[1.10204,1.10496]`、`[1.16607,1.16683]`；`SCAN_E/C_TASK_E` 为 **1.10850×**、**1.17162×**，范围 `[1.10409,1.10931]`、`[1.17061,1.17186]`，均六轮胜出。对应六轮重采样 95% 中位区间在 [summary_gist_half.json](summary_gist_half.json)。GIST normal B32 的 C_TASK_E 为 **1.01554×**，不足 1.03×；全命中最强基线是 SCAN_L，`SCAN_L/C_MASK_L=0.99486×`，`SCAN_L/C_TASK_L=0.90871×`，均无净收益。全命中每条查询确实返回 100 万对象，1024 条合计 1,024,000,000 条、有效载荷 8.192 GB；这些传输被计入时间。新 final 查询对应 GIST half 1,650,186 条、normal 90,799,280 条结果，不能直接拿旧查询的总时间作分母。

Deep/Tloc 候选结构先在各自开发 256 查询上按 L+E 总时间最小冻结：Deep 选 C_MASK，Tloc 选 C_TASK，然后才生成各自排除历史与开发 ID 的新 1024 查询。正式中位时间如下。

| 数据 / B | SCAN_L | 冻结树 L | SCAN_E | 冻结树 E | 同轮 E 比值 |
|---|---:|---:|---:|---:|---:|
| Deep normal / 32，C_MASK | 616.6 | 620.3 | **596.9** | 607.0 | 0.98769× |
| Tloc normal / 1，C_TASK | **67.7** | 94.5 | 74.4 | 93.5 | 0.79517× |
| Tloc normal / 32，C_TASK | 27.9 | 19.9 | 28.2 | **19.5** | **1.44889×** |

Tloc B32 的 E 比值六轮范围 `[1.39602,1.45468]`，重采样区间 `[1.41425,1.45422]`；B1 六轮均回退。Deep 的 `SCAN_E/C_MASK_E` 六轮范围 `[0.96527,0.99106]`。其余逐轮、每批 p50/p95、GPU-ready、摊销时间和 QPS 见 [summary_deep.json](summary_deep.json)、[summary_tloc.json](summary_tloc.json) 及 `latency_*.csv`。这些区间只描述冻结查询集上的运行波动，不能外推生产查询分布。

## 为什么 GIST half 有益，但全命中不行

GIST half 的新 final1024、B=32 候选账本：树后仍有 **780,584,300** 个 query-object 对，即全表的 **76.23%**；两条查询的对象并集仍达 **90.15%**，非空块占 **90.38%**。树确实少要求约 23.77% 的配对核验，但没有相应比例的共享对象读取下降。独立 dev32 工作量计数把树前/后的配对坐标更新记为 5.544→4.520 十亿（少 18.46%），逻辑共享坐标步数为 3.455→3.029 十亿（少 12.32%），warp 最长路径步数为 159.19→141.05 百万（少 11.39%）。它们是逻辑工作量，不能称为物理 DRAM 字节或端到端时间。父枢轴复用先核对实际 pivot ID；候选账本与旧 `strict_walk` 对每个位置一致。详见 `gist_half_final1024_candidates.*` 和 `gist_half_dev32_work.*`。

独立的 GIST half 开发 B32 Nsight Systems 样例中，SCAN_E 的 Host-ready 51.96 ms、距离核 51.60 ms；C_MASK_E 为 44.41/43.06 ms，另有树遍历 0.91 ms、mask 0.08 ms、清零 0.01 ms。C_TASK_E 为 44.30/42.75 ms，另有树遍历 0.90 ms、mask 0.08 ms、任务压缩 0.09 ms。核验节省大于树与组织成本，产生真实总时间收益；C_TASK 相对 C_MASK 只多约 0.4% 的正式收益，不宜把微小差异叙述为主要新机制。C_ID_E 的距离核反而 54.41 ms，朴素压缩与不规则 gather 没有保住批量共享。样例的同步 API 包含等待 GPU 工作，不能再加到核时间上。[profile_summary.csv](profile_summary.csv) 保存完整阶段。

NCU application replay、`cache-control=none`、`clock-control=none` 的同开发批次：**对象核** DRAM 读 SCAN_E/C_MASK_E/C_TASK_E 分别为 17.967/15.859/15.837 GB；**全部被剖析的 kernel** 分别为 18.002/15.901/15.874 GB，后者含树、掩码、压缩和收集核，不含 memcpy/Graph memset 的全部物理流量。全命中和 L 路径不能由 E 路径外推：开发样例中 C_TASK_L 与 C_MASK_L 的对象核 DRAM 读都约 55.75 GB，但 FP64 warp 指令约 4.367 对 3.319 十亿，C_TASK_L 明显更慢；指令分布是观测，具体代码生成原因尚未隔离。[ncu_summary.csv](ncu_summary.csv) 与原始 profiler 收据保留各自测量范围；profiler 绝对时间不与正式六轮计时混用。全命中没有对象可剪，树遍历和候选组织只增加工作。

## 正确性、边界与复现

12 个小规模 N/D/B 组合 ×8 模式，即 **96** 个完整输出，与独立 CPU 全枚举逐字节一致；包含 D=2/31/32/33/96/960、N=4096/4103、非整块、B=1/3/8/32/33。人工 mask 的全空、全满、同掩码、互斥、单 lane、尾位单测通过；代表性 C_TASK_E 的 memcheck、synccheck 零错误。百万规模新 final 的 **44 个逻辑条件**与独立旧 strict FR 完整输出逐字节一致；**264 个正式进程**有有效 GPU 收据，逐查询 count/有序 hash 和每批交付字节都匹配参考。[CORRECTNESS.json](CORRECTNESS.json) 汇总归档后重验，[raw_remote_runs.tar.gz](raw_remote_runs.tar.gz) 保存命令、收据、GPU 监控、逐查询 CSV 和 profiler 原始数据。大体积 `.bin` 未纳入 Git；参考输出 SHA-256 已保留。另对每个百万规模场景抽 16 条查询，用独立 CPU 复算抽样命中/未命中和 float32 距离位模式；这不是全库每一对的 CPU 证明。

原始归档保留两次无效尝试：早期 `small_matrix_v2` 的 B=33/Q_T 参数被旧二进制拒绝，修订后的 v3 小规模矩阵全部通过；一次 `ncu_full_half_b32_C_ID_E` 被 GPU 活动监控拒收，未用于性能结论。正式进程均有效。固定 P4 二进制 SHA-256 为 `36adb09b490d124591e78f0332e0dd0c114ee8f621018b82ae7be3d8dd491c77`；重新编译的 ELF 只在 nvcc 临时符号名 4 字节不同，两个副本 `strip --strip-all` 后逐字节相同，SHA-256 为 `d776609fc1fe5f9e1e81b2fe1417b10207783c272cedeb25ab85a7c9ff27d630`。命令、数据/树/query 哈希和采样 GPU 内存峰值见 [PREFLIGHT.json](PREFLIGHT.json)。

外部 cuVS 批量 pairwise + 全量范围输出对照**未完成**：独立环境安装 `cuvs-cu13==26.8.1`、`cupy-cuda13x==14.2.0` 时，大型依赖下载持续停滞后终止；准确命令与日志在 [cuvs_install_status.json](cuvs_install_status.json) 和 [cuvs_install.log](cuvs_install.log)。不能由本轮内部对照宣称超过 cuVS。实验仅覆盖静态、库内、L2 精确范围查询；没有覆盖插入/并发更新、KNN、外部查询、在线凑批或其他 GPU。
