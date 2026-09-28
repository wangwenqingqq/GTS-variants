# 遍历融合 × 新布局 × 结果融合

**已完成：423 次 GPU 5 运行及独立审计全部通过；没有组合达到预定跟进门槛。**

[完整结果与配对区间](RESULTS.md) · [机器可读证据](EVIDENCE.json) · [状态与哈希](CHECKPOINT.json)

GIST、Deep、Tloc 均为 N=2000、batch=1、float32 L2。六组性能对照共同保留结果融合和 CUDA Graph：

| 模式 | 遍历 | pivot 布局 |
|---|---|---|
| E | 分阶段 | 原布局 |
| R | 分阶段 | 连续 |
| T | 分阶段 | 分块 |
| F | 融合 | 原布局 |
| X | 融合 | 连续 |
| Y | 融合 | 分块 |

连续布局相对 F 的热查询耗时变化为 GIST −0.01%、Deep −0.04%、Tloc −1.11%；
分块布局为 +0.63%、+1.02%、−1.20%。Tloc 两种布局都只有 2/4 轮胜出，
配对区间均跨过 1，反向长测中均更慢。完整数据保留在结果报告，未修改生产路径。

NSYS 确认 E/R/T 为 17 kernels/query，F/X/Y 为 13；下游 kernel 签名一致。
这些是相对已经采用结果融合和 Graph 的基线的增量比较，不是相对原始 GTS 的总加速。

## 验证

- 153 组完整 ID、距离、float32 位模式及稳定顺序检查。
- 108 组 memcheck、synccheck、initcheck、racecheck。
- 36 组压力测试、72 组配对计时、36 组双顺序长测；所有查询核验完整有序输出哈希。
- 18 组 NSYS，核验函数身份、17/13 个 kernel、寄存器与公共下游流程。
- 源码、生成器输出、fixture、binary、原始回执与阶段日志的哈希/内容关联通过。

[CONTRACT.md](CONTRACT.md) 保留原始预注册，不追改阈值。
运行边界为热查询输入到完整输出在 CPU 就绪；建树、初始化、捕获、预热、哈希不计入。
准备及首查询成本另列。CPU 共享、GPU 时钟未锁定，干扰检查是抽样监控。

## 恢复与复现

原 GPU 0 在 Deep memcheck 阶段遇到外部 GPU 进程而停止；191 份记录保留，
其中无性能样本。GPU 5 在执行前记录修订并从头重复完整协议，未混用旧观察。
GPU 5 压力测试期间 SSH 中断，但远端 36 组压力运行继续并全部完成；
后续计时在完整阶段边界接续，未重复或替换样本。
详见 [RESTART.md](RESTART.md)、[INTERRUPTED_ATTEMPT.json](INTERRUPTED_ATTEMPT.json)
和 [TRANSPORT_CONTINUATION.json](TRANSPORT_CONTINUATION.json)。

- `prepare.py` / `test_cpu.py`：依赖本仓库既有生成器及外部 pinned 作者源码；恢复生成物与远端留存文件逐字节一致。
- `restart.py`：从留存的中断 artifact 创建全新目录，校验 pins、获取已有 GPU 锁、记录修订后执行完整协议。
- `finish_after_transport.sh`：仅在旧进程退出且压力阶段完整通过后衔接未运行阶段。
- `audit_static.py ROOT STATIC_EVIDENCE.json`：从同一 binary 的 cuobjdump 文件重建静态证据。
- `summarize.py ROOT EVIDENCE.json`：验证全部运行、哈希、阶段日志、输出及轨迹后生成统计，任一检查失败则拒绝输出。
- `report.py EVIDENCE.json RESULTS.md`：生成报告。

留存原始证据在 `local/raw`，中断记录在 `local/interrupted_gpu0`；均被 Git 忽略。
fixture、外部生成源码、可执行文件、日志及机器身份未加入版本控制。
