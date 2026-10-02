# P6：CAGRA / Faiss-IVFFlat 与完整 L2 范围检索

冻结起点为 `wangwenqingqq/GTS-variants@06570cd2e2857684984e43289d645b2b54903ae6`。生产查询路径未改；实验均在 `pro6000-8` 的指定 RTX PRO 6000 Blackwell GPU 上运行。任务是静态、库内查询的完整 L2 范围检索，返回原始 ID 与 float32 距离，按参考 `id_list` 顺序交付到 Host。数据为 GIST 1M×960D 和 Deep 1M×96D。上传的 [PLAN.md](PLAN.md) 与 [CONTRACT.yaml](CONTRACT.yaml) 保留设计时状态；本报告记录实际实施和偏离。

## 主要结果

**在完整范围合同下，没有发现 CAGRA 或 Faiss 原生 GPU range API 可直接取代精确基线。** 本次 cuVS CAGRA 只提供 top-K 搜索；实际安装的 Faiss 1.15.1 原生 GPU `GpuIndexIVFFlat.range_search` 报 `range search not implemented`。候选适配器虽可比完整返回快很多，但 GIST half 最宽的合法 K2048 在新最终集上的微平均 RangeRecall 上限仅 **14.414%**。即使 Faiss nprobe256 已达到这个上限，也不具备完整范围结果。GIST normal、Deep normal 的 K2048 上限分别只有 **1.679%**、**6.848%**。这来自真实命中数与 K 的离线算术上限，而非搜索参数不够强。[CAPABILITIES.json](CAPABILITIES.json)、[CAPACITY_BOUNDARY.json](CAPACITY_BOUNDARY.json) 保存能力及容量边界。

在完整交付表中，GIST half B32 的 `C_MASK_E` 六轮中位 **1505.9 ms/1024 查询**，比 `SCAN_E` 的 1745.6 ms 快约 **1.159×**；Faiss 桶结构加自定义完整 GPU 扫描及保序为 1770.8 ms。Deep normal B32 经新查询逐字节审核的 cuVS FP64 `LIB64_X` 为 **362.7 ms**，比扫描快。故结论只限于具体数据、半径与批量，不能概括为树总是最快。[exact_latency.csv](exact_latency.csv)、[ivf_full_latency.csv](ivf_full_latency.csv) 是六轮原始数据。

## 冻结、能力和数值合同

先在既有 GIST half、B32、256 查询上完成 **42** 个参数点（CAGRA K128/512/1024；Faiss nlist1024/4096、合法 nprobe 与 K128/512/2048），每点 3 轮。CAGRA K2048 实测超出 cuVS top-K 1024 上限；Faiss K4096 超出 GPU top-K 2048 上限，nlist4096 的 nprobe4096 超出 GPU nprobe2048 上限。nlist1024、nprobe1024 可探全桶，但 top-K 仍截断范围输出。开发集未有一个点达到 90% 微平均 RangeRecall。选取快点、较高覆盖点和容量饱和点后写入 [FROZEN_CONFIG.json](FROZEN_CONFIG.json)，**此后**才抽取 GIST、Deep 各 1024 条新 qid；分别排除 3552、3416 个 P0–P5 已见 ID，交集均为零。[QUERY_SETS.json](QUERY_SETS.json) 记录冻结配置与查询哈希。全网格见 [development_raw.json](development_raw.json)、[bucket_coverage.csv](bucket_coverage.csv)。

共同核验把有限 float32 输入升为 float64，逐维显式 RN 减、乘、加且关闭 FMA，判定平方和 `<= double(radius)^2`，再把 `sqrt` 转为 float32 距离。候选适配器对**所有返回候选**执行该核验；没有先按原生 FP32 距离筛选。GIST half/normal 与 Deep normal 的 `SCAN_L`、`SCAN_E`、`C_MASK_E` 及对应合格 cuVS FP64 模式，在新 1024 查询的完整 ID+距离二进制上均与严格参考逐字节一致。72 条开发/最终候选质量记录的误报、重复 ID 与已返回真答案的距离字段逐位差异均为零；漏检来自候选未覆盖。有限数据集审核不等于任意输入的数值等价证明。GIST all 每条查询命中全部 1M 点，只做完整计数与有序哈希：三个内部精确模式匹配，`LIB64_U` 有 1 条查询哈希不同，因此未列为该档的同合同对手。[numerical_qualification.csv](numerical_qualification.csv) 列出逐模式审核。

