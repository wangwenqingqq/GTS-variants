# P5：外部强基线与同核掩码因果验证

日期：2026-10-02
冻结仓库：`wangwenqingqq/GTS-variants@8cf31c448b968398207fe5a5eb358121be64c134`
建议新增目录：`diagnostics/external_mask_validation_20261002/`
状态：**实验设计；P5新增适配器与对照未实现，P5未运行，无新增GPU结果。**
配套配置：`GTS_P5_contract_20261002.yaml`，是约定文件，不是可直接启动的runner。

## 0. 本轮的唯一主问题

**已有的精确、高维、批量范围查询方案，相对强外部扫描是否有净优势；其中树的额外优势，是否真的来自少做了核验，而不是恰好换了一个更快的kernel形态？**

这是对既有成果的竞争与归因验证，不再开发一套新检索系统。单查询仍是基础回归点，多查询是主测范围。暂不增加树深、查询微块、检查间隔、TASK调优、查询排序、PCA、图、Tensor Core、量化、在线凑批和多GPU变量。

本轮先完成两个交付：一张外部同任务竞争表，一张同kernel掩码因果表。外部库尚不能运行时，内部因果实验可以继续，但P5竞争验证状态必须保持未完成。

## 1. 已有事实与继承规则

P4记录的GIST half、B=32、1024条查询总Host-ready中位数为：SCAN_E 1775.1 ms、C_MASK_E 1521.8 ms、C_TASK_E 1515.3 ms。MASK相对SCAN的配对中位加速为1.16657×；TASK相对MASK只有约0.4%的时间差。GIST normal收益未超过预设3%区分门槛，全命中无收益，Deep C1没有超过扫描。Tloc B32有正向结果，但B1的冻结TASK路径退化。[R1]

已测内核表明：C_ID使用单查询候选核，MASK使用两查询微块；两者比较不是纯粹的布局或候选压缩单因素消融。[R2][R3]

据此冻结以下角色：

| 角色 | 本轮处理 |
|---|---|
| SCAN_L、SCAN_E | 保留并同轮重测；外部比较不只对着更弱的一个 |
| C_MASK_E | 主要组合候选；GIST用C4，Deep负向检查用C1 |
| C_TASK_L/E | 保留全部P4收据和适用边界；不继续为0.4%差异调优 |
| 父枢轴复用、保守节点界 | 继承；核对实际pivot ID相同时才共享 |
| AoSoA32、Q_T=2、512线程、每32维早退 | 继承，不扩大搜索空间 |
| 并行稳定收集、按有效长度交付、CUDA Graph | 公共基础，不重复计算为P5新增贡献 |
| 历史PCA、快速筛查、单查询树与布局实验 | 原口径归档；不相乘，不因P5结果覆盖 |

**历史时间只用于说明动机，不作为新查询、新库或新二进制的速度分母。**

## 2. 范围、查询与资源

### 2.1 主范围

- 主数据：GIST 1,000,000×960、原始finite float32。
- 复验：Deep 1,000,000×96、普通半径。
- 主批量：B=8、32。B=1只做小样例及桥接，不扩B=128。
- GPU：pro6000-8，UUID `GPU-e5a0e7f5-9917-c2a1-ee8e-7282cbba2603`。运行前记录真实model/driver/toolkit/库版本，不能只照抄历史。
- 主机：继续核验该GPU对应NUMA节点。历史为节点3；仍需运行前确认，不改变全局驱动、功耗或时钟策略。
- 任务：静态、库内L2范围查询；结果按输入查询顺序、每查询按id_list顺序返回全部ID与float32距离，无top-k截断。

| 数据集 | 半径 | float32位模式 |
|---|---|---|
| GIST | half | `0x3f34a3d8` |
| GIST | normal | `0x3fb4a3d8` |
| GIST | all | `0x41cb7260` |
| Deep | normal | `0x3f8a3818` |

新查询上的all档要独立检查是否真的全命中。若不满足，保留失败并事前调整为覆盖数据的统一保守半径；不能偷偷改oracle或继续称为全命中。

### 2.2 查询集

先用已有dev256调试和小范围外部参数选择；P4 final1024保留作已知回归集。两个集合都不能重新称为未见测试。

