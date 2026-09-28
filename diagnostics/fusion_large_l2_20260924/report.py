#!/usr/bin/env python3
"""Render the audited large-L2 fusion campaign without changing its evidence."""
import csv
import json
import statistics as st
from pathlib import Path

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
DATASETS = ('GIST', 'Deep', 'Tloc')
SIZES = (65536, 1000000)


def render():
    evidence = json.loads((HERE / 'EVIDENCE.json').read_text())
    assert evidence['runs'] == 192
    records = []
    for dataset in DATASETS:
        for n in SIZES:
            item = evidence['data'][dataset][str(n)]
            c = st.median(p['mean_us'] for p in item['primary']['C'])
            e = st.median(p['mean_us'] for p in item['primary']['E'])
            pair = item['paired']
            assert abs(c/e-pair['ratio_of_medians']) < 1e-9
            records.append({
                'dataset': dataset, 'n': n, 'dimension': item['dimension'],
                'radius': item['normal_radius'], 'tree_height': item['tree']['tree_height'],
                'hit_median': item['work']['hit_median'],
                'candidate_median': item['work']['candidate_median'],
                'host_bytes': item['work']['d2h_bytes'],
                'c_us': c, 'e_us': e, 'saved_us': c-e,
                'ratio_of_medians': pair['ratio_of_medians'],
                'paired_geomean': pair['paired_geomean'],
                'paired_ci_low': pair['bootstrap_95'][0],
                'paired_ci_high': pair['bootstrap_95'][1],
                'wins': pair['wins'],
                'sustained_ce': item['sustained'][0]['C_over_E'],
                'sustained_ec': item['sustained'][1]['C_over_E'],
                'normal_boundary_count': item['full_verification']['normal_ambiguous_distance_count'],
                'c_kernels': item['nsys']['C']['kernels_per_query'],
                'e_kernels': item['nsys']['E']['kernels_per_query'],
                'c_count_kernel_us': item['nsys']['C']['selected_kernel_us']['getQresultCount('],
                'e_fused_kernel_us': item['nsys']['E']['selected_kernel_us']['fusedResultSelect('],
            })
    with (HERE / 'RESULTS.csv').open('w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=records[0])
        writer.writeheader()
        writer.writerows(records)

    colors = {'GIST': '#3366aa', 'Deep': '#c66a16', 'Tloc': '#27935c'}
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(10.8, 4.2), constrained_layout=True)
    for dataset in DATASETS:
        r = [x for x in records if x['dataset'] == dataset]
        xx = [0, 1]
        yy = [x['ratio_of_medians'] for x in r]
        ax.plot(xx, yy, marker='o', lw=2, markersize=7,
                color=colors[dataset], label=dataset)
        for x, y in zip(xx, yy):
            ax.annotate(f'{y:.2f}×', (x, y), xytext=(0, 8), textcoords='offset points',
                        ha='center', fontsize=9, color=colors[dataset])
        bx.plot(xx, [x['c_us']/1000 for x in r], marker='o', lw=2, color=colors[dataset], label=f'{dataset} C')
        bx.plot(xx, [x['e_us']/1000 for x in r], marker='s', lw=2, ls='--', color=colors[dataset], label=f'{dataset} E')
    for a in (ax, bx):
        a.set_xticks([0, 1], ['65,536', '1,000,000'])
        a.grid(alpha=.25)
        a.set_xlabel('Data points (N)')
    ax.axhline(1, color='#555', lw=.8)
    ax.set_ylabel('C / E complete-query speedup')
    ax.set_ylim(.8, 1.37)
    ax.legend(frameon=False, ncol=3, loc='lower left')
    bx.set_yscale('log')
    bx.set_ylabel('Host-ready query latency (ms, log scale)')
    bx.legend(frameon=False, ncol=2, fontsize=8, loc='upper left')
    fig.savefig(HERE / 'large_l2.png', dpi=180)
    plt.close(fig)

    lines = [
        '# 结果融合：三组 L2 数据集的大规模实验', '',
        '在 GIST、Deep、Tloc 的 65,536 和 1,000,000 条真实数据上，对比原结果整理 C 与融合结果整理 E。'
        '两组沿用原生布局和遍历、同一半径与输出容量；下表是完整查询的热态 host-ready 延迟。', '',
        '![大规模完整查询结果](large_l2.png)', '',
        '| 数据集 | N | 命中中位数 | C ms | E ms | 加速比 | 配对比值 [95% 区间] | 胜出 |',
        '|---|---:|---:|---:|---:|---:|---|---:|',
    ]
    for r in records:
        lines.append(f"| {r['dataset']} | {r['n']:,} | {r['hit_median']:g} | "
                     f"{r['c_us']/1000:.3f} | {r['e_us']/1000:.3f} | "
                     f"{r['ratio_of_medians']:.3f}× | "
                     f"{r['paired_geomean']:.4f} [{r['paired_ci_low']:.4f}, {r['paired_ci_high']:.4f}] | "
                     f"{r['wins']}/6 |")
    lines += [
        '',
        '六轮独立进程 CE/EC 交替配对，并反转数据集及规模顺序。表中 C/E 为进程均值的中位数；'
        '配对区间为六轮 log 比值的全部 6^6 重采样。每进程先预热 16 次，65,536 点计时 32 个查询，'
        '百万点计时 8 个查询；双顺序长测的查询数翻倍。', '',
        '保持原生布局时，GIST 百万点的 C/E 每查询节省约 39.9 ms，但原查询约 2.62 s，'
        '因此完整查询只快 1.5%；Deep 百万点节省约 40.9 ms，占原查询 315 ms 的约 13%；'
        'Tloc 百万点节省约 1.16 ms，占原查询 5.85 ms 的约 20%。'
        '这解释了为什么 Words 小规模的 1.8× 不能直接套用到不同维度和距离工作量的数据集。'
        '此前新布局实验是在这些数据集已经融合的 E 路径上进行，布局的额外影响应与此处 C/E 收益分开看。', '',
        '## 双顺序长测与工作量', '',
        '| 数据集 | N | 树高 | 候选中位数 | 每查询回传 | CE 长测 | EC 长测 |',
        '|---|---:|---:|---:|---:|---:|---:|',
    ]
    for r in records:
        lines.append(f"| {r['dataset']} | {r['n']:,} | {r['tree_height']} | "
                     f"{r['candidate_median']:g} | {r['host_bytes']/1e6:.2f} MB | "
                     f"{r['sustained_ce']:.3f}× | {r['sustained_ec']:.3f}× |")
    lines += [
        '',
        '固定半径分别取自之前各数据集 2,000 点实验；新增点采用固定种子且保留之前的 2,000 个原始 ID，'
        '八个查询源 ID 不变。各数据集维度和命中密度不同，不以跨数据集的绝对延迟比较算法优劣。'
        '之前 N=2,000 的 C/E 加速比分别为 GIST 1.007×、Deep 1.068×、Tloc 1.258×；'
        '它们是独立实验，不并入本轮统计。', '',
        '## 结果段归因（诊断性 profile）', '',
        '| 数据集 | N | C/E kernels/query | C 计数核 ms | E 融合核 ms |',
        '|---|---:|---:|---:|---:|',
    ]
    for r in records:
        lines.append(f"| {r['dataset']} | {r['n']:,} | {r['c_kernels']}/{r['e_kernels']} | "
                     f"{r['c_count_kernel_us']/1000:.3f} | {r['e_fused_kernel_us']/1000:.3f} |")
    lines += [
        '',
        'NSYS 每组仅追踪两个固定查询 ID、两次预热、首次调用，共五次执行；核时间受插桩影响，'
        '不能直接从主计时相减。trace 核对 C/E 公共遍历与叶子计算内核序列一致，差异在结果整理。', '',
        '## 正确性与计时口径', '',
        '- 192 次预登记运行。每个规模的 A/C/E 完整正常半径输出由独立 CPU float64 全矩阵检查：'
        '非边界点的成员资格和距离、全体命中数、稳定顺序与 float32 位模式。'
        '在百万点另验证零半径、全命中和负半径。C/E 在所有查询上与原路径 A 的有序输出位对位相同。',
        '- 正常半径附近允许绝对/相对容差带，六组八查询中带内点数分别为 '
        + '、'.join(f"{r['dataset']} {r['n']:,}: {r['normal_boundary_count']}" for r in records)
        + '；带外成员资格严格核对。',
        '- 每个规模 C/E 均通过 memcheck、synccheck；百万点 E 另通过 initcheck、racecheck。'
        '所有压力测试、主计时、长测和 profile 查询均与 CPU 验证后的原路径完整有序输出哈希一致。',
        '- 计时包含输入查询、GPU 遍历与结果整理、完整固定容量输出回传及 CPU 等待；'
        '不含二进制数据载入、建树、Graph 捕获、预热与结果哈希。二进制 loader 仅在建树前替代文本解析，'
        '两组路径完全相同。CPU 未绑核，GPU 时钟未锁。',
        f"- 硬件为 RTX PRO 6000 Blackwell Server，CUDA 13.1.115；GPU {evidence['hardware']['gpu_index']} "
        '运行期间有外部进程监控。此前 GPU 5 批次因外部进程进入而停止并留档，'
        '本表仅使用在同一张 GPU 上重新开始并完整通过核验的批次。'
        '结果限定于 batch=1、固定查询与半径、原生布局和当前固定容量结果回传策略。', '',
        '[原始数值](RESULTS.csv) · [审计证据](EVIDENCE.json) · [预登记约定](CONTRACT.md) · '
        '[复现实验说明](README.md)', '',
    ]
    (HERE / 'RESULTS.md').write_text('\n'.join(lines))


if __name__ == '__main__':
    render()
