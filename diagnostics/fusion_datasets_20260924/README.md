# 不同数据集上的结果融合实验

复测 Words、GIST、Deep、Tloc 各 2,000 条的固定查询样本，比较同一程序中的
C（原结果整理＋CUDA Graph）和 E（结果整理融合＋CUDA Graph）。
原始 2,000 条 Words 二进制另作同会话桥接对照，结果不混入四组比较。

[完整报告](RESULTS.md) · [曲线](datasets.png) · [数值表](RESULTS.csv) ·
[机器可读证据](EVIDENCE.json) · [预登记约定](CONTRACT.md)

`prepare.py` 从已核验的作者源码、Words 规模实验 fixture，以及此前 GIST/Deep/Tloc
的独立 CPU oracle fixture 准备实验。只放宽驱动的数据维度/度量断言，完整输出文本保留
9 位十进制精度以核验 float32 位模式。`verify.py` 对完整输出执行独立 CPU 成员与距离检查，
再与原查询路径比较完整顺序和 float32 位；`suite.py` 在同一 GPU 锁中执行全部阶段，
出错立即停止。`analyze.py` 独立审计所有运行后计算六轮配对统计；`report.py` 生成表格和
PNG/SVG/PDF 图。

原始输入、生成源码、二进制、sanitizer 与 profiler 记录在忽略目录 `local/raw/`。
不把大数据或机器身份纳入版本控制；未修改生产查询路径。

从仓库根目录重做分析：

```bash
python3 diagnostics/fusion_datasets_20260924/analyze.py \
  diagnostics/fusion_datasets_20260924/local/raw \
  diagnostics/fusion_datasets_20260924/EVIDENCE.json
python3 diagnostics/fusion_datasets_20260924/report.py \
  diagnostics/fusion_datasets_20260924/EVIDENCE.json \
  diagnostics/fusion_datasets_20260924
```
