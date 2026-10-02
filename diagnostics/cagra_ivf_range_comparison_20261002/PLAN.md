# P6：CAGRA / Faiss-IVFFlat 与高维精确范围检索的对齐对照

**状态：实验设计；未实现新增适配器，未运行新增 GPU 实验。**  
**日期：2026-10-02。**  
**项目起点：** `wangwenqingqq/GTS-variants@06570cd2e2857684984e43289d645b2b54903ae6`。这是本设计引用的 P5 快照，不声称后续分支没有新提交。  
**建议新增目录：** `diagnostics/cagra_ivf_range_comparison_20261002/`；不覆盖 P0–P5，不修改生产查询路径。

## 1. 实验要回答的问题

1. 在相同数据、查询、GPU、批量和完整交付计时边界下，CAGRA / IVF 为达到较高**范围结果召回率**需要多少成本？
2. 在完整覆盖与约定数值判定均满足时，安全树剪枝是否超过合理的扫描或 IVF 全覆盖执行？
3. 算法性漏检、候选输出上限、数值边界差异分别贡献多少？不能把三者混为“准确率不足”。

不要求 CAGRA 必须输，不以“GPU 图搜索一定比扫描慢”为假设。不把该对照等同于与 PDX、Buffer k-d Trees 等最近机制工作的差异证明。

## 2. 两张结果表，不能混成单一速度榜

### A. 完整范围检索主表

任务：在冻结的距离/半径合同下，交付每条查询的全部有效 ID 与距离。

保留 `SCAN_L`、`SCAN_E`、`C_MASK_E`，以及 P5 中实际通过相应数值审核的 cuVS 配置；native 但未通过合同的配置另列其性能及误差，不删除。

Faiss-IVFFlat 全覆盖对照必须满足：所有非空倒排桶、每条记录均被覆盖，无 `max_codes`、提前停止或输出 K 上限造成的截断。`nprobe=nlist` 是普通 IVF 的全覆盖设置，但仅把 top-k 搜索的 nprobe 调到 nlist，并不等于返回完整范围结果。完整覆盖还不意味着自动符合本项目的 FP64 边界判定。

CPU 的 `IndexIVFFlat.range_search` 可作为 CPU 参考/补充，不放进“同 GPU”主表。核对的 Faiss GPU 源码中 `GpuIndexIVF::range_search_preassigned` 抛出 `range search not implemented`；实施时必须再次冻结实际版本并做 smoke test。若需要 GPU 全范围适配器，使用 Faiss 构建的完整倒排桶，设备端枚举全部被选桶的全部 ID，再接公共核验与收集器，标为 **FAISS-IVF structure + custom GPU range executor**，不能标成原生 Faiss GPU range 性能。

若将来为 IVF 加入保守的桶级距离下界，应另命名为扩展方法、计入边界构建/筛选成本；不能冒充原生 Faiss。也不能只选全探桶退化配置来“证明 IVF 不如树”，须同时保留下面的探桶—召回曲线。

### B. 范围召回率—延迟对照

CAGRA 与 `GpuIndexIVFFlat` 可以先以原生 top-K 接口生成候选，再对**全部候选**采用公共参考距离核重算、按半径过滤、去重/保序与交付。

命名：`CAGRA_RANGE_ADAPTER(K)`、`FAISS_GPU_IVFFLAT_RANGE_ADAPTER(K,nprobe)`。二者是自建范围适配器，结果具有候选覆盖限制，不能称为原生完整范围 API。

不使用 native 返回的 FP32 距离先过滤候选再重算；否则可能先丢掉边界真答案。候选精算只能修复返回候选的字段和误报，无法恢复搜索遗漏或 top-K 截断的答案。

可加 CPU native IVF range 召回曲线，但明确 CPU 线程、NUMA、内存以及不同硬件，不能称同卡对比。

主表 A 与质量表 B 分开。即使图/部分探桶在测试集中达到 100% 召回，也只标为“测试集零漏检”，而不是一般输入的完整性保证。

## 3. 冻结的共同条件

| 项目 | 约定 |
|---|---|
| 数据 | GIST 1M×960D；Deep 1M×96D |
| 输入 | 原始有限 float32；不私自归一化、投影或量化 |
| 批量 | B=8、32；B=1只做 smoke/桥接 |
| GPU | pro6000-8，UUID `GPU-e5a0e7f5-9917-c2a1-ee8e-7282cbba2603`；执行前核验 |
| CPU | 固定并记录线程、CPU/内存 NUMA 绑定；CPU补充结果独立标注 |
| 内部配置 | Q_T=2；GIST C4、Deep C1；AoSoA32；保留现有父枢轴复用 |
| 场景 | GIST half / normal / all；Deep normal |
| 输出 | 原始对象 ID、每查询完整候选处理后结果；所有 ID 宽度转换、去重、排序或恢复共同顺序均计费 |
| 驻留 | 数据/索引热驻留 GPU；各方法可使用合理的原生布局；布局与建索引成本单列 |
| 公共资源 | 预分配工作区；无外部竞争任务；记录实际峰值而不强制各方法相同字节数 |

