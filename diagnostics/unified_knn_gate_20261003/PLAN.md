# P7-GATE：当前高维精确 kNN 实现的去留验证

**状态：DESIGN_NOT_RUN。** 本文是待执行计划，不包含新增 GPU 测量，也不代表已经完成任何替换。

**目标：** 判断当前 OPT-KNN-P7 是否存在一条有实测支持的、低成本接近成熟 GPU 精确扫描的路径；不是证明它比原始 GTS 快，也不是预先判定高维精确检索方向没有价值。

**本轮边界：** 一个主工作负载、四个基本模式、最多一次逻辑组件替换。任何继续结论只针对该工作负载的初步可行性，不是论文录用或普遍领先的证明。

## 0. 冻结起点与已有证据

- 检查日期：2026-10-03。仓库分支 `experiments/unified-knn-p7-20261003`，读取的 HEAD 为 `bb22a970d61076c597084cfd0196d1ba5156f31f`。
- 同流输入修复实现：`d65c6e41effad67dde8ae1f1f68e656562607817`。公开清单仍为 `R2_QUALIFIED_FORMAL_PENDING_R1_INVALIDATED`。
- 修复前 R1 正式时间以及未替换的 pilot_v3 先导不能用于本轮比值或决定去留。先导里约 133 ms 和 7 ms 只说明为什么需要复查，本文不将它们当作有效新基线。
- 保留范围查询 P4/P5/P6 的性能与因果证据；新 kNN 验证的成败不追溯撤销它们。
- 主生产代码、既有分支和历史记录不改写；新实验放独立 scratch/诊断目录。若执行时 HEAD 已变化，先记录差异，冻结一个明确版本，不能混用版本。
- 记录源、二进制、数据、索引、种子、查询、库、驱动、编译选项和实际设备 UUID 的身份。公开交付采用白名单和脱敏文本，不上传原始环境捕获、凭证、私有绝对路径。

## 1. 唯一首要问题

> 修复执行顺序后，当前方案相对 Faiss GPU Flat 的差距，能否通过一次有依据的主要组件替换显著缩小，而不放宽结果要求？

暂不测 CAGRA、部分探桶 IVF，也不重测原始 GTS：它们不是这轮决定是否救当前实现的必要分母。原始基线和 ANN 质量曲线都保留在历史账本中。

## 2. 冻结工作负载与四个模式

| 项目 | 本轮固定内容 |
|---|---|
| 数据 | GIST 1,000,000 × 960，使用既有相同数据哈希 |
| 检索 | 静态、库内、含自身的 L2 kNN |
| K / B | K=8，B=32 |
| 诊断查询 | P7 已有先导的同一组 32 条已见查询；从原调度元数据取得真实路径，不自行编造文件名 |
| 预热 | 两个固定、不同的开发批次；不得用 oracle 选容易批次 |
| 自有实现 | O_FULL、O_BOUND、O_MASK；AoSoA32、Q_T=2、4096 个相同种子、C4 不调参 |
| 外部 | FAISS_FLAT：当前已部署原生 GpuIndexFlatL2，useFloat16=False，use_cuvs=False |
| 输出 | 每条恰好 K 个不同合法 ID 及 float32 欧氏距离；距离有序、有限、非负 |
| 主指标 | 连续 Host-ready：从提交已就绪的这 32 条查询，到主机收到全部 32×8 条结果 |
| 静态成本 | 数据/索引载入、refit、布局、Graph 捕获单独记录，不计热查询；动态种子、掩码、选择、交付必须计入 |

O_FULL 是优化全表计算加 top-K；O_BOUND 在运行时由种子计算上界并允许早退；O_MASK 进一步使用浅层树掩码。三者是实验移植版，不称生产 GTS++。

**不同算法可用自己的布局和数值实现，不要求 Flat 全 FP64。** 统一任务和结果门槛，不强迫对手照抄我们的慢实现。

## 3. G0：正确性和计时资格先过关

### 3.1 执行顺序

检查自有 H2D、Graph、D2H、完成同步位于同一显式流，或有可靠跨流事件依赖。外部 Flat 的 gather、search、转换和回传也要检查实际 stream；当前代码使用 Faiss null stream 与 CuPy null stream，不能只看函数是否返回。