## 完整范围结果：全部 ID+距离 Host-ready

下表每格为同一新 1024 查询六个独立进程的总耗时中位数，单位 ms。B=8/32 是嵌套分批；这不是单请求响应时延。`IVF全桶*` 由 Faiss nlist1024 构建全部非空倒排桶，导出每个桶内的全部 ID，按该顺序用 P4 `SCAN_E` 完整扫描，再在 Host 恢复参考 ID 顺序，排序成本包含在时间内。它是 **Faiss-IVF structure + custom GPU range executor**，不是原生 Faiss GPU range。其诊断索引仅替换 SCAN 模式加载器要求的 ID 顺序字段；树节点不参与扫描。全部 36 个正式运行恢复顺序后均与严格参考逐位一致。

| 数据/半径 | B | SCAN_L | SCAN_E | C_MASK_E | 合格 cuVS FP64 | IVF全桶* |
|---|---:|---:|---:|---:|---:|---:|
| GIST half | 8 | 5722.2 | 1798.3 | **1639.0** | 19112.9 `LIB64_U` | 1825.8 |
| GIST half | 32 | 5683.8 | 1745.6 | **1505.9** | 4786.2 `LIB64_U` | 1770.8 |
| GIST normal | 8 | 5741.8 | **4630.7** | 4688.7 | 19130.4 `LIB64_U` | 7248.0 |
| GIST normal | 32 | 5702.6 | 4556.5 | **4525.9** | 4803.9 `LIB64_U` | 7451.7 |
| Deep normal | 8 | 597.6 | **590.2** | 600.5 | 1393.6 `LIB64_X` | 1376.2 |
| Deep normal | 32 | 586.7 | 578.2 | 585.2 | **362.7** `LIB64_X` | 1337.5 |

GIST half B32 的 IVF 全桶 1770.8 ms 中，完整 GPU 扫描六轮中位约 1749.5 ms、Host 保序约 24.0 ms。GIST normal B32 的 7451.7 ms 中，完整扫描约 4723.7 ms、保序约 2795.6 ms；Deep normal B32 的 1337.5 ms 中，扫描约 585.0 ms、保序约 752.3 ms。分阶段中位数之和不必等于总时延中位数。保序用唯一参考名次的 CPU quicksort；可能还有更快的 GPU/CPU 实现，因此该自定义执行器的排序成本不是 Faiss 所有可能实现的下界。[latency_breakdown.csv](latency_breakdown.csv) 给出对应分解。

## 候选范围适配器：RangeRecall—Host-ready

下表只列 B32；B8、每轮、批次 p50/p95、原生 top-K 时延在 [refined_latency.csv](refined_latency.csv)、[native_latency.csv](native_latency.csv)。时间是输入准备、原生候选搜索、全部候选严格 FP64 核验、过滤/去重、恢复统一顺序及 Host 输出的六轮中位数；质量是冻结后新查询的 RangeRecall 微平均。`F1/F16/F256` 均为 Faiss nlist4096，后面的数是 nprobe。原生 top-K 时延**不能**与这里的精算质量配对。

| 数据/半径 | CAGRA K128 | CAGRA K1024 | F1 K128 | F16 K2048 | F256 K2048 |
|---|---:|---:|---:|---:|---:|
| GIST half | 79.0 ms / 1.303% | 238.6 / 7.763% | 52.7 / 1.075% | 117.0 / 13.970% | 550.7 / 14.414% |
| GIST normal | 84.0 / 0.118% | 301.7 / 0.865% | 58.4 / 0.098% | 210.5 / 1.516% | 657.4 / 1.671% |
| Deep normal | 55.4 / 0.437% | 162.7 / 3.478% | 31.4 / 0.400% | 194.3 / 6.154% | 389.1 / 6.814% |