外部库版本、数值合同、块大小、内外部配置都冻结后，每数据集再生成1024条新查询：GIST seed=2026100205、Deep seed=2026100206，排除所有历史、P0–P4开发/正式查询ID。记录实际排除并集和SHA-256，不能只在说明中声称互斥。

随机顺序固定，B=8、32嵌套切分，原两查询微块配对固定；不按oracle命中数、候选相似性或运行时间重排。重复查询仅用于正确性测试。

### 2.3 资源与静态成本

建议统一workspace预算8 GiB、pinned输出预算4 GiB，数据、布局、树和静态FP64副本单独记账。对每条路径检查实际峰值，不强制外部同时保留所有未使用dtype副本。

库允许使用适合自身实现的连续布局，不能强迫它处理自有AoSoA32。数据库可在准备阶段按id_list预排列；输出时通过同一个id_list还原ID，无须每查询排序。静态重排和数据提升成本记录为冷成本。

所有路径的每查询gather、query dtype提升、临时距离生成、阈值判定、格式转换、compact、feedback、D2H和同步必须计入主时间。

## 3. P5-A：优先完成外部强基线

### 3.1 安装不是实验结果

P4中的cuVS安装只是依赖下载未完成，不是运行不兼容或性能失败。[R1]

在独立环境或独立C++前缀中安装，不改生产环境。先根据官方安装说明核对可用版本和依赖，再冻结实际版本，不将历史尝试的包版本自动当成已安装或当前最佳版本。[D4]

下载、安装、链接/导入、执行一次小矩阵距离计算分四项记录。下载使用缓存或本地wheel目录，避免每次删除已下载内容；下载失败应记录实际日志、包名、bytes、网络错误，不能用一次短时中止认定库不可用。

优先把C/C++库接入公共C++runner及stream，避免Python逐块调度对比C++ Graph造成偏差。Python可以用于环境探测或初步烟雾测试；若最终只能通过Python运行，内部候选也提供相同语言边界，且标明调用开销。

环境关卡通过条件：

1. 真实GPU设备上执行小矩阵；输出形状、dtype、平方/非平方距离单位均验证。
2. 记录cuVS/RAFT或相关依赖、编译器、CUDA、driver、linkage与库路径；保存命令与包/源码hash。
3. 检查是否有每次调用分配、隐式同步、自动copy或自动dtype变化。
4. Graph支持先实测；不支持时额外增加公共stream比较轨，不能只取消外部Graph而不说明。不在capture中调用未支持API。

### 3.2 最少筛选哪些库内实现

官方C++ pairwise_distance有float和double、连续行/列布局接口，并区分L2Unexpanded与L2Expanded。[D1] Python文档把`sqeuclidean`映射为L2Expanded，不能把该字符串当作直接逐维差平方和。[D2]

开发集小范围测试以下已支持组合；若某组合实际版本不支持，记录明确状态，不编造调用：

| 候选 | 算术路径 | 作用 |
|---|---|---|
| LIB64_U | double + L2Unexpanded | 与直接差平方距离较接近的外部数值参照 |
| LIB64_X | double + L2Expanded | 避免仅选较慢的double实现 |
| LIB32_U | float + L2Unexpanded（若支持） | 原生float扫描对照 |
| LIB32_X | float + L2Expanded | 强原生扫描对照，不先用固定FP64合同把它排除 |

每条路径要写明input/storage/accumulator/output dtype、是否FMA/TF32等数学模式、实际metric枚举和kernel。不能仅由名称推断使用Tensor Core或某一种归约。

随后冻结两个外部配置：

- `LIB64_FROZEN`：开发集选定的double配置；数值资格单独记录，不因double标签自动获得严格资格。
- `LIB_NATIVE_FROZEN`：开发集选定的原生float配置。

在同一数据集、同一B上，以GIST half+normal总Host-ready成本或Deep normal成本选择布局/块大小/metric；配置对最终查询与三档半径保持不变。数值不兼容的更快结果仍保存为native参考。若最快与严格可对齐的配置不同，两者均保留，可增加一个明确标识的严格对齐行。

### 3.3 比较完整范围查询，不比较孤立距离矩阵

执行链：

`准备当前批查询 → 库pairwise平方距离 → 半径阈值判定/命中距离sqrt → 公共保序收集 → 回传offsets → 回传全部有效ID和距离 → 同步完成`

