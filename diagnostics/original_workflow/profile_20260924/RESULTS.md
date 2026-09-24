# GPU2：原始 GTS 修复版的查询与更新分段实验

已按新授权在空闲 GPU2 完成 **36 个进程、3,648 次查询计数校验、4 份 NSYS trace**。14 项前置检查全部通过，其中 8 项为 memcheck/synccheck。运行前后及运行中检查未发现外来 GPU2 任务，结束时 GPU2 空闲。原版和一行修复基线均保留；此次未做新的算法优化。

结论：本轮高 CPU 用时主要与 CUDA 等待有关。仅改为阻塞等待，主线程 CPU 用时降低约 70%–73%，操作墙钟时间却增加约 20%。降低 CPU 占用和缩短查询延迟是不同目标。

| 工作负载 | 默认墙钟 ms | 阻塞墙钟 ms | 默认主线程 CPU ms | 阻塞主线程 CPU ms |
|---|---:|---:|---:|---:|
| 更新入口，128 次逐条范围查询 | 212.22 | 254.95 | 195.13 | 59.12 |
| 16 轮混合更新，共 432 操作 | 238.82 | 285.55 | 217.72 | 58.12 |

表中是各模式 3 个独立进程的中位数，计时范围为 `update.total`，不含输入读取、CUDA 初始化和首次建树。配对 CPU 降幅中位数分别为 69.7%、73.2%；配对墙钟增幅分别为 21.3%、19.7%。全部六对均表现为 CPU 用时下降、墙钟变慢。样本只有三组，全部保留，不报告统计显著性或泛化加速。

测试仍用 N1000/D128 的合成整数 L2 数据、半径0。128 次查询均按原生更新入口逐条执行，并非静态批量 Q128。混合负载每轮：查询→插入 row0→查询→删除该缓冲记录→查询→插入十条触发重建→查询→删除十条→查询，期望计数为 `1,2,1,11,1`。重复 16 轮后仍全部正确。row0 始终保留，峰值数据规模1010；不外推到任意重建后的 ID 语义或其他数据分布。

采用 CUDA13.1.115、PRO6000 Blackwell、驱动590.48.01、NSYS2025.5.2。同一 GPU、同一诊断二进制对比默认/阻塞等待，实际设备标志为8/12，调度位分别为0/4。诊断只增加主机计时/NVTX 标记；50 个 CUDA kernel 源码主体保持一致。原生树高3、叶容量20、缓冲阈值10、512线程均保留。同机其他 GPU 可运行其他任务，本轮不是整机隔离的性能基准。

**查询、重建和删除的具体位置已经分开。** 默认等待下，干净计时的128次查询中，遍历范围约100.75ms、叶子计算范围43.43ms、树结果组装22.53ms、最终合并13.10ms。这些主机范围包含已有等待，不能视为 CPU 算法计算时间。混合负载中，80次查询约140.87ms；插入范围79.49ms，其中16次重建78.38ms；176次删除约18.89ms。各项是独立中位数，且重建包含在插入内，不能重复相加。

默认等待的 NSYS trace 给出以下定位证据，trace 耗时不充当干净计时：

- 128次查询的 GPU kernel 区间共151.58ms，其中 `findNextRnn` 93.61ms，`leafProcessRnnUpdate` 42.38ms；`getQresultCount` 仅1.69ms。本轮主要 GPU 区间不在结果计数内核。kernel 区间可能包含 UVM fault 等停顿，未用 NCU 证明其为纯算术瓶颈。
- 16次重建的 GPU kernel 区间共69.94ms，其中 `getPivotDis` 50.93ms、`nodeSplit` 11.55ms、`getNewData` 5.93ms。建树距离和划分值得单独验证。
- 删除范围21.82ms，已记录 GPU 工作覆盖5.89ms，约27%；树结果组装和最终合并的 GPU 工作覆盖也较低。这些差额仍包含调度、分配、同步、UVM及 profiler 影响，不能直接叫作 CPU 计算。
- 无更新查询每次记录到16次 `cudaMalloc`、8次 `cudaMallocManaged`、24次 `cudaFree`、24次 kernel launch、12次 `cudaDeviceSynchronize`、9次 `cudaStreamSynchronize`，包含库调用。减少重复分配和主机控制往返有具体对象，但本轮没有测其可消除比例或加速收益。

**未观察到大块显式 CPU↔GPU 回传。** 128次查询的 `update.total` 内，显式 D2H 共1,024B；另记录统一内存 H2D 868,352B、D2H 913,408B，以及94个 CPU fault事件和2,761个 GPU page fault计数。混合流程另有约8.27MB的托管内存到显存 D2D 拷贝，主要来自重建。统一内存活动确实存在，但传输字节、fault计数、拷贝持续时间不能完整代表其服务延迟；不据此宣称 PCIe 带宽是主瓶颈或所有往返都冗余。

为控制计时改动，另测未插桩的一行修复二进制。三组按 `RDB / BDR / DRB` 顺序执行，R为未插桩默认等待，D/B为诊断默认/阻塞等待。原生打印的查询总时间 D/R 在0.953–1.014间；这里的负差异属于观测波动，不是“插桩带来加速”。完整配对值见 [samples.csv](results/samples.csv)，全部范围的原始计时见 [stages.csv](results/stages.csv)。

NSYS 的原始诊断信息含 `No NVTX events collected` 告警，但导出的 `NVTX_EVENTS` 表实际包含所需范围；分析逐一核对了自有范围次数与独立主机计数，全部一致，额外 Thrust/CUB 范围单独保留。告警原因尚未确定，原文未删除。另因关闭 context-switch tracing，未使用 NSYS 推断的线程调度状态；CPU结论来自 `CLOCK_THREAD_CPUTIME_ID`。GPU覆盖率是时间覆盖，非 SM 利用率；API等待与 GPU执行重叠，不能相加。

[CONTRACT.md](CONTRACT.md) 保存计时前冻结的有限方案；[EVIDENCE.json](results/EVIDENCE.json) 保存验证、分段、CUDA调用、迁移和原始文件哈希。所有原始日志、源码、输入和 trace 保存在本地 `../local/profile_raw/`，未纳入 Git；证据包为本地 `../local/profile_evidence.tgz`，SHA-256：

```text
36b6e274204d14f04d0c4c6b5379039bc4e4e4ea20b4d7ec12087e6a3adf0798
```

复现工具为 `prepare_profile.py`、`build_profile.py`、`run_profile.py`、`run_suite.py`；执行前重新核验空闲 GPU 及其锁。同一组对照固定物理 GPU；不得沿用上次空闲状态。分析无需 GPU：

```sh
python3 diagnostics/original_workflow/profile_20260924/analyze_profile.py \
  diagnostics/original_workflow/local/profile_raw "$NEW_REPORT_DIR"
```

下一轮应保持等待策略一致，分别做“距离内核改动”和“分配/同步改动”的单变量端到端对照，再验证更有代表性的工作负载。本轮不认证完整结果 IDs/距离、一般更新正确性、kNN、其他度量或所有 GPU tree；代码与汇总结果由 `wangwenqingqq/GTS-variants` 的 `analysis/gts-original-update-validation-20260924` 分支承载，未合并主分支。
