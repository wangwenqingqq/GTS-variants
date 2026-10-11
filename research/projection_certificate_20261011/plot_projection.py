#!/usr/bin/env python3
"""Four frozen-count projection/pivot comparison figures; not latency charts."""
import argparse,csv,hashlib,json,sys
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
COLORS={'PCA':'#0072B2','RANDOM_ORTHO':'#D55E00','GLOBAL':'#777777','REGION_ORACLE':'#333333'}

def main():
    p=argparse.ArgumentParser();p.add_argument('--analysis',type=Path,required=True)
    p.add_argument('--pivots',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--style-dir',type=Path);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    if a.style_dir:
        sys.path.insert(0,str(a.style_dir));from paper_style import setup_style,save_fig
        setup_style('acm_double',use_latex=False,font_family='serif')
    else:
        plt.rcParams.update({'font.family':'serif','font.size':9,'axes.titlesize':9,
            'axes.labelsize':9,'xtick.labelsize':8,'ytick.labelsize':8,'legend.fontsize':8,
            'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42,'ps.fonttype':42})
        def save_fig(fig,name,output_dir,**_):
            for fmt in ['pdf','png']:fig.savefig(Path(output_dir)/(name+'.'+fmt),dpi=300,bbox_inches='tight',pad_inches=.02)
    plt.rcParams.update({'legend.fontsize':7,'lines.markersize':4,'lines.linewidth':1.4})
    summary=json.loads((a.analysis/'SUMMARY.json').read_text());rows=summary['results']
    assert len(rows)==27;truth={r['level']:r['residual_fraction'] for r in summary['truth']}
    pivots=list(csv.DictReader(a.pivots.open()))
    def series(family,level):
        values=sorted([r for r in rows if r['family']==family and r['level']==level],key=lambda r:r['k'])
        return [next(r for r in rows if r['family']=='C0' and r['level']==level)]+values
    def panels():
        fig,axes=plt.subplots(1,3,figsize=(7.05,3.2),sharey=True,layout='constrained')
        for ax,l in zip(axes,[3,4,5]):ax.set_title(f'L{l}'+(' = leaf' if l==5 else ''))
        return fig,axes
    def finish(fig,name):
        save_fig(fig,name,output_dir=a.out,target_width_inches=fig.get_figwidth(),min_font_size=7);plt.close(fig)
    styles=[('PCA','o','-'),('RANDOM_ORTHO','s','--')]
    fig,axes=panels()
    for ax,l in zip(axes,[3,4,5]):
        for family,marker,ls in styles:
            s=series(family,l);ax.plot([r['k'] for r in s],[100*r['residual_fraction'] for r in s],
                color=COLORS[family],marker=marker,ls=ls,label='PCA' if family=='PCA' else 'Random ortho')
        ax.axhline(100*truth[l],color='black',ls=':',lw=1,label='Region truth')
        ax.set(xticks=[0,1,2,4,8],xlabel='Projection dimensions k',ylim=(-1,100))
    axes[0].set_ylabel('Remaining / 8M query-object pairs (%)');axes[0].legend(frameon=False,loc='center left')
    finish(fig,'figure1_residual')
    fig,axes=panels()
    for ax,l in zip(axes,[3,4,5]):
        for family,marker,ls in styles:
            s=series(family,l);ax.plot([r['k'] for r in s],[100*r['oracle_gap_coverage'] for r in s],
                color=COLORS[family],marker=marker,ls=ls,label='PCA' if family=='PCA' else 'Random ortho')
        ax.axhline(30,color='#555555',ls=':',lw=.8);ax.axhline(50,color='#555555',ls='--',lw=.8)
        ax.set(xticks=[0,1,2,4,8],xlabel='k (4 = 32B; 8 = 64B)',ylim=(-1,55))
    axes[0].set_ylabel('Covered native-to-truth gap (%)');axes[0].legend(frameon=False,loc='center left',bbox_to_anchor=(.02,.4))
    axes[1].text(.07,31,'30% kill line',fontsize=7);axes[1].text(.07,51,'50% information gate',fontsize=7)
    finish(fig,'figure2_gap')
    fig,axes=panels()
    handles=[Line2D([],[],color=COLORS[f],marker=m,ls=ls,label=label) for f,m,ls,label in
        [('PCA','o','-','PCA'),('RANDOM_ORTHO','s','--','Random ortho'),('GLOBAL','^',':','GLOBAL pivot'),('REGION_ORACLE','D','-.','REGION pivot (oracle)')]]
    for ax,l in zip(axes,[3,4,5]):
        for family,marker,ls in styles:
            s=series(family,l);ax.plot([r['aligned_bytes_per_region'] for r in s],
                [100*r['incremental_G0_pruning'] for r in s],color=COLORS[family],marker=marker,ls=ls)
        for family,marker,ls in [('GLOBAL','^',':'),('REGION_ORACLE','D','-.')]:
            s=sorted([r for r in pivots if r['selection_mode']==family and int(r['level'])==l],key=lambda r:int(r['pivot_count']))
            ax.plot([int(r['aligned_bytes_per_region']) for r in s],
                [100*float(r['incremental_G0_pruning']) for r in s],color=COLORS[family],marker=marker,ls=ls)
        ax.axvline(64,color='#777777',ls=':',lw=.8)
        ax.set(xlabel='Aligned metadata / region (B)',xticks=[0,16,32,48,64,80],xlim=(-2,83),ylim=(-.3,22))
        ax.tick_params(axis='x',labelsize=7)
    axes[0].set_ylabel('New pruning / original G0 visits (%)');axes[0].legend(handles=handles,frameon=False,loc='upper left')
    finish(fig,'figure3_bytes_pruning')
    fig,axes=panels()
    for ax,l in zip(axes,[3,4,5]):
        s=[r for r in summary['pivot_comparators'] if r['level']==l]
        x=[r['budget_bytes'] for r in s]
        ax.plot(x,[100*r['joint_gain'] for r in s],color=COLORS['PCA'],marker='o',label='Within-budget pivot')
        ax.plot(x,[100*r['gain_vs_unlimited'] for r in s],color='#333333',ls='--',marker='^',label='Unlimited pivot')
        ax.axhline(0,color='black',lw=.8);ax.set(xticks=[16,32,64],xlabel='PCA aligned budget (B)',ylim=(-5.5,5.5))
    axes[0].set_ylabel('PCA gap minus strongest pivot (pp)');axes[0].legend(frameon=False,loc='upper left')
    finish(fig,'figure4_joint_gain')
    (a.out/'PLOT_RECEIPT.json').write_text(json.dumps(dict(
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        summary_sha256=hashlib.sha256((a.analysis/'SUMMARY.json').read_bytes()).hexdigest(),
        pivot_csv_sha256=hashlib.sha256(a.pivots.read_bytes()).hexdigest(),
        complete_frozen_counts=True,queries=8,distinct_cells=27,
        uncertainty='deterministic counts on eight frozen stratified queries, no population CI or timing error bars',
        figure3_denominator='G0 visited objects at the same level, not C0 survivors',
        figure4_comparator='strongest GLOBAL/REGION_ORACLE within budget, plus strongest unrestricted pivot',
        figure4_joint_gain='difference from a pivot family, not attribution of sum-vs-max alone',
        no_latency_claim=True),indent=2)+'\n')
if __name__=='__main__':main()
