# D0：叶分组共享与现有掩码执行的机制差异

2026-10-08。**裁决：NO_DISTINCT_MECHANISM_YET，停止本轮扩表。** 这是一轮源码/文献核验，新增 GPU 进程为 0；不是 GROUP 对照的性能结论。上下文 `5f4abef1f137b679a1a791eea5eede72a093ed59`；所有范围源码从指定 `f16d09a4e8a32ab8afff3b1b92221a5e447725a0` Git 对象读取，不能替换为 P7/U10。逐文件 hash、入口依赖和论文 PDF hash 见 [SOURCE_PINS.json](SOURCE_PINS.json)。

G-PICS 已有叶查询登记、叶数据共享及分页输出[P1]；Harmonia 已讨论聚合/排序成本[P2]。下表核对具体实现差异，不能由差异直接推出新颖性。

| 维度 | 已有机制 | 本次冻结源码 | 相同点、差异与可验证后果 |
|---|---|---|---|
| 工作单位 | P1：quadtree 叶 | `TreeIndex` 的 `frontier_dev[pos]`；MASK 原对象位置，TASK 32 个位置一块 | P4 的停止深度分区不等于 P1 的真实叶；普通 BLOCK_LIST 也可保持物理块边界 |
| 查询—数据关联 | P1：叶查询列表 | `candidate_mask` 产生 `uint8_t` 的 `(q,pos)` 表；`make_tile_masks` 产生固定两查询的 32-bit lane mask | 都编码相关性；MASK **不是 1-bit 压缩**。TASK 不是任意活动查询列表 |
| 共享范围 | P1：叶对象存入 shared | MASK/TASK 的 `query_cache` 在 shared；对象坐标 `x` 是线程局部值，供相邻两查询复用 | 数据/查询驻留角色与线程映射不同；当前并非“整叶只读一次”，不等同于原论文线程实现 |
| 独立早退 | P1：搜索函数，未规定本轮高维规则 | 强 SCAN 的 `batchDistance:24–54` 已有每对独立 sum/active、每32维早退和 any-active 加载；MASK `:22–40` 加候选门控；TASK `:115–134` 复用该规则 | 相同有效 `(q,pos)` 的累加顺序不因容器改变；这组共享/早退状态机不是 MASK 新增的机制 |
| 中间物化 | P1：列表和分页池 | ID 做每查询 CUB select/gather；MASK 保留密集位置；TASK 从同一字节表再生成/压缩非空块；公共 `Batch::collect` 收集全量结果 | MASK 省去 ID 路径的热列表生成/gather，**仍写密集候选表**，不能称消除全部物化或首次两阶段输出 |
| 正确性 | P1 的空间任务不同 | 同一 P4 前端、安全界、FP64 顺序与公共输出 | 编码关系可对应；不是原 G-PICS 与高维 GTS 的整体算法/数值等价证明，未产生新 GROUP 正确性结果 |
| 代价 | P2：组织成本须付出 | `TreeBatch:96–108` 对全部树模式都保留 positions/task/mask 分配；TASK 另付块掩码与 CUB select | 热路径少写列表不等于释放其保留空间；现有 profile 不能证明一个合理区域分组对照仍有不可消除差距 |

**最强替代解释。** 令共同安全标记为 `F(q,g)`，位置归属为 `g(pos)`：区域列表 `L_g={q:F(q,g)=1}`、字节表 `M(q,pos)=F(q,g(pos))`、固定查询对的 lane bitset 表示同一候选关系。块注册也能保留原 packed 位置；跨分区时检查本位置归属即可。这是关系编码对应，不是已实现/资格化的新 GROUP，也不证明性能相同。改变查询分组会改变共享加载机会，不应改变同一对的距离或停止维度。

**D0 判断。** 当前新增动作可定位为候选谓词门控、普通线程/存储分块与空块压缩；共享与独立早退已在强 SCAN。尚未找到一个现有实现所解决、且不能由这些普通组织解释的额外交互，因此按上传计划 §2.3 停止，不为跑出“新颖性”新增 GROUP 家族。不能由此宣称原 G-PICS 完全等价、已经实测追平或所有未来设计无效。

历史 P4 的 SCAN_E/C_MASK_E/C_TASK_E 在 GIST half/B32 为 1775.1/1521.8/1515.3 ms（1024 查询），P5 同核真实/全候选控制支持真实剪枝收益；两者保留，但不作为新计时分母或相对 GROUP 的证据。独立结论见 [DECISION.md](DECISION.md)。

源码定位：`batch_candidate_tasks.cuh`、`batch_tree_prefix.cuh`、`p4_bench.cu` 属于冻结 P4；`batch_l2.cuh`、`batch_bench.cu` 属于其 P0–P3 依赖。完整 Git 路径均在 SOURCE_PINS；当前进展树未包含这些范围资产，不做隐式移植。

[P1] Nouri & Tu，SSDBM 2018，§4/Algorithm 5，PDF第6–7页：[作者原文](https://cse.usf.edu/~tuy/pub/SSDBM18.pdf)。
[P2] Yan et al.，PPoPP 2019，§4.1，PDF第6–7页：[作者原文](https://www.ece.lsu.edu/lpeng/papers/ppopp-19.pdf)。本轮成功下载两份原文并核对章节/算法版面；未做全面文献查新。
