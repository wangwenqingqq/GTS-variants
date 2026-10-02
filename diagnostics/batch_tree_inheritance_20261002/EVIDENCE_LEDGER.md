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
