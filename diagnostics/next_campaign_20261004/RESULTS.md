# 10K计划首轮执行：资格拒收，正式静态矩阵未启动

本轮按 [PLAN_10K.md](PLAN_10K.md) 的固定版本`480bc7dbdfaf6ff7048bc810d29f6b4aecbf2e16`执行，使用一张空闲RTX PRO 6000 Blackwell Server 96 GiB，所有GPU任务串行、固定同一物理GPU。未更改共享设备设置，未触碰其他进程。**原生Faiss Flat在GIST1M的开发1024上漏查并交付超容差字段，按wrong-result停止规则拒收。正式10K查询未生成，不能称本计划完成或获得静态稳定版。**

| 阶段 | 已取得的实际证据 | 状态 |
|---|---|---|
| N0 | 主要原始来源的重叠/边界矩阵；未引入新优化机制 | documented，见[N0](N0.md) |
| F0 bounded | 78进程；24对Graph/eager；600次状态复用；16次sanitizer；真实16条尾批次；完整CPU成员/字段核对 | 小规模passed；不是10K稳定性 |
| A0/A1 static | 12条NSYS trace及CPU samples；8个实际kernel的NCU计数；12个诊断输出全部审查 | measured，开发集、instrumented范围 |
| U10-NATIVE correctness | 三seed共30000查询、3000插入、3000删除、150次threshold rebuild | 全部passed，N1000原生逻辑多重集 |
| F0 developer | GIST/K8/B32的四个控制通过；原生Flat成员/字段失败 | partial/rejected，见下表 |
| Optional REF64 | GIST开发1024通过、memcheck零错误；small96成员失败 | rejected，未晋升 |
| K10-MATCHED/BULK | 开发池已登记；其他形状/ANN网格/bulk策略未完成；正式集未生成 | pending，零正式进程 |
| R10、30K sustained | 未启动 | pending |
| 更新完整计时/归因 | 当前U0 observer有观察打印，没有合格timed adapter | pending |
| U10-ARRIVAL | 统一keeper、真实新向量及稳定外部ID入口缺失 | not admitted |

## 1. 身份与查询隔离

检索实现沿用P7的`d65c6e41effad67dde8ae1f1f68e656562607817`，执行来源为P7已发布的`7bce3679c3e32e77fa25cf7842805926509e1412`。新编排主要增加八批预热、实际尾批次、逐批时延、约1K边界的CPU/RSS/device-memory快照和有界资格开关。没有为10K修改检索kernel、剪枝、seed或selector算法。

| 实际二进制 | SHA-256 |
|---|---|
| P7派生优化静态入口 | `70520e34a97b155a0aeffa58d0b1c851684a6be4cd4fd71b170099da64cfae17` |
| 原版静态full-output/capacity适配器 | `40c1cf9b1f0d855a4d4c1cd55a6e4916af90fc0ca75e18b5d8be372ba5dc2075` |
| U0原生rnum-reset观察入口 | `6c67544eb687c373bf71bf35662677dc7fb240d37cbd69b2f7462b911c4ce1e5` |

编排在开发阶段有迭代；[SOURCE_BRIDGE](evidence/SOURCE_BRIDGE.json)与[SOURCE_SNAPSHOT](evidence/SOURCE_SNAPSHOT.json)分开保存。停止后快照不冒充所有早期脚本版本或最终正式冻结。原版静态适配器保留原检索算术，原生更新另用其合法N1000容量与live-rank语义。

GIST/Deep分别排除5472/5336个历史query ID，再用seeds2026100411/12生成1024个新开发ID，用0413/14生成各10000个独立bulk-development ID。全部唯一、互不相交；具体文件/生成器/排除清单hash见[QUERY_DEVELOPMENT](evidence/QUERY_DEVELOPMENT.json)。**bulk开发文件生成不等于执行了bulk实验。** 正式0421/22未使用。GIST新1024的独立RN-FP64 oracle逐查询保存，完整原始结果/字段在外部bundle中。

实装环境及共享库hash见[ENV_FAISS](evidence/ENV_FAISS.json)、[ENV_CUVS](evidence/ENV_CUVS.json)；数据/cache/index/graph/header身份见[INPUT_IDENTITIES](evidence/INPUT_IDENTITIES.json)。Faiss为原生GPU路径，`use_cuvs=False`，未用同一cuVS实现冒充两个独立库。

## 2. 新1024开发筛选与停止原因

同一GIST1M/960D、K8/B32、八批开发预热、完整Host-ready结果。以下每项仅一份开发筛选，**没有六轮统计、正式优势或稳定性结论**。原版包含其声明的原始搜索及完整输出成本。

