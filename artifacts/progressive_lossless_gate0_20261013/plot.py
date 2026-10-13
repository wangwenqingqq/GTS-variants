#!/usr/bin/env python3
"""Three fixed-pool, logical-byte figures; no invented timing or uncertainty."""
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent


def figures():
    plt.rcParams.update({'font.family': 'DejaVu Serif', 'font.size': 9, 'axes.labelsize': 9,
                         'xtick.labelsize': 8, 'ytick.labelsize': 8, 'legend.fontsize': 8,
                         'axes.spines.top': False, 'axes.spines.right': False,
                         'pdf.fonttype': 42, 'svg.fonttype': 'none', 'savefig.dpi': 300})
    stage = json.loads((ROOT / 'model/STAGE_COUNTS.json').read_text())['rows']
    bits = json.loads((ROOT / 'model/REQUIRED_BITS.json').read_text())
    primary = json.loads((ROOT / 'model/LOGICAL_BYTES.json').read_text())
    target = ROOT / 'figures'
    target.mkdir(exist_ok=True)
    def save(fig, name):
        fig.tight_layout(pad=0.4)
        for ext in ('svg', 'png'):
            out = target / f'{name}.{ext}'
            fig.savefig(out, bbox_inches='tight')
            if ext == 'svg':
                out.write_text('\n'.join(line.rstrip() for line in out.read_text().splitlines()) + '\n')
        plt.close(fig)
    fig, ax = plt.subplots(figsize=(3.4, 2.45))
    y = [s['survivors'] / 32000000 * 100 for s in stage]
    ax.plot(range(4), y, marker='o', color='#0072B2', linewidth=1.5, markersize=4)
    ax.set_xticks(range(4), ['4', '8', '16', '32'])
    ax.set(xlabel='Cumulative bits / coordinate', ylabel='Surviving pairs (%)', ylim=(0, 110))
    ax.set_yticks([0, 20, 40, 60, 80, 100])
    ax.spines['left'].set_visible(True)
    ax.annotate(f'{y[0]:.3f}%', (0, y[0]), xytext=(5, 4), textcoords='offset points', fontsize=8)
    ax.annotate(f'{y[1]:.3f}%', (1, y[1]), xytext=(0, 10), textcoords='offset points', fontsize=8)
    ax.text(0.96, 0.93, '32 queries x 1M objects', transform=ax.transAxes, ha='right', va='top', fontsize=7)
    save(fig, 'survivor_curve')
    fig, ax = plt.subplots(figsize=(3.4, 2.45))
    values = [3.840, 1.014828776, primary['decimal_GB_per_query']]
    labels = ['Full FP32', 'Dim-progressive', 'Bit-progressive']
    bars = ax.barh(range(3), values, color=['#bcbcbc', '#777777', '#0072B2'],
                   edgecolor='black', linewidth=0.5, hatch=['', '//', '..'])
    ax.set_yticks(range(3), labels)
    ax.set(xlabel='Logical source payload (GB/query)', xlim=(0, 4.25))
    ax.invert_yaxis()
    for rect, value in zip(bars, values):
        ax.text(value + 0.045, rect.get_y() + rect.get_height() / 2,
                f'{value:.3f}', va='center', fontsize=8)
    ax.text(0.97, 0.02, 'Not measured DRAM or latency', transform=ax.transAxes, ha='right', fontsize=7)
    save(fig, 'bytes_per_query')
    fig, ax = plt.subplots(figsize=(3.4, 2.45))
    x = list(range(4)); y = [bits['histogram'][str(w)] / 32000000 * 100 for w in (4, 8, 16, 32)]
    ax.bar(x, y, color='#0072B2', edgecolor='black', linewidth=0.5, hatch='..')
    ax.set_xticks(x, ['4', '8', '16', '32'])
    ax.set(xlabel='Terminal bits / coordinate', ylabel='Pairs (%)', ylim=(0, 110))
    for at, height in zip(x, y):
        ax.text(at, height + 2, f'{height:.3f}%', ha='center', fontsize=8)
    ax.text(0.97, 0.93, f'Mean: {bits["mean_bits_per_coordinate"]:.3f} bits\nMedian / p90: 8\np95 / p99: 16',
            transform=ax.transAxes, ha='right', va='top', fontsize=8)
    save(fig, 'required_bits')


if __name__ == '__main__':
    figures()
