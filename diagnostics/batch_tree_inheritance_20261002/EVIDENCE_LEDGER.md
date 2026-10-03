# P4 证据账本

本轮以 `wangwenqingqq/GTS-variants@43463278fa1f2b7b8e6e36ff224e5c640036963e` 为冻结起点。历史证据保留原实验口径，不能与本轮收益相乘。

| 机制 | 历史来源与观测 | 本轮继承与检验 | 新语义 |
|---|---|---|---|
| 旧 GTS、`pow` 算术 | [距离路径报告](../arithmetic_path_boundary_20260928/REPORT.md)：固定工作量回放中 `pow` 很贵；该比值不是端到端收益 | 使用同一显式顺序 FP64 参考算术，并与旧 strict FR 完整输出比较 | 无 |
| 树拓扑、向外边界、C4/C1 | 同一报告：Tloc C4 正向，Deep C1 几乎不剪枝；GIST 单查询结果依半径变化 | 冻结原树 dump，父复用仅在实际 pivot ID 相同时生效；GIST 候选集合与旧 strict_walk 逐位置相同 | 有：批量树前缀与候选掩码 |
| 父 pivot 复用 | 旧树遍历中的共享 pivot 是同一查询内的距离复用；兄弟节点按同一 pivot 划分并非重复计算 | 每组核对 pivot ID 后算一次完整距离区间；账本记录 pivot 次数 | 无 |
| GPU Graph 与输出整理 | [Tloc 融合结果](../traversal_count_combo_20260924/TLOC_RESULTS.md)：去掉重复计数在当时单查询路径有收益 | P4 共用 P0–P3 的 Graph、稳定收集和两阶段有效长度 D2H | 无 |
| AoSoA32、跨查询对象复用、早退 | [P0–P3 报告](../batch_exact_highdim_20261001/RESULTS.md)，提交 `43463278fa1f2b7b8e6e36ff224e5c640036963e`：GIST/Deep B=32 的 TILE 相对 GRID 有正向收益，GIST 全命中早退不占优 | 同一新二进制内重测 SCAN_L/E；树模式共用布局、算术和输出，不能把旧收益另乘一遍 | 无 |
| `C_ID`、`C_MASK`、`C_TASK` | 历史没有与强批量 SCAN 在同一执行器内比较这三种组织 | 本轮唯一新增对照；三者使用完全相同的树候选集合，逐字节核对输出 | 有：候选组织方式 |

本轮最终计时、候选账本、profiler、源码/数据/query 哈希和原始收据索引见 [RESULTS.md](RESULTS.md) 与 [PREFLIGHT.json](PREFLIGHT.json)。

## 2026-10-03 收敛补记

上方历史六项原文保留；其相对链接在[原P4目录](https://github.com/wangwenqingqq/GTS-variants/tree/f16d09a4e8a32ab8afff3b1b92221a5e447725a0/diagnostics/batch_tree_inheritance_20261002)解析。本补记不合并旧分支历史。

| 项目 | 入口/契约/来源 | 完整时延与质量 | 正向与负向边界 | 允许论文表述 |
|---|---|---|---|---|
| K0静态kNN部分/P7 | OPT-KNN-P7@d65c6e4；P7 CONTRACT、IDENTITY、MANIFEST；R2 516进程，六轮配对，新最终查询，原始大输出远端保留SHA | GIST/K8/B32的256查询原GTS80743.955ms、O_BOUND1069.359ms、O_MASK1048.636ms、native Flat54.844ms。288完整进程逐查询tie-aware100%，自有144个确定ID100%；字段全部通过 | 替换原执行器收益明确；B32树掩码CI跨1、所有B1负收益，Flat显著领先；ANN100%开发不可达与12个最终失败均保留 | 静态实验执行器相对原GTS收益，不是统一query/update系统或强基线胜出；不由kNN代替range |
| R0历史E1/E5 | [审计](../claim_closure_20261003/R0.md)；有限历史索引与原始工作流记录 | 本轮无GPU计时；55.0→21.2→15.9→14.6μs和400→13→11原始运行身份未闭合 | 旧源/报告不能绑定完整trace与输出合法性；不重跑以保存headline | 数字退出主结果，只能标历史转述；分配与数值intrinsic分开 |
| C0统一入口 | [兼容性决定](../claim_closure_20261003/C0.md)、八文件原版manifest与各独立静态bin | 没有统一range/kNN/update keeper，无同契约集成时延分母 | 原生逻辑多重集≠稳定外部ID；重建使排列/布局/bounds/Graph失效 | “集成未完成”；Q0/U1前提未满足，M0按窄reuse表述取消 |
| U0原生更新完整ID | [结果](../claim_closure_20261003/RESULTS.md)、U0_NATIVE_LOGICAL_MULTISET、6f06897观测源、e783832合法容量fixture、MANIFEST/RAW_MANIFEST/13MB原始bundle SHA | 17合法场景69完整检查点，FN/FP/非法/重复ID均0；12项memcheck/synccheck零错误。观察过程不作计时样本，无性能倍率分母 | 原版在第五场景空buffer返回非法rank1000；独立rnum清零修补通过。N1990/MAX_H3容量不合法提前拒收，单独登记合法N2000场景；原版sanitizer可通过但输出仍错 | 一行正确性修补通过有界原生重复行/逻辑序号测试；不称真实新对象到达、稳定外部ID、通用动态100%、并发或更新性能收益 |
