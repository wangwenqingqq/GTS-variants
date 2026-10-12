#!/usr/bin/env python3
"""Four vector evidence figures, fixed-workload counts without fictitious CIs."""
import argparse
import sys
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pypdf import PdfReader,PdfWriter
from aabb_math import *

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--style-dir',type=Path);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    if a.style_dir:
        sys.path.insert(0,str(a.style_dir));from paper_style import setup_style,save_fig
        setup_style('acm_double',use_latex=False,font_family='serif')
    else:
        plt.rcParams.update({'font.family':'serif','font.size':9,'axes.titlesize':9,'axes.labelsize':9,'xtick.labelsize':8,'ytick.labelsize':8,'legend.fontsize':8,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42,'ps.fonttype':42})
        def save_fig(fig,name,output_dir,**_):
            for fmt in ['pdf','png']:fig.savefig(Path(output_dir)/(name+'.'+fmt),dpi=300,bbox_inches='tight',pad_inches=.02)
    summary=json.loads((HERE/'evidence/aggregate_summary.json').read_text());rows=summary['level_results'];by={(r['k'],r['level']):r for r in rows};names=[]
    def finish(fig,name):
        save_fig(fig,name,output_dir=a.out,target_width_inches=7.05,min_font_size=7);plt.close(fig);names.append(name)
    fig,axes=plt.subplots(1,3,figsize=(7.05,2.7),sharey=True,layout='constrained')
    for ax,l in zip(axes,SIZES):
        for key,label,color,marker,style in [('hard_point_alignment','Point-set safe','#555555','s','--'),('hard_alignment','FP32 box','#0072B2','o','-')]:
            ax.plot(KS,[100*by[k,l][key] for k in KS],color=color,marker=marker,ls=style,markersize=4,label=label)
        ax.set(ylim=(0,103),xticks=KS,xlabel='PCA dimensions',title=f'L{l}: {SIZES[l]:,} objects/region')
    axes[0].set_ylabel('Hard6 alignment (%)');axes[0].legend(frameon=False,loc='upper left');finish(fig,'figure1_pointset_vs_fp32')
    fig,ax=plt.subplots(figsize=(7.05,2.7),layout='constrained')
    for l,color,m,style in zip(SIZES,['#333333','#0072B2','#777777'],['s','o','^'],['--','-',':']):ax.plot(KS,[100*by[k,l]['hard_retention'] for k in KS],color=color,marker=m,ls=style,label=f'L{l}',markersize=4)
    ax.set(ylim=(0,103),xticks=KS,xlabel='PCA dimensions',ylabel='Hard6 box / point-set (%)');ax.legend(frameon=False,loc='upper left',ncol=3);finish(fig,'figure2_retention')
    fig,ax=plt.subplots(figsize=(7.05,2.7),layout='constrained')
    for key,label,color,m,style in [('canary_point_objects','Point-set safe','#555555','s','--'),('canary_aabb_objects','FP32 box','#0072B2','o','-')]:ax.plot(KS,[100*by[k,4][key]/by[k,4]['canary_truth_objects'] for k in KS],color=color,marker=m,ls=style,label=label,markersize=4)
    ax.set(ylim=(0,103),xticks=KS,xlabel='PCA dimensions',ylabel='Canary359924 alignment (%)',title='L4: fixed canary, original-truth denominator')
    if not summary['stage_B_admitted']:ax.text(.58,.90,'FP16 / INT8: not admitted',transform=ax.transAxes,fontsize=8)
    else:raise RuntimeError('Add measured Stage B series before publishing admitted-run figure')
    ax.legend(frameon=False,loc='upper left');finish(fig,'figure3_canary')
    fig,ax=plt.subplots(figsize=(7.05,2.7),layout='constrained')
    for l,color,m,style in zip(SIZES,['#333333','#0072B2','#777777'],['s','o','^'],['--','-',':']):ax.plot([8*k for k in KS],[100*by[k,l]['hard_alignment'] for k in KS],color=color,marker=m,ls=style,label=f'L{l}',markersize=4)
    ax.set(ylim=(0,103),xticks=[256,512,1024],xlabel='FP32 aligned record (bytes / region)',ylabel='Hard6 alignment (%)')
    ax.text(.45,.90,'Shared basis / query cache excluded here;\nsee metadata_budget.csv for full accounting',transform=ax.transAxes,fontsize=8,ha='center')
    ax.legend(frameon=False,loc='upper left',ncol=3);finish(fig,'figure4_bytes_vs_alignment')
    writer=PdfWriter()
    for name in names:
        for page in PdfReader(a.out/(name+'.pdf')).pages:writer.add_page(page)
    with (a.out/'highdim_compressibility_evidence.pdf').open('xb') as f:writer.write(f)
    save(a.out/'PLOT_RECEIPT.json',dict(source_sha256=sha(Path(__file__)),width_inches=7.05,min_font_pt=7,query_cells=72,level_cells=9,
        uncertainty='complete frozen eight-query workload; no population CI, runtime or GPU claim',stage_B_bars='omitted when not admitted, never zero-valued',
        F1='point-set and FP32 alignment at all levels',F2='pooled hard point-set-retention at all levels',F3='canary L4 original-truth alignment',F4='finite FP32 record budget; shared overhead disclosed separately'))

if __name__=='__main__':main()
