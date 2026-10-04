# 恢复执行角色及准入

本轮保留86cb65f全部失败与原计划文件，按[恢复说明](EXECUTION_RECOVERY.md)及[版本化策略](ADMISSION_POLICY.json)执行。尚未生成新的正式输入。

| 角色 | 实际入口/身份 | 数值、输出与维护边界 |
|---|---|---|
| 原版静态 | gts_bench_p7；binary `40c1cf9b1f0d855a4d4c1cd55a6e4916af90fc0ca75e18b5d8be372ba5dc2075` | 原始搜索算术、full-ID/capacity/FP32 loader适配；完整Host-ready输出计时 |
| 树kNN候选 | opt_knn_bench/O_MASK；binary `70520e34a97b155a0aeffa58d0b1c851684a6be4cd4fd71b170099da64cfae17` | 树mask、seed cutoff、验证和完整topK；静态layout/Graph setup单列 |
| 扫描控制 | 同bin/O_BOUND | 全对象遍历/早退；不能把其收益称为树剪枝收益 |
| 全扫描控制 | 同bin/O_FULL | 同selector与输出，关闭cutoff早退 |
| 原生Flat/IVF/CAGRA | 固定P7 native_knn.py派生八预热/窗口适配；当前安装库、源/库/索引hash重新核对 | 原生FP32字段；完整字段审查；strict失败为diagnostic，不修数值后冒充原生 |
| Range | 固定P4入口待补16-tail、完整输出与身份资格 | 独立variable-length范围契约；不是kNN替代品 |
| 原生更新 | U0修补bin `6c67544eb687c373bf71bf35662677dc7fb240d37cbd69b2f7462b911c4ce1e5`作正确性桥 | N1000/D128物理行重插、live-rank删除、串行逻辑多重集；lean计时入口另行资格 |
| 集成更新候选 | 无 | 不由静态扫描/树候选宣称统一keeper，也不阻断静态比较 |

搜索实现仍为P7 d65c6e4；编排来自7bce367。新runtime在独立任务目录，旧大输出/receipt只作匹配身份下的资格证据，不作为新计时进程。无树/扫描dispatch或新优化扫参；两类控制均保留。源码/二进制、数据/query/cache/library与实际命令写入私有执行卡，公开仅发布技术hash与契约。

CPU回归入口：`python3 test_recovery_cpu.py -v`，标准库、mocked receipts/audits，不加载GPU库。实际新入口为`campaign10k.py native-lane`、`native-development --dataset ... --family ... --pool dev1024|bulkdev10000`；oracle在外层独立锁进程先生成，再运行对应家族。`hook_control.py`先收集并决定观察成本；未获得`HOOK_CONTROL_ADMITTED.json`不生成正式查询。

观察成本预登记：每case六对fresh process，三对on/off、三对off/on，固定bootstrap seed2026100441；输出逐字节一致且paired slowdown upper95<=1.03才准入。原生数值失败不阻断这一对照。代表条件覆盖原版、tree/scan/full控制及快速原生B1/B32/bulk；开发输入与正式集分离。大型native调用只能在实际Host-ready调用边界观察，不能伪造内部1k交付或first/last2k时延。

预算检查：既有GIST/K8/B32原版1024为321.237s，线性预测10K单轮约52.3分钟、六轮约5.23GPU小时；原版八形状既有预测约25GPU小时。完整bulk网格、其他方法、原始工作流、R10与持续性另外收费。预测不当成实测或完工承诺；不降低Q、形状或六轮要求。