| 方法 | 完整1024查询pass，ms | tie-aware Recall@8 | 最差查询 | 完整成员/字段门槛 |
|---|---:|---:|---:|---|
| GTS_ORIG | 321237.054 | 1 | 1 | passed |
| O_FULL | 5825.095 | 1 | 1 | passed |
| IVF_ALL | 2613.011 | 1 | 1 | passed |
| O_BOUND | 4254.795 | 1 | 1 | passed |
| Native Faiss Flat | 214.312 | 0.9998779296875 | 0.875 | **rejected** |
| O_MASK | — | — | — | 本开发形状尚未执行 |

原生Flat第531条qid712558漏掉223837、返回695244；CPU对全部1M对象显式逐维FP64计算确认，kth与下一项平方距离差1.5641994874471266e-5，不是精确边界tie。另有qid853005把自身距离交付为0.008052940480411053，平方误差超过5e-5门槛。完整查询比例1023/1024。详见[CPU全枚举](evidence/FLAT_FAILURE_LOCALIZATION.json)与[原生逐查询audit](evidence/outputs/screen_GIST_FAISS_FLAT_k8_b32.audit.json)。

IVF_ALL是这个已执行开发形状里通过完整门槛的外部控制，单次时延低于O_BOUND；不据此宣称有六轮显著差异。原生Flat未准入完整质量表，不能把它的速度和别的行的精算质量拼成同质量优势。CAGRA在12条小诊断trace中可运行，但1024两遍网格未执行，不能省略其必选角色。

可选`FAISS_FLAT_REF64`把native取64、候选RN-FP64精算、选择、Euclidean字段、D2H和同步全计时；该1024首次通过231.328ms。但后续small96/N4097/K8/B1/Q48资格检查13条成员失败，平均0.7447916666666666，最差0。首个qid128约1e-40；真零距离128..135未返回，交付0..7且真实平方距离约9.6e-79。memcheck零错误且字段合格均不能挽救成员失败。安装CuPy不接受`lexsort(axis=1)`的首份运行也保留为rejected；那份被覆盖的R1源码没有执行前hash，不能补写为已观察身份。详细失败与可证伪重开条件见[ADMISSION_FAILURE](ADMISSION_FAILURE.md)。

## 3. U10原生更新：有界完整正确性

沿用上游`3bac1b7`加一行`rnum[0]=0`修补，真实原生N1000/D128。每seed100 cycles、10000次query、1000次insert、1000次delete，基础删除/重插入与buffer插入/删除交替；触发是当前buffer occupancy=10，不是累计插入十次。轨迹及expected在GPU执行前登记。

| Seed | 半径 | Queries | 实际threshold rebuild | 全部结果项 | FN/FP/重复/非法ID |
|---|---:|---:|---:|---:|---|
| 2026100431 | 0 | 10000 | 50 | 14990 | 全0 |
| 2026100432 | 10000 | 10000 | 50 | 10000000 | 全0 |
| 2026100433 | 512 | 10000 | 50 | 15361 | 全0 |

全部10030351个交付结果项的字段通过；共153棵实际树含三棵初始树，306000次ancestor/member区间检查通过。详见[预登记](evidence/native/REGISTERED.json)与[U10_NATIVE](evidence/U10_NATIVE.json)。这是重复物理行插入、当前live-rank删除、串行loop可见性的原生逻辑多重集实验。不能推广为任意新向量、稳定外部ID、并发更新、N1M动态100%或低延迟。观察打印/审查不构成合格性能分母，本轮没有更新性能倍率。

## 4. 静态归因：CPU等待与GPU距离工作

12条trace均为GIST1M/K8/开发32查询，B1/B32各六方法；全部完整输出经独立oracle审查，通过[PROFILE_OUTPUT_CHECKS](evidence/PROFILE_OUTPUT_CHECKS.json)。CAGRA只是在这32个查询上的经验完整结果。NSYS区间含instrumentation，不能替代正式时延。

| B32诊断方法 | query区间，ms | GPU kernel时间并集，ms | 对象距离kernel累计，ms |
|---|---:|---:|---:|
| GTS_ORIG | 10163.821 | 10151.519 | 10074.970 |
| O_BOUND | 134.890 | 134.629 | 129.750 |
| O_MASK | 133.391 | 133.115 | 127.230 |
| Native Flat | 7.821 | 6.759 | 库内部kernel单列 |
| IVF_ALL | 82.734 | 81.457 | 库内部kernel单列 |
| CAGRA | 7.499 | 4.742 | 库内部kernel单列 |

