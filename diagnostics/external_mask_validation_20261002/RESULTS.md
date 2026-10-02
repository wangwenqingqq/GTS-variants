# P5：外部完整范围基线与掩码因果验证

冻结起点为 `wangwenqingqq/GTS-variants@8cf31c448b968398207fe5a5eb358121be64c134`；生产路径没有修改。[CONTRACT.yaml](CONTRACT.yaml) 保留上传时的设计状态，本报告记录完成后的实际实验。测试是静态、库内查询、完整 L2 范围检索，不涉及 ANN 召回、kNN、在线排队或动态更新。机器为 `pro6000-8` 的 RTX PRO 6000 Blackwell，GPU UUID 和软件版本见 [ENVIRONMENT.json](ENVIRONMENT.json)。全部计时在独占 GPU、NUMA 3 下完成，缓存和时钟未人为固定。

## 结论

最强**同数值合同**对手因数据、半径和 B 而异：GIST half 是 P4 `C_MASK_E`，GIST normal B8 是 `SCAN_E`、B32 是 `C_MASK_E`，GIST all B8 是 `SCAN_L`、B32 是 cuVS `LIB64_U`（全半径仅以完整逐查询计数和有序哈希核对），Deep normal B8 是 `SCAN_E`、B32 是经完整输出审核的 cuVS `LIB64_X`。GIST half B32 时 `C_MASK_E` 对 `SCAN_E` 的六轮配对中位加速为 **1.162×**，6/6 轮胜出，精确配对 bootstrap 95% 区间 `[1.16178, 1.16244]`；对经过完整输出逐字节核对的 cuVS `LIB64_U` 为 **3.135×**。同一 `masked_distance<2,true>` 核验核函数的 `TREE_ALL_E`→`TREE_REAL_E` 在 GIST half 开发集把核验耗时从 52.347 降到 43.411 ms，DRAM 读量减少 2.140 GB、FP64 指令减少 208.6 M；`MASK_ALL_E` 本身没有带来加速，因此收益来自真实候选剪枝，而非仅换成掩码核函数。

## 合同与冻结

共同输出为每个查询的全部有效 ID 和 float32 距离，稳定地按查询顺序、`id_list` 顺序交付到 Host。严格参考把输入 float32 提升到 float64，以显式 RN 减法、乘法、逐维递增加法形成平方距离，关闭 FMA，判定 `sum64 <= RN(double(radius) * double(radius))`，距离为 `sqrt(sum64)` 后转 float32。外部适配器在同一 CUDA stream 上调用 cuVS C API `cuvsPairwiseDistance`，用共同收集器做阈值、压缩、偏移和全部有效载荷 D2H；并未使用 top-k 替代范围检索。`LIB64_U`、`LIB64_X`、`LIB32_U` 分别是 float64 L2Unexpanded、float64 L2Expanded、float32 L2Unexpanded。L2Expanded 捕获 CUDA Graph 失败，使用普通 stream；同一扫描器的 Graph/stream 配对差异在三轮内小于 0.11%，见 [stream_comparison.csv](stream_comparison.csv)。

开发查询先用于选外部模式和 `chunk_n`，然后才以固定种子抽取新的 GIST/Deep 各 1024 个最终 qid；与 P0–P4 已见 qid 的交集均为零，详见 [QUERY_SETS.json](QUERY_SETS.json)。选定 chunk 见 [frozen_external.json](frozen_external.json)，只有 GIST B32 `LIB32_U` 采用 262144，其余采用 1M。GIST 的 half/normal/all 半径位分别为 `0x3f34a3d8`、`0x3fb4a3d8`、`0x41cb7260`；Deep normal 为 `0x3f8a3818`。新 GIST all 的 1024 个查询每个恰好命中 1M 个数据点。

## 六轮正式 Host-ready 结果

每个数是同一组 1024 查询完整 ID+距离 D2H 的六轮总耗时中位数，单位 ms；B=8、32 按固定原顺序嵌套分批，正式计时 8 个开发批次预热，模式轮转。静态数据读取、AoSoA/有序数据布局、树重拟合不计入热查询；它们单独列于 [setup.csv](setup.csv)。批次 p50/p95、每查询摊销、QPS、六轮范围和配对比值可在 [summary_final.json](summary_final.json)、[paired_final.csv](paired_final.csv) 复查。批次耗时除以 B 仅是摊销值，并非单请求响应时延。

| 数据/半径 | B | SCAN_L | SCAN_E | C_MASK_E | LIB64_U | LIB64_X | LIB32_U |
|---|---:|---:|---:|---:|---:|---:|---:|
| GIST half | 8 | 5722.2 | 1825.7 | **1658.6** | 19112.0 | 11237.1 | 436.6 |
| GIST half | 32 | 5683.7 | 1773.8 | **1526.3** | 4786.4 | 2822.0 | 117.4 |
| GIST normal | 8 | 5743.6 | **4654.6** | 4702.0 | 19132.2 | 11278.9 | 439.0 |
| GIST normal | 32 | 5705.6 | 4581.8 | **4538.5** | 4804.3 | 2838.9 | 136.6 |
| GIST all | 8 | **6006.1** | 6038.4 | 6194.0 | 19376.7 | 11508.9 | 684.5 |
| GIST all | 32 | 6029.0 | 6052.2 | 6138.2 | **5103.4** | 3160.2 | 431.6 |
| Deep normal | 8 | 598.0 | **590.2** | 600.2 | 1937.2 | 1396.4 | 71.9 |
| Deep normal | 32 | 586.4 | 577.1 | 584.3 | 497.7 | **373.6** | 32.4 |

