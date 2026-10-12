#!/usr/bin/env python3
"""Four offline evidence figures. Exact frozen counts, never timing or invented CI."""
import argparse, csv, hashlib, json, sys
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from pypdf import PdfReader, PdfWriter
from partitions import PARTITIONS


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
    qrows = list(csv.DictReader((a.evidence / 'per_query_partition_summary.csv').open()))
    near = list(csv.DictReader((a.evidence / 'region_contamination.csv').open()))
    assert len(rows) == 18 and len(qrows) == 144
    lookup = {(r['partition'], r['level'], r['k']):r for r in rows}
    names = []
    def panels(shared=True):
        fig, axes = plt.subplots(1, 3, figsize=(7.05, 3.15), sharey=shared, layout='constrained')
        for ax, level in zip(axes, [3, 4, 5]): ax.set_title(f'L{level}: {10 ** (6-level):,} objects/region')
        return fig, axes
    def finish(fig, name):
        save_fig(fig, name, output_dir=a.out, target_width_inches=7.05, min_font_size=7)
        plt.close(fig); names.append(name)
    x = np.arange(3); labels = ['P0 GTS', 'P1 Random', 'P2 PCA']
    fig, axes = panels()
    for ax, level in zip(axes, [3, 4, 5]):
        for k, color, marker, ls in [(4, '#666666', 's', '--'), (8, '#0072B2', 'o', '-')]:
            ax.plot(x, [100 * lookup[(part,level,k)]['alignment_efficiency'] for part in PARTITIONS],
                    color=color, marker=marker, ls=ls, label=f'PCA{k} ({8*k}B)')
        ax.axhline(60, color='black', lw=.8, ls=':', label='60% information gate')
        ax.set(xticks=x, xticklabels=labels, ylim=(0, 100), xlabel='Partition (fixed region size)')
    axes[0].set_ylabel('Safely pruned / truth-prunable objects (%)')
    axes[0].legend(frameon=False, loc='upper left')
    finish(fig, 'figure1_alignment')
    fig, axes = panels()
    for ax, level in zip(axes, [3, 4, 5]):
        for offset, k, label, color, hatch in [(-.25,8,'Truth','#aaaaaa','..'), (0,4,'PCA4','#666666','//'), (.25,8,'PCA8','#0072B2','')]:
            field = 'truth_residual' if label == 'Truth' else 'certificate_residual'
            ax.bar(x + offset, [100 * lookup[(part, level, k)][field] for part in PARTITIONS],
                   width=.23, color=color, edgecolor='black', linewidth=.4, hatch=hatch, label=label)
        ax.set(xticks=x, xticklabels=labels, ylim=(0,100), xlabel='Partition')
    axes[0].set_ylabel('Remaining / 8M query-object pairs (%)'); axes[2].legend(frameon=False, loc='upper right')
    finish(fig, 'figure2_residual')
    hard = [359924,374533,96985,702545,55715,470632]
    qlookup = {(int(r['query_id']), r['partition'], int(r['level'])):100*float(r['alignment_efficiency']) for r in qrows if r['k']=='8'}
    fig, axes = panels()
    for ax, level in zip(axes, [3,4,5]):
        for part, color, marker, ls, label in [(PARTITIONS[0],'#666666','s','--','P0 GTS'), (PARTITIONS[2],'#0072B2','o','-','P2 PCA')]:
            ax.plot(np.arange(6),[qlookup[(q,part,level)] for q in hard],color=color,marker=marker,ls=ls,label=label)
        ax.set(xticks=np.arange(6), xticklabels=[str(q) for q in hard], ylim=(0,100), xlabel='Original G0 hard query')
        ax.tick_params(axis='x',labelrotation=55,labelsize=7)
    axes[0].set_ylabel('PCA8 alignment (%)'); axes[0].legend(frameon=False,loc='upper left')
    finish(fig,'figure3_hard_queries')
    fig, axes = panels(shared=False); rng = np.random.default_rng(20261012)
    for ax, level in zip(axes, [3,4,5]):
        values = [np.array([100*float(r['near_fraction']) for r in near if r['partition']==part and int(r['level'])==level and r['factor']=='1.0']) for part in PARTITIONS]
        boxes = ax.boxplot(values, positions=x, widths=.42, patch_artist=True, showfliers=False,
                           medianprops={'color':'black','linewidth':1.2})
        for i,(arr,box,color) in enumerate(zip(values,boxes['boxes'],['#bbbbbb','#dddddd','#56B4E9'])):
            box.set_facecolor(color)
            ax.scatter(i+rng.uniform(-.10,.10,len(arr)),arr,s=7,facecolors='none',edgecolors='black',linewidths=.4,alpha=.7)
        ax.axhline(100/10**(6-level),color='black',ls=':',lw=.8)
        ax.set(xticks=x,xticklabels=labels,xlabel='Truth-retained regions',yscale='log')
        # These are observed region distributions, not estimation uncertainty.
    axes[0].set_ylabel('Objects with d <= U* / region size (%)')
    finish(fig,'figure4_contamination')
    writer = PdfWriter()
    for name in names:
        for page in PdfReader(a.out/(name+'.pdf')).pages: writer.add_page(page)
    with (a.out/'partition_evidence.pdf').open('wb') as f: writer.write(f)
    (a.out/'PLOT_RECEIPT.json').write_text(json.dumps(dict(source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        primary_cells=18, queries=8, complete_frozen_counts=True, no_latency=True,
        uncertainty='no population CI; figure4 shows all observed truth-retained regions, not error bars',
        width_inches=7.05, min_font_pt=7, primary_native_bound=False,
        hard_query_selection='six highest original G0 leaf object visits, frozen before construction'),indent=2)+'\n')


if __name__ == '__main__': main()
