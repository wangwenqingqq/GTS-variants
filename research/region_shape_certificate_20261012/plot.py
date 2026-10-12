#!/usr/bin/env python3
"""Four preregistered vector figures, exact frozen counts, no invented confidence bands."""
import argparse
import csv
import json
import sys
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from pypdf import PdfReader,PdfWriter
from shape_math import NAMES,HERE,sha,save


def read(path):
    with Path(path).open() as f:return list(csv.DictReader(f))


def main():
    p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,default=HERE/'evidence');p.add_argument('--out',type=Path,required=True);p.add_argument('--style-dir',type=Path)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    if a.style_dir:
        sys.path.insert(0,str(a.style_dir));from paper_style import setup_style,save_fig
        setup_style('acm_double',use_latex=False,font_family='serif')
    else:
        plt.rcParams.update({'font.family':'serif','font.size':9,'axes.titlesize':9,'axes.labelsize':9,'xtick.labelsize':8,'ytick.labelsize':8,'legend.fontsize':8,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42,'ps.fonttype':42})
        def save_fig(fig,name,output_dir,**_):
            for fmt in ['pdf','png']:fig.savefig(Path(output_dir)/(name+'.'+fmt),dpi=300,bbox_inches='tight',pad_inches=.02)
    rows=json.loads((a.evidence/'aggregate_summary.json').read_text())['rows'];lookup={(r['shape'],r['level']):r for r in rows}
    labels=['AABB','Centroid ball','Minimax ball','Ellipsoid (80 B)'];colors=['#555555','#0072B2','#E69F00','#009E73'];hatches=['','//','..','xx'];markers=['s','o','^','D'];styles=['-','--',':','-.'];names=[]
    def finish(fig,name):
        save_fig(fig,name,output_dir=a.out,target_width_inches=7.05,min_font_size=7);plt.close(fig);names.append(name)
    fig,axes=plt.subplots(1,3,figsize=(7.05,2.9),sharey=True,layout='constrained')
    for ax,l in zip(axes,[3,4,5]):
        for i,(shape,col,hatch) in enumerate(zip(NAMES,colors,hatches)):
            v=100*lookup[shape,l]['hard_alignment'];ax.bar(i,v,color=col,hatch=hatch,edgecolor='black',lw=.4)
            ax.text(i,v+1.2,f'{v:.1f}',ha='center',fontsize=7)
        if l in (3,4):
            ax.axhline(45,color='black',lw=.6,ls=':')
            ax.text(1.5,47,'45% ancestor gate',ha='center',fontsize=7)
        ax.set(xticks=range(4),xticklabels=['AABB','C ball','M ball','Ellip.'],ylim=(0,70),title=f'L{l}: {10**(6-l):,} objects/region',xlabel='64 / 48 / 48 / 80 B per region')
        ax.xaxis.label.set_fontsize(7)
    axes[0].set_ylabel('Hard-6 safe alignment (%)');finish(fig,'figure1_hard_alignment')
    cdf=read(a.evidence/'dead_gap_cdf.csv');fig,ax=plt.subplots(figsize=(7.05,3.0),layout='constrained')
    for shape,label,color,marker,style in zip(NAMES,labels,colors,markers,styles):
        r=[v for v in cdf if v['shape']==shape]
        ax.plot([float(v['dead_gap']) for v in r],[float(v['empirical_cdf']) for v in r],label=label,color=color,marker=marker,ls=style,markevery=650,markersize=3,lw=1.2)
    ax.set(xlabel='Original region truth distance − safe shape LB (L2)',ylabel='Empirical CDF',ylim=(0,1.02),title='Hard6 L4: shape dead space, same 60,000 query-region pairs')
    ax.legend(frameon=False,loc='lower right',fontsize=8);finish(fig,'figure2_dead_space')
    query=read(a.evidence/'per_query_summary.csv');hard=[359924,374533,96985,702545,55715,470632]
    fig,ax=plt.subplots(figsize=(7.05,3.1),layout='constrained');x=np.arange(6);width=.18
    for si,(shape,label,color,hatch) in enumerate(zip(NAMES,labels,colors,hatches)):
        values=[100*float(next(r for r in query if r['shape']==shape and int(r['level'])==4 and int(r['query_id'])==q)['alignment']) for q in hard]
        ax.bar(x+(si-1.5)*width,values,width,color=color,hatch=hatch,edgecolor='black',lw=.35,label=label)
    ax.set(xticks=x,xticklabels=['359924*']+list(map(str,hard[1:])),ylim=(0,100),ylabel='Safe pruned / truth-prunable (%)',xlabel='Frozen hard query ID (* = canary)',title='L4 hard-query rescue (PCA8, unchanged P2 membership)')
    ax.legend(frameon=False,loc='upper left',ncol=2,fontsize=8);finish(fig,'figure3_hard_query_rescue')
    fig,ax=plt.subplots(figsize=(7.05,3.0),layout='constrained')
    for shape,label,color,marker in zip(NAMES,labels,colors,markers):
        r=[lookup[shape,l] for l in (3,4,5)];ax.scatter([v['aligned_bytes'] for v in r],[100*v['hard_alignment'] for v in r],label=label,color=color,marker=marker,s=40,edgecolors='black',linewidths=.4)
        for v in r:
            offset=(5,1);leader=None
            if shape=='CENTROID_BALL' and v['level'] in (3,4):
                offset=(-27,2 if v['level']==3 else 18);leader=dict(arrowstyle='-',lw=.4,color='#555555')
            if shape=='MINIMAX_BALL' and v['level']==3:
                offset=(11,2);leader=dict(arrowstyle='-',lw=.4,color='#555555')
            ax.annotate('L'+str(v['level']),(v['aligned_bytes'],100*v['hard_alignment']),xytext=offset,textcoords='offset points',fontsize=7,arrowprops=leader)
    ax.axvline(64,color='black',ls=':',lw=.75);ax.text(65,67,'64 B budget',fontsize=8)
    ax.set(xlim=(43,89),ylim=(-2,72),xticks=[48,64,80],xlabel='Aligned metadata bytes / region',ylabel='Hard-6 safe alignment (%)',title='Geometry and metadata budget are not interchangeable')
    ax.legend(frameon=False,loc='upper left',fontsize=8);finish(fig,'figure4_bytes_alignment')
    writer=PdfWriter()
    for name in names:
        for page in PdfReader(a.out/(name+'.pdf')).pages:writer.add_page(page)
    with (a.out/'region_shape_evidence.pdf').open('wb') as f:writer.write(f)
    save(a.out/'PLOT_RECEIPT.json',dict(source_sha256=sha(Path(__file__)),physical_cells=12,width_inches=7.05,min_font_pt=7,
        F1='all four shapes, all three frozen levels',F2='all hard6 L4 pairs with frozen4097 rank display',F3='all6 hard queries at L4; canary359924 marked separately from minimum hard query',
        F4='all12cells; ellipsoid80B never claimed matched64B',uncertainty='fixed-workload exact counts; no noisy timing or population CI'))


if __name__=='__main__':main()
