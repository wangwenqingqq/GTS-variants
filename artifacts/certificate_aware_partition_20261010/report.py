#!/usr/bin/env python3
"""Finite-query descriptive tables and three reproducible structural figures."""
import argparse
import csv
import json
import os
import sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

os.environ.setdefault('SOURCE_DATE_EPOCH','1791676800')


def load(p):return json.loads(p.read_text())
def table(p,header,rows):
    p.write_text('| '+' | '.join(header)+' |\n| '+' | '.join(['---']*len(header))+' |\n'+
                 ''.join('| '+' | '.join(map(str,r))+' |\n' for r in rows))
def csvout(p,rows):
    with p.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)


def main(root):
    skill=Path(os.environ.get('AGENTS_SKILLS_HOME',str(Path.home()/'.agents/skills')))/'paper-figures/scripts'
    sys.path.insert(0,str(skill))
    try:
        from paper_style import setup_style,save_fig,scatter_plot,grouped_bars
    except ImportError as e:
        raise SystemExit('Figure regeneration requires the installed paper-figures helper via AGENTS_SKILLS_HOME; no source copying is needed') from e
    setup_style('acm_double',width_inches=7.2,font_family='serif',use_latex=False)
    plt.rcParams.update({'font.size':8,'axes.titlesize':9,'axes.labelsize':8,'xtick.labelsize':8,'ytick.labelsize':8,'legend.fontsize':8})
    partitions=load(root/'partition/PARTITION_STATS.json')['rows'];query=load(root/'query/BLOCK_SELECTIVITY.json')
    updates=load(root/'update/UPDATE_RECHECK.json')['rows'];decision=load(root/'evidence/DECISION.json')
    pm={(r['snapshot'],r['strategy'],r['partition']):r for r in partitions}
    qm={(r['snapshot'],r['strategy'],r['partition'],r['pivot_count']):r['statistics'] for r in query['summary']}
    names=['initial','first_rebuilt'];strategies=['S0','S1'];kinds=['P0','P1','P2','P3']
    figdir=root/'figures';figdir.mkdir(exist_ok=True)
    band=[];select=[];balance=[];plotrows=[];trend=[]
    for n in names:
        for s in strategies:
            for k in kinds:
                p=pm[n,s,k];q=qm[n,s,k,4]
                band.append([n,s,k,f"{p['mean_normalized_width']['mean']:.8f}",f"{p['mean_normalized_width']['p90']:.8f}"])
                select.append([n,s,k,f"{100*q['surviving_block_fraction']['mean']:.4f}",f"{100*q['oracle_fraction']['mean']:.4f}",
                               f"{q['oracle_gap_blocks']['mean']:.3f}",f"{100*q['surviving_object_fraction']['mean']:.4f}"])
                balance.append([n,s,k,p['total_blocks'],int(p['size']['min']),int(p['size']['max']),f"{p['imbalance']:.6f}",f"{100*p['physical_occupancy']:.6f}",0])
                plotrows.append(dict(snapshot=n,strategy=s,partition=k,P=4,total_blocks=p['total_blocks'],
                                     mean_normalized_width=p['mean_normalized_width']['mean'],surviving_percent=100*q['surviving_block_fraction']['mean'],
                                     oracle_percent=100*q['oracle_fraction']['mean'],oracle_gap_blocks=q['oracle_gap_blocks']['mean']))
                trend.append([n,s,k,f"{100*qm[n,s,k,2]['surviving_block_fraction']['mean']:.4f}",f"{100*q['surviving_block_fraction']['mean']:.4f}"])
    table(root/'partition/PARTITION_STATS.md',['Snapshot','Pivots','Partition','Mean normalized width','P90 block mean width'],band)
    table(root/'partition/BALANCE.md',['Snapshot','Pivots','Partition','Blocks','Min rows','Max rows','Imbalance','Physical occupancy (%)','False prune'],balance)
    table(root/'query/BLOCK_SELECTIVITY.md',['Snapshot','Pivots','Partition','Surviving (%)','Oracle (%)','Mean oracle gap (blocks)','Surviving objects (%)'],select)
    table(root/'query/P2_TREND.md',['Snapshot','Pivots','Partition','P=2 surviving (%)','P=4 surviving (%)'],trend)
    for name in ('band_width_vs_survival','partition_comparison','oracle_gap'):csvout(figdir/(name+'.csv'),plotrows)
    colors=['#333333','#0072B2','#D55E00','#009E73'];markers=['o','s','^','D']
    fig,axes=plt.subplots(2,2,figsize=(7.2,4.6),sharex=True,sharey=True)
    for i,n in enumerate(names):
        for j,s in enumerate(strategies):
            ax=axes[i,j];rows=[r for r in plotrows if r['snapshot']==n and r['strategy']==s]
            _,_,artists,_=scatter_plot([r['mean_normalized_width'] for r in rows],[r['surviving_percent'] for r in rows],kinds,
                         xlabel='Mean normalized band width' if i==1 else '',ylabel='Surviving blocks (%)' if j==0 else '',
                         colors=colors,markers=markers,annotate=False,ax=ax)
            if ax.get_legend() is not None:ax.get_legend().remove()
            artists[3].lines[0].set_markerfacecolor('none');artists[3].lines[0].set_markeredgecolor(colors[3]);artists[3].lines[0].set_markeredgewidth(1.1);artists[3].lines[0].set_markersize(8)
            ax.set_title(('Initial' if i==0 else 'First rebuilt')+' / '+s)
            ax.set_xlim(0,.15);ax.set_ylim(0,100);ax.axhline(50,color='#999999',linestyle='--',linewidth=.8)
    handles=[Line2D([],[],color=colors[i],marker=markers[i],markerfacecolor='none' if i==3 else colors[i],linestyle='',label=k,markersize=5) for i,k in enumerate(kinds)]
    fig.legend(handles=handles,loc='lower center',ncol=4,frameon=False)
    fig.subplots_adjust(left=.09,right=.99,top=.93,bottom=.18,wspace=.16,hspace=.3)
    save_fig(fig,'band_width_vs_survival',output_dir=figdir,target_width_inches=7.2);plt.close(fig)
    for mode in ('partition_comparison','oracle_gap'):
        fig,axes=plt.subplots(1,2,figsize=(7.2,2.8),sharey=True)
        metric='surviving_percent' if mode=='partition_comparison' else 'oracle_gap_blocks'
        for i,n in enumerate(names):
            data=[[next(r[metric] for r in plotrows if (r['snapshot'],r['strategy'],r['partition'])==(n,s,k)) for k in kinds] for s in strategies]
            grouped_bars(data,kinds,['S0 GTS pivots','S1 Farthest-first'],ax=axes[i],colors=['#888888','#0072B2'],hatches=['//',''],legend=False,
                         ylabel=('Surviving blocks (%)' if mode=='partition_comparison' else 'Mean oracle gap (blocks)') if i==0 else None,
                         ylim=(0,100 if mode=='partition_comparison' else 4000))
            axes[i].set_title('Initial' if i==0 else 'First rebuilt');axes[i].set_xlabel('Partition')
            if mode=='partition_comparison':axes[i].axhline(50,color='#555555',linestyle='--',linewidth=.8)
        handles,labels=axes[0].get_legend_handles_labels();fig.legend(handles,labels,loc='lower center',ncol=2,frameon=False)
        fig.subplots_adjust(left=.095,right=.99,top=.87,bottom=.29,wspace=.15)
        save_fig(fig,mode,output_dir=figdir,target_width_inches=7.2);plt.close(fig)
    table(root/'update/UPDATE_RECHECK.md',['Interval','Events','Blocks','Actual empty slots (%)','Before surviving (%)','After surviving (%)','Changed blocks (%)','Existing moves','Splits','Refreshes'],
          [[r['snapshot']+' → '+r['ending_snapshot'],f"{r['actual_inserts']}I{r['actual_deletes']}D",r['initial_total_blocks'],f"{100*r['actual_initial_empty_slot_fraction']:.6f}",
            f"{100*r['initial_query_survival_mean']:.4f}",f"{100*r['post_update_query_survival_mean']:.4f}",f"{100*r['changed_block_fraction']:.4f}",
            r['moved_existing_objects'],r['splits'],r['certificate_refreshes']] for r in updates])
    assert decision['decision']=='CONDITIONAL' and decision['reason']=='uncovered_interval'
    s,k=decision['top_one'];base=[qm[n,s,'P0',4]['surviving_block_fraction']['mean'] for n in names];best=[qm[n,s,k,4]['surviving_block_fraction']['mean'] for n in names]
    ratios=[pm[n,s,k]['mean_normalized_width']['mean']/pm[n,s,'P0']['mean_normalized_width']['mean'] for n in names]
    oracles=[qm[n,s,k,4]['oracle_fraction']['mean'] for n in names]
    text=f'''# Decision: CONDITIONAL — uncovered interval, no CUDA admission

## Q1. Did partitioning tighten the bands?

Yes, for the recursive partitions, not for every partition. In the frozen joint
winner S1/P2, mean normalized width falls by {100*(1-ratios[0]):.2f}% / {100*(1-ratios[1]):.2f}%
relative to S1/P0 (initial / first rebuilt). Lexicographic P1 actually has wider
mean bands than P0 in all four snapshot/pivot-set combinations. Width is the
rounded-norm geometric diagnostic; filtering uses the unchanged conservative
outward endpoints. This is a descriptive finite-set result, not a significance test.

## Q2. Did tighter bands improve block filtering?

Yes, but not enough. The same S1/P2 configuration reduces mean surviving blocks
from {100*base[0]:.4f}% / {100*base[1]:.4f}% to **{100*best[0]:.4f}% / {100*best[1]:.4f}%**.
The reductions are {100*(base[0]-best[0]):.4f} / {100*(base[1]-best[1]):.4f} percentage points,
not end-to-end speedups. P0 has 3,907 physical blocks; P2 has 4,096. Corresponding
surviving-object fractions are {100*qm[names[0],s,k,4]['surviving_object_fraction']['mean']:.4f}% /
{100*qm[names[1],s,k,4]['surviving_object_fraction']['mean']:.4f}%, so this improvement is not
merely a block-count denominator effect. Query-to-pivot work remains four distances,
but P2 examines 4,096 certificates versus 3,907; preprocessing and routing are not free.
Oracle-required fractions for S1/P2 remain only {100*oracles[0]:.4f}% / {100*oracles[1]:.4f}%.
Even P3's slightly narrower bands do not uniformly outperform P2: average width
is an explanatory proxy, not a monotonic pruning guarantee.

## Q3. Does one P=4 configuration pass <=50% on both snapshots?

No. None of the eight shared configurations passes the joint GO (16 main
configuration-snapshot pairs, 512 query evaluations in total). Another 512 query evaluations reduce certificate dimensions
to P=2 on the same four-pivot partitions; they are a trend check, not a new search.
All 1,024 static rows have zero false prune.
The optimistic separately best certificate-aware results are
{100*decision['best_per_snapshot'][names[0]]:.4f}% / {100*decision['best_per_snapshot'][names[1]]:.4f}%.
These are not a shared winning algorithm. They also do not trigger the explicit
>70% / other-snapshot >50% NO-GO threshold.

## Q4. Is local update retained by the selected configuration?

Local writes are retained in the two bounded simulations. Capacity-aware
initialization, authorized before measurement, uses 4,167 physical blocks of
239/240 objects, actual empty-slot fraction {100*updates[0]['actual_initial_empty_slot_fraction']:.6f}%
(nominal reserve 6.25%). This is a different initialization from the static
4,096-block strict-median layout; its own before/after query survival is
{100*updates[0]['initial_query_survival_mean']:.4f}% / {100*updates[0]['post_update_query_survival_mean']:.4f}% for
initial→first_rebuilt and {100*updates[1]['initial_query_survival_mean']:.4f}% /
{100*updates[1]['post_update_query_survival_mean']:.4f}% for first_rebuilt→second_rebuilt.
Actual intervals are 10I10D and 20I20D. Changed blocks are
{100*updates[0]['changed_block_fraction']:.4f}% / {100*updates[1]['changed_block_fraction']:.4f}%; existing moves,
splits and event-time global repartitions are zero. All 128 before/after query
checks have zero false prune; full final occurrence IDs, lineage, slots and bounds
match the retained next states. The locality gate passes.
Each interval has its own global initialization; sustained cross-epoch ownership
is not tested. Insertion still scans all block means, so local writes do not
prove local total CPU work, low update latency or end-to-end gain.

## Q5. Final decision

**CONDITIONAL / uncovered_interval.** The selected pair's 68.90% / 67.87% is
above the stated <=65% conditional band but below the explicit NO-GO condition.
The fallback was frozen before running: retain uncertainty, do not lower thresholds,
and do not relabel this as a positive conditional pass or a family impossibility.
No CUDA prototype, more pivots, extra partition variants, or long campaign is admitted.
Partition tightness contributes materially, but it does not close the certificate
selectivity gap. This evidence does not uniquely prove why the residual gap exists.
Keep this checkpoint; require a separately approved, genuinely different low-cost
safe-summary hypothesis and nearest-prior-art kill test before further experiments.

## GTSPP narrative and claim boundary

**Redundancy → mechanism → module → role → end-to-end gain:** scattered verification
work → certificate-space grouping → deterministic partition + unchanged safe
interval filter + bounded ownership simulator → fewer surviving blocks with local
writes, still a large oracle gap → **end-to-end gain unknown; no GPU timing**.
This does not replace the existing end-to-end baseline matrix or rescue a novelty
claim. Pivot-space mappings and triangle-inequality filtering are established
([Pivot-based Metric Indexing, PVLDB 2017](https://www.vldb.org/pvldb/vol10/p1058-gao.pdf)).
Preserve P1's wider bands, all weaker configurations, and the failed query gates.

## Validation scope

GIST N=1,000,000; D=960; FP32/L2; B1; radius bits 0x3f34a3d8;
32 original queries on each of two pinned snapshots. Baseline b89264e.
Independent stable-sort construction, direct per-block reductions and owner-based
oracle reconstruction checked all 16 partitions, 64,024 block-statistic rows,
1,024 query rows, summaries and the decision. The prior freshly verified score
cache is reused by exact hash; no new object-pivot distance computation or GPU
execution is claimed. CPU tests, numerical provenance, update full-state checks,
and raw receipt bindings are separate from CUDA sanitizer/performance gates.
'''
    (root/'DECISION.md').write_text(text)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--artifact',type=Path,required=True);main(p.parse_args().artifact)