GIST 半径位：half `0x3f34a3d8`，normal `0x3fb4a3d8`，all `0x41cb7260`；Deep normal `0x3f8a3818`。

`METRIC_L2`、CAGRA/cuVS 的具体 metric、返回平方距离还是距离都要核对。Faiss 原生范围判定文档为 `distance < radius`；本项目为平方和 `<= radius²`。例如欧氏半径 2 对应平方距离阈值 4，而不是 2。严格小于与包含边界是合同差异；不能用一个随意 epsilon 同时掩盖接口和数值误差。

不强制 CAGRA/Faiss 内部 FP64、不禁止其成熟 kernel、缓存、共享存储等原生优化。保留 native 结果；共同参考重算模式另外计时。

## 4. 第一关：能力与接口检查

在 N=4096 / 4103、D=96 / 960、B=1 / 8 上验证：

- CAGRA build/search 真实在目标 GPU 运行；记录 cuVS 实际版本、图构建方法、图度数、搜索实现、合法 K / itopk 范围。
- Faiss 明确版本、编译选项、实际 CUDA/cuVS backend；`GpuIndexIVFFlat` 的构建、搜索、nprobe 设置真实生效。
- 分别检测原生 `range_search` / `range_search_preassigned`；继承自基类的函数名出现在文档里不等于可执行支持。
- 缺少接口、合法 K 限制、内存限制分别记为 `UNSUPPORTED_API` / `OUTPUT_BUDGET_LIMIT` / `RESOURCE_LIMIT`，不能记成算法“速度慢”或私自换到 CPU。
- 原生 CAGRA 若由 Faiss 包装 cuVS 调用，不重复宣称为两个独立算法。

## 5. 开发集调参：合理调强，不预设赢家

### CAGRA

优先不压缩原始数据库向量。先采用官方建议/默认图构建及 AUTO 搜索，再调 `itopk_size` 与 `search_width`；若高召回不足，再比较一个更大图度数。记录 `graph_degree`、`intermediate_graph_degree`、build method、iterations、搜索 algo、seed。

范围适配候选预算起始集合为 K=128/512/2048/8192，仅运行实际版本支持的值。`itopk_size>=K`，所有限制通过实际 smoke 验证。较大 K 不支持则记能力上限，不把低召回归咎于图探索。

### Faiss-IVFFlat

先测 IVFFlat，避免 IVF-PQ 额外量化混杂。开发 `nlist={1024,4096}`，`nprobe={1,4,16,64,256,1024,nlist}`；实际支持与全桶覆盖另行检查，不能绕过GPU限制而假称全覆盖。冻结训练样本和训练seed，不使用测试查询性能/ground truth调参。

K预算与 CAGRA 的候选适配器一致；同时保留IVF完整桶枚举/全范围版本，使 top-K 容量限制不被当作 IVF 分桶算法缺陷。IVF-PQ可在主对照完成后作为压缩参考，非本轮必做项。

### 冻结原则

开发目标召回锚点：90%、95%、99%、99.9%。选择每个算法实际达到对应开发范围召回率的最快配置，再在最终集测实际质量；没达到就明确报告，不插值伪造达标延迟。

允许在明显达不到锚点时逐级增加搜索预算；不无限重建/搜索配置，也不限制为默认参数。保留全部开发点、构建成本和失败点。每个方法L2阈值精算成本计入。

## 6. 候选容量上限：必须单独展示

假设真实半径内有30,000个答案，top-K只返回1,000个候选，即使这1,000个全对，范围召回率也至多3.33%。不能把它的低延迟与精确返回30,000个结果的延迟相除，写成同质量加速比。

对每条查询记录真实命中数m、候选预算K、候选实际数与容量上限 `min(K,m)/m`（m>0）。m仅用于离线评测，不能拿oracle的m指导测试查询运行时K。

若采用多轮扩大K，所有搜索、去重、精算与交付成本都计时；ANN 返回的最远候选距离超过r，并不能证明未访问区域没有半径内答案。第一版采用固定预算曲线，不引入新的自适应停止算法。

全命中场景以容量边界说明为主，不强迫图返回百万K、遍历全图来制造反面结果。若需要“CAGRA+补全扫描”，补全必须覆盖所有尚未被可靠排除的对象，明确是混合包装方案，而非原生CAGRA性能；本轮不把该包装作为必做项。

## 7. 正确性与质量指标

公共oracle沿用指定FP64参考；保留成员判定与距离字段两项审核。当前精确性相对于声明的计算合同，而非任意实数无误差运算。

必须记录：

