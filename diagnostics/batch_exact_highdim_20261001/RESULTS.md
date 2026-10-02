# GTS 高维精确范围查询的批量复用实验（P0–P3）

**结论。** 在 pro6000-8 的同一块 RTX PRO 6000 Blackwell 上，查询微块显式复用数据库坐标，相对于已经联合调度的 GRID，在 GIST 1M×960D 和 Deep 1M×96D 的 B=32 正式测试中均稳定降低完整 Host-ready 时间：无早退约 **1.10×**，带每 32 维安全早退约 **1.30×**。这不是只省了 kernel launch：开发批次的 NCU 记录显示 GIST 全维 GRID→TILE 的 DRAM 读取从 122.9 GB 降到 61.5 GB。提前退出不是普适收益；GIST 全命中时 TILE_E 比 TILE_L 略慢，Deep 中 GRID_E 也比 GRID_L 慢约 17%。

本报告完成了原计划 P0–P3；P4 树继承和 cuVS 外部对照尚未运行，因此不声称索引组合胜出或超过工业实现。原始设计附件 [CONTRACT.yaml](CONTRACT.yaml) 保留了设计时的 `DESIGN_ONLY` 标记；本报告和 [PREFLIGHT.json](PREFLIGHT.json) 记录实际执行状态。

## 同口径主结果

全部模式使用同一 AoSoA32 数据副本、同一批量稳定收集器、两阶段完整结果交付、FP64 顺序算术和相同的 1024 条冻结查询。`SEQ` 串行发出距离 kernel，但共享批量输出路径；`GRID` 一次二维调度而不显式复用数据库值；`TILE` 每个对象值供一个微块内的两条查询使用。`L` 全维，`E` 每 32 维做一次不会漏掉命中的安全早退。B=1 的 GRID/TILE 距离路径别名，未为别名重复制造独立样本。

下表是每条件六个独立进程的 **1024 条查询总 Host-ready 时间中位数**，单位 ms。每个进程先用开发查询预热 8 批；正式查询、批次成员和比较轮次配对。时间包括查询 H2D、CUDA Graph、距离、收集、count 回传、有效 ID/距离 D2H 与同步；不包括装载数据和构建布局。

| 数据 / 半径 | B | SEQ_L | GRID_L | TILE_L | SEQ_E | GRID_E | TILE_E |
|---|---:|---:|---:|---:|---:|---:|---:|
| GIST normal | 1 | 6,670 | 同 B=1 路径 | 同 B=1 路径 | 6,531 | 同 B=1 路径 | 同 B=1 路径 |
| GIST normal | 8 | 6,636 | 6,328 | 5,743 | 6,497 | 6,022 | 4,647 |
| GIST normal | 32 | 6,632 | 6,271 | 5,704 | 6,493 | 5,965 | 4,574 |
| GIST normal | 128 | 6,642 | 6,277 | 5,698 | 6,503 | 5,960 | 4,567 |
| GIST half | 32 | — | 6,249 | 5,684 | — | 2,300 | 1,784 |
| GIST all | 32 | — | 6,580 | 6,014 | — | 7,876 | 6,054 |
| Deep normal | 32 | — | 643 | 586 | — | 755 | 577 |

同轮总时间相除，B=32 的 GRID_L/TILE_L 中位比值分别是 GIST normal 1.099×、half 1.100×、all 1.094×、Deep normal 1.097×；GRID_E/TILE_E 分别是 1.304×、1.289×、1.304×、1.308×。B=128 的相应比值约 1.10× 和 1.29–1.31×。六轮逐轮比值、范围和配对轮次 bootstrap 区间在 [p1_summary.json](p1_summary.json)、[p2_summary.json](p2_summary.json)、[p3_summary.json](p3_summary.json)；这些区间描述同一固定查询集上的运行波动，不代表生产查询分布置信区间。

GIST half 的 TILE_L/TILE_E=3.186×，说明早退在稀疏命中时很有效；GIST all 的 TILE_L/TILE_E=0.994×，即带早退略慢。Deep normal 的 GRID_L/GRID_E=0.852×，提前退出反而使 GRID 慢约 17%；TILE_L/TILE_E=1.016×，改善仅约 1.6%。负例均保留，未按半径挑选有利场景。

## 吞吐与单批等待

GIST normal 的 TILE_E 同步单批返回时间中位数：B=8 为 36.4 ms、B=32 为 142.4 ms、B=128 为 571.2 ms；对应整轮吞吐约 220、224、224 查询/秒。B=1 的同距离路径约 157 查询/秒、单条约 6.77 ms。B=8 已接近本次吞吐上限；更大批量提高的是摊销吞吐，并没有缩短每条请求等待整个同步批次返回的时间。这里所有请求在计时起点已就绪，未计在线凑批等待或多租户干扰。逐批主机和 GPU 时间、结果字节在 [latency.csv](latency.csv)、[p2_latency.csv](p2_latency.csv)、[p3_latency.csv](p3_latency.csv)。

