#!/usr/bin/env python3
"""Generate descriptive tables and plots from byte-preserved CPU evidence."""
import argparse
import csv
import json
import os
import sys
from pathlib import Path
import numpy as np

METHODS=['GLOBAL4','LOCAL_BALL','ORACLE']
KEYS=['global4_survival_fraction','local_ball_survival_fraction','oracle_fraction']
SNAPS=['initial','first_rebuilt']


def table(headers,rows):
    return '| '+' | '.join(headers)+' |\n| '+' | '.join(['---']*len(headers))+' |\n'+''.join('| '+' | '.join(map(str,r))+' |\n' for r in rows)


def write_csv(path,rows):
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)


def main(root):
    q=json.loads((root/'query/SUMMARY_COMPARISON.json').read_text());bs=json.loads((root/'summary/LOCAL_BALL_STATS.json').read_text())
    sums={s['snapshot']:s['statistics'] for s in q['summary']};rows=q['rows'];means=[];robust=[];plotrows=[];cost=[]
    for name in SNAPS:
        s=sums[name]
        for method,key in zip(METHODS,KEYS):
            v=s[key];gap=(v['mean']-s['oracle_fraction']['mean'])*4096
            means.append([name,method,f"{100*v['mean']:.4f}",f"{100*s['oracle_fraction']['mean']:.4f}",f'{gap:.5f}',0])
            robust.append([name,method,*[f'{100*v[k]:.4f}' for k in ('min','p10','median','p90','max')]])
            plotrows.append(dict(snapshot=name,summary=method,surviving_percent=100*v['mean'],oracle_gap_blocks=gap))
        nr=[r for r in rows if r['snapshot']==name]
        for method,ev,objs in [('GLOBAL4',4,s['global4_surviving_objects']['mean']),('LOCAL_BALL',4096,s['surviving_objects']['mean']),('FULL_SCAN',0,1000000)]:
            cost.append([name,method,f'{objs:.5f}',f'{ev+objs:.5f}',f'{(ev+objs)*960*4:.0f}',sum((r['modeled_total_distance_evals']>1000000) for r in nr) if method=='LOCAL_BALL' else '—'])
    (root/'query/SUMMARY_COMPARISON.md').write_text('# Fixed-block summary comparison\n\nGIST N=1,000,000, D=960, FP32/L2; 4096 identical S1/P2 blocks and 32 fixed queries per snapshot. Arithmetic means; gap counts blocks, not objects. GLOBAL4 is the retained baseline and independently reconstructed; ORACLE is an unavailable-online lower bound, not a timed competitor.\n\n'+table(['Snapshot','Summary','Mean surviving blocks (%)','Oracle (%)','Mean oracle gap (blocks)','False-pruned blocks'],means)+'\nLOCAL_BALL is worse on 63/64 queries; it is better on one initial query and ties none. Zero false prune is not evidence of selectivity or speed.\n')
    (root/'query/ROBUSTNESS.md').write_text('# Per-query robustness\n\nDescriptive quantiles over each fixed 32-query set; NumPy linear interpolation. No repeated timing runs, confidence intervals or claim of distribution-wide generalization.\n\n'+table(['Snapshot','Summary','Min (%)','p10 (%)','Median (%)','p90 (%)','Max (%)'],robust)+'\nThe local-ball tail is near a full scan, not just a few hard outliers around a good median.\n')
    (root/'query/COST_PROXY.md').write_text('# Fully charged query work proxies\n\nEach distance evaluation is full D=960. Coordinate payload uses FP32 and excludes query coordinates, caching, reuse and output writes. This is a logical payload model, **not measured CPU/GPU time, DRAM traffic or cache transactions**.\n\n'+table(['Summary','Summary distance evals/query','Summary reads (bytes)','Coordinate payload (bytes/query)'],[['GLOBAL4',4,262144,15360],['LOCAL_BALL',4096,32768,15728640],['FULL_SCAN','1,000,000 (all verification)',0,3840000000]])+'\nGLOBAL4 reads 8 FP64 endpoints/block; LOCAL_BALL reads one FP64 radius/block. Optional 64-bit center IDs add 32,768 bytes; optional four pivot IDs add 32 bytes, listed separately from summary reads. Center coordinates are 15.72864 decimal MB versus a full-scan 3.84 decimal GB. The ball summary requires 1024 times as many distances as GLOBAL4, although it is only 0.4096% of full-scan distance work.\n\n## Remaining exact verification must still be paid\n\nModel: summary distances + one full-D distance per surviving object; no reuse of center distances during verification. FULL_SCAN uses all objects once.\n\n'+table(['Snapshot','Summary','Mean surviving objects','Mean total distance evals','Mean total coordinate bytes','Queries with total evals > full scan'],cost)+'\nThe extra summary cost does not purchase a smaller candidate set here. These proxies cannot establish an actual end-to-end slowdown or speedup. Offline certificate construction also costs N center/member distances per snapshot, in addition to reused four-pivot signatures and deterministic C0 selection; no build timing was collected.\n')
    br=[]
    for s in bs['summary']:
        v=s['covering_radius'];br.append([s['snapshot'],4096,'244/245',*[f'{v[k]:.8f}' for k in ('mean','median','p10','p90','min','max')]])
    (root/'summary/LOCAL_BALL_STATS.md').write_text('# One center and conservative radius per frozen block\n\nAll 8192 blocks retain their original membership. Each center is a real member nearest to the four-dimensional signature mean, not an original-space medoid optimization. Exact FP64 selection ties choose the smallest immutable occurrence ID. The JSON includes center row/occurrence IDs, size, covering upper radius and maximum ordered squared member score for every block. No raw coordinates are published.\n\n'+table(['Snapshot','Blocks','Objects/block','Mean radius','Median','p10','p90','Min','Max'],br)+'\nRadii are full-dimensional L2 conservative upper bounds. Their magnitudes alone do not prove a universal high-dimensional failure mechanism.\n')
    figs=root/'figures';figs.mkdir(exist_ok=True)
    write_csv(figs/'summary_survival.csv',plotrows)
    write_csv(figs/'local_vs_global.csv',[dict(snapshot=r['snapshot'],query=r['query'],qid=r['qid'],global4_percent=100*r['global4_survival_fraction'],local_ball_percent=100*r['local_ball_survival_fraction']) for r in rows])
    write_csv(figs/'oracle_gap.csv',[dict(snapshot=r['snapshot'],query=r['query'],qid=r['qid'],oracle_gap_blocks=r['local_ball_oracle_gap']) for r in rows])
    sys.path.insert(0,str(Path(os.environ.get('AGENTS_SKILLS_HOME',Path.home()/'.agents/skills'))/'paper-figures/scripts'))
    from paper_style import setup_style,grouped_bars,scatter_plot,save_fig
    import matplotlib.pyplot as plt
    setup_style('acm_double',use_latex=False)
    # Stable method grammar: gray global, blue local, pale oracle plus distinct hatches.
    colors=['#777777','#0072B2','#DDDDDD'];hatches=['','///','xx']
    fig,axes=plt.subplots(1,2,figsize=(7,2.8),sharey=True,layout='constrained')
    for ax,name in zip(axes,SNAPS):
        vals=[100*sums[name][k]['mean'] for k in KEYS]
        _,_,containers=grouped_bars([vals],METHODS,['Mean'],ylabel='Surviving blocks (%)',ax=ax,legend=False,ylim=(0,105))
        for rect,color,hatch,value in zip(containers[0].patches,colors,hatches,vals):
            rect.set_facecolor(color);rect.set_hatch(hatch);ax.annotate(f'{value:.2f}',(rect.get_x()+rect.get_width()/2,value),xytext=(0,3),textcoords='offset points',ha='center',fontsize=8)
        ax.axhline(50,color='black',ls='--',lw=.7);ax.set_title(name.replace('_',' '));ax.tick_params(axis='x',labelsize=8)
    save_fig(fig,'summary_survival',output_dir=figs,target_width_inches=7);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(7,3.3),sharex=True,sharey=True,layout='constrained')
    for ax,name in zip(axes,SNAPS):
        data=[r for r in rows if r['snapshot']==name]
        scatter_plot([100*r['global4_survival_fraction'] for r in data],[100*r['local_ball_survival_fraction'] for r in data],xlabel='GLOBAL4 surviving blocks (%)',ylabel='LOCAL_BALL surviving blocks (%)',ax=ax,annotate=False,colors=['#0072B2']*32,markers=['o']*32)
        if ax.get_legend() is not None:ax.get_legend().remove()
        ax.plot([0,100],[0,100],color='black',ls='--',lw=.8);ax.set(xlim=(0,103),ylim=(0,103),title=name.replace('_',' '));ax.set_aspect('equal',adjustable='box')
    save_fig(fig,'local_vs_global',output_dir=figs,target_width_inches=7);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(7,2.8),sharey=True,layout='constrained')
    for ax,name in zip(axes,SNAPS):
        data=[r for r in rows if r['snapshot']==name]
        scatter_plot([r['query'] for r in data],[r['local_ball_oracle_gap'] for r in data],xlabel='Query index (fixed order)',ylabel='Unnecessary surviving blocks (count)',ax=ax,annotate=False,colors=['#0072B2']*32,markers=['o']*32)
        if ax.get_legend() is not None:ax.get_legend().remove()
        ax.set(xlim=(-1,32),ylim=(0,4250),title=name.replace('_',' '));ax.set_yticks([0,1000,2000,3000,4096])
    save_fig(fig,'oracle_gap',output_dir=figs,target_width_inches=7);plt.close(fig)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--artifact',type=Path,default=Path(__file__).resolve().parent);main(p.parse_args().artifact)