库输出先进入公共flags/raw_distance接口，复用P4的稳定收集器和交付计时。不得只回传count，不得拿top-k替代范围查询，不得在CPU扫描一个巨大的GPU距离矩阵来人为拖慢外部对照。

对库筛选以下数据库分块上限：65,536、262,144、1,000,000个对象。不得预设必须很多小块；B=32时一百万对象的double距离矩阵约256 MB，float约128 MB，通常值得把整矩阵作为开发候选，而不是故意只测小块。实际能否使用由统一workspace预算和库临时空间决定。[D3]

距离矩阵显存预分配，块间不强制主机同步，判断并转换结果也在设备上。每个块的索引偏移保证还原到同一id_list位置。静态数据库double提升可常驻并单列成本；动态查询提升必须计时。

若库还提供可直接满足全部范围结果与距离字段的更强融合接口，可作为额外竞争行，但须先审计真实任务与数值接口。不能把本轮胜过某个pairwise适配器扩大成胜过所有cuVS功能。

### 3.4 公平数值资格：两张表，不互相混淆

**表A：严格因果/回归表。**保留指定FP64逐维RN减、乘、加，不改变维序，不启用融合。内部ID、顺序与float32距离字段应与冻结参考逐字节一致。

**表B：全量扫描竞争表。**外部是枚举全库的扫描，不因为浮点路径不同就称作ANN。分别报告：

- 漏检ID数、误报ID数；不只报告舍入到100%的recall。
- 重复/截断与输出顺序。
- 命中距离绝对/相对/ULP差异、最大值及非有限值。
- 半径边界和zero/self/duplicate等特殊输入的表现。

外部输出资格分为：`BITWISE_MATCH_ON_TESTED`、`MEMBERSHIP_MATCH_FIELDS_WITHIN_FROZEN_TOL_ON_TESTED`、`CONTRACT_MISMATCH`。如果采用距离字段容差，建议事前冻结 `abs_error <= 1e-7 + 1e-5*abs(reference_distance)`，同一竞争表对所有方法适用；**成员判定仍不允许误报/漏检**。这是有限测试资格，不是任意输入的数值证明。

仅距离末位不同不等于漏检；需要另查原因，也不能凭dtype判定结果是否精确。若成员判定有差异，不能混入同合同胜负表，也不能删除更快的native数据。假如要做认证边界回退，应针对该实际计算路径建立有效包围界，所有不确定对象重算且代价计入；仅重算已返回命中无法修复漏检。**本轮不要求另开一套混合精度科研路线，无可靠误差界时如实留出数值差异，不使用经验radius+epsilon。**

## 4. P5-B：最小同核因果验证

### 4.1 四个模式

只用GIST half与normal、B=32、原dev256，先跑E版本。四模式使用相同数据、查询配对、输出路径、设备和编译构建。

| 模式 | 是否执行真实树 | 送入masked_distance的掩码 | 用途 |
|---|---|---|---|
| S=SCAN_E | 否 | 无 | 原强扫描，必须保留 |
| M=MASK_ALL | 否 | 对全部有效对象为1 | 判断单纯换成masked核形态造成多少变化 |
| TA=TREE_ALL | 是 | 树算完后强制全部有效 | 测树前置成本，但不让它获得剪枝收益 |
| TR=TREE_REAL | 是 | 真实树候选掩码 | 完整算法效果 |

TA、TR必须调用**同一个**`masked_distance<2,true>`符号、同样grid/block/shared配置。掩码必须是运行时数据，不能通过template常量把ALL版本编译成另一个核。

TA与TR都运行同一真实前缀遍历和候选生成。推荐只在候选生成kernel增加一个运行时`force_all`参数：读取真实节点存活标志，写入`raw_keep | force_all`，并正确排除越界槽位。两个模式执行相同的mask生成代码，不允许TA直接跳过树。核对代码生成，若优化导致一侧不读raw标志，必须记录并控制这项差异。M自己每批生成/填充全1掩码并计时；不使用上一批残留。

所有掩码路径每批清零输出flags，负半径保持空结果，尾查询/尾对象不得置为有效。全1不是全部命中：仍需完整或早退距离判定，不能直接输出全库。

TA是无用工作控制，不是可部署的竞争算法。不得用TA作为对外速度分母夸大优势。

### 4.2 每组比较回答什么

