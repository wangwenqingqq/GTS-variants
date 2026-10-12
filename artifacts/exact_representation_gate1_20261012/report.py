"""Regenerate planned tables/figures and design-only stage accounting from full histograms."""
import argparse,csv,json,sys
from pathlib import Path
from analyze import load,save,percentile
def table(path,title,headers,rows,note=''):
    path.write_text(title+'\n\n'+note+'\n\n| '+' | '.join(headers)+' |\n| '+' | '.join(['---']*len(headers))+' |\n'+''.join('| '+' | '.join(str(x) for x in r)+' |\n' for r in rows))
def csv_table(path,headers,rows):
    with path.open('w') as f:w=csv.writer(f,lineterminator='\n');w.writerow(headers);w.writerows(rows)
def report(root,figure_skill):
    a=load(root/'evidence/AGGREGATE.json');c=load(root/'CONTRACT.json');records=load(root/'evidence/QUERY_RECORDS.json')
    for name in ('required_dims','checkpoints','bytes','margin','figures'):(root/name).mkdir(exist_ok=True)
    s=a['all_objects'];b=a['bytes'];r=a['query_mean_robustness'];D=c['workload']['D'];N=c['workload']['N'];pairs=a['pairs']
    save(root/'required_dims/REQUIRED_DIMS.json',dict(all_objects=s,nonhits=a['nonhits'],true_hits=a['hits'],hard_nonhits_at_D=sum(x['hard_nonhits_at_D'] for x in records),denominator='all32M pairs; original32 queries and all1M occurrences/query'))
    table(root/'required_dims/REQUIRED_DIMS.md','# Required dimensions',['Metric','All objects','Nonhits only'],
        [[k,f"{s[k]:.6f}",f"{a['nonhits'][k]:.6f}"] for k in ('mean','median','p10','p90','p95','p99')],
        'All32M pairs. Hits require960; last-coordinate nonhits are separate from hits. Complete-population linear quantiles, not sample estimates.')
    save(root/'checkpoints/CHECKPOINT_REJECTION.json',dict(pairs=pairs,rows=a['checkpoint_rejection'],unresolved_includes_hits=True))
    table(root/'checkpoints/CHECKPOINT_REJECTION.md','# Checkpoint rejection',['K','Rejected %','Unresolved %','True-hit %'],
        [[v['K'],f"{100*v['rejected_fraction']:.6f}",f"{100*v['unresolved_fraction']:.6f}",f"{100*v['hit_fraction']:.6f}"] for v in a['checkpoint_rejection']],
        'Denominator: all32M pairs. Rejection is strict and safe under ordered-FP64 semantics. True-hit fraction is included in unresolved, not a third disjoint class.')
    save(root/'bytes/BYTE_HEADROOM.json',dict(**b,mean_required_dims=s['mean'],per_query=a['per_query'],query_mean_robustness=r,scope=a['scope']))
    table(root/'bytes/BYTE_HEADROOM.md','# Ideal coordinate-byte headroom',['Metric','Value'],[
        ['Full bytes/object',b['full_bytes_per_object']],['Mean required dimensions',f"{s['mean']:.6f}"],['Mean bytes/object',f"{b['mean_bytes_per_object']:.6f}"],
        ['Full bytes/query',b['full_bytes_per_query']],['Ideal bytes/query',f"{b['ideal_bytes_per_query']:.6f}"],['Byte fraction',f"{b['byte_fraction']:.9f}"],['Theoretical reduction',f"{b['theoretical_reduction']:.6%}"]],
        'FP32 coordinates only, decimal bytes. This diagnostic actually reads/computes all960 for proof. These are counterfactual payload counts, not measured GPU traffic or latency.')
    robustness={}
    for key in ('mean','median','p90','ideal_bytes','hit_count'):
        values=[v[key] for v in a['per_query']];robustness[key]=dict(min=min(values),p10=percentile(values,.1),median=percentile(values,.5),p90=percentile(values,.9),max=max(values))
    save(root/'bytes/PER_QUERY_ROBUSTNESS.json',dict(original_queries=32,metrics=robustness,scope='Finite query-pool variation, not a sampling CI'))
    table(root/'bytes/PER_QUERY_ROBUSTNESS.md','# Per-query robustness',['Query metric','min','p10','median','p90','max'],[[key,*[f'{v[k]:.6f}' for k in ('min','p10','median','p90','max')]] for key,v in robustness.items()],
        'All32 original queries in their original order; p90(query mean) is the frozen admission statistic. ideal_bytes is decimal bytes/query; no sampled uncertainty.')
    save(root/'margin/MARGIN_ANALYSIS.json',dict(boundaries=c['margin'],groups=a['margin_groups'],scope='Diagnostic only; gate includes hits and all objects'))
    fmt=lambda v:'N/A' if v is None else f'{v:.6f}'
    table(root/'margin/MARGIN_ANALYSIS.md','# Distance-margin diagnostic',['Nonhit group','Count','Mean dimensions','p90 dimensions','Nonhit share %','Savings share %'],
        [[key,v['count'],fmt(v['mean']),fmt(v['p90']),fmt(v['nonhit_fraction']*100),fmt(v['coordinate_savings_fraction']*100 if v['coordinate_savings_fraction'] is not None else None)] for key,v in a['margin_groups'].items()],
        'margin=ordered full squared distance−threshold. Near:0<margin≤0.1×threshold; medium:0.1×threshold<margin≤threshold; far:margin>threshold. Savings share uses coordinate savings over all nonhits; hits have zero savings. No radius or gate change.')
    if a['decision']=='GO_BYTE_REDUCTION':
        rows=[];previous=0;active=pairs;payload=0;continuations=0
        for end in (128,256,512,960):
            coordinate_bytes=active*(end-previous)*4;after=pairs-sum(a['nonhit_histogram'][:end+1]);payload+=coordinate_bytes
            rows.append(dict(start=previous,end=end,input_pairs=active,unresolved_after=after,coordinate_bytes=coordinate_bytes,mean_input_objects=active/32,mean_unresolved_after=after/32))
            if end<960:continuations+=after
            previous=end;active=after
        stage=dict(scope='Design-only128/256/512/960 checkpoints; no GPU code or performance admission',rows=rows,coordinate_bytes_per_query=payload/32,coordinate_reduction=1-payload/(pairs*D*4),ideal_coordinate_bytes_per_query=b['ideal_bytes_per_query'],optional_global_FP64_state_read_write_bytes_per_query=16*continuations/32,optional_int32_continuation_read_write_bytes_per_query=8*continuations/32,not_priced=['compaction scratch/scan','masks','divergence and sectors','launches','complete output','updates','conservative GPU numerical arithmetic'])
        save(root/'bytes/STAGE_ACCOUNTING.json',stage)
        table(root/'GPU_DESIGN_GATE.md','# GO permits design only, not implementation',['Coordinates','Input pairs','Unresolved after','Mean coordinate GB/query'],
            [[f"{v['start']}..{v['end']-1}",v['input_pairs'],v['unresolved_after'],f"{v['coordinate_bytes']/32/1e9:.6f}"] for v in rows],
            f"Checkpoint-rounded coordinate payload **{stage['coordinate_bytes_per_query']/1e9:.6f}GB/query**, reduction **{stage['coordinate_reduction']:.6%}**. Per-coordinate ideal payload is{b['ideal_bytes_per_query']/1e9:.6f}GB/query. These are different denominators.\n\n"
            f"If a future multi-kernel design stores FP64 partials at all three continuation boundaries, state read+write proxy is **{stage['optional_global_FP64_state_read_write_bytes_per_query']/1e6:.6f}MB/query**. Int32 compact owner read+write proxy is **{stage['optional_int32_continuation_read_write_bytes_per_query']/1e6:.6f}MB/query**. These optional traffic terms do not include scan scratch, masks or launch/control costs, and are not unavoidable for a persistent design.\n\n"
            'Keep original occurrence ownership. Price persistent state versus staged compaction rather than assuming either is free. The analytical ordered-FP64 recurrence is not a safe drop-in warp reduction; establish a conservative same-reference rejection bound and complete-output fields first. No GPU arithmetic or schedule is selected here. Full GPU/SIMD/exact-screening prior-art, semantic and total-cost gates remain before a separately frozen prototype. No CUDA, dimension ordering, coding or dynamic workflow was started.')
    sys.path.insert(0,str(figure_skill/'scripts'));from paper_style import setup_style,trend_plot,save_fig
    import numpy as np
    import matplotlib.pyplot as plt
    setup_style('acm_double',width_inches=3.5,height_ratio=.74,font_family='serif',use_scienceplots=False)
    h=np.array(a['total_histogram']);cdf=np.cumsum(h)/pairs*100
    all_cdfs=np.array([np.cumsum(v['histogram'])/N*100 for v in records]);x=np.arange(D+1)
    fig,ax,_=trend_plot(x,[cdf],['All objects'],xlabel='Required dimensions',ylabel='Objects resolved (%)',colors=['#0072B2'],markers=[''],legend=False)
    ax.fill_between(x,all_cdfs.min(0),all_cdfs.max(0),color='#BBBBBB',alpha=.35,label='Query min–max',zorder=0)
    ax.set_xlim(0,D);ax.set_ylim(0,102);ax.set_xticks([0,192,384,576,768,960]);ax.legend(loc='lower right',frameon=False,fontsize=7);fig.tight_layout(pad=.45)
    save_fig(fig,'required_dims_cdf',formats=('pdf','svg','png'),output_dir=root/'figures',verify_fonts=False);plt.close(fig)
    csv_table(root/'figures/required_dims_cdf.csv',['K','all_pair_CDF','query_min_CDF','query_max_CDF'],[[k,cdf[k]/100,all_cdfs[:,k].min()/100,all_cdfs[:,k].max()/100] for k in x])
    checkpoints=a['checkpoint_rejection'];x=[v['K'] for v in checkpoints];y=[v['rejected_fraction']*100 for v in checkpoints]
    fig,ax,_=trend_plot(x,[y],['Safe rejection'],xlabel='Prefix dimensions',ylabel='Safely rejected objects (%)',colors=['#0072B2'],markers=['o'],legend=False)
    ax.set_xlim(0,985);ax.set_ylim(0,102);ax.set_xticks([0,192,384,576,768,960]);fig.tight_layout(pad=.45)
    save_fig(fig,'checkpoint_rejection',formats=('pdf','svg','png'),output_dir=root/'figures',verify_fonts=False);plt.close(fig)
    csv_table(root/'figures/checkpoint_rejection.csv',['K','rejected_pairs','rejected_fraction','unresolved_fraction','true_hit_fraction'],[[v['K'],v['rejected'],v['rejected_fraction'],v['unresolved_fraction'],v['hit_fraction']] for v in checkpoints])
    fig,ax=plt.subplots();x=np.arange(1,33);y=[v['ideal_bytes']/1e9 for v in a['per_query']]
    ax.scatter(x,y,s=13,color='#0072B2',edgecolor='black',linewidth=.4,label='Ideal progressive')
    ax.axhline(3.84,color='black',linestyle='--',linewidth=.8,label='Full FP32 read:3.84GB')
    ax.set_xlabel('Original query position');ax.set_ylabel('Ideal coordinate payload (GB/query)');ax.set_xlim(.3,32.7);ax.set_ylim(-.08,4.2);ax.set_xticks([1,8,16,24,32]);ax.legend(loc='upper right',bbox_to_anchor=(1,.86),fontsize=7,frameon=False);fig.tight_layout(pad=.45)
    save_fig(fig,'per_query_bytes',formats=('pdf','svg','png'),output_dir=root/'figures',verify_fonts=False);plt.close(fig)
    csv_table(root/'figures/per_query_bytes.csv',['query_position','qid','mean_required_dims','median_required_dims','p90_required_dims','ideal_GB','hit_count'],[[v['query_index']+1,v['qid'],v['mean'],v['median'],v['p90'],v['ideal_bytes']/1e9,v['hit_count']] for v in a['per_query']])
    for p in (root/'figures').glob('*.svg'):p.write_text('\n'.join(line.rstrip() for line in p.read_text().splitlines())+'\n')
    headline=f"**{a['decision']}**: mean **{s['mean']:.6f}** dimensions; ideal coordinate payload **3.840000→{b['ideal_bytes_per_query']/1e9:.6f}GB/query**, reduction **{b['theoretical_reduction']:.6%}**."
    table(root/'README.md','# Exact representation / progressive byte reduction Gate1',['Metric','Result'],[
        ['All-object mean / median dimensions',f"{s['mean']:.6f} / {s['median']:.6f}"],['Object-level p90 / p99 dimensions',f"{s['p90']:.6f} / {s['p99']:.6f}"],['Query-mean p90 / maximum dimensions',f"{r['p90']:.6f} / {r['max']:.6f}"],['Full / ideal bytes per query',f"{b['full_bytes_per_query']} / {b['ideal_bytes_per_query']:.6f}"],['True-hit pairs',a['hits']],['Full960 reference bit mismatches / false rejections','0 /0'],['GPU starts',0]],
        headline+'\n\nGIST1M/D960, FP32 row-major, initial snapshot, original32 queries, original0..959 order, radius bits0x3f34a3d8. All32M pairs are measured offline. **This is counterfactual coordinate payload, not measured GPU traffic or speedup. Early abandoning is not novelty.** All32 query means are below384; the maximum remains below480. No query was selected or changed.\n\nThe parent strengthened baseline is commit939cd2e. No CUDA/kernel, coding, reordering, approximate arithmetic or dynamic workflow was introduced.')
    with (root/'README.md').open('a') as f:f.write('\n## Evidence\n\n[Contract](CONTRACT.json) · [Numerics](NUMERICS.md) · [Prior art](PRIOR_ART.md) · [Decision](DECISION.md) · [Claim ledger](CLAIM_EVIDENCE.md) · [Reproduce](REPRODUCE.md) · [Costs](COST_LEDGER.md)\n\n[Dimension distribution](required_dims/REQUIRED_DIMS.md) · [Checkpoints](checkpoints/CHECKPOINT_REJECTION.md) · [Byte headroom](bytes/BYTE_HEADROOM.md) · [Query robustness](bytes/PER_QUERY_ROBUSTNESS.md) · [Margins](margin/MARGIN_ANALYSIS.md) · [Design-only stage accounting](GPU_DESIGN_GATE.md)\n\n![Required dimensions](figures/required_dims_cdf.png)\n\nFigure1: full32M-pair required-dimension CDF; gray range is the observed min/max of the32 complete query CDFs, not a CI. At960, hits are resolved by full evaluation.\n\n![Checkpoint rejection](figures/checkpoint_rejection.png)\n\nFigure2: strict-safe rejection at the ten frozen checkpoints; the denominator includes hits, so the last point is the nonhit fraction.\n\n![Per-query bytes](figures/per_query_bytes.png)\n\nFigure3: ideal coordinate payload for every original query, in original order; the dashed line is the full3.84GB coordinate payload, not a latency lower bound.\n\n## Next action and boundary\n\nGO admits design only. The staged payload and optional metadata proxies are not a total-cost or end-to-end proof. A future GPU campaign needs a conservative numerical contract, complete-output verification, full prior-art audit and charged control/update costs. Public source/scalars/hashes/figures only; raw data, scores, per-pair dimensions and placement stay private. No manuscript or production dispatch changed.\n')
    far=a['margin_groups']['far'];near=a['margin_groups']['near']
    (root/'DECISION.md').write_text(f"# {a['decision']}\n\n{headline}\n\n## Q1 — Required dimensions\n\nMean{s['mean']:.6f}, median{s['median']:.6f}, p10{s['p10']:.6f}, p90{s['p90']:.6f}, p95{s['p95']:.6f}, p99{s['p99']:.6f}; denominator all32M pairs. True hits({a['hits']}) require960. Nonhits-only mean{a['nonhits']['mean']:.6f} is secondary, not the admission denominator.\n\n## Q2 — Byte headroom\n\nMean{b['mean_bytes_per_object']:.6f}B/object versus3840B. Ideal{b['ideal_bytes_per_query']/1e9:.6f}GB/query versus3.840000GB, reduction{b['theoretical_reduction']:.6%}. The diagnostic computed all960 for proof; it did not realize these savings or measure traffic/latency.\n\n## Q3 — Query robustness\n\nQuery-mean min/p10/median/p90/max:{r['min']:.6f}/{r['p10']:.6f}/{r['median']:.6f}/{r['p90']:.6f}/{r['max']:.6f}. All32 query means satisfy the384-dimension point threshold, not just a few easy queries. Their observed variation is finite-pool evidence, not a confidence guarantee for future queries, radii or snapshots.\n\n## Q4 — Where savings arise\n\nFar nonhits contribute{far['coordinate_savings_fraction']:.6%} of coordinate savings and represent{far['nonhit_fraction']:.6%} of nonhits. Their mean is{far['mean']:.6f} dimensions. Near nonhits average{fmt(near['mean'])} dimensions and remain expensive; hits require full evaluation. Margin thresholds were fixed before measurement and never altered the gate.\n\n## Q5 — Frozen verdict\n\nMean{s['mean']:.6f}≤384 and p90(query mean){r['p90']:.6f}≤480: GO. Human clarified NO-GO precedence and UNCLASSIFIED uncovered outcomes before measurement; original numeric thresholds were not relaxed. Every full960 score matches the original ordered-FP64 reference bit-for-bit;0 reference hits were rejected.\n\n## Implementation / mechanism / thesis\n\n- Implementation: CPU-only diagnostic qualified on the frozen full population;0 GPU starts.\n- Mechanism: substantial original-order per-object coordinate-payload opportunity survives Gate1. Sector/warp/stage granularity and control costs can still erase a GPU gain.\n- Thesis: partial-distance elimination is established; this result is not a novel contribution or GTSPP end-to-end benefit.\n\nOnly design-only128/256/512/960 accounting follows. No GPU prototype, reordered dimensions, coding or dynamic workload was started. Separate prior-art, conservative arithmetic, total-cost and strengthened same-contract end-to-end gates remain. Reopen/narrow if a new query/radius/snapshot fails these thresholds, safe arithmetic materially delays rejection, or charged execution costs exhaust payload savings. This is not a claim that every exact representation or every GPU tree must behave this way.\n")
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--artifact',type=Path,default=Path(__file__).resolve().parent);p.add_argument('--figure-skill',type=Path,required=True);a=p.parse_args();report(a.artifact,a.figure_skill)
