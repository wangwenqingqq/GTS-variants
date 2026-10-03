# 原版更新完整ID与主张收敛实验

R0/C0/U0已完成当前准入范围，见[RESULTS](RESULTS.md)。原版空缓冲返回非法ID1000；独立一行rnum清零修补在17个合法场景69个完整输出检查点通过，FN/FP/非法/重复ID均0；12项sanitizer通过，原版两个负例的成员错误仍保留。N1990原生固定高度容量拒收另存，不伪装成通过。

只验证原生重复引用现有行与逻辑序号多重集，不包含真实外部新ID到达、并发或一般动态100%保证。统一keeper未实现，Q0/U1不准入，M0取消；P7静态kNN已完成。历史时延/重建headline退出主结果。计划原文保持[PLAN](PLAN.md)，来源和状态以本目录结果及evidence为准。

全部旧标签处置见[CORRECTIONS](CORRECTIONS.md)，包括核对Tloc的GPU6身份与区别旧native-IVF八个失败锚点和本轮P7。
