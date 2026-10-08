# REGION_EXEC 原型

原生 range/update 有界子树执行实验；上游 `ZJU-DAILY/GTS@3bac1b725e92e98e3b69d5cb79ad9c56ccb5e639`，已资格化 lean 适配器来自 `ab742e2`。首个提交实现 NATIVE/PAR_STRONG 同入口桥接，尚无融合性能结论。

N1000/D128/B1/L2。U10 输入值是整数，原配置 `#define short float` 实际存储 float；保留原配置、float 累加、维度次序、pow、边界及对象自身分支。新路径仅支持此冻结接口，其他距离合同明确拒绝。

`PAR_STRONG` 一 block/parent、实际 pid 共享；当前层父标记只读，独立下一层输出。规范槽按终端叶编号和叶内顺序，共同稳定收集；原缓冲、live-rank、重数、删除和串行 ACK 保持。CPU RegionPlan 在初建及实际重建后通过计入成本的 D2H/规划/H2D 重建，初建单列，重建嵌入触发 insert。

`PAR_BRIDGE_CHECK.json`：两半径 × 两模式，小型 57-event/19-query mixed trace，每模式完整多重集/FP32/更新状态/6034 祖先成员校验通过；两模式有序输出逐字节一致。`test_plan.cpp` 独立覆盖对象255/256/257、非空节点127/128/129、root leaf和超预算叶 fallback。开发耗时不是正式性能证据。

执行文件位于用户指定 ANNS 目录；复用原 U10 输入、独立 CPU oracle 与设备独占 guard，不修改任何历史证据。
