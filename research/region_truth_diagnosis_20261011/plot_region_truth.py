#!/usr/bin/env python3
"""Four diagnostic figures from complete observations; no latency or CI claims."""
import argparse
import csv
import json
from pathlib import Path
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm

COLORS = ['#999999', '#0072B2', '#D55E00']
LABELS = ['A: Current-prunable', 'B: Certificate failure', 'C: Partition floor']


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--analysis', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--style-dir', type=Path, help='Optional installed paper_style.py directory; never copied into the artifact')
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=False)
    if a.style_dir:
        sys.path.insert(0, str(a.style_dir))
        from paper_style import setup_style, save_fig
        setup_style('acm_double', use_latex=False, font_family='serif')
    else:
        # Portable native matplotlib configuration, not a vendored skill/runtime.
        plt.rcParams.update({'font.family':'serif','font.size':9,'axes.titlesize':9,
            'axes.labelsize':9,'xtick.labelsize':8,'ytick.labelsize':8,'legend.fontsize':8,
            'axes.spines.top':False,'axes.spines.right':False,
            'pdf.fonttype':42,'ps.fonttype':42,'svg.fonttype':'none'})
        def save_fig(fig, name, output_dir, **_):
            for fmt in ['pdf','png']:
                fig.savefig(Path(output_dir)/(name+'.'+fmt), dpi=300, bbox_inches='tight',pad_inches=.02)
    def finish(fig, name):
        save_fig(fig,name,output_dir=a.out,target_width_inches=fig.get_figwidth(),min_font_size=7)
        plt.close(fig)

    summary = json.loads((a.analysis/'aggregate_summary.json').read_text())
    rows = list(csv.DictReader((a.analysis/'per_query_summary.csv').open()))
    arrays = [np.load(a.analysis/('query_'+r['query_id']+'.npz')) for r in rows]
    classes = summary['class_order']
    fig, ax = plt.subplots(figsize=(7,3),layout='constrained')
    bottom = np.zeros(8)
    for j,c in enumerate(classes):
        height = np.array([int(r[c+'_objects'])/1e6 for r in rows])
        ax.bar(np.arange(8),height,bottom=bottom,color=COLORS[j],hatch=['..','///','xx'][j],
               label=LABELS[j],edgecolor='black',linewidth=.35)
        bottom += height
    ax.set(ylim=(0,1),xticks=np.arange(8),xticklabels=[r['query_id'] for r in rows],
           xlabel='Frozen query ID',ylabel='Object fraction at oracle U*')
    ax.legend(loc='upper center',bbox_to_anchor=(.5,1.22),ncol=3,frameon=False)
    for i,r in enumerate(rows):
        ax.text(i,.95,'C: '+r['PARTITION_FAILURE_objects'],ha='center',va='top',fontsize=8,
                bbox=dict(facecolor='white',edgecolor='none',alpha=.85,pad=1))
    ax.set_title('Perfect leaf truth retains only 70–80 objects/query (C labels are counts)',pad=7,fontsize=9)
    finish(fig,'figure1_classes')

    density = json.loads((a.analysis/'scatter_density.json').read_text())
    fig, axes = plt.subplots(2,4,figsize=(7,4.3),layout='constrained')
    vmax = max(max(max(row) for row in d['histogram']) for d in density)
    for ax,d in zip(axes.flat,density):
        h = np.array(d['histogram']).T
        mesh = ax.pcolormesh(d['x_edges'],d['y_edges'],np.ma.masked_equal(h,0),
                            cmap='cividis',norm=LogNorm(vmin=1,vmax=vmax),rasterized=False)
        upper = min(d['x_edges'][-1],d['y_edges'][-1])
        ax.plot([0,upper],[0,upper],':',color='black',lw=1.1)
        ax.set_title(str(d['query_id'])+' | '+str(d['visited_regions'])+' leaves')
        ax.tick_params(labelsize=7)
    fig.supxlabel('Current path bound, LB_GTS (L2)')
    fig.supylabel('Region truth bound, LB_truth (L2)')
    fig.colorbar(mesh,ax=axes,label='Visited regions / bin',fraction=.025,pad=.02)
    finish(fig,'figure2_bound_gap')

    gts = np.concatenate([z['LB_GTS'][z['visited']]/z['U_star'] for z in arrays])
    truth = np.concatenate([z['LB_truth'][z['visited']]/z['U_star'] for z in arrays])
    edges = np.unique(np.r_[np.linspace(0,max(truth.max(),gts.max())*1.001,1201),1.])
    fig,ax = plt.subplots(figsize=(4.4,3),layout='constrained')
    for values,label,color,style in [(gts,'LB_GTS / U*',COLORS[1],'-'),(truth,'LB_truth / U*',COLORS[2],'--')]:
        # Evaluate the inclusive empirical CDF exactly at every plotting edge.
        sorted_values = np.sort(values)
        cdf = np.searchsorted(sorted_values,edges,side='right')/len(values)
        ax.step(edges,cdf,where='post',label=label,color=color,ls=style,lw=1.3)
    m1 = summary['M1_visited_certificate_fraction']
    ax.axvline(1,color='black',ls=':',lw=.8)
    ax.text(.97,.49,f'CDF gap at 1: {m1:.2%}\nAll G0-visited leaves',transform=ax.transAxes,
            ha='right',va='center',fontsize=8)
    ax.set(xlim=(0,edges[-1]),ylim=(0,1.02),xlabel='Bound / U* (dimensionless)',ylabel='Cumulative fraction of visited regions')
    ax.legend(loc='lower right',frameon=False)
    finish(fig,'figure3_relative_radius')

    # No x-jitter or invented size variation: all 800,000 records have x=10.
    all_truth = np.concatenate([z['LB_truth']/z['U_star'] for z in arrays])
    all_labels = np.concatenate([z['labels'] for z in arrays])
    require_sizes = all(np.all(z['sizes']==10) for z in arrays)
    if not require_sizes:
        raise ValueError('Size plot must be redesigned for a nondegenerate partition')
    yedges = np.linspace(0,all_truth.max()*1.001,91)
    plot4 = []
    fig,axes = plt.subplots(1,3,figsize=(7,3.4),sharey=True,layout='constrained')
    for j,ax in enumerate(axes):
        y = all_truth[all_labels==j]
        hist,_ = np.histogram(y,bins=yedges)
        keep = hist>0
        sums,_ = np.histogram(y,bins=yedges,weights=y)
        means = sums[keep]/hist[keep]
        ax.scatter(np.full(keep.sum(),10),means,s=7+8*np.log10(hist[keep]),
                   c=COLORS[j],marker=['s','o','^'][j],linewidths=.4,edgecolors='black')
        ax.axhline(1,color='black',ls=':',lw=.8)
        ax.set(xlim=(9,11),xticks=[10],title=LABELS[j]+'\n'+str(len(y))+' regions')
        ax.text(.96,.97,'All x = 10',transform=ax.transAxes,ha='right',va='top',fontsize=8)
        plot4.append(dict(category=classes[j],counts=hist.tolist(),y_edges=yedges.tolist(),
                          occupied_bin_means=means.tolist(),object_count=10))
    axes[0].set_ylabel('LB_truth / U* (dimensionless)')
    fig.supxlabel('Region object count (fixed; no size-effect inference)')
    finish(fig,'figure4_region_size')
    (a.out/'PLOT_RECEIPT.json').write_text(json.dumps(dict(
        source='complete offline observations; no random plotting subset',
        figures_1_4_denominator='all 800000 query-region pairs',
        figures_2_3_denominator=int(summary['visited_object_weighted']['denominator']/10),
        figure2_binning='70 by 70 inclusive-range bins per query, shared logarithmic count color scale',
        figure3_cdf='inclusive exact CDF at 1202 or fewer edges, including ratio=1; step display',
        figure4_binning='90 y bins; plotted y is observed bin mean, not bin center; all x exactly 10; marker area = 7 + 8 log10(count)',
        figure4_data=plot4,all_observations_deterministic=True,no_latency_error_bars_applicable=True),indent=2)+'\n')


if __name__=='__main__':
    main()