- S vs M：无剪枝时，masked核、读mask、清零/填充等整体结构改变的代价；不能全部叫作“掩码一次读取的成本”。
- M vs TA：额外真实树前置与mask准备的净代价，含其缓存影响；不是严格无干扰的纯遍历时间。
- TA vs TR：同一核验kernel中，改变掩码所带来的实际核验节省；两边已支付相同树阶段。
- S vs TR：计入真实前置成本后的端到端优势，最终是否值得用树。

以距离kernel事件时间单独检查TA→TR；以干净Host-ready检查S→TR。不能把独立profiler测到的8 ms和另一次运行的1 ms直接相减作为正式净收益。

如果M已解释了大部分S→TR的改善，要下调“树剪枝贡献”的说法；原P4组合提速观测仍保留。如果TA→TR减少了坐标更新、真实读取并缩短核验，而S→TR仍快，剪枝的因果证据才更强。

### 4.3 与P4源码桥接

先在旧P4 dev或回归集比较原C_MASK_E与TR：新增运行时force参数不能改变实际候选和最终输出。若时间有变化，单独记桥接成本，不覆盖P4原收据。

冻结相同kernel后保留SASS/符号hash、编译命令、寄存器/shared资源。只做这一组控制，不同时修复TASK、重写distance内循环或调整父节点分组。

若E组结论依赖明显代码生成差异，再追加L对应组作为定向解释；不是默认把L/E所有组合全面扩展。

### 4.4 可选同候选核回放，仅作诊断

确需剥离树前置的缓存影响时，可对预定32查询开发批次导出真实mask，与全1mask在相同受控热状态下做相同kernel回放。必须标为`PRECOMPUTED_MASK_DIAGNOSTIC_ONLY`，不能将预计算候选当免费查询输入，不能报它作为端到端搜索性能。

## 5. 最小执行顺序与运行预算

### G0：环境与正确性烟雾测试

首先让外部库真实执行一次 `4096对象×32查询` 的距离加范围筛选，而非只import成功。选择非零普通半径，并补zero/self/duplicate、边界附近的nextafterf半径、负半径、全命中、非整对象块和查询尾块。

小例子用D=31/32/33/96/960，N=4096/4103，B=1/3/8/32代表性组合，不机械做大笛卡尔积。独立CPU参考不包含待测kernel头文件。边界压力场景与性能场景分开报告，不因边界错误删除真实任务结果。

### G1：外部pilot（主优先级）

GIST half、B=32、dev256，比较SCAN_L、SCAN_E、原C_MASK_E、库double和native候选。三轮交错完成后，先看正确性、端到端与距离阶段。不用跨实验1775/1522 ms作分母。

只在开发集用少数布局/块大小调库，内部不调C4/Q_T/检查间隔。外部pilot明显更快仍保留结果，不挑更慢库参数。若库调用尚失败，保存环境进展，允许G2继续，G3外部状态不可宣布完成。

### G2：同核掩码pilot（归因补证）

GIST half与normal、B=32、dev256，S/M/TA/TR各三轮：2工作负载×4模式×3轮=24进程。先确认小规模正确性、TA/TR同核和P4桥接。

半径half保留正向场景，normal作为弱收益对照。此阶段可复用既有开发计数，不能选择事后最快的一批。

### G3：冻结后的竞争确认

主表初始配置：SCAN_L、SCAN_E、C_MASK_E、LIB64_FROZEN、LIB_NATIVE_FROZEN。若G2中MASK_ALL在开发集成为更快且同合同的无树实现，必须增加MASK_ALL竞争行，或按开发集冻结为无树主对照并保留原SCAN附表；不能因为它不利于树贡献而只藏在因果附表。

| 数据 | 半径 | B | 工作负载数 |
|---|---|---|---:|
| GIST | half、normal、all | 8、32 | 6 |
| Deep | normal | 8、32 | 2 |

总计8工作负载×5模式=40逻辑条件，6轮为240正式进程。若外部需要同时保留“最快native”和“已对齐配置”，或MASK_ALL需要进入强无树对照，明确列出新增行和实际进程数；不要为了维持40这个数字隐藏重要对照。

外部LIB配置由开发集固定，不按final结果逐查询选择。SCAN_L/E与C_MASK_E的所有结果都展示；部署配置只能按开发集选择。事后逐查询或逐半径最优只能标为oracle上限，不可作已实现系统性能。

