#!/usr/bin/env python3
"""Reproducible finite-query structural tables and vector-first plots, not speedups."""
import argparse,csv,json,os,sys
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np
HERE=Path(__file__).resolve().parent
os.environ.setdefault('SOURCE_DATE_EPOCH','1791590400')

def load(p):return json.loads(p.read_text())
def table(p,header,rows):p.write_text('| '+' | '.join(header)+' |\n| '+' | '.join(['---']*len(header))+' |\n'+''.join('| '+' | '.join(map(str,r))+' |\n' for r in rows))
def csvout(p,rows):
    with p.open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
def saveplot(fig,p):
    if STYLE:
        from paper_style import save_fig
        save_fig(fig,p.name,output_dir=p.parent,target_width_inches=7.2)
    else:
        fig.savefig(p.with_suffix('.pdf'),bbox_inches='tight');fig.savefig(p.with_suffix('.png'),dpi=300,bbox_inches='tight')
    plt.close(fig)

def main(root):
    global STYLE
    skill=Path(os.environ.get('AGENTS_SKILLS_HOME',str(Path.home()/'.agents/skills')))/'paper-figures/scripts'
    sys.path.insert(0,str(skill));STYLE=False
    try:
        from paper_style import setup_style
        setup_style('acm_double',width_inches=7.2,font_family='serif',use_latex=False);STYLE=True
    except ImportError:
        plt.rcParams.update({'font.family':'DejaVu Serif','font.size':8,'axes.labelsize':8,'axes.titlesize':9,'legend.fontsize':7,'pdf.fonttype':42,'ps.fonttype':42,'svg.fonttype':'none','axes.spines.top':False,'axes.spines.right':False})
    plt.rcParams.update({'font.size':8,'axes.titlesize':9,'axes.labelsize':8,'xtick.labelsize':7,'ytick.labelsize':7,'legend.fontsize':7})
    l=load(root/'layout/LAYOUT_RESULTS.json');o=load(root/'oracle/ORACLE_BLOCK_RESULTS.json');c=load(root/'certificate/CERT_SWEEP.json');u=load(root/'update/UPDATE_LOCALITY.json');closure=load(root/'evidence/CLOSURE.json');assert closure['passed']
    names=['initial','first_rebuilt'];labels=['L0','L1','L2','L3'];titles=['Current','Leaf-contiguous','Depth-3 contiguous','DFS order'];strategies=['S0','S1','S2'];colors=['#0072B2','#D55E00','#333333'];marks=['o','s','^'];styles=['-','--',':'];figdir=root/'figures';figdir.mkdir(exist_ok=True)
    lmap={(r['snapshot'],r['layout']):r['statistics'] for r in l['summary']};omap={(r['snapshot'],r['layout'],r['block_size']):r['statistics'] for r in o['summary']};cmap={(r['snapshot'],r['layout'],r['strategy'],r['pivot_count'],r['block_size']):r['statistics'] for r in c['summary']}
    rows=[]
    for name in names:
        for label in labels:
            s=lmap[name,label];rows.append([name,label,f"{100*s['candidate_fraction']['mean']:.3f}",*[f"{100*s['reach_'+str(size)+'_fraction']['mean']:.3f}" for size in (32,256,512)]])
    table(root/'layout/LAYOUT_RESULTS.md',['Snapshot','Layout','Candidates (%)','Reach32 (%)','Reach256 (%)','Reach512 (%)'],rows)
    rows=[]
    for name in names:
        for label in labels:
            s=omap[name,label,256];rows.append([name,label,f"{s['current_tree_reached_blocks']['mean']:.2f}",f"{s['oracle_required_blocks']['mean']:.2f}",f"{100*s['oracle_fraction']['mean']:.4f}",f"{s['block_amplification']['mean']:.2f}",f"{s['empty_but_currently_reached_blocks']['mean']:.2f}"])
    table(root/'oracle/ORACLE_BLOCK_RESULTS.md',['Snapshot','Layout','Mean tree reached','Mean oracle required','Oracle (%)','Mean per-query amplification','Mean empty-but-reached'],rows)
    rows=[];best={}
    for name in names:
        for p in (1,2,4,8):
            choices=[(cmap[name,label,s,p,256]['surviving_block_fraction']['mean'],label,s) for label in labels for s in strategies];value,label,s=min(choices);best[name,p]=(value,label,s)
            rows.append([name,p,label,s,f'{100*value:.4f}',f"{cmap[name,label,s,p,256]['oracle_gap_blocks']['mean']:.2f}",2*p*3907])
    table(root/'certificate/CERT_SWEEP.md',['Snapshot','P','Best diagnostic layout','Strategy','Mean surviving256 (%)','Mean oracle gap (blocks)','Scalar reads/query'],rows)
    with (root/'certificate/CERT_SWEEP.md').open('a') as f:f.write('\nEach row is the best of 12 layout/strategy configurations at this P on that snapshot, **not one shared algorithm across snapshots**. All rejected/weaker rows, 32/512 sensitivity and per-query tails are retained in JSON. Query distance cost is exactly P, no early exit. Metadata is 16*P*3907 bytes for block256. False prune is zero for every configuration/query/block-size.\n')
    power=[];gaps=[]
    for name in names:
        for label in labels:
            for s in strategies:
                for p in (1,2,4,8):
                    z=cmap[name,label,s,p,256];power.append(dict(snapshot=name,layout=label,strategy=s,P=p,query_pivot_distances=p,mean_surviving_percent=100*z['surviving_block_fraction']['mean'],oracle_percent=100*omap[name,label,256]['oracle_fraction']['mean'],tree_reach_percent=100*lmap[name,label]['reach_256_fraction']['mean']));gaps.append(dict(snapshot=name,layout=label,strategy=s,P=p,query_pivot_distances=p,mean_oracle_gap_blocks=z['oracle_gap_blocks']['mean']))
    csvout(figdir/'pruning_power_curve.csv',power);csvout(figdir/'oracle_gap.csv',gaps)
    for mode in ('pruning_power_curve','oracle_gap'):
        fig,axes=plt.subplots(2,4,figsize=(7.2,4.2),sharex=True,sharey=True)
        for ni,name in enumerate(names):
            for li,label in enumerate(labels):
                ax=axes[ni,li]
                for si,s in enumerate(strategies):
                    ys=[100*cmap[name,label,s,p,256]['surviving_block_fraction']['mean'] if mode=='pruning_power_curve' else cmap[name,label,s,p,256]['oracle_gap_blocks']['mean'] for p in (1,2,4,8)]
                    ax.plot([1,2,4,8],ys,color=colors[si],marker=marks[si],linestyle=styles[si],linewidth=1.1,markersize=3)
                if mode=='pruning_power_curve':
                    ax.axhline(100*omap[name,label,256]['oracle_fraction']['mean'],color='#666666',linestyle='-.',linewidth=.8);ax.axhline(100*lmap[name,label]['reach_256_fraction']['mean'],color='#AAAAAA',linestyle=(0,(1,2)),linewidth=.8);ax.set_ylim(-2,103)
                else:ax.set_ylim(0,4000)
                ax.set_xscale('log',base=2);ax.set_xticks([1,2,4,8],labels=['1','2','4','8']);ax.set_title(label+' '+titles[li],fontsize=8)
                if li==0:ax.set_ylabel(('Initial\n' if ni==0 else 'First rebuilt\n')+('Surviving blocks (%)' if mode=='pruning_power_curve' else 'Oracle gap (blocks)'))
                if ni==1:ax.set_xlabel('Query-pivot distances')
        handles=[Line2D([],[],color=colors[i],marker=marks[i],linestyle=styles[i],label=['GTS pivots','Farthest-first','Fixed random'][i],markersize=3) for i in range(3)]
        if mode=='pruning_power_curve':handles+=[Line2D([],[],color='#666666',linestyle='-.',label='Oracle'),Line2D([],[],color='#AAAAAA',linestyle=(0,(1,2)),label='Tree candidates')]
        fig.legend(handles=handles,loc='lower center',ncol=len(handles),bbox_to_anchor=(.5,0),frameon=False);fig.subplots_adjust(left=.085,right=.995,bottom=.17,top=.94,wspace=.18,hspace=.4);saveplot(fig,figdir/mode)
    update_plot=[];summary=[]
    for name in names:
        rs=[r for r in u['rows'] if r['snapshot']==name]
        summary.append([name,'10I10D' if name=='initial' else '20I20D',f"{100*min(r['changed_block_fraction'] for r in rs):.4f}–{100*max(r['changed_block_fraction'] for r in rs):.4f}",f"{min(r['moved_existing_objects'] for r in rs)}–{max(r['moved_existing_objects'] for r in rs)}",f"{min(r['block_splits'] for r in rs)}–{max(r['block_splits'] for r in rs)}",0])
        for r in rs:update_plot.append({k:r[k] for k in ['snapshot','layout','strategy','pivot_count','active_capacity','slack_fraction','actual_inserts','actual_deletes','initial_query_survival_mean','post_update_query_survival_mean','changed_block_fraction','moved_existing_objects','coordinate_payload_model_bytes','certificate_write_model_bytes','block_splits','global_repartition_events']})
    table(root/'update/UPDATE_LOCALITY.md',['Snapshot','Actual update interval','Changed blocks (%) range','Moved existing occurrences range','Splits range','Global repartitions'],summary)
    with (root/'update/UPDATE_LOCALITY.md').open('a') as f:f.write('\nAcross all layouts, strategies and P, both slack settings (240/224 active capacity in 256 slots) moved **zero** existing objects and needed zero splits. These are independent interval initializations, not one organization maintained through both intervals. Duplicate coordinates remain separate immutable occurrences. Inserts still scan every block summary to choose a destination. Local writes do not establish local total CPU work or an update speedup. Payload bytes are a copy model, not measured traffic.\n')
    csvout(figdir/'pruning_vs_update.csv',update_plot)
    fig,axes=plt.subplots(2,4,figsize=(7.2,4.2),sharex=True,sharey=True)
    slack_marks={256:'o',240:'s',224:'^'}
    for ni,name in enumerate(names):
        for li,label in enumerate(labels):
            ax=axes[ni,li]
            for r in update_plot:
                if r['snapshot']==name and r['layout']==label:
                    si=strategies.index(r['strategy']);ax.scatter(100*r['post_update_query_survival_mean'],100*r['changed_block_fraction'],facecolors='none' if si==1 else colors[si],edgecolors=colors[si],marker=slack_marks[r['active_capacity']],s=8+4*r['pivot_count'],linewidth=.5,alpha=.7)
            ax.set_title(label+' '+titles[li],fontsize=8);ax.set_xlim(65,102);ax.set_ylim(0,1.4);ax.set_xticks([70,85,100])
            if ni==1:ax.set_xlabel('Surviving blocks (%)')
            if li==0:ax.set_ylabel(('Initial: 10I10D\n' if ni==0 else 'First rebuilt: 20I20D\n')+'Changed blocks (%)')
    handles=[Line2D([],[],marker='o',linestyle='',color=colors[i],markerfacecolor='none' if i==1 else colors[i],label=['GTS pivots','Farthest-first','Fixed random'][i],markersize=4) for i in range(3)]+[Line2D([],[],marker=slack_marks[cap],linestyle='',color='black',label=f'{(256-cap)/256*100:g}% slack',markersize=4) for cap in (256,240,224)]
    fig.legend(handles=handles,loc='lower center',ncol=3,bbox_to_anchor=(.5,-.025),frameon=False);fig.subplots_adjust(left=.085,right=.995,bottom=.22,top=.94,wspace=.18,hspace=.4);saveplot(fig,figdir/'pruning_vs_update')
    initial4=best['initial',4][0];rebuilt4=best['first_rebuilt',4][0];initial8=best['initial',8][0];rebuilt8=best['first_rebuilt',8][0]
    decision=f'''# Decision: CONDITIONAL — no GPU prototype

## Q1. Current problem

Physical scatter consumes much of the current tree's logical pruning. With exact
candidate identities unchanged, L0 mean block256 reach is 99.4633% / 99.5585%;
L1/L3 reduce it to 76.5477% / 63.8589% (initial / first rebuilt).
This is an offline permutation/count result, not executed GPU layout or speed.
The initial snapshot still exceeds the plan's 70% layout target.

## Q2. Headroom

Oracle block256 reach is 2.7995% / 4.2496% in L0, and 0.3311% / 0.3183% in L3.
These are means of the 32 original queries per snapshot; oracle is never used in
pivot selection, certificates, layouts, or insertion placement.
There is strong ideal block headroom, but no cheap realization is established.

## Q3. Cheap safe certificate

**No.** Even the separately best P<=4 configuration retains {100*initial4:.4f}% /
{100*rebuilt4:.4f}% blocks, not <=50%. At P=8 the separately best results are
{100*initial8:.4f}% / {100*rebuilt8:.4f}%, with different winning strategies.
No identical configuration passes both snapshots' GO gates. Oracle gaps remain
large; non-tiny queries (>=1% required blocks) are explicitly identified in JSON,
and small-oracle queries are not silently treated as ratio passes.
All 9,216 static configuration/query/block-size rows have zero false prune.
The closest cheap design is still substantially weaker than the current tree's
logical selection after contiguity, especially on initial.

## Q4. Update locality

**Local writes are possible in this model, not proved fast or sustained.**
All 288 layout/strategy/P/slack simulations are below 1.28% distinct changed
blocks. With 6.25% or 12.5% initial slack, no existing objects move and no blocks
split. Without slack, up to 1,288 / 2,579 existing occurrences move. Global
repartition is zero by construction. All 9,216 post-update query checks have
zero false prune, and final exact occurrence/lineage deltas match the retained
next snapshots. The first interval is actual 10I10D; the second is actual
20I20D, although its net entering/removing base instances are 10/10.
Each interval initializes its own organization; this does not establish
maintenance across consecutive epochs. Best-match insertion scans all block
summaries. Copy-model bytes exclude allocation, scheduling and measured I/O.

## Q5. Decision and next falsifiable action

**CONDITIONAL; do not enter GPU Flat Block Index v0.**
The cheap-query <=50% gate failed. Neither snapshot's best P8 result is >80%,
so the predeclared explicit global-design NO-GO is not triggered. Initial lies
in the otherwise unspecified 70–80% gray zone; CONDITIONAL means *not admitted*,
not a relaxed positive result. The original automatic D gate was false and its
receipt is retained. The user subsequently authorized D only as an additional
ownership diagnostic, under a separate pre-D contract.

Do not increase P beyond 8 or promote local-write success into a system claim.
The next bounded proposal should attack partition tightness or a genuinely
stronger <=4-cost summary, independently falsifiable against matched scan.
Before new work, test novelty against prior metric-indexing systems. Global
pivot triangle-inequality filtering is established prior art, not our invention
([Pivot-based Metric Indexing, PVLDB 2017](https://www.vldb.org/pvldb/vol10/p1058-gao.pdf)).
This round tests a GPU-block ownership realization, and **does not claim its
novelty or end-to-end benefit**.

## Narrative and evidence boundary

Redundancy: logical pruning still touches most complete verification blocks.
Mechanism tested: stable blocks plus globally shared conservative distance bands.
Modules: partition, certificate filter and local ownership simulator only.
Role: scatter is reduced and writes are bounded, but cheap block filtering is
not selective enough. **End-to-end gain: unknown, no GPU implementation/timing.**
Preserve this negative cheap-query result, all weak strategies and sensitivity
rows. Reopen only with a different partition/summary mechanism that clears the
same <=4-pivot/equivalent-cost query gate, not by adding more pivots.

## Validation and provenance

- Baseline: db89d2f1aa66b934f3b99b5730efafa87cee5a71.
- GIST N=1,000,000, D=960 FP32, L2, B1; original radius bits 0x3f34a3d8.
- 2 frozen snapshots ×48 main configurations ×32 original queries; block32/512
  are sensitivities using the same selected pivots, not additional searches.
- Fresh CPU library recomputed all 48,000,000 object-pivot distances bitwise;
  every layout/oracle/certificate row and summary reconstructed.
- Original and fresh four-test numerical suites passed; delivered suite adds
  joint-admission, proof-tamper and executed-copy recipe regressions. See closure and source hashes.
- Immutable execution copies remain outside Git. Delivered drivers were hardened
  after execution; original source identities and deferred-D receipt are not
  rewritten. Closure binds actual original inputs despite entry-gate omissions.
- No GPU process launched, no external matrix rerun, no real traffic/latency
  measurement, no sustained-workload validation. CPU-only four-thread helper,
  low-priority orchestration; no foreign process modified.
'''
    (root/'DECISION.md').write_text(decision)
    (figdir/'README.md').write_text('''# Figure semantics

All curves show exact arithmetic means over the frozen 32 queries, not repeated
process timing. No confidence intervals are invented. Numeric distributions are
retained per query in JSON. Figures are authored at 7.2-inch full-paper width;
vector PDFs and 300-DPI PNGs are generated from the adjacent CSVs.

1. `pruning_power_curve`: Global pivot bands are far less selective than oracle;
   the horizontal tree-candidate line counts the same layout's original candidates.
2. `oracle_gap`: Most surviving blocks contain no range hit even at eight pivots.
3. `pruning_vs_update`: Local writes do not solve weak query filtering. All points
   recompute post-update survival for their actual slack packing; intervals have
   different true I/D counts. Marker size grows with P=1/2/4/8, shape encodes slack,
   facets encode layout, color/fill encodes pivot strategy; all three strategies are retained, coincident points are
   not jittered. Results are counts/models, not GPU speed or traffic.
''')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--artifact',type=Path,default=HERE);main(p.parse_args().artifact)
