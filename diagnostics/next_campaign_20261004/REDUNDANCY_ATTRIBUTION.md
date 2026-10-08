# 既有计数对齐与原生 U10 资源预算（2026-10-08）

本次分析只读取已采集报告，新增 GPU 任务为 0。K10 的 834 行、资格与统计结果保持不变。四份直接计数由 `EXACT_WORK_COUNTERS.json` 的实际 `--export` 解析，报告/CSV SHA、两次采集的 source/binary、data/query/order/warm/tree/seed、完整核名、所选 launch ID、grid/block 及输出逐字节对齐。公开追溯信息在 [CANDIDATE_MANIFEST.json](CANDIDATE_MANIFEST.json)，原始报告留在外部。receipt 的 `binary_sha256` 是 NCU 可执行文件；实际搜索二进制采用 identity.files 中的 SHA，避免把两者混称。

## 能解释的工作减少

| GIST N1M/D960，K8/B32/Q32，同一正式核验 launch | 实际坐标累计次数 | DRAM read（十进制 GB） | read bytes/坐标 |
|---|---:|---:|---:|
| O_FULL | 30,720,000,000 | 61.464299 | 2.00079 |
| O_BOUND | 16,368,553,024 | 45.350214 | 2.77057 |
| O_MASK | 15,929,000,640 | 44.898862 | 2.81869 |

此处坐标数不是仅凭 DMUL 猜测：`knn_verify.cuh` 每个活动查询维度显式执行一次 `__dmul_rn` 与两次 double 加/减；同一二进制的 QT2 三个模板 SASS 对应 DADD→DMUL→DADD，没有 DFMA。相同查询/launch 的 O_FULL 计数恰等于 N×D×Q，三个模式 DADD 均严格为 DMUL 的两倍、DFMA 为 0。没有额外计数 kernel、原子操作或生产版 binary 改动；独立 NCU replay 的时间不替代干净生产时间。

相对 Full，Bound/Mask 分别少执行约 46.72%/48.15% 坐标；Mask 相对 Bound 仅再少约 2.69%。这是这一诊断输入的实际少算证据，不代表所有 K10 查询。总读取下降约 26%–27%，但单位坐标读取反而增加：不能由总字节下降推导纯合并访存提升。整个 kernel 还读取 query、mask、元数据并写结果，缓存/replay 与活跃线程也会影响计数。

原版 `dataProcessKnn` 的 78,050,481,962 次 DMUL 与 457,124,843,534 次 DFMA 涉及原距离路径、`pow` 及其实现，缺少可用的一次坐标对应关系。此报告只覆盖第一次迭代匹配 launch，不能与完整优化 pass 等工作相除。[WORK_TRAFFIC_ALIGNMENT.csv](WORK_TRAFFIC_ALIGNMENT.csv) 明确拒绝其坐标归一化。Masked 的被拒槽位/实际开始配对数、动态 shared-coordinate steps 没有直接计数，保留为空，不从字节或 DMUL 反推。

## 主张分类

| 主张 | 当前证据等级与允许表述 |
|---|---|
| 坐标工作减少 | 已对齐的实际指令计数、源码及本次 Full 校准；上述诊断输入成立 |
| 显式跨查询读取复用 | QT2 源码每个 object-coordinate 读取供最多两条活动查询使用；结构证据成立，动态加载次数缺失，独立倍率未分解 |
| 纯 coalescing 因果收益 | 尚不支持；没有固定工作/精度/活跃线程的布局单因素对照，不用 sectors/request 或整体倍率替代 |
| 算术路径变化 | 原版复杂路径与优化显式 FP64 round-to-nearest 操作不同；不能把它藏进布局收益；未单独量出贡献 |
| 静态累计 46.956–76.846 倍 | 原 K10 合格暖查询比较事实；包含执行器、算术、选择和批量等多项变化，不能精确拆成可相乘因子 |
| 原生 U10 生命周期重复 | 已有 trace 与源码确认逐查询分配/释放；存在预算，净收益等待同轮干预 |