只测得同语义有限测试优势时，结论限于这些数据、半径、batch、硬件和配置；不是所有精确高维检索的领先。

### G4：正向证据保留与暂停条件

Tloc、TASK、C_ID、PCA等不默认加到本轮正式大矩阵。若公共runner/collector/树边界发生修改，必须重新跑P4历史小规模正确性，以及Tloc B1/B32的已知回归；不修改则保留原账本即可。

新高维数据集、真实外部query向量、其他GPU和更广半径曲线是G3之后的扩展关卡，不是在外部基线未跑通前用更多内部实验代替竞争验证。

## 6. 计时口径

主指标：从批查询已就绪并提交到同一主机API，到全部有效ID+距离可用的Host-ready。GPU-ready指完整结果已生成、计数/收集完成，不包括后续主机交付。两者必须同时记录。

主口径包括：query gather/提升、H2D、实际树遍历、mask生成/清零、全部距离及外部距离矩阵写入、阈值判定/转换、公共收集、offset反馈、D2H和同步。公共CPU输入复制若仍不计时，必须各模式一致并明确边界；不得只排除外部库特有的准备工作。

排除并单列：数据读盘、静态数据重排/转换、建树与refit、layout、内存预分配、Graph捕获、JIT初次编译、预热、oracle和审计hash。必要时补共同stream轨检查Graph差异，而非假定库兼容Graph。

每进程8个开发批次预热；每条件6独立进程；同轮固定查询/批次/配对，轮换模式顺序和批次遍历方向。禁止外来GPU活动，记录NUMA、温度、频率等状态，不为单一模式私自锁频。

报告每轮1024查询总时间、逐批p50/p95、paired ratio六个原值/中位数/范围、按轮配对bootstrap。固定查询集的运行区间不是查询分布的统计泛化；若另做按批次重采样，明确其统计单位与目的。

QPS用总查询数除以累计Host-ready秒；batch_time/B叫摊销时间，不能叫响应延迟。本轮未计在线排队。

## 7. Breakdown、工作量和冷成本

正式运行不插计数。独立开发批次用于NVTX/NSYS/NCU与工作量计数。阶段至少分为：query准备、树/候选、距离、矩阵阈值转换、结果收集、feedback、D2H。API同步包含等待，不能重复相加。

对TA/TR记录配对坐标更新、共享坐标步数、warp最长路径、候选并集/非空块、全部核与对象核DRAM读写、L1/L2请求、FP64指令与资源占用。逻辑坐标步数不是DRAM字节；SASS指令计数不能直接换算为FLOP或能耗。

外部库同时报告distance-only和完整wrapper成本，以便看清差距来自距离核心还是矩阵物化/收集；最终优势只根据完整查询。

NCU优先使用已验证的application/range replay，固定查询与核活动，记录cache/clock策略和无法采集项。官方文档要求application replay活动确定性；profiler结果不作为正式速度分母。[D5]

对SCAN与树分开建立准备账：原扫描仍可能依赖id_list来源，不可直接称为真正无索引冷启动。库若不需要树，不得为了公平强迫它建树。各方法独立记所需读盘、索引、转换、layout、静态memory；首次查询任务补Q=1/32/1024的实际总时间时，才可声称完整任务优势。只用额外构建除以单查询节省所得回本数，必须标为摊销估算。

## 8. 通过、失败与下一步判据

| 结果 | 处理 |
|---|---|
| 同核TA→TR确实减少核验，且TR优于S | 保留“剪枝在强批量执行上有净价值”的因果证据 |
| M已接近TR，实际剪枝增量很小 | 保留组合观测，降低树贡献表述；先承认无树掩码核也是强基线 |
| C_MASK超过内部S，但输给同任务、同合同外部扫描 | 原结果不作废；不继续打磨0.4%TASK；优先分析库距离执行与表示差异 |
| 外部更快但合同不一致 | 保留native速度与所有数值差异，不算同合同胜利；是否需要认证回退另作决定 |
| 仅小半径胜出 | 定位条件性精确范围组件；保留normal/all/Deep负向结果 |
| 配对中位速度≥1.10×且6轮都快、正确性通过 | 作为优先扩展门槛，进入新数据/外部query复验；不是论文创新性证书 |
| 1.03–1.10×稳定 | 保留工程收益，不扩大表述 |
| <1.03×或波动覆盖1 | 暂不区分，停止围绕细微差异调参 |
| 安装/链接/正确性未过 | 明确未完成；不拿更多内部结果替代外部对照 |

