# P5 证据账本

| 判断 | 证据 | 限度 |
|---|---|---|
| 严格内部路径保持完整输出 | 新 qid 的旧 FR oracle；GIST half/normal 和 Deep 的完整 ID+距离二进制审核；GIST all 的 1024 个逐查询 1M 计数和有序哈希 | all 未物化 8.192 GB 的完整二进制；哈希不是数学证明 |
| 外部强基线可比 | cuVS C API 26.8.1，完整 B×N 距离矩阵分块，经相同阈值与收集交付；[源码](p5_external.cu)、[安装记录](EXTERNAL_INSTALL.log)、[数值审核](numerical_qualification.csv) | LIB32_U 和 GIST 的 LIB64_X 在最终集不满足严格数值合同 |
| GIST half 有树剪枝净收益 | [六轮配对](paired_final.csv)：B32 为 1.162×，6/6，完整输出相同；[开发同核实验](causal_dev.csv)：TA→TR 为 1.211×，M 比 S 慢 | normal/all/Deep 无可推广的树收益；B8 区间跨 1.10 门槛 |
| 节省发生在核验工作 | [候选账本](gist_half_candidates.summary.txt)：77.108% query-object 对；[NCU](ncu_summary.csv)：同符号、同 launch 的读量 -11.9%、FP64 指令 -17.2%；[Systems](profile_summary.csv)：距离核 52.347→43.411 ms | profiler 用独立的 32 开发查询；单核 DRAM 读量不等于端到端数据搬运 |
| Graph 差异没有解释扫描与树的差距 | [相同扫描器三轮 Graph/stream 对照](stream_comparison.csv) 差异小于 0.11% | 只针对扫描器及该开发工作负载 |
| 结果可复查 | [冻结参数与 qid](PREFLIGHT.json)、[原始收据](raw_remote_runs.tar.gz)、[环境](ENVIRONMENT.json)、[源码和二进制散列](SOURCE_PINS.json)；288/288 正式收据有效 | 时钟与缓存未固定；未覆盖其他 GPU、外部 query、在线并发 |

P4 之前的算术、AoSoA32、稳定收集、Graph 和树拓扑均作为冻结起点继承，历史收益未与 P5 相乘。本轮新增的因果因素是实际候选掩码与同核强对照；不把兄弟节点到同一 pivot 的距离称作重复计算。