GIST half B32 的 Faiss F256 K2048 微召回 **14.414%** 恰好达到 K 容量上限，仍漏掉 85.586% 真答案。其完整查询比例为 95.12%，因为半径较小且许多查询只有 self；去 self 后的非空查询宏召回为 81.57%。Deep normal 同配置微召回 6.814%、完整查询比例 **0%**。GIST normal 同配置为 1.671%、完整查询比例 19.24%。因此不能用完整查询比例或 Recall@10 代替微平均 RangeRecall。开发集桶审计显示 nlist4096 的 nprobe16/64/256 分别覆盖 43.5%/90.2%/100% 真答案；nprobe256 后 K 的输出容量成为主要限制。[range_quality.csv](range_quality.csv) 还列宏召回、低分位、漏检、容量上限和去 self 指标；其中候选真答案覆盖率与精算后的微召回相同，是在公共严格核验下推导的。GIST all 仅作边界：K1024/K2048 的微召回理论上限为 **0.1024%/0.2048%**，没有强行请求不支持的百万 K。

## 构建、剖析与界限

静态成本不算热查询响应时间。GIST 的 CAGRA 图构建六轮中位约 3.8 s，原始数据到 GPU 布局约 2.4 s；Faiss nlist4096 训练约 1.56 s、添加 1M 向量约 1.9 s，公共精算数据布局约 2.0 s。Deep 对应 CAGRA 构建约 2.3 s，Faiss 训练/添加约 0.30/0.85 s。全桶自定义 nlist1024 的 Faiss 训练/添加/导出 GIST 为 1.51/1.39/4.23 s，Deep 为 0.27/0.33/0.41 s；扫描器自身数据布局另列。[BUILD_COST.csv](BUILD_COST.csv)、[IVF_LAYOUT.json](IVF_LAYOUT.json)、[EXACT_SETUP.json](EXACT_SETUP.json) 有原始记录。

两条单独的 Nsight Systems 开发集 trace 确认实际 GPU kernel 活动：CAGRA trace 可见 `compute_similarity`、`kern_fused_prune`、`search_multi_cta`，Faiss trace 可见 `ivfInterleavedScan` 等。它们覆盖**建索引、预热、原生搜索及精算全进程**，因此 [profile_summary.csv](profile_summary.csv) 的 kernel 总时间不可当作查询阶段或热查询时延。[latency_breakdown.csv](latency_breakdown.csv) 的原生—精算差值也包括额外 D2H、CPU 过滤/排序，并非孤立的 GPU 核时间。Faiss Python 原生接口先把候选送回 Host，精算路径再送往 GPU，这个往返包含在测量中；更紧的设备端集成可能不同。

本轮 Faiss 1.15.1 是从官方 v1.15.1 源码按 CUDA 13.1、`sm_120` 构建的 **原生 GPU backend**，`FAISS_ENABLE_CUVS=OFF`；预编译 cu12 包在该卡报无可用 kernel，预编译 cuVS 包报 PTX/CUB 错误，均保留失败收据。没有把它们静默回退到 CPU。所有正式运行由目标 GPU UUID admission、NUMA 3 绑定，监测到的外来 GPU 进程数为零；缓存与时钟未人为固定。六轮新查询、静态索引、合法 K/nprobe 与实际软件版本见 [SOURCE_PINS.json](SOURCE_PINS.json)、[ARTIFACT_MANIFEST.json](ARTIFACT_MANIFEST.json)。[raw_remote_runs.tar.gz](raw_remote_runs.tar.gz) 保留命令、收据、原始日志/CSV、失败点和两条 profile trace；大结果二进制由 manifest 的 SHA256 及生成命令代替。

这些结论只适用于上述两套数据、库内新查询、这块 GPU、已测试的 Faiss/cuVS 后端及输出合同。候选方法没有达到 90% 范围微召回锚点，故不存在可与完整精确模式进行“同质量加速比”的本轮配置；若应用容许少量候选答案，它们的低时延仍是真实的质量—成本选择。
