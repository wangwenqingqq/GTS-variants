# P7-GATE 去留结果

**决策：STOP_CURRENT_KNN_PATH。** 在冻结的 GIST1M×960、库内 L2、K=8、B=32 切片上，当前 OPT-KNN-P7 的最快模式 O_MASK 经同流修复后仍约为 Faiss GPU Flat 的 **19.09 倍耗时**。现有 FP64 距离候选不足以通过一次组件替换使它接近 Flat，因此暂停这套一般静态 kNN 实现的继续投入。此结论不否定 P4–P6 范围查询结果，也不声称所有树或高维精确检索方向无效。

## 闸门结果

起点为 `wangwenqingqq/GTS-variants@bb22a970d61076c597084cfd0196d1ba5156f31f`；同流修复为 `d65c6e41effad67dde8ae1f1f68e656562607817`。G0 的 A→B→A 顺序回归在四种模式上全部通过，最后的 A 与首次 A 逐位一致；全体查询满足独立 FP64 oracle 的 tie-aware Recall@8、唯一合法 ID、距离字段门槛。详见 [G0.json](G0.json)、[IDENTITY.json](IDENTITY.json)。R1 正式计时和未更新的 pilot_v3 均未用作本轮分母。

G1 按合同次序执行 4 轮 × 4 模式，共 16 个独占 GPU、NUMA 3 的进程。每个进程均通过质量和运行资格检查；固定 32 条 pilot 查询，每进程两个不同开发批次预热。连续 Host-ready 包含输入、查询、结果转换、最终 K 个 ID 与距离回传及同步；静态载入、布局、refit、Graph 捕获和审计不计入，相关设置时间单列在 [latency.csv](latency.csv)。

| 模式 | 四轮 Host-ready 中位数 | 对 Flat 的同轮耗时比中位数 |
|---|---:|---:|
| FAISS_FLAT | 6.971 ms | 1.00× |
| O_FULL | 191.450 ms | 27.47× |
| O_BOUND | 137.281 ms | 19.69× |
| O_MASK | 133.049 ms | 19.09× |

O_MASK 相对 O_BOUND 只快约 **3.1%**，而自身仍远慢于 Flat，不能据此宣称树机制有竞争力。原值、同轮比值和逐进程质量收据见 [latency.csv](latency.csv)、[QUALITY.json](QUALITY.json)。

G2 为四种模式各采集一个 query-only Nsight Systems node trace；下面是 O_MASK 实际 Graph 重放的 GPU 活动归因，非 G1 的无 profiler Host-ready 计时：

| 阶段 | GPU 时间 |
|---|---:|
| 输入 | 0.000 ms |
| 种子（含种子 top-K） | 0.964 ms |
| 树与掩码 | 0.999 ms |
| `verify_distances` | 126.939 ms |
| 最终 top-K 与输出核 | 4.118 ms |
| D2H | 0.001 ms |
| GPU 活动间隙 residual | 0.158 ms |
| 活动跨度 | 133.179 ms |

阶段按重放时的实际核名、网格和先后顺序归类，未把 Graph 捕获时的 NVTX CPU 范围当作重放时间，也未把主机等待和其所等待的 GPU 核重复相加。[breakdown.csv](breakdown.csv) 和 [PROFILE_KERNELS.csv](PROFILE_KERNELS.csv) 保存四模式拆分与核序列。若把 `verify_distances` 假设为零成本，在其余阶段不变的诊断口径下，余量为 **6.240 ms**，低于 2×Flat；所以 G2 本身不能按预算闸门直接排除一次距离替换。

G3 只回放已有 P5 cuVS `LIB64_X` FP64 `L2Expanded` 距离路径，使用相同 GIST 数据和 pilot32 查询、B=32。测得最后一个批次的 pairwise 核合计 **91.010 ms**（8.321+82.689 ms）；其原有范围查询适配器的 Host-ready 为 101.456 ms，因回传全部范围结果，**不可当作 kNN 端到端时间**。仅将 pairwise 核替换进上述不变余量，且暂不计查询转换、适配与额外工作，账面值仍为 **97.251 ms / 6.971 ms ≈ 13.95×Flat**。该回放没有验证 kNN 成员质量，也没有完成 kNN 集成；它只证明这条现有候选远超本轮 1.25× 投入门槛。[intervention.csv](intervention.csv) 与 [INTERVENTION.json](INTERVENTION.json) 明确记录 `NO_INTEGRATION` 和未测字段。现有其他可直接接入且已满足同一 kNN 质量合同的距离路径未找到；本轮没有把裸 FP32、无安全边界的早退或另造混合精度路由当作合格替换。

按合同在没有可行单组件候选时停止：**G3 桥接 0/12，G4 新查询确认 0/24**，因此不存在独立 96 条查询上的 GO 证据，也不报告六轮正式胜率。使用预算为 G1 16 个干净计时进程、G2 4 个 trace、G3 1 条组件候选回放、NCU 0；未扩展数据集、K/B 或外部基线网格。结论只针对冻结切片与当前可用的一次组件替换路线。原始受限环境收据保留在实验 scratch；仓库交付仅包含脱敏摘要和哈希。
