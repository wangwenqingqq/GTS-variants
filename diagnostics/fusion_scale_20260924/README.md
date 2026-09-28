# Words 结果融合的规模实验

本目录回答：原先在 2,000 条 Words 上观察到的约 1.8× 查询加速，随数据规模如何变化。
两组均启用 CUDA Graph，只比较结果整理未融合 C 与结果整理融合 E。
不叠加遍历融合或数据布局变化。

- [实验约定](CONTRACT.md)：CUDA 编译和运行前冻结的比较、验证与计时口径。
- [预登记](PREREGISTRATION.json)：源码、输入、容量、运行计划的固定哈希；其中 pending 是登记时状态。
- [结果报告](RESULTS.md)、[数据表](RESULTS.csv)、[曲线](scale.png)。
- [审计证据](EVIDENCE.json)：各进程计时、配对区间、验证回执哈希与 profiler 签名。

`prepare.py` 从已有实验生成驱动，只将节点/结果容量、树高和融合核的容量断言扩展到本轮规模。
原作者源码按哈希复制，融合核仍为单 CTA、512 线程、逐 tile 扫描。
`fixtures.py` 构造嵌套数据集，保留 64 个相同查询词；`oracle.cpp` 独立计算 CPU 编辑距离。
`suite.py` 顺序执行所有 307 次运行并在每阶段检查失败；`verify.py` 核验完整输出。
`analyze.py` 独立审计全部原始记录，`report.py` 从审计结果生成报告及 PNG/SVG/PDF 曲线。

采集文件在忽略目录 `local/raw/`，包含原始输出、fixture、固定源码、二进制、编译记录、sanitizer 日志和 NSYS 数据。
不将大体积数据或机器身份写入版本控制。实验未修改生产查询实现。

从仓库根目录重做结果分析：

```bash
python3 diagnostics/fusion_scale_20260924/analyze.py \
  diagnostics/fusion_scale_20260924/local/raw \
  diagnostics/fusion_scale_20260924/EVIDENCE.json
python3 diagnostics/fusion_scale_20260924/report.py \
  diagnostics/fusion_scale_20260924/EVIDENCE.json \
  diagnostics/fusion_scale_20260924
```

重跑 GPU 采集需要按预登记恢复精确源码和输入、保留旧二进制锚点，并使用新的空运行目录。
`suite.py` 的参数为准备目录、`--gpu` UUID 与 `--index`，它持有既有 GPU advisory lock，
检查进程干扰，失败时停止且保留记录。不得覆盖或挑选已有计时结果。
