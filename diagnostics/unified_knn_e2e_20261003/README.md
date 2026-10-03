# P7：统一 kNN 端到端实验

当前状态：已实现并通过 P7.0，21/21 个先导进程完成；开发网格及正式六轮仍在运行。原始上传 PLAN.md/CONTRACT.yaml 保留设计原文，实际进度以本文件和 evidence 为准。

自有三个模式为实验移植版 OPT-KNN-P7。核心实现提交 947b8b9bc1dd7465d6a275b4a0c9b6824c30f8c6；原始基线为 publication/gts-knn-comparisons-20261003@957ccf0，原搜索算术/剪枝/排序未改。gts_bench_p7 仅把原诊断适配器的两次预热改为固定开发批次，重新编译和计时，身份见 evidence/IDENTITY.json。

28 组小规模检查与独立 CPU 全枚举一致；1150198 个上界内对象均未被错误排除，树实际排除了397152个对象配对，非全放行退化；12 项独立 GPU memcheck/synccheck 检查通过。误差包围推导见 knn_reference_contract.md，逐项检查见 evidence/QUALIFICATION.json 和 evidence/SANITIZER.json。

[先导结果](PILOT_RESULTS.md)保留外部胜出和 CAGRA 漏检。正式结果将使用冻结后新生成、排除 P0–P6 及已见查询的256条/数据集，包含全部 O_* 和 Flat/全桶IVF，逐轮审核；不使用历史倍率补行。