- 非空查询的宏平均 RangeRecall，以及按答案数量加权的微平均；不以 Recall@10 替代 RangeRecall。
- 每查询范围召回的中位数、低分位、最小值；对1024个查询，这些只作描述性统计。
- 完整查询比例：结果ID集合完全等于oracle的查询占比；单独记录空结果错误，避免空查询抬高召回。
- false negatives / false positives / duplicate IDs / output truncation。
- 候选覆盖率（精算前）、精算后范围召回、字段差异、阈值边界错误类型。
- 当前库内查询含self match：主合同保持不变，另给去除self后的质量统计，避免稀疏场景被容易找回自身抬高召回；不能暗中改变正式输出。

同条件不是强制所有算法同样计算顺序：native允许其数值路径；共同精算统一返回候选的判定；结构性未覆盖与数值问题分开归因。采样100%不证明一般精确。

## 8. 计时与 breakdown

主计时：已就绪查询提交至完整被返回结果在主机可用。包括查询转换/H2D、粗量化或图导航、候选生成、候选gather、参考精算、阈值筛选、去重/排序、收集、数量反馈、ID宽度转换、全部有效结果D2H及同步。

raw native 与 common-refinement 作为两组测量：不得把前者计时配后者精度。返回答案少时的D2H减少属于质量—成本权衡，不能在不同召回率下宣称同结果优势。

补充分阶段：图导航/候选维护（接口可观察的范围）、IVF粗选桶/桶扫描、候选精算、输出；物理读取与距离次数按工具可获得性注明不可见项，不能凭索引大小猜访问量。正式计时无profile/计数插桩。

预热构建后搜索/JIT/工作区，8批开发查询；6轮独立进程，轮换模式和批次顺序。吞吐按完成查询数/总Host-ready时间算，B分摊时间不写成单请求响应延迟。静态训练、图构建、桶构建、布局、显存峰值、第一次调用单列。

## 9. 执行顺序与停止点

**P6.0：**能力smoke和合同校验，输出 CAPABILITIES.json；先确认GPU API真实可用，再安排大矩阵。

**P6.1：**GIST half、B=32、既有dev256。保留SCAN_E/C_MASK_E和P5强cuVS参照；加入CAGRA范围候选适配器、Faiss GPU IVFFlat范围候选适配器；跑参数—RangeRecall—Host-ready曲线。补IVF全覆盖能力检查。三轮开发比较，先不扩大数据。

**P6.2：**配置冻结后，用排除所有已见ID的新1024条最终查询，GIST half/normal、B=8/32与Deep normal、B=8/32确认。保留达不到召回锚点、最慢点、容量受限点。GIST all只作完整输出与候选容量边界检查，不编造不支持的大K配置。

**P6.3：**最终交三项：完整范围合同下性能表；各方法RangeRecall—Host-ready数据（含完整查询比例）；能力/数值/构建资源边界表。原生kNN的Recall@10/100可以另作附录，但若我们的方案没有正确实现同样的精确kNN，就不加入该速度排名，更不能将范围过滤的top-K当成全库kNN。

## 10. 预先约定的解释

- CAGRA/部分探桶IVF快但漏检：说明近似—精确权衡，不能宣布它们在同结果条件下胜出；也不据此说它们无价值。
- ANN在最终集经验零漏检且更快：诚实保留其工程优势，同时区分完整性保证；不能因它名为ANN而从图中删掉。
- GPU全覆盖IVF或数值处理完善的扫描更快：保留结果，缩小当前优势范围，不通过强制坏布局/小K/默认nprobe挽救结论。
- 索引少算距离但变慢：用实际访问、候选维护、精算、输出breakdown解释，不能直接断言“图不好”。
- API不支持/输出预算不足：说明比较边界，不作为通用算法优劣证据。

## 11. 证据来源（核对日期：2026-10-02）

[S1] 本项目P5报告：`wangwenqingqq/GTS-variants@06570cd2e2857684984e43289d645b2b54903ae6`，`diagnostics/external_mask_validation_20261002/RESULTS.md`。

[S2] NVIDIA cuVS CAGRA指南：`https://docs.nvidia.com/cuvs/user-guide/api-guides/indexing-guide/cagra`；官方定位近似kNN，支持以itopk_size等参数调节搜索预算。

[S3] cuVS CAGRA Python/C API：`https://docs.nvidia.com/cuvs/api-reference/python-api-neighbors-cagra`；公开search返回k个邻居，不是全量范围结果接口。

[S4] Faiss FAQ：`https://github.com/facebookresearch/faiss/wiki/FAQ`；IVFFlat nprobe=nlist退化为全覆盖扫描，须保留Flat竞争基线。

[S5] Faiss源代码核对：`facebookresearch/faiss@76c0e01e0f4db5f943b44cf85530e68efe29f355`，`faiss/gpu/GpuIndexIVF.h`与`faiss/gpu/GpuIndexIVF.cu`；range_search_preassigned未实现。该SHA是源码核对快照，不替代实验实际安装版本pin。

[S6] Faiss IndexIVFFlat API：`https://faiss.ai/cpp_api/struct/structfaiss_1_1IndexIVFFlat.html`；原始float向量、native range接口与严格小于阈值语义。