## 全部 18 个干净 on 进程的阶段账

[U10_STAGE_BUDGET.csv](U10_STAGE_BUDGET.csv) 保存 18×8 个阶段的每进程原值、调用数与自身 trace 占比。三个 seed 每个均为六个 fresh on 进程；不是用单进程代表整个实验。

| seed | query.tree 占 trace 中位数 | 六进程最小–最大 |
|---|---:|---:|
| 2026100431 | 84.347% | 84.033%–84.478% |
| 2026100432 | 85.026% | 84.854%–85.198% |
| 2026100433 | 85.183% | 84.921%–85.255% |

这些是 Host 包含区间，不是可消除成本。所有 rebuild 阶段属于 insert，不能再次加入完整 trace。

另一个已有 NSYS seed0431 进程：完整区间 18,575.558ms，query.tree Host 15,302.160ms；其中 kernel 累计 11,011.279ms，kernel/copy/memset 设备活动并集 11,020.346ms。主要 kernel 是 findNextRnn 6,815.859ms、leafProcessRnnUpdate 3,257.795ms。主树区间没有导出的 memset 操作，必要初始化由 initQnode/initRes 等 kernel 完成，候选标记扫描/压缩和两个 reduce 的标量反馈保留。D2H 标量 copy 共 20,000 次、80,000B；其他 copy kind 原样列出，不把未知 UVM fault 换成迁移字节。

query.tree 内分配：60,000 次 Managed +150,000 次 Device；释放 170,000 次。API 包含时间分别 172.124+379.489+543.594=1,095.207ms；含 Thrust 临时分配与外部所有权结果，不能全部声明可省。通过每个查询的固定 API 序列与源码逐项对应，11 个内部工作区的 110,000 次申请、110,000 次释放合计 **612.809ms**（profile 区间的约 3.30%，只是可检查预算，不是预计或已实现加速）。每个查询均验证 6 Managed/15 Device/17 free 的序列，未知序列会停止映射。

cudaDeviceSynchronize 11,364.799ms、cudaStreamSynchronize 362.947ms 是包含等待，重叠设备工作；不能加到 GPU 时间上，也不能把 trace−kernel 命名为 CPU 有用工作。已有 IP samples 大多 unresolved，CPU useful 精确毫秒仍不可得。Runtime export 没有 malloc size 参数，实际申请字节不能从这份 trace 恢复；源码提供容量表达式，下次两模式需直接记录账本。prefix 的 139.598ms 是独立 profile 的 scan 累计，不和某个干净 trace 拼成精确节省比例。

## 唯一下一步

预算与所有权边界足以选择 **U_LIFE_BRIDGE**：只复用 searchIndexRnnUpdate 内部 2 个 Managed 标量、9 个 Device 数组。外部结果/count 分配与 Thrust 分配不动。按本次请求上界检查容量、扩容在操作内计时；所有初始化、计算 kernel、同步、full output 与 ACK 保留，最后释放计入 trace/final drain。该预算不保证显著收益。

先核对串行多重集/重建/非空变空/大与尾部结果，再资格化新身份的 on/off 观察器；首条固定 seed0431 做六对 U_BASE/U_LIFE，若没有可信完整流程净收益即停止，不自动转向融合、FP32、Graph、P7 kNN 或改阈值。R10/30k/全冷/百万动态/新向量/并发仍为 pending。

CPU 重建命令（原始外部路径由使用者传入；脚本不申请 GPU）：

```bash
python3 align_work_and_traffic.py --raw-root RAW_ROOT --workflow-root WORKFLOW_ROOT --sass OPT_SASS --evidence evidence/recovery --out .
```

`OPT_SASS` 可由 CUDA cuobjdump 对已冻结二进制离线导出。该命令生成两份 CSV 和 manifest；本文是经过源码与归因审阅的解释，不由脚本自动改写。原始 report/hash 与旧资格结果不回填。