粗体仅标注在本次数值审核支持下的最快同合同模式。`LIB32_U` 虽通常快得多，但在最终 GIST half 有 1 个误报，GIST normal 有 86 漏检和 48 误报，Deep normal 有 15 漏检和 11 误报。`LIB64_X` 在 GIST half/normal 的成员集合相同，但各有 215 个距离字段超出事前固定容差 `1e-7 + 1e-5*|reference|`；它在 Deep normal 的完整 ID+距离审核中逐字节一致。GIST all 的逐查询完整计数、ID 顺序和字段的 64 位有序哈希用于比较，未物化每模式约 8.192 GB 的结果二进制，因此该行不声称已作逐字节全量审核。[numerical_qualification.csv](numerical_qualification.csv) 保留漏检、误报和字段差异；小规模 D=2/31/32/33/96/960 边界矩阵见 [boundary_qualification.csv](boundary_qualification.csv)。有限测试的通过不构成任意输入的浮点等价证明。

相对 `SCAN_E`，`C_MASK_E` 的六轮配对中位比值为 GIST half B8 **1.101×**（6/6，95% 区间 `[1.09874,1.10161]`，跨过 1.10 门槛）、B32 **1.162×**（6/6）；GIST normal B8/B32 为 0.990×/1.009×，all 为 0.975×/0.988×，Deep 为 0.984×/0.988×。按事前规定的“中位数至少 1.10× 且六轮都快”，half B8 和 B32 均通过优先扩展门槛；B8 的区间跨过 1.10，仅 B32 有稳定高于门槛的区间。其他档位不支持泛化的树加速说法。GIST half B32 与外部 `LIB64_U` 的 3.135× 是特定数据、半径和批量的比较，也不能与 P0–P4 历史收益相乘。

## 同核函数因果验证

开发集 GIST B32、256 查询、三轮中位 Host-ready 耗时如下。`S` 是强批量扫描，`M` 每批生成全 1 掩码，`TA` 与 `TR` 都执行真实树前缀及候选生成，只在运行时参数 `force_all` 上不同；后两者调用同一 `masked_distance<2,true>` 符号，grid `(1954,16,1)`、512 线程、32 寄存器和共享内存配置相同。掩码清零、树前端、收集、D2H 都纳入耗时。

| 半径 | S = SCAN_E | M = MASK_ALL_E | TA = TREE_ALL_E | TR = TREE_REAL_E | TA/TR | S/TR |
|---|---:|---:|---:|---:|---:|---:|
| half | 449.186 | 452.623 | 459.952 | 379.701 | 1.211× | 1.183× |
| normal | 1167.912 | 1176.593 | 1184.169 | 1155.834 | 1.024× | 1.010× |

在 half 的独立 Nsight Systems 开发查询 profile 中，距离核 S/M/TA/TR 分别为 51.913/52.315/52.347/43.411 ms，见 [profile_summary.csv](profile_summary.csv)。对 TA/TR 的相同距离核做 Nsight Compute application replay：DRAM 读量由 17.999 GB 降至 15.858 GB（-11.9%），L1 全局加载请求 164.944 M→146.805 M，L2 读扇区 569.870 M→502.533 M，FP64 指令 1.2095 B→1.0009 B（-17.2%）。这是单核 profiler 证据，不当作端到端读量；原始指标、编译与符号收据见 [ncu_summary.csv](ncu_summary.csv)、[MASK_KERNEL.json](MASK_KERNEL.json)。

在新 GIST half B32 最终查询上，候选账本统计 789,585,900 / 1,024,000,000 个待验 query-object 对（77.108%），真实候选与旧 strict walk 逐位置一致；双查询微块的 union 为 462,640,300、intersection 为 326,945,600，pivot 距离计算 940,930 次。账本与六轮计时分开运行，详见 [work.csv](work.csv) 与 [gist_half_candidates.summary.txt](gist_half_candidates.summary.txt)。

## 收据与界限

完成 8 工作负载 × 6 模式 × 6 轮 = **288** 个正式独占 GPU 进程；每个 `runtime_valid=true`，GPU UUID、二进制哈希、原始批次耗时和命中总数均已与表格逐项核对，期间记录的外来 GPU 进程数为零。原始 JSON/CSV/log、四条 Systems trace 在 [raw_remote_runs.tar.gz](raw_remote_runs.tar.gz)；大结果 `.bin` 已排除，SHA256 在 [PREFLIGHT.json](PREFLIGHT.json)。峰值显存、冷加载与静态布局成本分别见 [memory.csv](memory.csv)、[setup.csv](setup.csv)，例如 GIST half B32 的 `C_MASK_E`/`LIB64_U` 峰值分别为 8534/12268 MiB；全部结果搬运包含在热查询时间中。

由于只测试两套数据、库内新 qid、四种半径/B 组合和一块 GPU，此结论限于这些条件。cuVS 使用可比较的完整范围任务和共同输出路径，但数值模式不同的行必须遵守上面的数值资格。源码、依赖版本、散列、失败的 Graph 捕获处理和决策都保存在 [SOURCE_PINS.json](SOURCE_PINS.json)、[DECISIONS.json](DECISIONS.json) 与 [EVIDENCE_LEDGER.md](EVIDENCE_LEDGER.md)。
