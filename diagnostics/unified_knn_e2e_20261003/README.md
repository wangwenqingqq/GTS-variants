# P7：统一 kNN 端到端实验

当前状态：修复输入拷贝的 CUDA 流顺序后，28 组资格和12项 GPU 检查再次通过；R1正式轮作废归档，R2先导与正式六轮重跑。原开发448次pass和所选参数保持不变，R1所有最终查询ID加入新排除集。原始上传 PLAN.md/CONTRACT.yaml 保留设计原文，实际进度以本文件和 evidence 为准。

自有三个模式为实验移植版 OPT-KNN-P7。核心实现提交 d65c6e41effad67dde8ae1f1f68e656562607817；原始基线为 publication/gts-knn-comparisons-20261003@957ccf0，原搜索算术/剪枝/排序未改。gts_bench_p7 仅把原诊断适配器的两次预热改为固定开发批次，重新编译和计时，身份见 evidence/IDENTITY.json。

28 组小规模检查与独立 CPU 全枚举一致；1150198 个上界内对象均未被错误排除，树实际排除了397152个对象配对，非全放行退化；12 项独立 GPU memcheck/synccheck 检查通过。误差包围推导见 knn_reference_contract.md，逐项检查见 evidence/QUALIFICATION.json 和 evidence/SANITIZER.json。

[先导结果](PILOT_RESULTS.md)保留外部胜出和 CAGRA 漏检。正式结果将使用冻结后新生成、排除 P0–P6 及已见查询的256条/数据集，包含全部 O_* 和 Flat/全桶IVF，逐轮审核；不使用历史倍率补行。
