# A0 算子登记：尚未完成的行保持 pending

静态入口：P7 派生 `opt_knn_bench.cu`、`gts_bench_p7.cu`、`native_knn.py`。更新入口：上游 `3bac1b7` 的 `updateIndexRnn` 加 `rnum[0]=0`，使用独立 U0 观察二进制。kernel 名称与执行次数从实际 NSYS SQLite 获取，来源/二进制 hash 单独保存；下表不会把静态没有执行的更新算子删掉。

| 阶段 | 实际入口/算子 | 当前 CPU/GPU 证据 | 状态与边界 |
|---|---|---|---|
| 输入文件与加载 | f32bin/ID parser、native memmap、H2D | 每次 setup 字段；独立环境/输入 hash | 冷总时延分段仍 pending |
| 初始资源与分配 | cudaMalloc/Managed、Faiss StandardGpuResources、CuPy pool | setup；GPU 准入和峰值日志 | 分配调用细分 pending，不关闭库 scratch |
| 构建 pivot 距离 | indexConstru 的原始构建 kernel | 静态查询加载固定 index，不执行构建 | 更新/rebuild trace 中的运行归因 pending |
| 构建排序与排列 | 原版 Thrust sort、id_list | 输入 cache 完整排列/叶容量已审查 | 完整构建运行归因 pending；host 调库不等于 CPU 排序 |
| 查询输入提交 | H2D IDs；native gather | 12 条 B1/B32 NSYS，copies/API/CPU samples | measured，具体明细见 ATTRIBUTION.json |
| 原版 query-pivot | 原版 V2 tree traversal | 同一 NSYS 的实际 kernel 名称/次数 | measured，不能把兄弟节点不同半径划分叫重复距离 |
| seed/cutoff | seed_distances、block_topk、select_cutoff | NSYS；匹配的一次 NCU launch | measured，真实4096 seed，未使用 oracle cutoff |
| tree flags/mask | knn_parent_walk、knn_mask | NSYS；独立 NCU launch | measured；O_BOUND/O_FULL 不执行该阶段 |
| 叶/对象距离 | dataProcessKnn、verify_distances | NSYS 和实际 kernel 的 NCU | measured，单 kernel replay 不等于完整 pass |
| early exit | verify_distances 中定期 partial-sum 检查 | NCU 指令与 sectors/bytes | measured；地址效果/计算减少仍需因果控制 |
| counts/prefix | 原版 Thrust scan/reduce；range 输出 count | 静态原版 kNN 运行事件 | kNN measured；range/native update runtime pending |
| topK/merge | block_topk 各层、原版 sort、库原生 selector | NSYS；一次指定 block_topk NCU | measured；保留 score/workspace 成本 |
| 输出转换/Host-ready | final_output；native sqrt/ID cast；D2H/sync | 每次完整字段输出；NSYS APIs/copies | measured，10K 输出与稳定性门槛尚 pending |
| native 只读更新查询 | searchIndexRnnUpdate + buffer + mergeTotalResult | 三条长 replay，全部30000查询完整成员/字段通过 | correctness measured；观察日志时间不能作性能 |
| 插入 bookkeeping | insert_list[in_size]；occupancy==10 | native 来源已跟踪 | 新长 trace state/计时归因 pending |
| 基础删除定位 | bitmap inclusive_scan、findIdx、tombstone | native 来源已跟踪 | runtime pending；参数是 live rank |
| buffer 删除 | is_delete_in、inclusive_scan、mergeInResult | native 来源已跟踪 | runtime pending；删除最后一项返回空 buffer |
| query 删除 prefix | is_delete inclusive_scan；mergeTotalResult rank 转换 | native 来源已跟踪 | runtime pending；未实现缓存或宣称其收益 |
| compaction | data_d_temp D2D、getNewData | native 来源已跟踪 | runtime pending；包括分配、拷贝与旧状态释放 |
| rebuild | indexConstru；reset bitmap/buffer | 每seed实际50次；共153棵树含初始树、306000 ancestor/member检查 | 完整容量/覆盖correctness measured；timed adapter pending |
| publish/ACK | 原版 loop 下一事件 | 原版同步/控制流源证据 | 串行 loop 可见性；没有独立 RPC 或并发快照 |
| AoSoA refresh | 静态 pack32 / P4 pack | kNN 静态一次 setup；不接 native update | 更新不执行；统一 keeper 缺失，不隐藏维护 |
| Graph refresh | full/tail capture，地址生命周期 | 24 eager/Graph 对照；600 次复用；16 sanitizers | 小规模 measured；真实更新后重捕获未准入 |
| 清理/final drain | cudaFree/Graph destroy/stream destroy；native cleanup | 源码控制流；owned-process completion receipts | 独立清理时间/长 trace memory 高水位 pending |

CPU samples、进程 CPU-time delta、API inclusive wait、GPU union、真实 copies 和 UVM fault 分开记录。UVM faults 已在原版查询 trace 中观测到；fault 数不是迁移字节。无表导出时不能区分零事件与工具未提供。栈中未解析 IP 只按 module 合并，不把它们解释为某个 CPU 函数。

机制控制与晋升仍须 A2 独立登记。恢复 NCU 计数并不重新开启已取消的“纯合并访存”贡献。
