# 搜索顺序收益空间：E0

实测结论见 [DECISION.md](DECISION.md)，逐轮干净时间见 [latency.csv](latency.csv)，汇总见 [summary.csv](summary.csv)。本轮按上传方案完成 E0，触发停止规则，E1/E2/E3 未进入。

- `PLAN.md`、`CONTRACT.yaml`：原始设计稿快照，保持事前约束；设计状态字段不代表当前实测状态。
- `SOURCE_PINS.json`：冻结提交、GPU UUID/NUMA、数据/树/种子/查询/库/二进制及源文件哈希。
- `ORACLE_MANIFEST.json`、`oracle_GIST_pilot32.json`：重新生成的独立 RN FP64 参考。STAR 仅取得标量 U_star，普通模式不加载 oracle。
- `ideal_cutoff.csv`：每查询 U0/U_star、候选与坐标更新、终端节点/对象保留比例；`evidence/count_*.pairs.csv` 保存配对并集及共享读取步数。
- `breakdown.csv`、`PROFILE_KERNELS.csv`、`profile_bridge.csv`：额外 query-only Graph 节点剖析及其计时桥接。
- `BRIDGE.json`：原无物化 pass 与新 O_MASK 的独立 ABBA 桥接，不进入主计时分母。
- `QUALIFICATION.json`、`evidence/`、`runs/`：小表检查、正式输出、质量、日志、独占监控与回执。大体积小表逐对象 audit 和完整 profiler trace 留在远端实验目录。

`prepare_source.py` 从相邻冻结 P7 源码生成 `headroom_bench.cu`。原来的距离、界与 top-K 头文件不修改；新 `headroom_count.cuh` 提供统一阈值物化核和单独的计数核。计数核只在正式 pass 交付后的诊断回放调用，不进入计时 Graph。

编译：

```bash
python diagnostics/search_ordering_headroom_20261003/prepare_source.py
nvcc -O3 -std=c++17 --fmad=false -arch=sm_120 -I/usr/local/cuda/include diagnostics/search_ordering_headroom_20261003/headroom_bench.cu -o headroom_bench
```

`run_e0.py` 中记录本次远端资产及解释器的准确路径。复现时准备相同哈希的资产，设置新的空 `ROOT`、可写的 `TMP`，保持冻结 GPU/NUMA 与参数，然后依次执行 `prepare`、`small`、`clean`、`count`、`bridge`、`profile`，最后运行 `analyze_e0.py`。所有 GPU 调用沿用钉住的 P7 独占 runner；正式计时严格为四轮×五模式，每个模式每轮独立进程。

本次远端结果目录为 `/home/data/wangxuran/tmp/gts_search_ordering_headroom_20261003/`，profiler 临时目录为 `/home/data/gts_search_ordering_tmp_20261003/`。运行目录已有记录时拒绝覆盖；小表仅允许核对相同命令、二进制和成功回执后重新汇总，不重复执行 GPU 测试。