额外做 A→B→A 两组不同查询输入的顺序回归；最后一次 A 的答案必须与参考一致。不得通过一直重复同一个查询掩盖旧数据问题。

### 3.2 结果门槛

使用已有独立全表 FP64 oracle 与补充字段检查，均在计时外运行。

- 每条查询 tie-aware Recall@8=100%，允许参考平方距离真正相等的边界替代；不使用 epsilon 将不同距离算成并列。
- 必须恰好输出 K 个不同、合法 ID，无缺槽、重复、NaN 或 Inf；交付字段有限、非负、有序。
- 沿用原 kNN 字段门槛：`abs(delivered_distance**2 - reference_squared) <= 5e-5 * max(1, reference_squared)`。另报纯相对误差、近零误差和确定性 ID 召回；不能把字段容差用于成员正确性。
- 每个计时进程均校验，不只验证第一轮。自有剪枝仍需要覆盖安全理由；有限测试通过不是任意输入证明。
- 已有 28 组资格与 12 项 sanitizer 只有二进制和相关代码身份匹配时可作为继承依据。任何新组件都须补尾块、并列、零距离、上界边界、哨兵 Inf 和内存/同步检查。

Flat 若在声明工作负载上未通过，不把慢方法宣布为赢家，也不临时改变门槛；标为 `QUALITY_NOT_ALIGNED`。可以保留其 native 性能并单列数值问题，但不能继续计算同质量去留比值。

## 4. G1：修复后四模式复测——16 个计时进程

四种模式各四个独立进程，每进程两个固定预热批次，然后一次完整 32 查询 pass。模式次序固定如下（F=O_FULL，B=O_BOUND，M=O_MASK，L=FAISS_FLAT）：

| 轮次 | 模式顺序 |
|---|---|
| 1 | F, B, L, M |
| 2 | B, M, F, L |
| 3 | M, L, B, F |
| 4 | L, F, M, B |

保持同一物理 GPU、主机/内存绑定和无外来 GPU 任务；不修改其他服务、时钟或功耗。进程失败、外来活动、结果失败原样保存，不补一个更快样本。需要重做时整轮标明新版本，超出本轮预算则输出 INCONCLUSIVE，不无限重跑。

至少输出：

| 模式 | 4 次 Host-ready 原值 ms | 中位数 ms | 与 Flat 同轮耗时比 | 每条查询全对 | 字段通过 |
|---|---|---:|---:|---|---|
| O_FULL | 待测 | 待测 | 待测 | 待测 | 待测 |
| O_BOUND | 待测 | 待测 | 待测 | 待测 | 待测 |
| O_MASK | 待测 | 待测 | 待测 | 待测 | 待测 |
| FAISS_FLAT | 待测 | 待测 | 1.0 | 待测 | 待测 |

比值方向固定：`slowdown_vs_flat = T_method / T_flat`。2 表示我们慢 2 倍；0.8 表示我们的耗时为 Flat 的 80%。不以原始 GTS 作去留分母。

若修复后的最佳自有路径已经不超过 Flat 的 1.25 倍，可跳过组件替换，直接进入 G4 的独立确认；这仍不是已赢外部基线。

## 5. G2：只定位主成本，先判断一次替换够不够

### 5.1 独立 query-only breakdown

对上述四种模式各做一次查询阶段 Nsight Systems 记录，总计四个 trace；禁止使用建库/预热/Graph 捕获阶段总计。

| 阶段 | 包含什么 |
|---|---|
| input | 查询 gather、H2D 和输入依赖 |
| seed | 4096 个对象距离、种子 top-K、上界生成 |
| tree_mask | 树界计算、遍历、清零、候选掩码 |
| verify | 全维或早退距离计算及分数写出 |
| final_topk | 最终局部前 K、逐层归并、最终 ID/距离生成 |
| delivery | 最终 K 的格式转换、D2H，以及未重复计算的主机收尾 |
| residual | 尚无法归类的时间，单列而不是塞进 CPU 或 PCIe |

