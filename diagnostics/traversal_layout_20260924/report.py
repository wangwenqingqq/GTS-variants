#!/usr/bin/env python3
"""Render the audited evidence without changing the registered decision rule."""
import argparse
import json
from pathlib import Path
import statistics as st


def render(e):
    datasets = e['datasets']
    selected = [(ds, m) for ds, v in datasets.items() for m in 'XY'
                if v['decisions'][m]['followup_warranted']]
    verdict = ('本轮没有一种组合达到预定跟进门槛；不将新布局加入推荐路径。' if not selected
               else '达到预定跟进门槛的组合：'+', '.join(ds+'/'+m for ds, m in selected)+'；仍未提升为生产实现。')
    lines = ['# 遍历融合 × 新布局 × 结果融合：组合实验', '',
             '**'+verdict+'**', '',
             '完成同卡同轮六组对照；所有性能组均保留结果融合和 CUDA Graph。', '',
             '| 模式 | 遍历 | pivot 布局 |', '|---|---|---|',
             '| E | 分阶段 | 原布局 |', '| R | 分阶段 | 连续布局 |',
             '| T | 分阶段 | 4 父节点 × 8 维分块 |',
             '| F | 融合 | 原布局 |', '| X | 融合 | 连续布局 |',
             '| Y | 融合 | 分块布局 |', '',
             '## 完整热查询延迟', '',
             '单位 μs；每组四个独立进程，每进程 64 次预热、512 次计时。'
             '表中为四个进程均值的中位数。包含输入/完整输出传输和 CPU 等待完成，'
             '不包含建树、布局准备、工作区初始化、Graph 捕获、预热和输出哈希。', '',
             '| 数据集 | E | R | T | F | X | Y |', '|---|---:|---:|---:|---:|---:|---:|']
    for ds, v in datasets.items():
        lines.append('| '+ds+' | '+' | '.join(f"{v['statistics'][m]['median_process_mean_query_us']:.3f}" for m in 'ERTFXY')+' |')
    lines += ['', '## 直接回答组合是否有用', '',
              '以下为中位耗时的相对变化，负数表示更快；不把历史不同轮次的收益连乘。', '',
              '| 数据集 | F 相对 E | X 相对 F | Y 相对 F | X 相对 E | Y 相对 E | 组合通过预定门槛 |',
              '|---|---:|---:|---:|---:|---:|---|']
    for ds, v in datasets.items():
        t = {m: x['median_process_mean_query_us'] for m, x in v['statistics'].items()}
        changes = [100*(t[b]/t[a]-1) for a, b in ['EF', 'FX', 'FY', 'EX', 'EY']]
        chosen = ', '.join(m for m in 'XY' if v['decisions'][m]['followup_warranted']) or '无'
        lines.append('| '+ds+' | '+' | '.join(f'{x:+.2f}%' for x in changes)+' | '+chosen+' |')
    lines += ['', '组合必须相对 E 和 F 都取得 4/4 轮胜出，配对加速比 95% bootstrap '
              '区间下界 >1.03，且两种长测顺序均无超过 5% 退化，才进入后续候选。'
              '本轮不改变生产路径。', '',
              '## 配对推断与交互效应', '',
              '比值分子为参照耗时，分母为候选耗时；>1 表示候选更快。'
              '四轮配对 log ratio，枚举 4^4 个重采样；四轮样本较少，仅作为有界筛选。', '',
              '| 数据集 | 比较 | 配对几何均值 | 95% 区间 | 胜出轮数 |',
              '|---|---|---:|---|---:|']
    for ds, v in datasets.items():
        for key, p in v['paired'].items():
            lo, hi = p['bootstrap_95']
            lines.append(f"| {ds} | {key[0]}/{key[1]} | {p['geomean']:.5f} | [{lo:.5f}, {hi:.5f}] | {p['wins']}/4 |")
    lines += ['', '交互效应为 `(F/X)/(E/R)` 或 `(F/Y)/(E/T)`；>1 表示布局在遍历融合后相对更有利，'
              '不等于组合本身快于 F。', '',
              '| 数据集 | 连续布局交互比 [95% 区间] | 分块布局交互比 [95% 区间] |',
              '|---|---|---|']
    for ds, v in datasets.items():
        cells = []
        for m in 'RT':
            p = v['interaction'][m]
            cells.append(f"{p['geomean']:.5f} [{p['bootstrap_95'][0]:.5f}, {p['bootstrap_95'][1]:.5f}]")
        lines.append('| '+ds+' | '+' | '.join(cells)+' |')
    lines += ['', '## 长测与准备成本', '',
              '正常半径长测每进程 4096 次查询；空结果/零半径/全命中仅有完整输出覆盖。', '',
              '| 数据集 | 顺序 | E | F | X | Y |', '|---|---|---:|---:|---:|---:|']
    for ds, v in datasets.items():
        for run in v['sustained']:
            lines.append('| '+ds+' | '+run['order']+' | '+' | '.join(f"{run['query_us'][m]:.3f}" for m in 'EFXY')+' |')
    lines += ['', '将本进程实际布局准备＋工作区初始化（已含捕获）＋首查询成本加到 512 次计时查询，'
              '再除以 512；单位 μs/查询，四进程中位数。该口径仍不含建树、加载和预热，不是完整冷启动。', '',
              '| 数据集 | E | R | T | F | X | Y |', '|---|---:|---:|---:|---:|---:|---:|']
    for ds, v in datasets.items():
        lines.append('| '+ds+' | '+' | '.join(f"{st.median(v['statistics'][m]['setup_first_plus_512_queries_us_per_query']):.3f}" for m in 'ERTFXY')+' |')
    lines += ['', '## 验证与诊断', '',
              '- 153 组完整结果验证：CPU oracle 的成员集合/距离、参考程序的 float32 位模式和稳定顺序。',
              '- 108 组 sanitizer：12 种 stream/Graph 模式的 memcheck/synccheck，六种 Graph 模式的 initcheck/racecheck；融合标记审计也经过四种检查。',
              '- 36 组压力运行，共 147456 次计时查询；72 组主计时，共 36864 次；36 组长测，共 147456 次。均逐查询核验完整有序输出哈希。',
              '- 18 组 NSYS：E/R/T 均为 17 kernels/query，F/X/Y 均为 13；每组检查 193 次 Graph 执行，下游结果融合及其他 kernel 签名一致。',
              '- 六组使用相同固定可执行文件；静态 SASS 和 NSYS 的函数身份、寄存器数关联通过。未新增 NCU 计数器实验，不能据此断言本轮减少了缓存事务。', '',
              '| 数据集 | E 遍历段 | F 遍历段 | X 遍历段 | Y 遍历段 |', '|---|---:|---:|---:|---:|']
    for ds, v in datasets.items():
        lines.append('| '+ds+' | '+' | '.join(f"{v['nsys'][m]['traversal_kernel_sum_us']:.3f}" for m in 'EFXY')+' |')
    lines += ['', '上表是 NSYS 诊断的遍历 kernel 时长总和，单位 μs；不是完整查询延迟，不能作为加速比分母。', '',
              '## 环境与边界', '',
              f"- 同一张物理 GPU {e['hardware']['gpu_index']}，{e['hardware']['gpu_name']}；CUDA 13.1.115，驱动 {e['hardware']['driver']}，sm_120，功率上限 {e['hardware']['power_limit']}。",
              '- N=2000，GIST/Deep/Tloc 为 960/96/2 维 float32 L2；64 个固定 query ID，batch=1，树高 3、fanout 10，固定容量。',
              '- GPU 时钟未锁定，CPU 共享且未绑核；抽样干扰监控通过不代表绝对独占硬件。未外推到百万规模、其他距离或动态更新。',
              '- 原 GPU 0 在 sanitizer 阶段受外部进程干扰而停止；完整失败记录保留，GPU 5 从头重复，未混用旧测量。',
              '- E 已包含结果融合与 Graph，原版 A 仅作正确性锚点；本轮不提供相对原始 GTS 的累计加速。', '',
              '所有进程均值、逐进程 p10/p50/p90、运行顺序、准备成本、输出/回执哈希、'
              '长测和 NSYS 证据见 [EVIDENCE.json](EVIDENCE.json)。'
              '复现约束见 [CONTRACT.md](CONTRACT.md)，中断与恢复见 [RESTART.md](RESTART.md)。', '']
    return '\n'.join(lines)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('evidence', type=Path)
    p.add_argument('output', type=Path)
    a = p.parse_args()
    a.output.write_text(render(json.loads(a.evidence.read_text())))
