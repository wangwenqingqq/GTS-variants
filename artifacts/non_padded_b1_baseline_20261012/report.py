"""Regenerate tables and the three planned figures from public scalar evidence."""
import argparse,csv,json,sys
from pathlib import Path
import numpy as np

def read(p):return json.loads(p.read_text())
def table(p,headers,rows,caption):
    p.write_text(caption+'\n\n| '+' | '.join(headers)+' |\n| '+' | '.join(['---']*len(headers))+' |\n'+''.join('| '+' | '.join(map(str,r))+' |\n' for r in rows))
def report(a):
    root=a.artifact;t=read(root/'timing/BASELINE_TIMING.json');names=['Native','Non-padded','Read-only'];keys=['N0','N1','R0']
    profiles=[read(root/'profiler'/f'{p}_METRICS.json') for p in ('NATIVE','NON_PADDED','READ_ONLY')]
    m=[t['modes'][k] for k in keys]
    table(root/'timing/BASELINE_TIMING.md',['Mode','ACK ms/query','p10 / p90 ms','32-query pass ms','Relative latency vs native'],
        [[names[i],f"{v['median_process_mean_ms']:.6f}",f"{v['p10_ms']:.6f} / {v['p90_ms']:.6f}",f"{v['median_pass_ms']:.6f}",f"{v['median_process_mean_ms']/m[0]['median_process_mean_ms']:.6f}"] for i,v in enumerate(m)],
        '# Same-campaign B1 baseline\n\nMedian of six fresh process mean Host ACKs; p10/p90 across processes, not CI.32-query pass is continuous host wall. READ_ONLY is a checksum control, not complete search. All32 per-query observations/process and matched-round ratios/CI are retained in JSON.')
    table(root/'profiler/KERNEL_RESOURCES.md',['Mode','Kernel ms','DRAM GB/s','DRAM read / write GB','SM %','Active-warps %','Registers','Work inflation'],
        [[names[i],f"{v['kernel_ms']:.6f}",f"{v['DRAM_GBs']:.3f}",f"{v['metrics']['dram__bytes_op_read.sum']['value']/1e9:.6f} / {v['metrics']['dram__bytes_op_write.sum']['value']/1e9:.6f}",f"{v['metrics']['sm__throughput.avg.pct_of_peak_sustained_elapsed']['value']:.2f}",f"{v['metrics']['sm__warps_active.avg.pct_of_peak_sustained_active']['value']:.2f}",f"{v['metrics']['launch__registers_per_thread']['value']:g}",'N/A' if v['work_inflation'] is None else f"{v['work_inflation']:.6f}×"] for i,v in enumerate(profiles)],
        '# Independent main-kernel diagnostics\n\nOne first-measured-query NCU capture/mode; no sampling CI. Decimal total DRAM GB/s uses the same capture duration and real bytes. Occupancy is NCU active-warps percentage. READ_ONLY arithmetic is a checksum, not search work; inflation is N/A. Profiler duration is not Host ACK.')
    table(root/'timing/GAP_ACCOUNTING.md',['Quantity','Value'],[
        ['Native − read-only',f"{t['native_minus_readonly_ms']:.6f} ms"],
        ['Non-padded − read-only',f"{t['nonpadded_minus_readonly_ms']:.6f} ms"],
        ['Latency recovery',f"{t['latency_recovery']:.4%}"],
        ['Recovery95% CI',f"[{t['latency_recovery_CI95'][0]:.4%}, {t['latency_recovery_CI95'][1]:.4%}]"],
        ['Non-padded / read-only',f"{t['nonpadded_over_readonly']:.6f}"],
        ['Residual / non-padded',f"{t['residual_fraction']:.4%}"],
        ['Bandwidth recovery',f"{t['bandwidth_recovery']:.4%} (single captures)"],
        ['Decision',t['decision']]],'# Gap accounting\n\nPoint gates use medians; recovery CI bootstraps matched-round triples. READ_ONLY is a reachable structural reference, not a universal mathematical lower bound.')
    d=read(root/'timing/DYNAMIC_INTEGRATION.json')
    rows=[]
    for key in ('old','strengthened'):
        v=d['modes'][key];groups={f:sum(float(o['ack_ms']) for o in v['ops'] if int(o['flag'])==f) for f in range(4)}
        rows.append([key,f"{v['meta']['trace_ms']:.6f}",*[f'{groups[f]:.6f}' for f in (2,3,0,1)],f"{v['meta']['release_ms']:.6f}"])
    table(root/'timing/DYNAMIC_INTEGRATION.md',['Mode','Trace ms','128 range ACK sum ms','128 kNN ACK sum ms','40 insert ACK sum ms','40 delete ACK sum ms','Release ms'],rows,
        '# Conditional short integration pair\n\n336 events:40 insert,40 delete,128 range,128 kNN; initial1M/D960. One old→strengthened pair only. Inherited trace_ms includes final-state copy/release and host bookkeeping; context/setup/disk/serialization excluded. Operation sums are not the full trace. No CI or sustained benefit claim.\n\n'
        +f"Observed trace reduction **{d['inherited_trace_reduction']:.4%}**, speedup **{d['inherited_trace_speedup']:.6f}×**. Both measured256 and warmup8 complete queries passed with final-state checks. Original reference-ownership false failure remains; old output was rechecked offline, not rerun. Only the strengthened process was resumed after human approval.")
    sys.path.insert(0,str(a.figure_skill/'scripts'));from paper_style import setup_style,grouped_bars,save_fig
    import matplotlib.pyplot as plt
    setup_style('acm_double',width_inches=3.5,height_ratio=.78,font_family='serif',use_scienceplots=False)
    colors=['#888888','#0072B2','#FFFFFF'];hatches=['///','','...']
    for name,values,ylabel in (
        ('latency_comparison',[v['median_process_mean_ms'] for v in m],'Host ACK (ms/query)'),
        ('bandwidth_recovery',[v['DRAM_GBs'] for v in profiles],'Measured DRAM bandwidth (GB/s)')):
        errors=None
        if name=='latency_comparison':errors=np.array([[[values[i]-m[i]['p10_ms'] for i in range(3)]],[[m[i]['p90_ms']-values[i] for i in range(3)]]])
        fig,ax,_=grouped_bars([values],names,[''],ylabel=ylabel,errors=errors,colors=['#888888'],hatches=[''],legend=False)
        for i,bar in enumerate(ax.patches):bar.set_facecolor(colors[i]);bar.set_edgecolor('black');bar.set_hatch(hatches[i])
        for i,value in enumerate(values):ax.text(i,value+(max(values)*.075),f'{value:.3f}' if name=='latency_comparison' else f'{value:.1f}',ha='center',va='bottom',fontsize=8)
        if name=='latency_comparison':
            for i,v in enumerate(m):ax.scatter(i+np.linspace(-.10,.10,6),v['process_means_ms'],s=9,facecolors='white',edgecolors='black',linewidths=.5,zorder=5)
        ax.set_ylim(0,max(values)*1.25);fig.tight_layout(pad=.45)
        save_fig(fig,name,formats=('pdf','svg','png'),output_dir=root/'figures',verify_fonts=False);plt.close(fig)
        with (root/'figures'/(name+'.csv')).open('w') as f:
            w=csv.writer(f,lineterminator='\n');w.writerow(['mode','value','p10','p90','scope'])
            for i,value in enumerate(values):w.writerow([names[i],value,m[i]['p10_ms'] if errors is not None else '',m[i]['p90_ms'] if errors is not None else '', 'six-process median+p10/p90' if errors is not None else 'one diagnostic capture'])
    fig,ax=plt.subplots();values=[v['work_inflation'] for v in profiles[:2]]
    for i,value in enumerate(values):
        ax.scatter(i,value,marker=['s','o'][i],s=40,color=colors[i],edgecolors='black',linewidths=.7,zorder=3)
        ax.annotate(f'{value:.3f}×',(i,value),xytext=(0,8),textcoords='offset points',ha='center',fontsize=8)
    ax.axhline(1,color='black',linestyle='--',linewidth=.6);ax.set_yscale('log',base=2);ax.set_ylim(.75,128);ax.set_xlim(-.5,1.5)
    ax.set_xticks([0,1],names[:2]);ax.set_yticks([1,2,4,8,16,32,64],list(map(str,[1,2,4,8,16,32,64])))
    ax.set_ylabel('Executed/useful FP32 proxy (×)');fig.tight_layout(pad=.45)
    save_fig(fig,'work_inflation',formats=('pdf','svg','png'),output_dir=root/'figures',verify_fonts=False);plt.close(fig)
    with (root/'figures/work_inflation.csv').open('w') as f:
        w=csv.writer(f,lineterminator='\n');w.writerow(['mode','executed_useful_proxy','scope']);w.writerows([[names[i],v,'one diagnostic capture'] for i,v in enumerate(values)])
    for p in (root/'figures').glob('*.svg'):p.write_text('\n'.join(s.rstrip() for s in p.read_text().splitlines())+'\n')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--artifact',type=Path,default=Path(__file__).resolve().parent);p.add_argument('--figure-skill',type=Path,required=True)
    report(p.parse_args())
