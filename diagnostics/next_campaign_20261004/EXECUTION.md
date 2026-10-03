# 10K 实验执行登记

计划固定为 `480bc7dbdfaf6ff7048bc810d29f6b4aecbf2e16`。独立工作分支 `experiments/10k-stability-20261004`；读取 P7 `7bce367` 的执行器，检索实现沿用 `d65c6e4`。原版静态比较沿用已声明的 full-ID/capacity 适配器，不替换原始检索算术。

`prepare_runtime.py` 创建独立运行目录：只扩展预热到每种实际形状八批、16 条尾批次预热、逐批时延、约每 1K 边界的 CPU/RSS/device-memory 快照、显式 eager/Graph 验证开关、100 次状态复用压力验证和执行超时参数。距离、剪枝、seed、selector 和 CUDA Graph 拓扑不变。原始源码及派生源码逐文件 SHA 写入 `SOURCE_BRIDGE.json`。窗口钩子的成本包含在时延中，其开销验证仍需登记。

2026-10-04 初始实时准入：RTX PRO 6000 Blackwell Server 96 GiB 的一张空闲 GPU，NUMA3。所有任务串行使用该物理 GPU 与既有两把锁；出现外部活动、错误或版本漂移时只终止任务自己的进程。原始设备/进程准入日志保存在私有实验目录，公开身份以模型、版本及内容 hash 标识。

开发 seed：GIST 2026100411、Deep 2026100412；bulk-development seed 2026100413/14。读取 P7 历史排除清单，加上其最终查询及 prior native 查询；分别生成唯一 1024 和唯一 10000 开发输入。正式 10K 使用 2026100421/22，只有全部参数、bulk 策略、生成器与排除清单冻结后才生成。正式输出逐查询、逐字段审查，不抽样。

Matched 使用 B1/B32，bulk 原生库测试 chunk 32/128/512/2048/8192/10000；GTS/当前优化入口固定支持的最大 B32。每个 native ANN 配置在新 1024 上跑两次；bulk 在独立开发 10K 上跑两次，冻结后才进入正式集。保留未达到目标的最高质量 CAGRA 点。六轮完整模式次序沿用 P7；ANN 三轮在完整模式前、三轮在后。

共用 device-memory 上限暂登记 80 GiB（96 GiB 设备），原始数据/index/layout/workspace 分开记录。运行超时初始 7200 秒，oracle/grid 上限 14400 秒；开发 1024 后重新核对原版预计耗时，再冻结实际正式限制。

## 可执行入口

运行器依赖 P7 的固定源码、原始 adapted headers、数据/index/图与现有独立 Faiss/cuVS 环境，路径作为私有执行卡保存。公开代码不包含这些大文件。

```bash
python3 prepare_runtime.py --p7 "$P7_SOURCE" --output "$NEW_RUNTIME"
# 在 NEW_RUNTIME 编译两种适配器，命令沿用 P7，记录完整命令及二进制 SHA。
python qualify10k.py --gpu "$SELECTED_GPU_UUID" --p7 "$P7_RUNTIME"
python campaign10k.py pipeline --gpu "$SELECTED_GPU_UUID" \
  --data-root "$DATA_ROOT" --faiss-python "$FAISS_PYTHON" \
  --cuvs-python "$CUVS_PYTHON" --p7 "$P7_RUNTIME"
```

`pipeline` 从开发筛选、bulk、正式输入冻结到静态 matched/bulk 矩阵；每个子进程保留 receipt/full output/审查结果，失败即停止，不能把已有失败目录当成功复用。F0_SMALL 尚未通过时不能启动开发矩阵。30K sustained、R10、U10-NATIVE 和归因各有独立准入，静态矩阵完成不等于整个计划完成。

## 范围/更新登记

R10 半径继承 P4：GIST half `0x3f34a3d8`、normal `0x3fb4a3d8`，Deep normal `0x3f8a3818`，Tloc `0x4045b6eb`（P4 实际 pilot 登记）。待核对对应数据/index、原版完整输出适配器以及 P4 16-tail 入口：P4 当前 parser 要求 Q%B==0，不能直接把 10000 当 10016。R10 五个条件保持 pending。

U10-NATIVE 固定 N1000/D128、100 cycles、每条10000 queries、1000 inserts、1000 deletes、50 个 occupancy=10 的 threshold rebuild；seeds 2026100431/32/33 在执行前登记，半径分别0/10000/512。使用 U0 修补后的原生观察二进制，三条完整-ID/字段/树覆盖审查已通过。观察打印不能作计时样本，没有观察打印的完整输出计时适配器与阶段归因仍 pending。U10-ARRIVAL 因统一 keeper/真实向量入口缺失而未准入。

## 本轮实际停止边界

F0小规模78进程通过；静态12条NSYS和8条NCU已采集，三条U10原生长轨迹通过。GIST1M/K8/B32/开发1024的原生Flat成员和字段未通过，主pipeline按wrong-result停止规则拒收。可选Flat取64候选后RN-FP64精算仅通过该1024开发集，随后在small96/K8/B1资格集失败，也停止晋升。详见 [RESULTS.md](RESULTS.md) 和 [ADMISSION_FAILURE.md](ADMISSION_FAILURE.md)。

正式10K尚未生成，native开发网格、bulk策略选择、其他静态形状、R10、30K持续性、窗口钩子开销和更新完整计时均未完成。上面的pipeline是分阶段入口，不是完成收据。断点恢复必须重新拒绝已有失败audit，不能跳过后把矩阵标为成功。

主检索源码/二进制在开发筛选中不变；编排脚本在正式输入生成前有迭代，`SOURCE_BRIDGE`与停止后的`SOURCE_SNAPSHOT`分开记录。当前源码快照不冒充所有早期脚本版本或最终正式冻结。`prepare_runtime.py`补齐编排辅助文件复制，使公开入口可复现；本轮早期运行通过单独复制提供这些文件。