**Graph 陷阱：** 目前若干 `seed/tree_mask/distance/topk_merge` NVTX 范围包在 Graph 构造调用里，不能直接拿这些 CPU 范围持续时间解释 Graph 重放。用实际 query-pass 的 Graph 节点/核名/依赖拓扑映射归因；先用 `nsys profile --help` 核对本机支持 `--cuda-graph-trace=node`。若无法映射 seed 和 final 中同名 top-K 核，使用专门阶段标识或独立顺序执行诊断版，并报告该版对执行的影响。

Profiler 的包含时间可能重叠且有插桩成本，不能用 profiler 的总时间替代 G1 的干净延迟；`cudaStreamSynchronize` 等等待时间不能与所等 GPU 核重复相加。Flat 若距离与选择融合，记为 fused_distance_select，不强拆虚假的单项。GPU 时间覆盖不是 SM 利用率。

必要时仅补两个 NCU 目标：自有主要核与 Flat 主要核，核对 DRAM 读写、FP64/FP32/SASS 指令、寄存器/spill、活动线程和等待；实际指标名从安装版本查询。使用一致的缓存/重放策略、不修改用户 GPU 时钟；完整查询速度仍以无 profiler 运行计。

### 5.2 先算“只修一项”的乐观估计

在相同诊断时间口径内，将目标组件暂按零成本计算：

`optimistic_remainder = current_total - target_component`

这只是**其余阶段成本不变**的账面估计，不是所有可能重构的理论下界。必须说明缓存、并行和融合改变可能影响其他成本；不得从重叠 API 时间中做减法。

假设（不是新结果）：

- 当前 100 ms，其中距离 85 ms，其他 15 ms；Flat 5 ms。即使距离免费，仍有 15 ms，即 3 倍 Flat。只换距离核不能把当前流水线救到近似持平。
- 当前 100 ms，其中 top-K 96 ms，其他 4 ms；Flat 5 ms。替换选择器具有算术空间，但还需测真实替换后时间。

**研发闸门：** 若任一允许替换的单组件免费后，剩余成本仍大于 2×Flat，停止本轮单组件救援并记录证据；不继续调树深、块大小，也不将这一结论扩大为整个研究方向不可能。

## 6. G3：最多选择一个组件，做真实替换

先写 `INTERVENTION.json`，固定目标、候选实现、版本、预计节省与质量约束，再看替换结果。最多两种固定候选做一次组件回放筛选，只把其中一个集成；失败后不再切第二条研究方向。

### 分支 A：若 top-K/归并占大头

1. 从正常执行中保存该批查询在最终选择前的**完整 FP64 分数矩阵**、位置到原 ID 的映射；包含被排除对象的 Inf。保存不在正式计时中。
2. 在同一分数上回放当前选择器和一个/至多两个可用成熟 FP64 选择/排序实现。可从已安装 CCCL 的 CUB radix 排序组件开始，先确认实际模板、容量、Inf、尾块和关联 ID 支持。cuVS 的 k-selection 不应被默认假定支持当前版本的 double。
3. 输出分数及成员必须一致或仅有合法边界并列；若更换 tie 顺序，主表仍用事前登记的 tie-aware 标准，确定性 ID 差异单列。不能把 double 转 float 来制造排序加速。
4. 只替换这一逻辑选择组件，并在所有 O_* 的对应调用点公平接入；若种子 top-K 也复用该组件，改动同样应用于 O_BOUND 和 O_MASK，保持种子数值上界一致。
5. 将实际运行矩阵产生、选择工作区、归并、转换、D2H 重新接回完整查询计时。**使用缓存分数直接输出答案的回放不计端到端收益。**

若替换只有局部改善而无法接近强基线，停止；不立即再优化距离核作为第二次补救。

### 分支 B：若距离计算占大头

