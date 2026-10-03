# P7：统一 kNN 端到端实验

R2已完成六轮、516个独立进程：288个完整模式通过逐查询tie-aware 100%与完整Host字段检查；自有三个模式144个进程也通过固定ID排序参考。OPT-KNN-P7是静态实验执行器，统一查询／更新keeper仍未完成。

[最终结果](RESULTS.md)保留48行完整查询表、48行ANN目标表及全部失败锚点。GIST/Deep各1M，K8/32，B1/32；两份256条最终查询在参数冻结后生成且排除已见查询。B32下O_MASK仍慢于Flat；树掩码未取得稳定收益，所有B1均负收益。

核心实现提交`d65c6e41effad67dde8ae1f1f68e656562607817`；[身份](evidence/IDENTITY.json)、[来源清单](evidence/MANIFEST.json)记录源码、二进制、查询和原始收据哈希。R1流顺序缺陷的正式结果作废，R2保持448次开发选择不变并重跑。

28组小规模检查与CPU全枚举一致；1150198个上界内对象无错误排除，树实际排除397152个对象配对；12项memcheck/synccheck通过。推导见[参考契约](knn_reference_contract.md)。NSYS单独剖析；NCU启动失败，无物理计数结论。
