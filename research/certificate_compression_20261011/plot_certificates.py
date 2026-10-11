#!/usr/bin/env python3
"""Four deterministic count figures; retain separate cost units, not latency."""
import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

COLORS = {3:'#0072B2',4:'#D55E00',5:'#555555'}
LEVELS = {3:'L3',4:'L4',5:'L5 = leaf'}
MODES = {'GLOBAL':'GLOBAL','REGION_ORACLE':'REGION (query-oracle)'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--analysis',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--style-dir',type=Path)
    a = p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    if a.style_dir:
        sys.path.insert(0,str(a.style_dir))
        from paper_style import setup_style,save_fig
        setup_style('acm_double',use_latex=False,font_family='serif')
    else:
        plt.rcParams.update({'font.family':'serif','font.size':9,'axes.titlesize':9,
            'axes.labelsize':9,'xtick.labelsize':8,'ytick.labelsize':8,'legend.fontsize':8,
            'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42,'ps.fonttype':42})
        def save_fig(fig,name,output_dir,**_):
            for fmt in ['pdf','png']:
                fig.savefig(Path(output_dir)/(name+'.'+fmt),dpi=300,bbox_inches='tight',pad_inches=.02)
    plt.rcParams.update({'legend.fontsize':8,'lines.markersize':4,'lines.linewidth':1.4})
    rows = list(csv.DictReader((a.analysis/'per_level_summary.csv').open()))
    summary = json.loads((a.analysis/'aggregate_summary.json').read_text())
    assert len(rows)==30 and summary['leaf_alias']==5 and summary['region_stage_run']
    def series(mode,level):
        result = sorted([r for r in rows if r['selection_mode']==mode and int(r['level'])==level],
                        key=lambda r:int(r['pivot_count']))
        assert [int(r['pivot_count']) for r in result]==[0,1,2,4,8]
        return result
    def finish(fig,name):
        save_fig(fig,name,output_dir=a.out,target_width_inches=fig.get_figwidth(),min_font_size=7)
        plt.close(fig)
    def level_lines(ax,mode,metric):
        for level,marker,style in [(3,'o','-'),(4,'s','--'),(5,'^',':')]:
            data=series(mode,level)
            ax.plot([int(r['pivot_count']) for r in data],[100*float(r[metric]) for r in data],
                color=COLORS[level],marker=marker,ls=style,label=LEVELS[level])
        ax.set(xticks=[0,1,2,4,8],xlabel='Pivot count',title=MODES[mode])
    fig,axes=plt.subplots(1,2,figsize=(7,3.1),sharey=True,layout='constrained')
    for ax,mode in zip(axes,MODES):
        level_lines(ax,mode,'residual_object_fraction');ax.set_ylim(0,100)
    axes[0].set_ylabel('Remaining objects / 8M objects (%)')
    axes[0].legend(frameon=False,loc='lower left')
    finish(fig,'figure1_residual')

    fig,axes=plt.subplots(1,2,figsize=(7,3.1),sharey=True,layout='constrained')
    for ax,mode in zip(axes,MODES):
        level_lines(ax,mode,'oracle_gap_coverage');ax.set_ylim(0,100)
        ax.axhline(70,color='#777777',ls='--',lw=.8)
        ax.text(.04,.72,'70% promotion gate (L3/L4)',transform=ax.transAxes,fontsize=8)
        if mode=='REGION_ORACLE':
            ax.axhline(50,color='#777777',ls=':',lw=.8)
            ax.text(.04,.52,'50% pool-route kill gate',transform=ax.transAxes,fontsize=8)
    axes[0].set_ylabel('Covered native-to-truth gap (%)')
    axes[0].legend(frameon=False,loc='center right')
    finish(fig,'figure2_gap_coverage')

    mode_handles=[Line2D([],[],color='black',marker='o',ls='-',label=MODES['GLOBAL']),
                  Line2D([],[],color='black',marker='^',ls='--',label=MODES['REGION_ORACLE'])]
    fig,axes=plt.subplots(1,3,figsize=(7,3.1),sharey=True,layout='constrained')
    for ax,level in zip(axes,[3,4,5]):
        for mode,marker,style in [('GLOBAL','o','-'),('REGION_ORACLE','^','--')]:
            data=series(mode,level)
            ax.plot([int(r['aligned_bytes_per_region']) for r in data],
                    [100*float(r['incremental_G0_pruning']) for r in data],
                    color=COLORS[level],marker=marker,ls=style)
        ax.axvspan(64,85,color='#eeeeee',zorder=0)
        ax.axvline(64,color='#777777',lw=.8,ls=':')
        ax.axhline(10,color='#777777',lw=.8,ls=':')
        ax.set(title=LEVELS[level],xlim=(-2,85),ylim=(0,15),xticks=[0,16,32,48,64,80],
               xlabel='Aligned bytes / region (B)')
        ax.tick_params(axis='x',labelsize=7)
    axes[0].set_ylabel('New pruning / original G0 visits (%)')
    axes[0].legend(handles=mode_handles,frameon=False,loc='upper left',fontsize=7)
    finish(fig,'figure3_bytes_pruning')

    fig,axes=plt.subplots(1,2,figsize=(7,3.3),sharey=True,layout='constrained')
    for level in [3,4,5]:
        for mode,marker,style in [('GLOBAL','o','-'),('REGION_ORACLE','^','--')]:
            data=series(mode,level)
            y=[float(r['object_distance_coordinate_updates_avoided'])/1e6 for r in data]
            for ax,key,scale in [(axes[0],'pivot_distance_coordinate_updates',1e3),
                                  (axes[1],'metadata_bytes_read',1e6)]:
                ax.plot([float(r[key])/scale for r in data],y,
                        color=COLORS[level],marker=marker,ls=style)
    axes[0].set(xlabel='Pivot-coordinate updates (thousand)',
                ylabel='Avoided object-coordinate updates (million)',title='Distance work only')
    axes[1].set(xlabel='Metadata bytes read (MB; 10$^6$ B)',title='Metadata ledger only')
    for ax in axes:ax.set_ylim(bottom=0);ax.set_xlim(left=0)
    handles=[Line2D([],[],color=COLORS[level],label=LEVELS[level]) for level in [3,4,5]]+mode_handles
    axes[0].legend(handles=handles,frameon=False,loc='upper left',fontsize=7)
    finish(fig,'figure4_cost_avoided_work')
    (a.out/'PLOT_RECEIPT.json').write_text(json.dumps(dict(
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        summary_csv_sha256=hashlib.sha256((a.analysis/'per_level_summary.csv').read_bytes()).hexdigest(),
        rows=30,queries=8,levels=[3,4,5],leaf_alias=5,
        aggregation='pooled counts, not mean of per-query ratios',
        figure3_denominator='original G0 visited objects at the SAME level; not threshold-only work',
        figure4_units='two panels, coordinate updates and bytes never added',
        figure4_metadata='base-surviving query-regions times aligned record bytes; no cache model',
        figure4_avoided_work='incremental C0-to-candidate object updates; fixed U* counterfactual',
        no_latency_or_population_or_confidence_interval_claim=True,
        uncertainty='deterministic complete counts of the frozen 8 queries; no random-run error bars'),indent=2)+'\n')


if __name__=='__main__':main()