1. 对固定、相同 query-object 工作量执行回放，区分访问组织和算术路径。主候选应是已有、可接入、满足声明质量要求的距离实现；没有这种候选时，本轮输出“未找到可验证的替换路径”，不再泛泛承诺重写。
2. 可使用既有 cuVS FP64 距离适配资产作为一个有限候选；不能假设它必然更快。外部密集计算若不能保留稀疏掩码，应明确记录全量额外计算及适配成本，不能声称保留了剪枝节省。
3. 裸 FP32 与关闭 FMA 限制等仅可作为**诊断对照**；它们不自动获得新方法资格。需要满足同一结果合同，尤其不能在 FP32 上直接套用未经误差包围的早退拒绝规则。
4. 不在本轮新造混合精度安全路由、不扫描 Tensor Core 配置、不改变距离任务。若只有一条尚无安全性的低精度路径快，结论是当前严格逐维实现路线未通过，不是直接放松精确性。
5. 唯一候选通过后，完整集成并重测 O_FULL/O_BOUND/O_MASK；需要新增转换、矩阵落地或边界回退时全部计入。

### 分支 C：若没有一个主组件能承担差距

若距离与选择都远高于 Flat，或树/种子等成本共同阻止接近，停止当前单组件救援。本轮不演变成重新设计整套搜索系统。

### 替换后的桥接预算

对三个采用同一逻辑替换的自有模式和 Flat 运行三轮，共 **12 个计时进程**。桥接只筛可行性，三轮不能当正式稳定性证明。所有结果按旧门槛逐轮校验。

只有最佳自有路径的成对耗时中位数不超过 Flat 的 **1.25倍**，才进入 G4。否则输出 STOP_CURRENT_KNN_PATH 并保留改进和负向结果。1.25 是本轮预先选择的投入门槛，不是学术录用标准或自然常数。

## 7. G4：独立查询上一次确认，不继续调参

冻结代码、选择器/距离组件、库配置之后，生成 96 条未被用来调试/看过性能的库内查询，排除所有已见 query IDs；保留随机种子与清单。它们只提供该数据集下的初步独立确认，不替代外部查询或其他数据集。

三组嵌套 B32 批次，比较四模式（O_FULL、O_BOUND、O_MASK、Flat）六轮，总计 **24 个计时进程**。若未做组件替换则沿用修复后原版本；若做过替换，三个自有模式使用同一改动。

六轮采用三个明确互为逆序的模式对，并对同一轮各方法使用同一查询批次顺序。默认：

1. F, B, M, L
2. L, M, B, F
3. B, L, F, M
4. M, F, L, B
5. M, B, L, F
6. F, L, B, M

每轮记录 96 查询完整总时间、三个批次的时间、每查询质量；最终只将总时间除以 Q 当作摊销，不称单请求时延。样本不足，不宣称可靠在线 p99。

## 8. 去留判定：分开实现价值与树机制价值

所有门槛均为**本次研发决策建议**，必须在实验前冻结。没有跨过门槛，不得事后改门槛、换数据或只选最有利查询。

### 8.1 整套实现的竞争力

用同轮 `T_candidate/T_Flat` 计算，结合所有原始轮次而非最快一轮：

| 独立确认结果 | 决策 |
|---|---|
| 至少有一个自有模式 ≤0.90×Flat，六轮更快，质量全通过 | GO：当前切片有竞争证据，才申请扩大实验；仍不等于新颖性成立 |
| 最佳自有模式介于0.90×与1.25×Flat | 只进入机制价值判断，不宣称外部领先 |
| 所有自有模式 >1.25×Flat，或没有稳定结论 | STOP_CURRENT_KNN_PATH：暂停这套一般静态L2 kNN竞争实现，保留资产 |
| 仍 >2×Flat | 强停止信号；不要继续为数个百分点的树收益调参 |
| 任一必要质量/身份/计时门槛不通过 | INCONCLUSIVE / QUALITY_NOT_ALIGNED：不能报有效加速，也不能归因算法失败 |

### 8.2 树本身的价值

比较 O_MASK 与**同一执行基础的 O_BOUND**，并且还要比较最快无树路径 O_FULL/O_BOUND：

- `T_O_BOUND / T_O_MASK >=1.10`，六轮均快，且 O_MASK 不慢于 O_FULL；若同时 O_MASK≤1.25×Flat，可以**条件保留树组件研究**，不是已胜过外部系统。
- 树增益很小或 O_MASK 不及最快无树模式：暂停树＋掩码的 kNN 主张；扫描/选择组件若有效可以保留。
- 树在慢底座上仍快10%但整体显著慢于Flat，不算通过继续条件。
- 若只有O_FULL接近/超过Flat，结论是扫描底座有价值，不用它替树贡献背书。

