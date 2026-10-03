# U0、R0、C0收敛验证结果

已在pro6000-8物理GPU7（RTX PRO 6000 Blackwell、CUDA13.1）完成本计划当前准入工作。没有改变GPU设置、生产代码或引入新优化机制。R0/C0先做CPU核对；U0冻结源/输入/oracle后执行。

原版完整ID检查复现空缓冲失效：`insert row0 → query → delete rank1000 → query`最后期望`[0]`，实际`[0,1000]`。此时活对象1000个，ID1000非法。首次失败在step3，原版矩阵于第5场景停止；此前4场景通过。失败在[LOCALIZATION](evidence/LOCALIZATION.json)与完整原始stdout中保留。

原因是原版`rnum`只在非空缓冲搜索时更新，空缓冲仍加入旧值。定位后另编译一行修补`rnum[0]=0`，插在可选缓冲搜索之前。原版bin SHA `26afe17b…`，修补bin SHA `6c67544e…`；[原版/修补build身份](evidence/original.build.json)与[修补diff](rnum_reset.diff)独立登记。额外观测仅在原合并/同步之后读取完整ID/字段，并在建树后检查容量、排列和祖先成员，不改搜索算术或更新结构；这不是性能优化。

修补版17个合法场景、69个完整输出检查点全部通过。原生出现序号没有重复/非法ID，精确整数平方距离oracle下FN=FP=0，所有对应距离字段通过预先冻结误差门。不是只比较计数。

| 场景 | 完整查询检查点 | 实测状态 |
|---|---:|---|
| query_only | 3 | 通过 |
| all_include | 1 | 通过 |
| buffer_insert | 2 | 通过 |
| base_delete | 2 | 通过 |
| buffer_delete | 2 | 通过 |
| rebuild_no_prior_buffer_query | 1 | 通过 |
| rebuild_after_buffer_query | 3 | 通过 |
| mixed_delete_rebuild | 1 | 通过 |
| rebuild_then_delete | 2 | 通过 |
| zero_hit | 1 | 通过 |
| buffer_first_last_empty | 3 | 通过 |
| threshold_each_prefix | 14 | 通过 |
| rank_delete_twice | 2 | 通过 |
| tombstone_pending_rebuild | 4 | 通过 |
| far_buffer_then_rebuild | 14 | 通过 |
| tied_radius_boundary | 3 | 通过 |
| leaf_capacity_20（独立登记R2） | 11 | 通过 |

69个检查点包括空buffer、零命中、精确命中、全包含、首尾buffer删除至空、连续逻辑rank删除、阈值前/恰好重建/重建后、tombstone加pending buffer、不同物理行重复插入、半径边界等距、未更新的重复查询和合法叶容量20。观察到全部54134个祖先—成员关系在每次实际建树的原生FP32范数下落在其已存区间内；delete-only前缀保持原覆盖，pending buffer独立扫描。该检查不证明一般FP32实数距离上的sound pruning，也不验证未知新向量进入旧树。

原版另有容量限制：N1990、MAX_H3、MAX_SIZE20会将每个199项父节点分成9个19项子节点和最后一个28项子节点。最后子节点不能继续分裂，原树不完整。观测guard在任何query前以91退出，此次不能作计时或正确性通过。记录见[CAPACITY_REJECTION](evidence/CAPACITY_REJECTION.json)。只更换合法fixture：N2000初始叶正好20，先删10条，再逐条插入，恰好回到2000触发重建；重建后再插入1条位于buffer。新fixture提前登记commit e783832，源/bin保持不变，其余16个场景输入与契约逐项相同，不重跑已通过部分。不从N≤2000推断原固定高度对所有N均合法。

[12项sanitizer](evidence/U0_SANITIZER.json)均为0错误：修补版5个代表边界×memcheck/synccheck共10项，完整ID也通过；原版空buffer负例2项sanitizer通过但仍返回非法ID。这正是“sanitizer静默不能替代完整结果认证”。首次工具调用用相对可执行路径，runner收据收集失败，未接受；改成绝对工具路径后独立重跑，失败目录与原因留在RAW_MANIFEST，未修改runner。

本轮ID语义限定为原生逻辑多重集：insert/query引用当前物理数组行，delete引用当前存活序号，重建重排物理数组，返回ID随删除压缩。相同向量的不同出现有不同逻辑序号；连续delete rank1移除两个不同出现，不是稳定ID的幂等删除。原程序没有逐条RPC/ACK，所谓ACK是串行事件边界：触发重建的insert分支全部完成后才进入下一事件。没有独立的新向量/稳定外部ID输入接口，因此不准入真实新对象到达，也不宣称一般动态100%或并发查询/更新。

[R0](R0.md)已退役来源不完整的55.0→21.2→15.9→14.6μs与400→13→11主结果；恢复的旧原版9项计数收据是7通过、2失败，纠正“仅准备无outcome”标签，但未代替U0。[C0](C0.md)确认没有统一range/kNN/update keeper；Q0、U1前置条件未满足，未启动。M0按显式reuse窄表述取消。K0静态部分已有[P7六轮结果](../unified_knn_e2e_20261003/RESULTS.md)：强基线优势与掩码负收益均保留，不把P7称作统一keeper。

源码观测入口commit6f06897，合法容量fixture生成commit e783832；所有输入/事件、源与二进制SHA、命令、原始收据索引、归档SHA见[evidence/MANIFEST](evidence/MANIFEST.json)、[RAW_MANIFEST](evidence/RAW_MANIFEST.json)、[ARCHIVE](evidence/ARCHIVE.json)。完整stdout含所有ID/距离与实际树，保存在远端13MB原始bundle。过程wall与原main的更新平均数字均不作性能样本，不提供更新加速比。

重现：以八文件ORIGINAL_SOURCE验证上游`Source Code/GTS`目录；运行`python3 u0.py prepare SOURCE SCRATCH`，按build receipt编译observed。用现有P7 `run_locked.py`在空闲且加锁GPU执行`bin/u0_original_obs DATA UPDATES 2 RADIUS COST`，然后`python3 u0.py check SCRATCH CASE runs/LABEL/stdout.log`。遇首次差异停止；定位后`u0.py repair SCRATCH`并独立编译repaired，绝对路径compute-sanitizer作独立诊断。修补版69点正式来源为R1前16场景加R2合法容量场景；复现代码当前生成全部17个合法场景。无需新增runner。计划引用的ORIGINAL_PAPER_REUSE.md未随本次文件提供，未猜测页面级论文改写。
