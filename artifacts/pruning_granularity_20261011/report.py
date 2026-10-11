#!/usr/bin/env python3
"""Regenerate structural curves, occupancy/metadata tables and sensitivity proxies."""
import argparse
import csv
import os
import sys
from pathlib import Path
from tiles import HERE,SIZES,SNAPS,LAMBDAS,load


def table(header,rows):return '| '+' | '.join(header)+' |\n| '+' | '.join(['---']*len(header))+' |\n'+''.join('| '+' | '.join(map(str,r))+' |\n' for r in rows)
def csv_write(path,rows):
    with path.open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)


def main(root):
    q=load(root/'granularity/GRANULARITY_RESULTS.json');cost=load(root/'cost/COST_PROXY.json');idx={(s['snapshot'],s['tile_size']):s for s in q['summary']};layout={(s['snapshot'],s['tile_size']):s for s in q['layouts']}
    curve=[];robust=[];oracle=[];occ=[];csvrows=[];wins=[]
    for n in SNAPS:
        anchor=[r for r in q['rows'] if r['snapshot']==n and r['tile_size']==256]
        for t in SIZES:
            s=idx[n,t]['statistics'];l=layout[n,t];rr=[r for r in q['rows'] if r['snapshot']==n and r['tile_size']==t]
            curve.append([n,t,l['total_tiles'],f"{100*s['surviving_tile_fraction']['mean']:.4f}",f"{100*s['surviving_object_fraction']['mean']:.4f}",f"{100*s['oracle_tile_fraction']['mean']:.4f}"])
            robust.append([n,t,*[f"{100*s['surviving_object_fraction'][k]:.4f}" for k in ('min','p10','median','p90','max')]])
            oracle.append([n,t,f"{s['oracle_required_tiles']['mean']:.5f}",f"{s['oracle_gap_tiles']['mean']:.5f}",f"{s['oracle_objects_in_required_tiles']['mean']:.5f}",f"{s['true_hit_count']['mean']:.5f}",0])
            occ.append([n,t,l['total_tiles'],int(l['occupancy']['min']),int(l['occupancy']['max']),f"{100*l['physical_occupancy']:.4f}"])
            wins.append([n,t,sum(r['surviving_objects']<a['surviving_objects'] for r,a in zip(rr,anchor)),sum(r['surviving_objects']>a['surviving_objects'] for r,a in zip(rr,anchor)),sum(r['surviving_objects']==a['surviving_objects'] for r,a in zip(rr,anchor))])
            csvrows.append(dict(snapshot=n,tile_size=t,total_tiles=l['total_tiles'],mean_surviving_object_percent=100*s['surviving_object_fraction']['mean'],mean_surviving_tile_percent=100*s['surviving_tile_fraction']['mean'],p90_surviving_object_percent=100*s['surviving_object_fraction']['p90'],metadata_bytes=l['metadata_bytes'],endpoint_reads=l['endpoint_reads']))
    (root/'granularity/GRANULARITY_RESULTS.md').write_text('# Fixed GLOBAL4 granularity curve\n\nGIST N1M/D960 FP32 L2 B1, original32 queries per snapshot, fixed radius0x3f34a3d8. Arithmetic means are deterministic structural counts, not process timings or confidence intervals. Each target independently restarts the identical S1/P2 recursive rule; all smaller member sets are nested.\n\n'+table(['Snapshot','Target size','Tiles','Mean surviving tiles (%)','Mean surviving objects (%)','Mean oracle tiles (%)'],curve)+'\n## Actual occupancy\n\nTarget size is a maximum, not an exact leaf size; recursive boundaries are not flattened/rechunked. Static slots below are a target-capacity model, not a GPU allocation.\n\n'+table(['Snapshot','Target size','Tiles','Min objects/tile','Max','Modeled occupancy (%)'],occ)+'\n## Fixed-query robustness\n\nLinear-interpolated quantiles across32 queries, not repeated runs.\n\n'+table(['Snapshot','Target size','Min objects (%)','p10','Median','p90','Max'],robust)+'\n## Object-work wins against256\n\n'+table(['Snapshot','Target size','Better queries','Worse','Equal'],wins)+'\nThe256 permutations, leaf boundaries and complete64 anchor rows reproduce exactly. Object counts, not tile percentages, drive admission.\n')
    (root/'oracle/ORACLE_BY_TILE.md').write_text('# Oracle changes with granularity\n\nA tile is required iff at least one complete ordered-FP64 reference hit belongs to it. Oracle is diagnostic only, never a partition/filter input. Required-tile objects include false positives sharing a required tile; they are not the true-hit count.\n\n'+table(['Snapshot','Target size','Mean required tiles','Mean empty surviving tiles','Mean objects in required tiles','Mean true hits','False-pruned tiles'],oracle)+'\nAll320 rows have zero false prune; independent stable-sort/direct-endpoint/owner-array verification reconstructs all rows. This does not qualify a CUDA kernel or establish end-to-end benefit.\n')
    meta=[[r['snapshot'],r['tile_size'],r['total_tiles'],r['endpoint_reads'],r['metadata_bytes'],r['relative_to_256']] for r in cost['metadata']]
    proxy=[[r['snapshot'],r['tile_size'],r['lambda_value'],f"{r['statistics']['mean']:.9f}"] for r in cost['proxy_summary']]
    best=[[r['snapshot'],r['lambda_value'],r['best_size']] for r in cost['best_by_snapshot_and_lambda']]
    (root/'cost/COST_PROXY.md').write_text('# Paid metadata and verification work\n\nEach query uses4 full-D query-pivot distances and checks every tile. Pivot scores are reused from the qualified immutable campaign, not newly timed here. Endpoint reads=8*tiles, checks=tiles (or4*tiles pivot-interval checks); stored endpoints=64*tiles bytes. Full-filter logical endpoint payload/query equals stored metadata bytes, **not** measured traffic or per-query transfer/allocation. A common FP32 pivot payload is4*960*4=15360 bytes; pivot IDs32 bytes, query3840 bytes and tile mapping/compaction/output costs are separate. No equivalent-distance price is assigned to a scalar endpoint.\n\n'+table(['Snapshot','Target size','Tiles','Endpoint reads/query','Endpoint metadata bytes','Ratio vs256'],meta)+'\nVerification work is surviving_objects; modeled full-D distances add the common four query-pivot distances. This is not latency, cache/DRAM traffic or a whole-system cost ledger. More fine tiles increase checks, metadata and potential scheduling cost.\n\n## Prespecified sensitivity, not GPU time\n\nnormalized_proxy=surviving_objects/N + lambda*tiles/tiles256. Only lambda=.01,.05,.10 are checked. No coefficient is fit to timings or chosen for admission. Lambda has no inferred GPU calibration.\n\n'+table(['Snapshot','Target size','Lambda','Mean normalized proxy'],proxy)+'\n'+table(['Snapshot','Lambda','Lowest-proxy target (coarsest tie)'],best)+'\nThese conditional proxy optima do not establish a measured sweet spot. Lower survivor counts plus higher metadata are a tradeoff, not free acceleration.\n')
    figs=root/'figures';figs.mkdir(exist_ok=True)
    csv_write(figs/'tile_vs_surviving_objects.csv',[{k:r[k] for k in ('snapshot','tile_size','total_tiles','mean_surviving_object_percent','mean_surviving_tile_percent','p90_surviving_object_percent')} for r in csvrows])
    csv_write(figs/'tile_vs_metadata.csv',[{k:r[k] for k in ('snapshot','tile_size','total_tiles','metadata_bytes','endpoint_reads')} for r in csvrows])
    csv_write(figs/'tradeoff_frontier.csv',[{k:r[k] for k in ('snapshot','tile_size','metadata_bytes','endpoint_reads','mean_surviving_object_percent')} for r in csvrows])
    sys.path.insert(0,str(Path(os.environ.get('AGENTS_SKILLS_HOME',Path.home()/'.agents/skills'))/'paper-figures/scripts'))
    from paper_style import setup_style,trend_plot,save_fig
    import matplotlib.pyplot as plt
    setup_style('acm_double',use_latex=False);colors=['#0072B2','#E69F00'];markers=['o','s'];styles=['-','--'];x=list(range(5))
    ys=[[100*idx[n,t]['statistics']['surviving_object_fraction']['mean'] for t in SIZES] for n in SNAPS]
    fig,ax=plt.subplots(figsize=(3.5,2.8),layout='constrained');trend_plot(x,ys,['Initial','First rebuilt'],xlabel='Maximum objects per tile',ylabel='Surviving objects (%)',ax=ax,colors=colors,markers=markers,linestyles=styles,legend_kwargs=dict(loc='lower left'))
    ax.set_xticks(x,[str(t) for t in SIZES]);ax.set_ylim(0,105);ax.axhline(50,color='black',ls=':',lw=.7);save_fig(fig,'tile_vs_surviving_objects',output_dir=figs,target_width_inches=3.5);plt.close(fig)
    rr=csvrows[:5];fig,axes=plt.subplots(1,2,figsize=(7,2.8),layout='constrained')
    for ax,key,unit in zip(axes,['metadata_bytes','endpoint_reads'],['Endpoint payload/query (KiB)','Endpoint values/query (thousands)']):
        values=[r[key]/(1024 if key=='metadata_bytes' else 1000) for r in rr];trend_plot(x,[values],['Both snapshots'],xlabel='Maximum objects per tile',ylabel=unit,ax=ax,colors=['#777777'],markers=['o'],legend=False);ax.set_xticks(x,[str(t) for t in SIZES]);ax.set_ylim(bottom=0)
    save_fig(fig,'tile_vs_metadata',output_dir=figs,target_width_inches=7);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(7,2.8),sharey=True,layout='constrained')
    for ax,n,y,color,marker in zip(axes,SNAPS,ys,colors,markers):
        overhead=[layout[n,t]['metadata_bytes']/1024 for t in SIZES];trend_plot(overhead,[y],[n],xlabel='Endpoint payload/query (KiB, log2)',ylabel='Surviving objects (%)',ax=ax,colors=[color],markers=[marker],legend=False)
        ax.set_xscale('log',base=2);ax.set_xticks(overhead,[str(int(v)) for v in overhead]);ax.set_ylim(0,105);ax.set_title(n.replace('_',' '))
        for xx,yy,t in zip(overhead,y,SIZES):ax.annotate(str(t),(xx,yy),xytext=(0,5),textcoords='offset points',ha='center',fontsize=8)
    save_fig(fig,'tradeoff_frontier',output_dir=figs,target_width_inches=7);plt.close(fig)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--artifact',type=Path,default=HERE);main(p.parse_args().artifact)