原版GPU并集覆盖99.879%的区间，对象距离占约99.126%；`cudaDeviceSynchronize`的10138.802ms inclusive时间与GPU工作重叠，不能再加一次。原版/优化开发1024进程的query CPU-time约为一个busy-core equivalent，NSYS leaf-IP samples主要在libcuda与vdso且未解析到具体函数；这是与driver等待一致的证据，不能把全部CPU time称为有用CPU计算或断言唯一函数。数据见[ATTRIBUTION](evidence/ATTRIBUTION.json)和各[query CPU记录](evidence/outputs/screen_GIST_O_BOUND_k8_b32.cpu.json)。

八个NCU条目均采到实际kernel，使用kernel replay、cache-control none、clock-control none；每条只分析第一个匹配的开发warmup launch，不是完整query pass。Blackwell的实际名称为`dram__bytes_op_read.sum`等，单位保留，不用旧名称/理想字节公式代替物理计数。

| 单次指定距离launch | DRAM读，Gbyte | DRAM写，Mbyte | FP64 pipe % peak sustained elapsed |
|---|---:|---:|---:|
| O_FULL verify | 61.460491 | 322.162176 | 84.986841 |
| O_BOUND verify | 45.353963 | 321.025536 | 85.137842 |
| O_MASK verify | 44.902589 | 322.362624 | 85.229083 |
| 原版dataProcessKnn | 44.777665 | 647.834368 | 86.255742 |

这些launch的筛选/迭代阶段未必同工作量。计数支持“距离计算路径压力明显”的下一步归因，**未证明纯合并访存贡献，也未量化精度替换收益**。物理bytes/requests/sectors、寄存器等见[PHYSICAL_COUNTERS](evidence/PHYSICAL_COUNTERS.json)，最后FP64名称展开是归档后的CPU提取，来源hash见[DERIVED_ANALYSIS](evidence/DERIVED_ANALYSIS.json)。最初不兼容的NCU导出参数失败日志保留；兼容导出来自同一已有report，无新增GPU样本，见[NCU_EXPORT_RECOVERY](evidence/NCU_EXPORT_RECOVERY.json)。

原版B32有22次CPU UVM fault、254次GPU UVM fault；B1分别672/11952。这是fault事件计数，不是迁移字节。未导出的事件表不区分无事件与工具不可用，仍为unknown。冷构建、完整更新stage、钩子开销和等工作量因果控制仍pending，见[OPERATOR_INVENTORY](OPERATOR_INVENTORY.md)。

## 5. 决定、证据保存与剩余门槛

实现决定：保留P7静态入口为控制；没有晋升新“stable”或统一query/update版本。机制决定：不因本轮归因恢复纯coalescing或历史allocation/rebuild headline；有限候选精算拒收。论文影响：U0修补增加了有界长轨迹完整正确性证据，静态10K、外部优势和动态端到端性能仍不能主张。

原生Flat失败的重开条件是单独声明并合格的完整数值/输出入口，保留原native失败；有限overfetch修补须先通过全部bounded成员资格与复用门槛，不能只增加候选数后复用已看过的正式集。本轮没有正式集，不存在最终集调参。任何后续路线保持原5e-5字段及精确tie成员约定，重新登记身份与参数，不把ANN经验质量冒充完整性证明。

完整计划尚需：其他七个静态形状及O_MASK、IVF/CAGRA两遍开发网格、bulk10K开发、全部参数与源冻结、两数据集正式10K、八matched/四bulk形状六轮、真实16-tail、30K持续性、五个R10工作负载、更新timed adapter/阶段归因与冷成本。U10-ARRIVAL须实际统一keeper准入后才能开展。明确未完成项是计划要求的停止报告，不是省略基线后的成功结果。

完整原始bundle为449921764 bytes，SHA-256 `a07a521352a17884ec7782b32fd7bfa4f4ea132c9c392c6b7e2c805cff5a8a0e`，保存在任务私有远端与本地私有副本，未上传Git。1715个原始文件逐个hash校验通过，包括全部字段输出、query/trace/oracle、源码/二进制、rejected receipts、NSYS/NCU报告。大数据/index/图内容以输入hash引用。见[EXTERNAL_BUNDLE](evidence/EXTERNAL_BUNDLE.json)、[RAW_MANIFEST](evidence/RAW_MANIFEST.json)、[ARCHIVE_VERIFICATION](evidence/ARCHIVE_VERIFICATION.json)。

公开evidence清单移除了私有scratch前缀与GPU UUID，原始设备/进程/profiler日志留在私有bundle。归档后CPU派生摘要另记来源hash；不把规范化公开JSON的hash称为未修改原始文件hash。完整观察与晋升边界见[PUBLICATION](evidence/PUBLICATION.json)。
