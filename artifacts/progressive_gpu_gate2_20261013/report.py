"""Regenerate the four requested figures and scalar tables; no GPU work."""
import argparse,csv,sys
from pathlib import Path
import numpy as np
from pre_cost import read,save
def table(path,headers,rows,caption):
    path.write_text(caption+'\n\n| '+' | '.join(headers)+' |\n| '+' | '.join(['---']*len(headers))+' |\n'+''.join('| '+' | '.join(map(str,row))+' |\n' for row in rows))
def report(a):
    root=a.artifact;ev=root/'evidence';t=read(ev/'PRIMARY_TIMING.json');traffic=read(ev/'DRAM_ACCOUNTING.json');b=read(ev/'STAGE_BREAKDOWN.json');c=read(ev/'STAGE_COUNTS.json');cost=read(root/'cost/PRE_GPU_COST.json')
    table(root/'timing/PRIMARY_TIMING.md',['Mode','Median ACK ms/query','Process p10 / p90 ms','Relative to B1'],[[m,f"{t['modes'][m]['median']:.6f}",f"{t['modes'][m]['p10']:.6f} / {t['modes'][m]['p90']:.6f}",f"{t['modes'][m]['median']/t['modes']['B1']['median']:.6f}"] for m in ('B0','B1','P1')],
          '# Complete Host-ready timing\n\nSix fresh processes per mode, eight warmups plus the original32 measured queries. p10/p90 across process means are not confidence intervals. B0 is structural READ_ONLY, not a search algorithm. All576 measured ACK samples retained in JSON.\n\n'+f"P1/B1 marginal median ratio **{t['latency_ratio']:.6f}**; matched-round geometric ratio **{t['paired_geometric_ratio']:.6f}**; 95% process bootstrap CI **[{t['paired_95_CI'][0]:.6f}, {t['paired_95_CI'][1]:.6f}]**; wins **{t['wins']}/6**.")
    table(root/'traffic/DRAM_ACCOUNTING.md',['Mode','All-kernel total GB/query','Read GB','Write GB','L2 GB','NCU kernel ms','Launches /32 queries'],[[m,*[f"{v['means'][k]/1e9:.6f}" for k in ('DRAM_bytes','DRAM_read_bytes','DRAM_write_bytes','L2_bytes')],f"{v['means']['kernel_ms']:.6f}",v['launches']] for m,v in traffic['modes'].items()],
          '# Complete DRAM accounting\n\nIndependent diagnostics cover all32 measured queries and every scan, flag, CUB-selection and final materialization kernel. Decimal GB. NCU duration is never primary Host ACK.\n\n'+f"P1/B1 traffic ratio **{traffic['dram_fraction']:.6f}**; DRAM reduction **{traffic['dram_reduction']:.4%}**; latency reduction **{traffic['latency_reduction']:.4%}**. The conversion ratio is descriptive, not a causal attribution.")
    counts=np.array(c['measured32_counts'],dtype=float)
    stage_rows=[];event_rows=[]
    for s,row in enumerate(cost['rows']):
        scan=np.mean([r['stages'][s]['scan_ms'] for r in b['queries']]);compact=np.mean([r['stages'][s]['compact_ms'] for r in b['queries']]);host=np.mean([r['stages'][s]['host_stage_ms'] for r in b['queries']])
        stage_rows.append([s+1,f"{row['input_pairs']/32:.5f}",f"{counts[:,s].mean():.5f}",f"{row['coordinate_bytes']/32/1e6:.6f}",f"{(row['owner_bytes']+row['state_bytes'])/32/1e6:.6f}",f"{scan:.6f}",f"{compact:.6f}"])
        event_rows.append([f'S{s+1}',scan,compact,max(0,host-scan-compact)])
    table(root/'stages/STAGE_COUNTS.md',['Stage','Mean input','Mean output','Coordinate MB/query','Modeled owner/state MB','Scan event ms','CUB event ms'],stage_rows,
          '# Exact checkpoint ownership and stage accounting\n\nEvery complete checkpoint ID for all40 target qualification invocations matched Gate1/original ordered-FP64. The table excludes eight warmups. Coordinate/owner/state columns are logical cost models, not NCU DRAM; scan/CUB times come from the separate event-enabled diagnostic. Tuple padding, flags, refinement and CUB scratch are additionally charged/reported, not folded into owner/state.')
    table(root/'breakdown/STAGE_BREAKDOWN.md',['Component','Diagnostic mean ms/query','Fraction of diagnostic ACK'],[[k,f"{b['means'][k]:.6f}",f"{b['means'][k]/b['means']['ack_ms']:.4%}"] for k in ('scan_ms','compact_ms','fields_ms','unattributed_host_minus_events_ms')],
          '# Separate event-enabled breakdown\n\nThe denominator is this diagnostic\u2019s complete ACK, not the primary six-process estimator. Host-minus-events is retained as an unattributed residual: it is NOT automatically evidence of CPU scheduling, a launch bottleneck, or recoverable control cost. Compaction is directly event-isolated.\n\n'+f"CUB share **{b['isolated_compaction_share']:.4%}**. The preregistered 25% threshold motivates only a future persistent design; this campaign implements none.")
    sys.path.insert(0,str(a.figure_skill/'scripts'));from paper_style import setup_style,grouped_bars,trend_plot,save_fig
    import matplotlib.pyplot as plt
    setup_style('acm_double',width_inches=3.5,height_ratio=.77,font_family='serif',use_scienceplots=False)
    def export(fig,name,headers,rows):
        fig.tight_layout(pad=.55);save_fig(fig,name,formats=('pdf','svg','png'),output_dir=root/'figures',verify_fonts=False);plt.close(fig)
        with (root/'figures'/(name+'.csv')).open('w') as f:
            w=csv.writer(f,lineterminator='\n');w.writerow(headers);w.writerows(rows)
    modes=['B0','B1','P1'];labels=['Read-only\n(control)','Exact scan\nB1','Staged\nP1'];values=[t['modes'][m]['median'] for m in modes]
    errors=np.array([[[values[i]-t['modes'][m]['p10'] for i,m in enumerate(modes)]],[[t['modes'][m]['p90']-values[i] for i,m in enumerate(modes)]]])
    fig,ax,_=grouped_bars([values],labels,[''],ylabel='Host-ready latency (ms/query)',errors=errors,colors=['#888888'],hatches=[''],legend=False)
    for i,bar in enumerate(ax.patches):bar.set_facecolor(['white','#888888','#0072B2'][i]);bar.set_hatch(['...','///',''][i]);bar.set_edgecolor('black')
    for i,m in enumerate(modes):
        ax.scatter(i+np.linspace(-.08,.08,6),t['modes'][m]['process_means'],s=11,facecolors='white',edgecolors='black',linewidths=.6,zorder=5)
        ax.text(i,values[i]+max(values)*.09,f'{values[i]:.3f}',ha='center',fontsize=8)
    ax.set_ylim(0,max(values)*1.25)
    export(fig,'latency_comparison',['mode','median_ms','p10_ms','p90_ms'],[[m,values[i],t['modes'][m]['p10'],t['modes'][m]['p90']] for i,m in enumerate(modes)])
    modes=['B1','P1'];v=[traffic['modes'][m]['means']['DRAM_bytes']/1e9 for m in modes]
    quantiles=[np.quantile([q['DRAM_bytes']/1e9 for q in traffic['modes'][m]['queries_detail']],[.1,.9]) for m in modes]
    errors=np.array([[[max(0,v[i]-quantiles[i][0]) for i in range(2)]],[[max(0,quantiles[i][1]-v[i]) for i in range(2)]]])
    fig,ax,_=grouped_bars([v],['Exact scan B1','Staged P1'],[''],ylabel='All-kernel DRAM (GB/query)',errors=errors,colors=['#888888'],hatches=[''],legend=False)
    for i,bar in enumerate(ax.patches):bar.set_facecolor(['#888888','#0072B2'][i]);bar.set_edgecolor('black');bar.set_hatch(['///',''][i])
    for i,value in enumerate(v):ax.text(i,max(value,quantiles[i][1])+max(v)*.07,f'{value:.3f}',ha='center',fontsize=8)
    ax.set_ylim(0,max(v)*1.26)
    export(fig,'traffic_comparison',['mode','mean_GB','query_p10_GB','query_p90_GB'],[[m,v[i],*quantiles[i]] for i,m in enumerate(modes)])
    active=np.concatenate([np.full((32,1),1e6),counts],axis=1);x=np.array([0,128,256,512,960]);center=active.mean(axis=0)
    fig,ax=plt.subplots()
    for i in range(1,5):ax.scatter(np.full(32,x[i]),active[:,i],s=6,color='#777777',alpha=.45,zorder=2)
    ax.plot(x,center,'o-',color='#0072B2',linewidth=1.2,markersize=4,zorder=3)
    bounds=np.quantile(active,[.1,.9],axis=0);ax.fill_between(x,bounds[0],bounds[1],color='#0072B2',alpha=.16);ax.set_yscale('log');ax.set_xticks(x);ax.set_xlabel('Checkpoint (original dimensions)');ax.set_ylabel('Active objects/query');ax.set_ylim(max(.5,float(active.min())*.55),1.8e6)
    export(fig,'stage_survivors',['checkpoint','mean','query_p10','query_p90'],[[int(x[i]),center[i],bounds[0,i],bounds[1,i]] for i in range(5)])
    output=b['means']['host_output_ms'];field=b['means']['fields_ms'];event_rows.append(['Output',field,0,max(0,output-field)])
    hosttotal=sum(np.mean([r['stages'][s]['host_stage_ms'] for r in b['queries']]) for s in range(4))
    event_rows.append(['Other',0,0,max(0,b['means']['ack_ms']-hosttotal-output)])
    fig,ax=plt.subplots();x=np.arange(6);bottom=np.zeros(6)
    for j,(label,color,hatch) in enumerate((('Scan / fields','#0072B2',''),('CUB select','#BBBBBB','///'),('Host-phase residue','white','...'))):
        v=np.array([r[j+1] for r in event_rows]);ax.bar(x,v,bottom=bottom,color=color,edgecolor='black',linewidth=.6,hatch=hatch,label=label);bottom+=v
    ax.set_xticks(x,[r[0] for r in event_rows]);ax.set_ylabel('Diagnostic time (ms/query)');ax.set_ylim(0,max(bottom)*1.55);ax.legend(loc='upper right',fontsize=7,frameon=False)
    export(fig,'stage_time_breakdown',['phase','scan_or_fields_ms','CUB_ms','host_phase_residue_ms'],event_rows)
    for path in (root/'figures').glob('*.svg'):path.write_text('\n'.join(line.rstrip() for line in path.read_text().splitlines())+'\n')
    save(root/'figures/CAPTIONS.json',dict(latency_comparison='Six-process median complete Host ACK with process p10/p90 whiskers and individual process means; READ_ONLY is not search.',traffic_comparison='Mean all-kernel DRAM across32 queries in independent NCU diagnostics; whiskers are query p10/p90, not confidence intervals.',stage_survivors='Mean exact active population after each frozen checkpoint; shading is query p10/p90 and gray dots are all32 individual queries. The mean can exceed p90 because two queries have large outputs; this is not sampling confidence.',stage_time_breakdown='Separate event diagnostic phase walls split into measured scan/fields, measured CUB and host-phase residue; residue is not proven recoverable control.'))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--artifact',type=Path,default=Path(__file__).resolve().parent);p.add_argument('--figure-skill',type=Path,required=True);report(p.parse_args())
