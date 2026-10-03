# P4 证据账本

本轮以 `wangwenqingqq/GTS-variants@43463278fa1f2b7b8e6e36ff224e5c640036963e` 为冻结起点。历史证据保留原实验口径，不能与本轮收益相乘。

| 机制 | 历史来源与观测 | 本轮继承与检验 | 新语义 |
|---|---|---|---|
| 旧 GTS、`pow` 算术 | [距离路径报告](https://github.com/wangwenqingqq/GTS-variants/blob/8cf31c448b968398207fe5a5eb358121be64c134/diagnostics/arithmetic_path_boundary_20260928/REPORT.md)：固定工作量回放中 `pow` 很贵；该比值不是端到端收益 | 使用同一显式顺序 FP64 参考算术，并与旧 strict FR 完整输出比较 | 无 |
| 树拓扑、向外边界、C4/C1 | 同一报告：Tloc C4 正向，Deep C1 几乎不剪枝；GIST 单查询结果依半径变化 | 冻结原树 dump，父复用仅在实际 pivot ID 相同时生效；GIST 候选集合与旧 strict_walk 逐位置相同 | 有：批量树前缀与候选掩码 |
| 父 pivot 复用 | 旧树遍历中的共享 pivot 是同一查询内的距离复用；兄弟节点按同一 pivot 划分并非重复计算 | 每组核对 pivot ID 后算一次完整距离区间；账本记录 pivot 次数 | 无 |
| GPU Graph 与输出整理 | [Tloc 融合结果](https://github.com/wangwenqingqq/GTS-variants/blob/8cf31c448b968398207fe5a5eb358121be64c134/diagnostics/traversal_count_combo_20260924/TLOC_RESULTS.md)：去掉重复计数在当时单查询路径有收益 | P4 共用 P0–P3 的 Graph、稳定收集和两阶段有效长度 D2H | 无 |
| AoSoA32、跨查询对象复用、早退 | [P0–P3 报告](https://github.com/wangwenqingqq/GTS-variants/blob/8cf31c448b968398207fe5a5eb358121be64c134/diagnostics/batch_exact_highdim_20261001/RESULTS.md)，提交 `43463278fa1f2b7b8e6e36ff224e5c640036963e`：GIST/Deep B=32 的 TILE 相对 GRID 有正向收益，GIST 全命中早退不占优 | 同一新二进制内重测 SCAN_L/E；树模式共用布局、算术和输出，不能把旧收益另乘一遍 | 无 |
| `C_ID`、`C_MASK`、`C_TASK` | 历史没有与强批量 SCAN 在同一执行器内比较这三种组织 | 本轮唯一新增对照；三者使用完全相同的树候选集合，逐字节核对输出 | 有：候选组织方式 |

本轮最终计时、候选账本、profiler、源码/数据/query 哈希和原始收据索引见 [RESULTS.md](https://github.com/wangwenqingqq/GTS-variants/blob/8cf31c448b968398207fe5a5eb358121be64c134/diagnostics/batch_tree_inheritance_20261002/RESULTS.md) 与 [PREFLIGHT.json](https://github.com/wangwenqingqq/GTS-variants/blob/8cf31c448b968398207fe5a5eb358121be64c134/diagnostics/batch_tree_inheritance_20261002/PREFLIGHT.json)。

## 2026-10-03 convergence extension

**Status:** existing measurements were aligned with source identities; no new
GPU experiment was run. Mechanism experiments are complete at their registered
scopes; the integrated search/update version is not complete. This extension
continues P4's ledger rather than introducing a parallel evidence system.

### Candidate and comparator identity

- Original comparator: `ZJU-DAILY/GTS@3bac1b725e92e98e3b69d5cb79ad9c56ccb5e639`.
  The eight GTS CUDA files were locally rehashed against the existing manifest.
  Native range counts/kth distances are distinct from complete host-ID output.
- Recent original kNN adapter: measured binary
  `2871b26adf8b1109795291ffb0ff8645390365d89a20ec41ac3d6a239a27043c`;
  fixed MAX_H6, 1 GiB workspace, FP32 input loader and full-ID observation.
  It is not an untouched published executable.
- P4 static component: source snapshot
  `8cf31c448b968398207fe5a5eb358121be64c134`, measured binary
  `36adb09b490d124591e78f0332e0dd0c114ee8f621018b82ae7be3d8dd491c77`.
  `p4_bench.cu:10–161` shares P0–P3 object order, AoSoA32, explicit sequential
  FP64, Graph and stable full-result delivery; it adds static tree/mask/task
  organization. It contains no update loop or optimized kNN entry.
- Tloc count-removal binary and driver are separate. No current commit/hash
  represents a unified production query/update candidate. Root historical
  `include/src` remains incremental and is not the active original comparator.

### E1–E6 disposition and claim boundaries

| ID / proposed claim | Result and code entry | Verified scope / disposition | Missing or prohibited |
|---|---|---|---|
| E1 / resource lifetime | Original `update.cuh:341–348,589–628` contains transient query/result allocations | Source-established lifecycle traffic; no current qualified resource-only or complete-sequence measurement is registered here. | Historical claims require separately authorized provenance before reuse; no numerical implementation change may masquerade as allocation-only. |
| E2 / C2 phase continuity | [Fixed Tloc report](https://github.com/wangwenqingqq/GTS-variants/blob/f16d09a4e8a32ab8afff3b1b92221a5e447725a0/diagnostics/traversal_count_combo_20260924/TLOC_RESULTS.md), `prepare.py:18–40`; E/R/Q 3.809/1.228/0.929 ms | Four alternating process rounds, same binary **GPU6** (`TLOC_EVIDENCE.json`); R/Q full-output and memcheck/synccheck gates. Separate Graph driver, not production integration. | Not all fusion/coalescing, not P4 integration or dynamic throughput. P alone is bimodal and wins only 2/4. |
| E3 / C1 explicit reuse | [Fixed P0–P3 report](https://github.com/wangwenqingqq/GTS-variants/blob/43463278fa1f2b7b8e6e36ff224e5c640036963e/diagnostics/batch_exact_highdim_20261001/RESULTS.md), common `Batch` executor | Development GIST full-dimensional DRAM 122.9→61.5 GB; separately qualified final B32 Host-ready benefit. Same AoSoA32 in GRID/TILE. | Not pure layout/coalescing; read halving is not time halving; do not multiply with P4. |
| E4 / C1 candidate organization | This P4 report; `batch_tree_prefix.cuh:11–47`, `batch_candidate_tasks.cuh:7–101`, `p4_bench.cu` | GIST half B32 SCAN_E/C_MASK_E 1775.1/1521.8 ms per1024 queries, paired ratio1.16657; common candidates/collector. Positive Tloc B32; Deep, full-output GIST and Tloc B1 negative. | No universal ANN/index advantage; C_TASK's small additional gain is not a distinct major contribution. |
| E5 / maintenance attribution | Original `update.cuh:493–539`, `tree.cuh:361–383` contains buffer-triggered compaction/rebuild | Source-established maintenance amplification; reasonable-buffer comparator and complete operation costs required. | No current rebuild speedup claim; duplicate base-ID insertion cannot certify new arrivals. |
| E6 / C3 state safety | Public original-workflow preparation separates abandoned direct insertion from original buffering | Prepared probes are inputs/expectations; current candidate sequential visibility and external IDs are unclosed. | No transferred legacy bug/fix status, no certification from insert ACK, and no GPU result from expected counts. |

### External kNN counterevidence and cost ownership

The [native comparison](https://github.com/wangwenqingqq/GTS-variants/blob/8d300725eb0d9e1fd99213109b85cdff9b260b13/diagnostics/native_knn_faiss_ivf_20261003/RESULTS.md)
retains all failed frozen100% quality points. Later native all-list IVF1024/1024
reaches100% tie-aware recall on eight shapes; six-process Host-ready medians are
63.6–140.2× shorter than the original adapter. This is a **non-paired
supplement**, uses `GpuIndexIVFFlat` rather than a Flat API benchmark, and has
admissible GIST boundary ties rather than deterministic-ID parity. No optimized
GTS++ or update result follows. The [original-only pilot](https://github.com/wangwenqingqq/GTS-variants/blob/957ccf0b3592cebf2aeb49678a58f2c9379ed363/diagnostics/original_gts_compare_20261003/RESULTS.md)
does not fill that missing candidate.

In the GIST K8/B32 diagnostic, `dataProcessKnn` occupies99.087% of the recorded
query interval and GPU temporal work covers99.866%. Actual ordinary D2H/UVM
activity is small. The small Words query-only update trace instead has temporal
gaps and mostly one-block launches. Host synchronization overlaps GPU work;
neither trace establishes CPU distance arithmetic, bulk PCIe dominance, or a
universal GPU-tree bottleneck. Host-invoked `thrust::device` sorts/scans are GPU
work.

### Novelty and next evidence gate

[P5 complete-range evidence](https://github.com/wangwenqingqq/GTS-variants/blob/06570cd2e2857684984e43289d645b2b54903ae6/diagnostics/external_mask_validation_20261002/RESULTS.md)
also remains admitted at its own contract. P5 GIST half
B32 records C_MASK_E1526.3, SCAN_E1773.8 and qualified cuVS FP64 LIB64_U4786.4
ms per1024-query pass, paired ratios1.162/3.135. Deep's qualified LIB64_X is
faster; FP32 membership and GIST expanded-distance field failures are retained.
The same masked kernel's real/all candidate control establishes pruning
attribution, not coalescing-only benefit.
[P6 capability evidence](https://github.com/wangwenqingqq/GTS-variants/blob/f16d09a4e8a32ab8afff3b1b92221a5e447725a0/diagnostics/cagra_ivf_range_comparison_20261002/RESULTS.md)
retains the tested native GPU top-k/range
capabilities and K2048 capacity bound do not turn a truncated candidate result
into complete range output. Its custom full-bucket scan/reorder is not native
Faiss range performance. These frozen sets differ from P4; no cross-campaign
timing substitution is permitted.

Primary G-PICS leaf registration/reuse, Harmonia compact/query-organized GPU
trees, and MVGpuBTree device snapshots remain nearest mechanism precedents.
Generic pooling, batching, coalescing and GPU residency are not standalone new
contributions. A unified non-incremental thesis is not yet established.

Priority: close candidate/contract compatibility; recover or retire E1/E5;
check retained original update-prefix oracles before any new U0 tests; run an
integrated complete-query/sequence bridge only when a keeper exists. A
coalescing-specific experiment is conditional on retaining that claim, not
required to preserve the measured reuse/count-removal statements. Every new
run must identify one section, claim and missing qualifying evidence. No global
historical rerun or new optimization direction is authorized by this ledger.
