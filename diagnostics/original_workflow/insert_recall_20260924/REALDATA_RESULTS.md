# SIFT/GIST 大规模插入结果验证（2026-09-24）

更正后纳入结论的 5 次独立运行均通过完整结果核对：**85 次查询、101,220 个预期结果 ID**，没有漏报、多报、重复 ID 或超过 `1e-3` 的距离误差。符合半径的插入实例共 **107/107 次命中**；按各独立运行中的插入实例计为 **55/55 条**。这只说明所测数据、半径和更新序列，不证明任意插入均可百分百查到。

| 数据与规模 | 维度 | 半径 | 查询 | 预期结果 ID | 插入命中 | 完整结果 |
|---|---:|---:|---:|---:|---:|---|
| SIFT，1 万 | 128 | 0 | 17 | 38 | 21/21 | 通过 |
| SIFT，10 万 | 128 | 0 | 17 | 38 | 21/21 | 通过 |
| SIFT，100 万 | 128 | 0 | 17 | 39 | 21/21 | 通过 |
| SIFT，100 万 | 128 | 200 | 17 | 451 | 21/21 | 通过 |
| 原始浮点 GIST，10 万 | 960 | 1.5 | 17 | 100,654 | 23/23 | 通过 |

数据取自本机现有的 SIFT1M、GIST1M `base.fvecs`；两者也是 [ANN-Benchmarks 列出的欧氏距离数据集](https://github.com/erikbern/ann-benchmarks/blob/main/ann_benchmarks/datasets.py)。SIFT 的原始值是整数，GIST 保留原始 `float32`，没有量化；GIST 文本输入重新解析成 `float32` 后，10 万 × 960 个坐标与 `.fvecs` **逐元素完全相同**。CPU 真值针对这些实际浮点输入计算，输入及原始 `.fvecs` 的哈希见 [REALDATA_EVIDENCE.json](REALDATA_EVIDENCE.json)。

**源码类型更正：**原版 `include/config.cuh` 有 `#define short float`，`include/file.cuh` 在声明 `data_d` 前包含它。因此这条构建路径中的 `short *data_d` 预处理后是 `float *data_d`，`sizeof(short)` 也是 `sizeof(float)`，数值数组每元素占 4 字节。原先把 `short` 文本当成实际 16 位存储、进而认为 GIST 必须量化，是错误解释。先前量化 GIST 的运行保留在证据中，但不纳入上表；本次原始浮点 GIST 运行取代它。注释掉宏才会切换到真正的 `short`，并在读取浮点输入时损失小数精度。

原版固定 `MAX_H=3`、10 叉树、叶上限 20，名义叶容量约 2,000 条；直接声称在其原配置下测试 100 万条会失真。本轮从已验证的 `rnum_reset` 审计副本仅把 `MAX_H` 改为 6，精确差异见 [height6.patch](height6.patch)。实际树高在 SIFT 1 万、10 万、100 万时分别为 4、5、6，GIST 10 万为 5。缓冲阈值 10、树分裂、搜索和结果合并代码未改；审计输出仍仅在原有同步之后读取结果，不用于时延分析。

每次运行插入 10 条、触发一次重建，查询插入前后的原始行及重建后的插入行，删除一条已重建的插入记录，再插入和查询。独立 CPU oracle 对当前活动行逐条生成逻辑 ID 与距离真值，核对完整集合。插入记录在重建前命中 47/47、重建后未删除时命中 40/40、删除后查询中命中 20/20。GIST 的非零半径查询覆盖约 10 万个结果，能检查大结果集中的漏报和多报。

五次进程均正常退出，无记录到的 CUDA 运行错误、超时或运行中的外来 GPU 活动；按仓库约束每次检查空闲并持有设备锁。SIFT 运行使用 GPU3（`GPU-a149f5af-55ab-ce33-8d3d-371a7ae61dd2`）；原始浮点 GIST 启动前 GPU3 已被其他任务占用，故使用空闲 GPU4（`GPU-863c06a5-9f33-0265-b098-013fa840d5db`）。SIFT 原始记录在本地 `diagnostics/original_workflow/local/realdata_recall_primary_evidence.tgz`（SHA-256 `ee1972162145339e177c31be57711512f350e050f1a010f43d45303f7dc7dadb`）；原始浮点 GIST 的初次距离 oracle 错误记录、修正后的真值和 GPU4 重跑记录在 `diagnostics/original_workflow/local/realdata_float_correction_evidence.tgz`（SHA-256 `bc0fd1dfb1352223c2f4e5a11d646deb54d48faaee5282b619834db271f94472`）。修正的是 CPU oracle 曾对浮点平方距离错误地取整；二进制、输入文本及操作哈希均相同。大体积派生数据文本未打包，可由原始 `.fvecs` 和 [prepare_real.py](prepare_real.py) 重建。本轮没有把审计程序的用时当成端到端性能结果，也未在这些规模运行 sanitizer。

限制：API 插入的是已有数据行的副本；本轮仅测固定的 17 步序列、两个真实数据集及表中半径，不能外推到任意新向量、删除模式或无限次重建。源码基线为只读的 `ZJU-DAILY/GTS@3bac1b725e92e98e3b69d5cb79ad9c56ccb5e639`；提交目标是 `wangwenqingqq/GTS-variants`。
