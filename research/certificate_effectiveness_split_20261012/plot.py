#!/usr/bin/env python3
"""Four vector count figures; oracle diagnosis, not population or timing estimates."""
import argparse, csv, hashlib, json, sys
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from pypdf import PdfReader, PdfWriter
from splits import PARTITIONS


def read(path):
    with path.open() as f: return list(csv.DictReader(f))


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--evidence', type=Path, required=True); p.add_argument('--out', type=Path, required=True)
    p.add_argument('--style-dir', type=Path); a = p.parse_args(); a.out.mkdir(parents=True, exist_ok=False)
    if a.style_dir:
        sys.path.insert(0, str(a.style_dir)); from paper_style import setup_style, save_fig
        setup_style('acm_double', use_latex=False, font_family='serif')
    else:
        plt.rcParams.update({'font.family':'serif', 'font.size':9, 'axes.titlesize':9,
            'axes.labelsize':9, 'xtick.labelsize':8, 'ytick.labelsize':8, 'legend.fontsize':8,
            'axes.spines.top':False, 'axes.spines.right':False, 'pdf.fonttype':42, 'ps.fonttype':42})
        def save_fig(fig, name, output_dir, **_):
            for fmt in ['pdf', 'png']: fig.savefig(Path(output_dir)/(name+'.'+fmt), dpi=300, bbox_inches='tight', pad_inches=.02)
    plt.rcParams.update({'legend.fontsize':7, 'lines.markersize':4, 'lines.linewidth':1.3})
    rows = json.loads((a.evidence / 'aggregate_summary.json').read_text())['results']
    qrows = read(a.evidence / 'per_query_alignment.csv'); parents = read(a.evidence / 'parent_split_regret.csv')
    frequencies = read(a.evidence / 'proposal_frequency.csv'); assert len(rows) == 12 and len(qrows) == 96
    lookup = {(r['partition'], r['level']):r for r in rows}; names = []
    def panels():
        fig, axes = plt.subplots(1, 3, figsize=(7.05, 3.05), sharey=True, layout='constrained')
        for ax, level in zip(axes, [3, 4, 5]): ax.set_title(f'L{level}: {10 ** (6-level):,} objects/region')
        return fig, axes
    def finish(fig, name):
        save_fig(fig, name, output_dir=a.out, target_width_inches=7.05, min_font_size=7)
        plt.close(fig); names.append(name)
    fig, axes = panels(); x = np.arange(4)
    for ax, level in zip(axes, [3, 4, 5]):
        for delta, field, color, hatch, label in [(-.18, 'alignment', '#aaaaaa', '..', 'All 8 queries'),
                         (.18, 'hard_alignment', '#0072B2', '//', 'Hard 6 queries')]:
            ax.bar(x + delta, [100 * lookup[(part, level)][field] for part in PARTITIONS], width=.33,
                   color=color, edgecolor='black', linewidth=.4, hatch=hatch, label=label)
        ax.axhline(60, color='black', lw=.8, ls=':', label='60% gate')
        ax.set(xticks=x, xticklabels=['P0', 'P2', 'P3', 'P4'], ylim=(0, 100), xlabel='Partition (same PCA8 / 64 B)')
    axes[0].set_ylabel('Pruned / truth-prunable objects (%)'); axes[0].legend(frameon=False, loc='upper left')
    finish(fig, 'figure1_split_headroom')
    hard = [359924, 374533, 96985, 702545, 55715, 470632]
    qlookup = {(int(r['query_id']), r['partition'], int(r['level'])):100 * float(r['alignment']) for r in qrows}
    fig, axes = panels()
    for ax, level in zip(axes, [3, 4, 5]):
        for part, color, marker, ls, label in [('PCA_BALANCED', '#666666', 's', '--', 'P2 max-spread'),
                                            ('ORACLE_HARD6', '#0072B2', 'o', '-', 'P4 hard oracle')]:
            ax.plot(np.arange(6), [qlookup[(q, part, level)] for q in hard], color=color, marker=marker, ls=ls, label=label)
        ax.set(xticks=np.arange(6), xticklabels=[str(q) for q in hard], ylim=(0, 100), xlabel='Frozen hard query ID')
        ax.tick_params(axis='x', labelrotation=55, labelsize=7)
    axes[0].set_ylabel('PCA8 alignment (%)'); axes[0].legend(frameon=False, loc='upper left')
    finish(fig, 'figure2_hard_query_rescue')
    fig, axes = panels()
    for ax, level in zip(axes, [3, 4, 5]):
        for part, color, ls, label in [('ORACLE_ALL8', '#666666', '--', 'P3 all-8 oracle'),
                                    ('ORACLE_HARD6', '#0072B2', '-', 'P4 hard-6 oracle')]:
            values = np.array([float(r['normalized_regret']) for r in parents if r['partition'] == part and int(r['child_level']) == level])
            unique, counts = np.unique(values, return_counts=True)
            xx = np.r_[0., unique * 100]; yy = np.r_[0., np.cumsum(counts) / len(values) * 100]
            ax.step(xx, yy, where='post', color=color, ls=ls, label=label)
        ax.set(ylim=(0, 102), xlim=(0, None), xlabel='Same-parent regret / QN (%)')
    axes[0].set_ylabel('Parents at or below regret (%)'); axes[0].legend(frameon=False, loc='lower right')
    finish(fig, 'figure3_parent_regret')
    fig, axes = plt.subplots(2, 3, figsize=(7.05, 5.0), sharex=True, sharey=True, layout='constrained')
    labels = ['S0', *['PC' + str(i) for i in range(1, 9)], 'Cyc', 'Lex', 'Rad']
    for row, part in enumerate(['ORACLE_ALL8', 'ORACLE_HARD6']):
        for col, level in enumerate([3, 4, 5]):
            ax = axes[row, col]; rr = [r for r in frequencies if r['partition'] == part and int(r['child_level']) == level]
            ax.bar(np.arange(12), [100 * float(r['fraction']) for r in rr], color='#777777' if row == 0 else '#0072B2',
                    edgecolor='black', linewidth=.35, hatch='..' if row == 0 else '//')
            ax.set(xticks=np.arange(12), xticklabels=labels, ylim=(0, 100), title=('P3' if row == 0 else 'P4') + f' / child L{level}')
            ax.tick_params(axis='x', labelsize=7, labelrotation=90)
            if col == 0: ax.set_ylabel('Selected parents (%)')
            if row == 1: ax.set_xlabel('Proposal ID')
    finish(fig, 'figure4_proposal_identity')
    writer = PdfWriter()
    for name in names:
        for page in PdfReader(a.out / (name + '.pdf')).pages: writer.add_page(page)
    with (a.out / 'split_evidence.pdf').open('wb') as f: writer.write(f)
    (a.out / 'PLOT_RECEIPT.json').write_text(json.dumps(dict(source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        primary_cells=12, per_query_rows=96, queries=8, complete_frozen_counts=True, no_latency=True,
        uncertainty='none invented: complete fixed-workload counts and all observed parent regrets, not a population estimate',
        width_inches=7.05, min_font_pt=7, oracle_is_greedy_not_global=True,
        proposal_frequency_caveat='lowest-ID ties favor S0; retained duplicate proposals; not an intrinsic split-quality ranking'), indent=2) + '\n')


if __name__ == '__main__': main()