百分比门槛是本轮研发决策规则，不是普遍定律。有统计稳定性不等于有大实际价值；方法新颖性仍须另做相关工作比较。

## 9. 交付目录与字段

```text
diagnostics/external_mask_validation_20261002/
  PLAN.md / CONTRACT.yaml
  ENVIRONMENT.json / EXTERNAL_INSTALL.log / SMOKE_TEST.json
  SOURCE_PINS.json / PREFLIGHT.json / DECISIONS.json
  adapter_cuvs.cpp                   # 拟新增，不是已有代码
  prepare_effective_mask.cuh         # 拟新增运行时full/real切换
  causal_bench.cu                    # 同核S/M/TA/TR控制
  external_bench.cpp                 # 统一Host-ready适配器
  boundary_audit.jsonl / correctness.jsonl
  external_dev.csv / causal_dev.csv / latency_final.csv
  numerical_qualification.csv / profile_summary.csv / work.csv
  setup.csv / memory.csv / EVIDENCE_LEDGER.md / RESULTS.md
  raw_receipts/                      # 命令、stderr、GPU监控、hash
```

`latency_final.csv`至少包含：dataset、split、qid_sha、radius_bits、B、Q_T、mode、library_version、metric_enum、input/accumulator/output_dtype、math_mode、layout、chunk_N、graph_policy、round、batch_id、host_ms、gpu_ms、result_count、d2h_bytes、ID资格、距离字段资格、valid/invalid_reason。

`causal_dev.csv`另加：distance_symbol_hash、force_full、tree_executed、mask_hash、candidate_pair_count、coordinate_updates、shared_coordinate_steps、tree_ms、mask_ms、distance_ms、collect_ms。

**最终只需明确答复三句话：最强同任务对手是谁；同合同能快多少；同kernel实验显示树独立省下了什么。**

## 10. 第一批执行指令（任务级，不是已存在的CLI）

先让cuVS在真实设备完成4096×32的小例子并完整返回范围结果；随后GIST half、B=32、dev256跑SCAN_L/SCAN_E/C_MASK_E和候选库配置。同时完成S/M/TA/TR同核小对照。拿到这两张表以后，再冻结新final并扩8个工作负载。现在不再开发新树、选择器或TASK技巧。

## 来源

下列仓库引用固定到已核对提交；官方接口资料访问日期为2026-10-02。设计、运行预算和门槛是本计划建议，不是已发生的测量。

- [R1] https://github.com/wangwenqingqq/GTS-variants/blob/8cf31c448b968398207fe5a5eb358121be64c134/diagnostics/batch_tree_inheritance_20261002/RESULTS.md
- [R2] https://github.com/wangwenqingqq/GTS-variants/blob/8cf31c448b968398207fe5a5eb358121be64c134/diagnostics/batch_tree_inheritance_20261002/batch_candidate_tasks.cuh
- [R3] https://github.com/wangwenqingqq/GTS-variants/blob/8cf31c448b968398207fe5a5eb358121be64c134/diagnostics/batch_tree_inheritance_20261002/p4_bench.cu
- [R4] https://github.com/wangwenqingqq/GTS-variants/blob/8cf31c448b968398207fe5a5eb358121be64c134/diagnostics/batch_tree_inheritance_20261002/PREFLIGHT.json
- [R5] https://github.com/wangwenqingqq/GTS-variants/blob/8cf31c448b968398207fe5a5eb358121be64c134/diagnostics/batch_tree_inheritance_20261002/EVIDENCE_LEDGER.md
- [D1] https://docs.nvidia.com/cuvs/api-reference/cpp-api-distance-distance
- [D2] https://docs.nvidia.com/cuvs/api-reference/python-api-distance
- [D3] https://docs.nvidia.com/cuvs/user-guide/api-guides/other-ap-is/pairwise-distances
- [D4] https://docs.nvidia.com/cuvs/installation
- [D5] https://docs.nvidia.com/nsight-compute/ProfilingGuide/