不能把 STOP 写成“所有树没有用”或“精确高维没前途”。它只终止当前实现/当前投入方式；范围查询证据仍保留，未来新机制须另有明确假设才能申请新预算。

## 9. 总预算与不做事项

- G1：16 个干净计时进程。
- G2：4 个 query-only NSYS；必要时最多2个 NCU 目标，以及最多2个固定输入组件候选回放。均不作为性能分母。
- G3：仅一次逻辑组件替换，12 个干净桥接计时进程；没有可行候选直接停止。
- G4：只有过闸才运行，24 个确认计时进程。
- **最大有效性能计时预算：52个进程。** 不包含必要的小规模正确性/sanitizer；执行失败不自动增加预算。
- 不运行新CAGRA/IVF参数网格，不比较原始GTS累计倍率，不扩K/B/数据，不做查询重排、动态策略、新图、新树或混合精度研究，不完整重做P7数百条件。

## 10. 最小交付

交付三张表和一个有明确状态的决定即可：

1. `latency.csv`：phase、round、mode、source/binary/query hash、Host-ready、质量门槛、与Flat比值。
2. `breakdown.csv`：输入、seed、tree_mask、verify、final_topk、delivery、residual；注明 Graph、profiler 和计时范围。
3. `intervention.csv`：唯一替换前后目标时间、完整时间、剩余成本估计、质量、内存和适配开销。
4. `DECISION.md`：GO / CONDITIONAL_COMPONENT_ONLY / KEEP_SCAN_DROP_TREE / STOP_CURRENT_KNN_PATH / INCONCLUSIVE，引用具体结果，不只写“后面再优化”。

任何空白填写 `NOT_MEASURED`，任何失败保留原始身份与理由。旧成果不删除，修订后的结果也不覆盖作废记录。

## 11. 来源（用于事实核对，不代表新实验已执行）

[S1] P7 MANIFEST：https://github.com/wangwenqingqq/GTS-variants/blob/bb22a970d61076c597084cfd0196d1ba5156f31f/diagnostics/unified_knn_e2e_20261003/evidence/MANIFEST.json

[S2] P7 实际Graph与计时调用：https://github.com/wangwenqingqq/GTS-variants/blob/bb22a970d61076c597084cfd0196d1ba5156f31f/diagnostics/unified_knn_e2e_20261003/opt_knn_bench.cu

[S3] P7 当前256点局部排序与分层归并：https://github.com/wangwenqingqq/GTS-variants/blob/bb22a970d61076c597084cfd0196d1ba5156f31f/diagnostics/unified_knn_e2e_20261003/knn_select.cuh

[S4] P7 原生Flat输入/输出桥接：https://github.com/wangwenqingqq/GTS-variants/blob/bb22a970d61076c597084cfd0196d1ba5156f31f/diagnostics/unified_knn_e2e_20261003/native_knn.py

[S5] P7 质量与数值合同：https://github.com/wangwenqingqq/GTS-variants/blob/bb22a970d61076c597084cfd0196d1ba5156f31f/diagnostics/unified_knn_e2e_20261003/knn_reference_contract.md

[S6] NVIDIA Nsight Systems User Guide，focused profiling、Graph node tracing及其开销：https://docs.nvidia.com/nsight-systems/UserGuide/index.html

[S7] NVIDIA Nsight Compute CLI，application replay、cache/clock control：https://docs.nvidia.com/nsight-compute/NsightComputeCli/index.html

[S8] NVIDIA CCCL CUB BlockRadixSort，原始数值类型含double与关联负载；执行时核对本机版本：https://nvidia.github.io/cccl/unstable/cub/api/classcub_1_1BlockRadixSort.html

[S9] NVIDIA cuVS k-selection，功能说明，不推定安装版本有double重载：https://docs.nvidia.com/cuvs/user-guide/api-guides/other-ap-is/k-selection

[S10] Faiss indexes，IndexFlatL2的穷举性质：https://github.com/facebookresearch/faiss/wiki/Faiss-indexes
