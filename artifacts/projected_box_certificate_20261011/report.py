#!/usr/bin/env python3
"""Regenerate exact descriptive tables, resource accounting and three figures."""
import argparse
import csv
import json
import os
import sys
from pathlib import Path
import numpy as np
METHODS=['GLOBAL4','LOCAL_BALL','PROJECTED_BOX','ORACLE']
KEYS=['global4_survival_fraction','local_ball_survival_fraction','projected_box_survival_fraction','oracle_fraction']
SNAPS=['initial','first_rebuilt']


def table(h,rows):return '| '+' | '.join(h)+' |\n| '+' | '.join(['---']*len(h))+' |\n'+''.join('| '+' | '.join(map(str,r))+' |\n' for r in rows)


def csv_write(p,rows):
    with p.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)


def main(root):
    q=json.loads((root/'query/SUMMARY_COMPARISON.json').read_text());b=json.loads((root/'summary/PROJECTED_BOX_STATS.json').read_text());p=json.loads((root/'directions/DIRECTION_PROOF.json').read_text())
    d=json.loads((root/'directions/PCA_DIRECTIONS.json').read_text());ss={s['snapshot']:s['statistics'] for s in q['summary']};rows=q['rows'];means=[];robust=[];wins=[];cost=[];plot=[]
    for name in SNAPS:
        s=ss[name];rr=[r for r in rows if r['snapshot']==name]
        for method,k in zip(METHODS,KEYS):
            v=s[k];gap=(v['mean']-s['oracle_fraction']['mean'])*4096
            means.append([name,method,f"{100*v['mean']:.4f}",f"{100*v['p90']:.4f}",f'{gap:.5f}',0])
            robust.append([name,method,*[f'{100*v[j]:.4f}' for j in ('min','p10','median','p90','max')]])
            plot.append(dict(snapshot=name,summary=method,surviving_percent=100*v['mean'],oracle_gap_blocks=gap))
        wins.append([name,sum(r['projected_box_surviving_blocks']<r['global4_surviving_blocks'] for r in rr),sum(r['projected_box_surviving_blocks']>r['global4_surviving_blocks'] for r in rr),sum(r['projected_box_surviving_blocks']==r['global4_surviving_blocks'] for r in rr)])
        for method,ev,key,dbytes in [('GLOBAL4',4,'global4_surviving_objects',15360),('LOCAL_BALL',4096,'local_ball_surviving_objects',15728640),('PROJECTED_BOX',5,'surviving_objects',30720)]:
            no=s[key]['mean'];cost.append([name,method,f'{no:.5f}',f'{no+ev:.5f}',f'{dbytes+3840+no*3840:.0f}'])
    (root/'query/SUMMARY_COMPARISON.md').write_text('# Summary-family comparison\n\nGIST N1M/D960 FP32 L2, B1; 4096 identical frozen S1/P2 blocks of 244/245 objects; 32 original queries/snapshot. GLOBAL4 and LOCAL_BALL are hash-bound retained results, previously independently verified; this round newly evaluates PROJECTED_BOX and independently reconstructs its complete rows. ORACLE is an unavailable-online lower bound.\n\n'+table(['Snapshot','Summary','Mean surviving blocks (%)','p90 (%)','Mean oracle gap (blocks)','False-pruned blocks'],means)+'\n## Per-query wins against GLOBAL4\n\n'+table(['Snapshot','PROJECTED_BOX better','Worse','Equal'],wins)+'\nPROJECTED_BOX is not uniformly worse: ten queries improve, while 54 regress. Aggregate survival and tail gates nevertheless fail. No measured query speed follows from these counts.\n')
    (root/'query/ROBUSTNESS.md').write_text('# Fixed-query descriptive robustness\n\nLinear-interpolated quantiles across each frozen 32-query set, not repeated process timings or confidence intervals. No cross-snapshot averaging for admission.\n\n'+table(['Snapshot','Summary','Min (%)','p10 (%)','Median (%)','p90 (%)','Max (%)'],robust)+'\nPROJECTED_BOX p90 remains above 92%, failing the 70% target on each snapshot.\n')
    (root/'query/COST_PROXY.md').write_text('# Query cost class and remaining verification\n\nAll reductions span D960. A dot, maximum and ordered squared distance are different operations; counts are work-class proxies, **not identical instructions or latency**. The safe projection computes four dots and one max-absolute-coordinate reduction, fused into one query-input pass. The max reduction is not free.\n\n'+table(['Summary','Query full-D reductions','Endpoints/block','Metadata bytes','Direction/pivot bytes'],[['GLOBAL4','4 distances',8,262144,15360],['LOCAL_BALL','4096 distances','1 radius',32768,15728640],['PROJECTED_BOX','4 dots + 1 numeric max',8,262144,30720],['FULL_SCAN','1,000,000 distances',0,0,0]])+'\nPROJECTED_BOX directions are FP64, GLOBAL4 pivots are FP32. LOCAL_BALL optional center IDs add 32,768 bytes; GLOBAL4 optional pivot IDs add 32 bytes. Those ID payloads are separate. Endpoint reads are 32,768 FP64 values/query for GLOBAL4 and PROJECTED_BOX, not measured memory transactions.\n\n## Fully charged work and logical coordinate payload\n\nModel: summary full-D reductions plus one exact distance per surviving object. Projected work is shown both as `4+survivors` and fully charged `5+survivors` in JSON. The table uses the latter. Coordinate payload includes one shared 3840-byte query, all direction/pivot coordinates and surviving FP32 objects; metadata is separate. No cache reuse, actual DRAM traffic or output cost is claimed. This convention explicitly differs from old coordinate proxies that excluded query coordinates. The core model assumes four direction maximum-absolute coefficients and A2 are cached as static build state (40 more FP64 bytes/index), derived from frozen U/Gram. The offline envelope helper recomputes direction maxima once per batch and its C entry validates all direction coefficients per call; it is not a deployed online operator. If direction maxima were recomputed per online query, charge four additional full-D maxima (nine reductions instead of five). No whole-Python execution-cost equivalence is claimed.\n\n'+table(['Snapshot','Summary','Mean surviving objects','Mean full-D reductions incl verification','Mean logical coordinate bytes'],cost)+'\nFULL_SCAN has 1,000,000 distances and 3,840,003,840 logical coordinate bytes including the query. These counts do not predict an actual end-to-end ratio. PCA/training and block construction also have costs; see the separate resource account below.\n')
    frac=sum(d['eigenvalues'][:4])/sum(d['eigenvalues']);eig=d['eigenvalues'][:5]
    (root/'directions/PCA_RESOURCES.md').write_text('# Initial-only PCA qualification and paid resources\n\nOne deterministic streaming FP64 mean/covariance construction over all 1M initial vectors. No sampling, randomized solver, rebuilt refit, query-selection or oracle tuning. Some dataset rows later serve as fixed query fixtures; they participate only as ordinary training objects, not using their query roles. Covariance/eigenvector determinism is scoped to the retained backend and chunk/thread settings; cross-library bit equality is not promised.\n\n'+table(['Field','Value'],[['PCA wall seconds (one construction + qualification)',f"{p['PCA_wall_seconds']:.9f}"],['Process CPU seconds',f"{p['PCA_process_CPU_seconds']:.6f}"],['Explicit covariance-chunk live arrays peak (bytes)',p['explicit_chunk_live_array_bytes_peak']],['Process peak RSS incl mapped input/runtime (bytes)',p['process_peak_RSS_bytes']],['Pre-PCA process peak RSS (bytes)',p['pre_PCA_peak_RSS_bytes']],['Direction matrix (bytes)',p['direction_matrix_bytes']],['Top-four covariance variance fraction',f'{frac:.9f}'],['Relative eigen residual',f"{p['eigen_residual_relative_fro']:.6g}"],['Exact-Gram infinity deviation upper',f"{p['gram_infinity_deviation_upper']:.6g}"],['Represented projection norm squared upper A2',repr(p['operator_norm_squared_upper'])]])+'\nTime includes two full input passes, covariance, two eigh/sign/Gram qualifications. It excludes earlier registration/build/test/input hashing. Input validation has already read the data, so this is not a cold-start full index build. RSS includes mapped input pages; it is not temporary-array size. The explicit chunk-array account excludes BLAS/LAPACK/runtime internal allocation; both measures are retained rather than conflated. No query time is collected.\n\nTop five covariance eigenvalues: '+', '.join(f'{x:.12g}' for x in eig)+'. The top-four variance fraction alone does not identify which omitted directions determine range separation or prove a universal anisotropy explanation. Directions, signs and exact represented Gram bounds are retained in JSON. Actual native-library hashes/configuration and actual OpenBLAS threads=4 are retained in evidence/REGISTERED.json.\n')
    br=[]
    for s in b['summary']:
        for j,v in enumerate(s['width_by_direction']):br.append([s['snapshot'],j,*[f'{v[k]:.9f}' for k in ('mean','median','p10','p90','min','max')]])
    (root/'summary/PROJECTED_BOX_STATS.md').write_text('# Conservative box statistics\n\nEach of the unchanged 8192 snapshot-block pairs retains four lower and four upper FP64 endpoints. Bounds are built without query/radius/oracle information. The full scalar JSON records membership size, endpoints and widths per direction/block; no per-object projections or raw coordinates are published.\n\n'+table(['Snapshot','Direction (0-based)','Mean width','Median','p10','p90','Min','Max'],br)+'\nThese are widths in the represented linear projection coordinates; Gram repair makes them safe even when stored directions are not mathematically exact orthonormal vectors.\n')
    figs=root/'figures';figs.mkdir(exist_ok=True);csv_write(figs/'summary_survival.csv',plot)
    csv_write(figs/'projected_vs_global.csv',[dict(snapshot=r['snapshot'],query=r['query'],qid=r['qid'],global4_percent=100*r['global4_survival_fraction'],projected_box_percent=100*r['projected_box_survival_fraction']) for r in rows])
    csv_write(figs/'oracle_gap.csv',[dict(snapshot=r['snapshot'],query=r['query'],qid=r['qid'],oracle_gap_blocks=r['projected_box_oracle_gap']) for r in rows])
    sys.path.insert(0,str(Path(os.environ.get('AGENTS_SKILLS_HOME',Path.home()/'.agents/skills'))/'paper-figures/scripts'))
    from paper_style import setup_style,grouped_bars,scatter_plot,save_fig
    import matplotlib.pyplot as plt
    setup_style('acm_double',use_latex=False)
    colors=['#777777','#0072B2','#E69F00','#DDDDDD'];hatches=['','///','\\\\','xx']
    fig,axes=plt.subplots(1,2,figsize=(7,3.0),sharey=True,layout='constrained')
    for ax,name in zip(axes,SNAPS):
        vals=[100*ss[name][k]['mean'] for k in KEYS]
        _,_,containers=grouped_bars([vals],['GLOBAL4','LOCAL\nBALL','PROJECTED\nBOX','ORACLE'],['Mean'],ylabel='Surviving blocks (%)',ax=ax,legend=False,ylim=(0,105))
        for rect,color,hatch,v in zip(containers[0].patches,colors,hatches,vals):
            rect.set_facecolor(color);rect.set_hatch(hatch);ax.annotate(f'{v:.2f}',(rect.get_x()+rect.get_width()/2,v),xytext=(0,3),textcoords='offset points',ha='center',fontsize=8)
        ax.axhline(50,color='black',ls='--',lw=.7);ax.set_title(name.replace('_',' '));ax.tick_params(axis='x',labelsize=8)
    save_fig(fig,'summary_survival',output_dir=figs,target_width_inches=7);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(7,3.3),sharex=True,sharey=True,layout='constrained')
    for ax,name in zip(axes,SNAPS):
        rr=[r for r in rows if r['snapshot']==name]
        scatter_plot([100*r['global4_survival_fraction'] for r in rr],[100*r['projected_box_survival_fraction'] for r in rr],xlabel='GLOBAL4 surviving blocks (%)',ylabel='PROJECTED_BOX surviving blocks (%)',ax=ax,annotate=False,colors=['#E69F00']*32,markers=['s']*32)
        if ax.get_legend() is not None:ax.get_legend().remove()
        ax.plot([0,100],[0,100],color='black',ls='--',lw=.8);ax.set(xlim=(0,103),ylim=(0,103),title=name.replace('_',' '));ax.set_aspect('equal',adjustable='box')
    save_fig(fig,'projected_vs_global',output_dir=figs,target_width_inches=7);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(7,2.8),sharey=True,layout='constrained')
    for ax,name in zip(axes,SNAPS):
        rr=[r for r in rows if r['snapshot']==name]
        scatter_plot([r['query'] for r in rr],[r['projected_box_oracle_gap'] for r in rr],xlabel='Query index (fixed order)',ylabel='Unnecessary surviving blocks (count)',ax=ax,annotate=False,colors=['#E69F00']*32,markers=['s']*32)
        if ax.get_legend() is not None:ax.get_legend().remove()
        ax.set(xlim=(-1,32),ylim=(0,4250),title=name.replace('_',' '));ax.set_yticks([0,1000,2000,3000,4096])
    save_fig(fig,'oracle_gap',output_dir=figs,target_width_inches=7);plt.close(fig)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--artifact',type=Path,default=Path(__file__).resolve().parent);main(p.parse_args().artifact)
