#!/usr/bin/env python3
"""Four fixed-capacity vector plots; numerical envelopes, never population CIs."""
import argparse
import csv
import json
import sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pypdf import PdfReader,PdfWriter
from common import HERE,KS,SIZES,sha,save

def read(path):
    with path.open() as f:return list(csv.DictReader(f))

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--style-dir',type=Path);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);E=HERE/'evidence'
    if a.style_dir:
        sys.path.insert(0,str(a.style_dir));from paper_style import setup_style,save_fig
        setup_style('acm_double',use_latex=False,font_family='serif')
    else:
        plt.rcParams.update({'font.family':'serif','font.size':9,'axes.titlesize':9,'axes.labelsize':9,'xtick.labelsize':7,'ytick.labelsize':8,'legend.fontsize':8,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42,'ps.fonttype':42})
        def save_fig(fig,name,output_dir,**_):
            for fmt in ['pdf','png']:fig.savefig(Path(output_dir)/(name+'.'+fmt),dpi=300,bbox_inches='tight',pad_inches=.02)
    summary=json.loads((E/'aggregate_summary.json').read_text());rows=summary['rows'];qrows=read(E/'per_query_capacity.csv');loss=read(E/'projection_loss_summary.csv');names=[]
    def xaxis(ax):
        ax.set_xscale('log',base=2);ax.set_xticks(KS,[str(k) for k in KS],rotation=45,ha='right');ax.set_xlim(7,1080);ax.set_xlabel('Nested PCA dimensions')
    def finish(fig,name):
        save_fig(fig,name,output_dir=a.out,target_width_inches=7.05,min_font_size=7);plt.close(fig);names.append(name)
    fig,axes=plt.subplots(1,3,figsize=(7.05,3.0),sharey=True,layout='constrained')
    for ax,l in zip(axes,SIZES):
        r=[v for v in rows if v['level']==l]
        for scope,label,color,marker,style in [('all','All8','#555555','s','--'),('hard','Hard6','#0072B2','o','-')]:
            low=np.array([v[scope+'_alignment'] for v in r])*100;high=np.array([v[scope+'_possible_alignment'] for v in r])*100
            ax.plot(KS,low,color=color,marker=marker,ls=style,markersize=3,label=label);ax.fill_between(KS,low,high,color=color,alpha=.12)
        ax.set(ylim=(0,103),title=f'L{l}: {SIZES[l]:,} objects/region');xaxis(ax)
        if l in (3,4):
            ax.axhline(70,color='black',ls=':',lw=.6);ax.text(8,72,'70% hard',fontsize=7)
        if l==3:
            value=next(v['hard_alignment'] for v in r if v['k']==64)*100
            ax.annotate(f'{value:.2f}% < 70%',(64,value),xytext=(90,57),fontsize=7,arrowprops=dict(arrowstyle='-',lw=.5,color='#333333'))
    axes[0].set_ylabel('Projected point-set alignment (%)');axes[0].legend(frameon=False,loc='lower right');finish(fig,'figure1_capacity_curve')
    ids=[359924,374533,96985,702545,55715,470632];colors=['#D55E00','#777777','#333333','#999999','#555555','#009E73'];markers=['o','s','^','D','x','v'];styles=['-','--',':','-.',(0,(4,1)),(0,(6,2))]
    fig,axes=plt.subplots(1,3,figsize=(7.05,3.35),sharey=True,layout='constrained')
    for ax,l in zip(axes,SIZES):
        for q,c,m,style in zip(ids,colors,markers,styles):
            r=[v for v in qrows if int(v['level'])==l and int(v['query_id'])==q]
            ax.plot(KS,[100*float(v['safe_alignment']) for v in r],label=str(q),color=c,marker=m,ls=style,markersize=3,lw=1.6 if q in (359924,470632) else 1.0)
        ax.set(ylim=(0,103),title=f'L{l} hard queries');xaxis(ax)
    axes[0].set_ylabel('Guaranteed projected alignment (%)');fig.legend(*axes[0].get_legend_handles_labels(),loc='outside lower center',ncol=6,frameon=False,fontsize=7);finish(fig,'figure2_hard_queries')
    spectrum=json.loads((E/'PCA_SPECTRUM.json').read_text());fig,axes=plt.subplots(1,2,figsize=(7.05,3.0),sharey=True,layout='constrained')
    axes[0].plot(KS,[100*v['ratio'] for v in spectrum['explained_variance']],color='#333333',marker='s',markersize=4);axes[0].set(title='Variance retention (database)',ylabel='Retained fraction (%)',ylim=(0,103));xaxis(axes[0])
    for l,m,style in zip(SIZES,['s','o','^'],['--','-',':']):
        r=[v for v in rows if v['level']==l];axes[1].plot(KS,[100*v['hard_alignment'] for v in r],label=f'L{l}',color='#0072B2',marker=m,ls=style,markersize=4)
    axes[1].set(title='Exact exclusion capacity (Hard6)');xaxis(axes[1]);axes[1].legend(frameon=False,loc='lower right');finish(fig,'figure3_variance_vs_capacity')
    fig,axes=plt.subplots(1,3,figsize=(7.05,3.0),sharey=True,layout='constrained')
    for ax,l in zip(axes,SIZES):
        r=[v for v in loss if int(v['level'])==l and v['scope']=='hard6']
        for key,label,c,m,style in [('median','Median','#0072B2','o','-'),('p90','p90','#D55E00','s','--')]:ax.plot(KS,[float(v[key]) for v in r],label=label,color=c,marker=m,ls=style,markersize=3)
        ax.axhline(0,color='black',lw=.5);ax.set_title(f'L{l}: all Hard6 pairs');xaxis(ax)
    axes[0].set_ylabel('Original − projected distance (L2)');axes[0].legend(frameon=False,loc='upper right');finish(fig,'figure4_projection_loss')
    writer=PdfWriter()
    for name in names:
        for page in PdfReader(a.out/(name+'.pdf')).pages:writer.add_page(page)
    with (a.out/'projection_capacity_evidence.pdf').open('wb') as f:writer.write(f)
    save(a.out/'PLOT_RECEIPT.json',dict(source_sha256=sha(Path(__file__)),cells=192,width_inches=7.05,min_font_pt=7,
        F1='all8/hard6 all3levels; band from measured arithmetic envelopes, not CI;70% guide only ancestors',F2='all6 hard queries at all3levels;359924 canary and470632 emphasized',
        F3='variance and safe hard capacity separate panels, no combined metric',F4='signed central distance loss median/p90, all hard pairs, not clipped',uncertainty='finite frozen workload; no population CI, runtime or metadata claim'))

if __name__=='__main__':main()