全命中是输出成本的边界：GIST final1024 共 1,024,000,000 条结果，完整 ID+float32 距离载荷 8.192 GB。B=32 的 TILE_E 六轮总 GPU-ready 中位数约 5.744 s、Host-ready 约 6.054 s，差额约 310 ms 已包含反馈和 D2H 等主机交付。normal 共 94,439,507 命中，half 共 499,264 命中；Deep normal 共 28,562,882 命中。正式路径依据实际 count 传输有效长度，没有利用 oracle 预知结果大小。

## 正确性、根因与资源

独立 CPU 全枚举覆盖 2 种 N、6 种 D、7 种 B、6 模式共 504 个小规模组合，包括非整块、重复查询、零/全命中和边界半径；全部输出字节一致，代表性 TILE_E 通过 CUDA memcheck 与 synccheck。大规模部分先用独立旧 strict FR 实现生成完整参考，再对 GIST 三档半径和 Deep normal 的 50 个最终逻辑条件逐字节比较查询顺序、每个 ID 和 float32 距离；全部通过。Deep 开发集 16 个微块筛选条件也逐字节通过。正式计时的 300 个独立进程逐查询核对已审计结果的 count/有序 hash，并核对交付字节。审计明细在 [correctness.jsonl](correctness.jsonl)，原始收据、输出 hash、GPU 监控和 profiler 文件在 [raw_remote_runs.tar.gz](raw_remote_runs.tar.gz)，旧参考的命令/收据在 [strict_oracle_metadata.tar.gz](strict_oracle_metadata.tar.gz)。大规模完整输出是独立 GPU 参考的逐字节比对；不能将其表述成所有大规模对象对都经 CPU 复算，也不能外推任意未测输入的位级保证。

GIST 开发集 B=32 normal/half 的 Q_T=1/2/4/8 合计 Host-ready 时间分别为 5389/4613/4414/4854 ms；Deep 分别为 611/516/495/539 ms。Q_T=4 对 Q_T=2 的收益均低于预先约定的 5% 换档阈值，因此在生成最终 1024 查询之前，两数据集均冻结 Q_T=2，L/E 共用。开发记录在 [qt_sweep.csv](qt_sweep.csv) 和 [qt_sweep_deep.csv](qt_sweep_deep.csv)。

独立的 GIST 开发批次 NSYS 中，距离阶段占 GPU 阶段加 D2H 的约 99.4–99.6%。NCU 的同批次 kernel replay、`cache-control=none`、`clock-control=none` 记录：全维 GRID_L→TILE_L 的 DRAM 读 122.9→61.5 GB，提前退出 GRID_E→TILE_E 为 84.9→49.3 GB；全维全局加载请求约减半。全维距离 kernel 的寄存器由 32 增至 35/线程、动态共享存储 3840→7680 字节，未见 spill。这些计数只解释被剖析的开发批次，profiler 开销下的绝对时间不与正式计时混用。见 [profile_summary.csv](profile_summary.csv) 和 [ncu_summary.csv](ncu_summary.csv)。NCU 缓存和时钟没有做全局锁定，跨运行小差异不应过度解释。

GIST 的布局副本为 3.84 GB，Deep 为 0.384 GB；六轮正式进程的布局构建中位数约 21.0/2.2 ms，冷数据准备约 3.99/0.62 s，均单列而不混进热查询时间。监控到的 B=128 GPU 内存峰值上限约 9586 MiB（GIST）和 3012 MiB（Deep）；没有落地 B×N 的 FP64 距离矩阵。B=1 的旧输出路径→公共新收集器桥接在 GIST normal 的 L/L_E 上约 1.40/1.42×，这是公共输出修复，不能乘进 GRID→TILE 的复用收益；细节见 [bridge.csv](bridge.csv)。

## 尚未覆盖的边界

P4 需要为浅层 C4 生成候选/块掩码，并在相同批量距离核和完整输出路径下比较朴素候选与共享核验；本轮未实现，因此旧树报告的正向收益不能直接与这里的批量收益相乘。pro6000-8 当前环境没有 cuVS/RAFT 库，外部 pairwise-distance + 完整范围输出对照未运行；不能据此宣称超过 cuVS。当前实测只覆盖静态、库内查询、L2 完整范围输出，不覆盖在线队列、并发更新、top-k 或外部查询。额外的逐配对早退坐标工作量版也尚未测量；本文的物理复用结论依赖正式端到端配对和独立 NCU/NSYS 证据，而不是宣称完整工作量归因。

冻结基线为 `wangwenqingqq/GTS-variants@4eae62e53daeff0e040d26bbada9c60b8469e3aa`；正式二进制 SHA-256 为 `70462c768d50ad7349b7b0143572e9fa665b8116c6e1f2b41ff16e6b2de4e3c3`。GPU UUID、CUDA 13.1、驱动 590.48.01、数据/查询哈希、编译命令和归档 SHA-256 见 [PREFLIGHT.json](PREFLIGHT.json)、[EVIDENCE.json](EVIDENCE.json)。完整参考输出约 7.2 GB，保存在本地工作区 `gts_batch_evidence_20261001/` 而未纳入 Git；全命中 gzip 的 SHA-256 为 `7390b1fb18d7ecd84d7b78a3e4a10387b3ae69504a9cd16e72fcc3da8a37cff5`。
