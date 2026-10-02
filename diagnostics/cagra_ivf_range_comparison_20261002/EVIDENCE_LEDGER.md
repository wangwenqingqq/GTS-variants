# P6 证据账本

| 判断 | 原始证据 | 边界 |
|---|---|---|
| 目标 GPU 与能力限制 | [CAPABILITIES.json](CAPABILITIES.json)、[SOURCE_PINS.json](SOURCE_PINS.json)、[raw_remote_runs.tar.gz](raw_remote_runs.tar.gz) 中 capability smoke 收据 | CAGRA K≤1024；Faiss 原生 GPU K/nprobe≤2048；GPU range API 实测不支持；失败路径保留，不按 CPU 结果替代。 |
| 开发参数冻结先于新最终 qid | [FROZEN_CONFIG.json](FROZEN_CONFIG.json)、[QUERY_SETS.json](QUERY_SETS.json)、[development_raw.json](development_raw.json) | 42 个开发点、三轮；两个新 1024 qid 与已见 ID 交集为零。冻结文件哈希写入查询记录。 |
| 严格完整输出 | [numerical_qualification.csv](numerical_qualification.csv)、[exact_latency.csv](exact_latency.csv)、[ivf_full_latency.csv](ivf_full_latency.csv) | half/normal/Deep 逐字节；all 只比较逐查询完整计数与有序哈希。IVF 自定义全桶扫描恢复参考顺序后逐位一致。 |
| 候选质量及结构性容量 | [range_quality.csv](range_quality.csv)、[CAPACITY_BOUNDARY.json](CAPACITY_BOUNDARY.json)、[bucket_coverage.csv](bucket_coverage.csv) | 微/宏 RangeRecall、去 self、漏检与 K 上限分别呈现。容量上限仅离线评测，运行时未使用 truth count。 |
| 全流程 Host-ready 时延 | [native_latency.csv](native_latency.csv)、[refined_latency.csv](refined_latency.csv)、[exact_latency.csv](exact_latency.csv)、[ivf_full_latency.csv](ivf_full_latency.csv) | 同一模式的六个独立正式进程取中位；原生 top-K 时延不能配精算后的 RangeRecall。 |
| 静态成本与阶段 | [BUILD_COST.csv](BUILD_COST.csv)、[IVF_LAYOUT.json](IVF_LAYOUT.json)、[EXACT_SETUP.json](EXACT_SETUP.json)、[latency_breakdown.csv](latency_breakdown.csv) | 构建/布局与热查询分列；精算减原生是接口可见残差，不是孤立 kernel 时间。 |
| GPU 活动 | [profile_summary.csv](profile_summary.csv)、[raw_remote_runs.tar.gz](raw_remote_runs.tar.gz) 中两条 `.nsys-rep` | 整进程开发 trace 含构建与预热，仅用于确认实际 kernel，不能作为热查询 breakdown。 |
| 可追溯运行 | [ARTIFACT_MANIFEST.json](ARTIFACT_MANIFEST.json)、[raw_remote_runs.tar.gz](raw_remote_runs.tar.gz) | 144 个完整精确、60 个候选、36 个自定义 IVF 正式进程全部有效；42 个开发点有效；外来 GPU 进程观测为零。11 个早期失败收据保留。 |

Faiss 全桶适配器的精确定义：由原生 GPU IVFFlat 构建 nlist1024 的倒排桶，导出所有桶内 ID；P4 `SCAN_E` 按此排列完整扫描全部 1M 向量；Host 用唯一参考名次 quicksort 恢复共同顺序。由于 P4 的 SCAN 模式加载器也验证树文件内的 ID 顺序，诊断脚本仅复制树文件并将其末尾的 ID 顺序字段换成桶顺序，断言原字段等于参考排列；SCAN 不使用树节点。初次校验失败与较慢的 stable-sort 试跑保存在 archive，正式 36 轮均由 quicksort 版本重跑。该结果不能称为原生 Faiss range API 性能，也不证明其他自定义 IVF range 实现的性能下界。

冻结配置内 `dev_source_sha256` 的 `refined_latency.csv`、`range_quality.csv` 指向冻结时的开发集快照；提交时分别保存为 [dev_refined_latency.csv](dev_refined_latency.csv)、[dev_range_quality.csv](dev_range_quality.csv)，哈希逐字节相同。无 `dev_` 前缀的同名 CSV 是开发+最终合并视图，不应再与冻结哈希直接比较。

实验限定与上传计划的差异：合法 K 与 nprobe 被实际版本限制，故不运行 K8192、CAGRA K2048、Faiss K4096、nlist4096 的全探桶 native top-K。所有开发点低于 90% 微召回锚点，因此不以测试集调高预算或报告虚构的达标时延。GIST all 只保留容量边界及精确模式计数/哈希，不物化十亿条命中的候选实验。CPU 原生 Faiss range 没有放进同 GPU 主表；本轮未进行 kNN 速度排名、在线更新或并发测试。
