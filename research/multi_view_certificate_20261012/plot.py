#!/usr/bin/env python3
"""Four preregistered count plots, with no invented population uncertainty."""
import argparse, csv, hashlib, json, sys
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from pypdf import PdfReader, PdfWriter

def read(p):
    with p.open() as f:return list(csv.DictReader(f))

def main():
    p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--style-dir',type=Path)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    if a.style_dir:
        sys.path.insert(0,str(a.style_dir));from paper_style import setup_style,save_fig
        setup_style('acm_double',use_latex=False,font_family='serif')
    else:
        plt.rcParams.update({'font.family':'serif','font.size':9,'axes.titlesize':9,'axes.labelsize':9,'xtick.labelsize':8,'ytick.labelsize':8,'legend.fontsize':8,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42,'ps.fonttype':42})
        def save_fig(fig,name,output_dir,**_):
            for fmt in ['pdf','png']:fig.savefig(Path(output_dir)/(name+'.'+fmt),dpi=300,bbox_inches='tight',pad_inches=.02)
    plt.rcParams.update({'lines.linewidth':1.25,'lines.markersize':4,'legend.fontsize':7})
    rows=json.loads((a.evidence/'aggregate_summary.json').read_text())['rows'];view=read(a.evidence/'query_view_gain.csv')
    lookup={(r['config'],r['level']):r for r in rows};names=[]
    colors=['#555555','#0072B2','#E69F00','#009E73'];labels=['PCA blocks','Interleaved','Spread32','Random']
    def finish(fig,name):
        save_fig(fig,name,output_dir=a.out,target_width_inches=7.05,min_font_size=7);plt.close(fig);names.append(name)
    fig,axes=plt.subplots(1,3,figsize=(7.05,3.05),sharey=True,layout='constrained')
    for ax,l in zip(axes,[3,4,5]):
        for family,label,color,marker,ls in zip(['BLOCKS','INTERLEAVED','SPREAD32','RANDOM'],labels,colors,['s','o','^','x'],['-','--',':','-.']):
            values=[100*lookup[('PCA8',l)]['hard_alignment']] if family=='BLOCKS' else [np.nan]
            for layout in ['2x4','4x2','8x1']:
                target='BLOCKS_8x1' if family=='INTERLEAVED' and layout=='8x1' else family+'_'+layout
                values.append(100*lookup[(target,l)]['hard_alignment'])
            ax.plot(range(4),values,color=color,marker=marker,ls=ls,label=label)
        ax.axhline(55,color='black',lw=.7,ls=':',label='55% ancestor gate' if l==3 else None)
        ax.set(xticks=range(4),xticklabels=['1×8','2×4','4×2','8×1'],ylim=(-1,65),title=f'L{l}: {10**(6-l):,} objects/region',xlabel='Views × dimensions (64 B)')
    axes[0].set_ylabel('Hard-6 alignment (%)');axes[0].legend(frameon=False,loc='upper right',bbox_to_anchor=(1.,.73))
    finish(fig,'figure1_layout_alignment')
    diagnostic=['BLOCKS_2x4','INTERLEAVED_2x4','SPREAD32_2x4','RANDOM_2x4'];queries=[660835,90208,359924,374533,96985,702545,55715,470632]
    vl={(r['config'],int(r['query_id']),int(r['view'])):r for r in view if int(r['level'])==4}
    matrix=np.array([[100*float(vl[(c,q,v)]['alignment']) for c in diagnostic for v in range(2)] for q in queries])
    fig,ax=plt.subplots(figsize=(7.05,3.6),layout='constrained')
    im=ax.imshow(matrix,cmap='cividis',vmin=0,vmax=100,aspect='auto',interpolation='nearest')
    ax.set(xticks=range(8),xticklabels=[label+'\nV'+str(v+1) for label in labels for v in range(2)],yticks=range(8),yticklabels=[str(q)+(' *' if i>=2 else '') for i,q in enumerate(queries)],xlabel='Frozen 2×4 families at L4',ylabel='Query ID (* = hard)',title='Different directions do not rescue the hard-query canary')
    for i in range(8):
        for j in range(8):ax.text(j,i,f'{matrix[i,j]:.1f}',ha='center',va='center',fontsize=7,color='white' if matrix[i,j]<45 else 'black')
    for j in [1.5,3.5,5.5]:ax.axvline(j,color='white',lw=1)
    fig.colorbar(im,ax=ax,label='Constituent pruned / truth-prunable (%)',pad=.02,fraction=.025)
    finish(fig,'figure2_query_view')
    unique=[];shared=[]
    for c in diagnostic:
        for v in range(2):
            rr=[vl[(c,q,v)] for q in queries[2:]]
            unique.append(sum(int(r['unique_pruned_objects']) for r in rr)/60000)
            shared.append(sum(int(r['shared_pruned_objects']) for r in rr)/60000)
    fig,ax=plt.subplots(figsize=(7.05,3.2),layout='constrained');x=np.arange(8)
    ax.bar(x,unique,color='#0072B2',edgecolor='black',lw=.35,hatch='//',label='Only this view')
    ax.bar(x,shared,bottom=unique,color='#aaaaaa',edgecolor='black',lw=.35,hatch='..',label='Also another view')
    ax.set(xticks=x,xticklabels=[label+'\nV'+str(v+1) for label in labels for v in range(2)],ylim=(0,35),ylabel='Pruned object-query pairs / hard-6 full scan (%)',xlabel='Frozen 2×4 families at L4',title='Most pruning comes from one view; overlap is not new coverage')
    ax.legend(frameon=False,loc='upper right');finish(fig,'figure3_unique_pruning')
    configs=[r['config'] for r in rows if r['level']==3]
    short=['PCA8','B 2×4','B 4×2','B 8×1','I 2×4','I 4×2','S 2×4','S 4×2','S 8×1','R 2×4','R 4×2','R 8×1']
    fig,axes=plt.subplots(1,3,figsize=(7.05,3.35),sharey=True,layout='constrained')
    for ax,l in zip(axes,[3,4,5]):
        values=[100*lookup[(c,l)]['worst_hard_alignment'] for c in configs]
        ax.bar(range(12),values,color='#777777',edgecolor='black',lw=.4,hatch='//')
        ax.axhline(25,color='black',lw=.7,ls=':')
        ax.set(xticks=range(12),xticklabels=short,ylim=(0,28),title=f'L{l}',xlabel='B blocks / I interleaved / S spread / R random')
        ax.tick_params(axis='x',labelrotation=90,labelsize=7)
        ax.xaxis.label.set_fontsize(7)
    axes[0].set_ylabel('Minimum hard-query alignment (%)');finish(fig,'figure4_worst_query')
    writer=PdfWriter()
    for n in names:
        for page in PdfReader(a.out/(n+'.pdf')).pages:writer.add_page(page)
    with (a.out/'multi_view_evidence.pdf').open('wb') as f:writer.write(f)
    (a.out/'PLOT_RECEIPT.json').write_text(json.dumps(dict(source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),physical_cells=36,figures_2_3_selection='all four distinct 2x4 families at L4, preregistered',width_inches=7.05,min_font_pt=7,
        uncertainty='exact fixed-workload counts, not population estimates; no repeated noisy timing or invented CI',shared_view_bars='overlap counted per view, not union; do not sum shared bars to obtain unique total',aliases='D1 omitted as duplicate; D2 8x1 reuses BLOCKS 8x1'),indent=2)+'\n')

if __name__=='__main__':main()
