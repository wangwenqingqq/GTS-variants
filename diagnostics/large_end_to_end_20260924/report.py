#!/usr/bin/env python3
"""Render large-L2 per-improvement host-ready latency ledger."""
import csv
import json
import math
import statistics as st
from pathlib import Path

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm

HERE = Path(__file__).resolve().parent
DATASETS = ('GIST', 'Deep', 'Tloc')
SIZES = (65536, 1000000)
MODES = 'ABCDE'
PAIRS = ('A/B', 'B/C', 'B/D', 'C/E', 'D/E', 'A/E')
NAMES = {'A/B': 'fixed path', 'B/C': 'Graph (old result)',
         'B/D': 'fusion (stream)', 'C/E': 'fusion (Graph)',
         'D/E': 'Graph (fused)', 'A/E': 'all changes'}


def render():
    evidence = json.loads((HERE/'EVIDENCE.json').read_text())
    assert evidence['runs'] == 264
    records = []
    for d in DATASETS:
        for n in SIZES:
            item = evidence['data'][d][str(n)]
            row = {'dataset': d, 'n': n, 'dimension': item['dimension'],
                   'normal_radius': item['normal_radius'],
                   'tree_height': item['tree']['tree_height'],
                   'slots': item['tree']['slots'],
                   'host_bytes_fixed': 4+8*item['tree']['slots']}
            for mode in MODES:
                row[f'{mode}_ms'] = st.median(p['mean_us'] for p in item['primary'][mode])/1000
            for name in PAIRS:
                pair = item['ratios'][name]
                tag = name.replace('/', '_')
                row[f'{tag}_median_ratio'] = pair['ratio_of_medians']
                row[f'{tag}_paired_geomean'] = pair['paired_geomean']
                row[f'{tag}_ci_low'] = pair['bootstrap_95'][0]
                row[f'{tag}_ci_high'] = pair['bootstrap_95'][1]
                row[f'{tag}_wins'] = pair['wins']
                row[f'{tag}_sustained_forward'] = item['sustained'][0]['ratios'][name]
                row[f'{tag}_sustained_reverse'] = item['sustained'][1]['ratios'][name]
            records.append(row)
    with (HERE/'RESULTS.csv').open('w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=records[0])
        writer.writeheader()
        writer.writerows(records)

    matrix = [[math.log2(row[f"{name.replace('/', '_')}_median_ratio"]) for name in PAIRS]
              for row in records]
    cap = max(abs(value) for line in matrix for value in line)
    fig, ax = plt.subplots(figsize=(11.8, 4.7), constrained_layout=True)
    visual = ax.imshow(matrix, cmap='RdBu', norm=TwoSlopeNorm(vcenter=0, vmin=-cap, vmax=cap), aspect='auto')
    ax.set_xticks(range(len(PAIRS)), [NAMES[name] for name in PAIRS], rotation=20, ha='right')
    ax.set_yticks(range(len(records)), [f"{row['dataset']}  {row['n']:,}" for row in records])
    for i, row in enumerate(records):
        for j, name in enumerate(PAIRS):
            value = row[f"{name.replace('/', '_')}_median_ratio"]
            ax.text(j, i, f'{value:.3f}×', ha='center', va='center', fontsize=9,
                    color='white' if abs(matrix[i][j]) > cap*.48 else '#111')
    ax.set_title('Completed hot-query ratios: before / after  (>1 is faster)')
    fig.colorbar(visual, ax=ax, label='log₂ speedup', fraction=.035, pad=.025)
    fig.savefig(HERE/'improvement_ledger.png', dpi=180)
    plt.close(fig)

    lines = [
        '# 大规模端到端收益与对应改进', '',
        '在 GIST、Deep、Tloc 的 65,536 和 1,000,000 点上，同卡、同输入、同一二进制重新测量五条路径。'
        '所有数值是一次完整热查询的 host-ready 耗时；模式 A 是原查询函数，B 是固定容量普通 stream，'
        'C 在 B 上加入 CUDA Graph，D 在 B 上加入结果融合，E 同时使用结果融合与 Graph。', '',
        '![逐项改进的完整查询加速比](improvement_ledger.png)', '',
        '| 数据集 | N | A 原路径 ms | B 固定 stream ms | C +Graph ms | D +融合 ms | E 融合+Graph ms | A/E 累计 |',
        '|---|---:|---:|---:|---:|---:|---:|---:|',
    ]
    for row in records:
        lines.append(f"| {row['dataset']} | {row['n']:,} | "
                     + ' | '.join(f"{row[f'{mode}_ms']:.3f}" for mode in MODES)
                     + f" | {row['A_E_median_ratio']:.3f}× |")
    lines += ['',
        '表中耗时取四个独立进程均值的中位数。下表比值是两条路径的中位数之比；'
        '>1 为右侧改进更快，<1 为退化。括号内是**同一轮**比较时候选胜出的轮数（共 4 轮）。', '',
        '| 数据集 | N | A/B 固定路径 | B/C Graph | B/D 融合 | C/E Graph 下融合 | D/E 融合下 Graph | A/E 累计 |',
        '|---|---:|---:|---:|---:|---:|---:|---:|',
    ]
    for row in records:
        cells = [f"{row[name.replace('/', '_')+'_median_ratio']:.3f}× "
                 f"({row[name.replace('/', '_')+'_wins']}/4)" for name in PAIRS]
        lines.append(f"| {row['dataset']} | {row['n']:,} | " + ' | '.join(cells) + ' |')
    lines += ['',
        'A/B 是一整组实现变化：原路径每查询分配/释放临时结果，B 复用固定容量工作区并回传完整槽位。'
        '因此 A/B 不能归因于某个单独内核。B/C 与 D/E 分别隔离未融合、已融合条件下的 Graph 提交；'
        'B/D 与 C/E 分别隔离普通 stream、Graph 条件下的结果融合。A/E 是本轮同输入的累计观测，'
        '不由跨实验加速比相乘得到。所有模式保持原生布局、原遍历和距离算术。', '',
        '## 配对区间与长测', '',
        '每组四轮顺序为 ABCDE、EDCBA、CDEAB、BAEDC，并交替反转数据集与规模顺序。'
        '区间使用四轮 log 比值的全部 4^4 配对重采样；轮数有限，应结合两个相反顺序的加倍查询长测。'
        '下表列出 A/E 累计和隔离 Graph 的 B/C，以及结果融合的 C/E；其余逐对区间和长测见 CSV/EVIDENCE。', '',
        '| 数据集 | N | A/E 配对比值 [95%] | A/E 长测 正/反 | B/C [95%] | C/E [95%] |',
        '|---|---:|---|---|---|---|',
    ]
    for row in records:
        def ci(name):
            tag = name.replace('/', '_')
            return f"{row[tag+'_paired_geomean']:.4f} [{row[tag+'_ci_low']:.4f}, {row[tag+'_ci_high']:.4f}]"
        lines.append(f"| {row['dataset']} | {row['n']:,} | {ci('A/E')} | "
                     f"{row['A_E_sustained_forward']:.3f}× / {row['A_E_sustained_reverse']:.3f}× | "
                     f"{ci('B/C')} | {ci('C/E')} |")
    lines += ['',
        '## 核验与边界', '',
        '- 264 次运行经本地审计，包含 B/D 的完整 CPU float64 输出验证、Sanitizer、压力测试、'
        '120 次主计时、60 次长测和 12 次 stream trace。每次非完整输出运行都核对 CPU 验证后的原路径有序哈希。',
        '- B/D 的 profiler 内核签名分别与前一批同二进制的 C/E Graph 签名一致；'
        'Graph 比较保留相同 GPU 工作。Profiler 插桩时间不作为端到端加速比分母。',
        '- 热查询计时包含查询输入、GPU 计算、完整结果交付和 CPU 等待；'
        '不含数据载入、建树、工作区准备、Graph 捕获、预热或结果哈希。'
        'A 只回传有效结果，B/C/D/E 回传完整固定槽位，因此 A/B 与 A/E 不是等量字节传输比较。',
        f"- GPU {evidence['hardware']['gpu_index']} 为 RTX PRO 6000 Blackwell Server，CUDA 13.1.115。"
        'CPU 共享未绑核、GPU 时钟未锁；监控未检测到同卡外部进程。'
        '结论限于 batch=1、固定查询和半径、原生布局及原遍历。'
        '遍历融合和新布局尚无这些规模的有效数据，不列入累计收益。', '',
        '[原始数值](RESULTS.csv) · [审计证据](EVIDENCE.json) · [实验约定](CONTRACT.md)', '',
    ]
    (HERE/'RESULTS.md').write_text('\n'.join(lines))


if __name__ == '__main__':
    render()
