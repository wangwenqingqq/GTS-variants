# 无新增GPU实验的标签纠正

按PLAN §2登记最终边界；历史计时原样保留，旧报告不被改写为本轮复现。来源文件哈希见[CORRECTION_INPUTS](evidence/CORRECTION_INPUTS.json)、LOCAL_RECOVERY_INPUTS与各独立实验manifest。

| 旧风险 | 本轮采用的解释与来源 |
|---|---|
| Tloc GPU4标签 | 直接读TLOC_EVIDENCE：**GPU6**，bin SHA `1f6ca13bfc4e01449b85995acefa545ee81dede85f58197c199fce3202341ee3`。E/P/R/Q原轮次与输出相等、R/Q检查保留；P双峰不支持单独稳定收益。原文件SHA `d8f514f6…`，不新跑 |
| GRID→TILE纯布局/coalescing | 共同AoSoA32上的显式跨查询复用；开发DRAM122.9→61.5GB不代表纯地址布局或时延减半。取消M0，不保留纯coalescing贡献 |
| 去dead-count、Graph/pooling都叫融合 | 分别是依赖移除、提交/内存生命周期复用、producer-consumer融合。P4实际长度反馈不能按旧dead-count直接删除 |
| API wait=CPU算术或PCIe物理时长 | 旧与P7 NSYS都显示长API等待与GPU执行重叠。P7原GTS开发K8/B32的10.157s范围中，叶距离约10.066s；不把API与GPU相加，不泛化所有GPU树 |
| 先前全桶IVF=Flat/配对实测 | [先前native-kNN结果](../native_knn_faiss_ivf_20261003/RESULTS.md)调用GpuIndexIVFFlat，1024桶全探测，补充六进程比较**非配对**。P7才另测native Flat与配对轮，二者不互换 |
| 旧100%参数全通过 | 先前native-IVF开发选择的八个最终100%锚点全部失败；99/99.9%最低目标不等于相同实得质量。P7新最终集的14个可执行100%锚点中2通过/12失败，另2个开发不可达，不混淆两次实验 |
| latest HEAD=统一GTS++ | P4 range和P7 kNN均是独立静态执行器；原生update另测。没有统一query/update keeper，C0/Q0/U1边界不变 |
| 旧direct-insert失败证明原始GTS失败 | 旧stride/祖先负证据属于已弃用incremental；本轮原始buffered GTS实际定位的是空buffer rnum失效，不能互相转移 |
| 原9项仅准备、无运行收据 | 本轮已恢复2026-09-24原版九个计数收据：7通过/2失败。与早期PREFLIGHT仅准备阶段区分；仍没有完整ID资格，本次由U0补充 |
| 55.0→21.2→15.9→14.6μs、400→13→11当前有效 | R0未恢复完整运行身份，退出主结果；末步数值intrinsic与分配-only分开；buffer调优和leaf机制不能互相归因 |
| gamma=1自动精确 | 只恢复相应GTS剪枝基线；仍须独立oracle。P7/U0实际检验不以gamma开关推断完整性 |

原始论文页面复用附件未随此次上传提供；不猜页面级改写，也不从当前L2记录补一般度量或九数据集主张。
