"""Four scoped study figures using standard Matplotlib;no external style runtime."""
if not __debug__:
    raise SystemExit('Mandatory checks require ordinary Python without optimization.')
import argparse
import csv
import json
from pathlib import Path
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    p=argparse.ArgumentParser();p.add_argument('--data',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    plt.rcParams.update({'font.family':'serif','font.size':8,'axes.labelsize':8,'xtick.labelsize':7,'ytick.labelsize':7,'legend.fontsize':7,
        'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42,'ps.fonttype':42,'svg.hashsalt':'update-critical-path-20261015','svg.fonttype':'none'})
    d=json.loads((a.data/'results/DERIVED.json').read_text());cells=d['micro'];batches=(1,32,512);ops=('I','D','R')
    colors=['#777777','#0072B2','#D55E00'];markers=['o','s','^'];labels=['Insert','Delete','Replacement (2B updates)']
    def export(fig,name,rows):
        assert all(text.get_fontsize()>=7 for text in fig.findobj(matplotlib.text.Text) if text.get_text())
        paths=[a.out/(name+'.'+ext) for ext in ('pdf','svg','png')]
        for path in paths:fig.savefig(path,dpi=400,bbox_inches='tight',pad_inches=.02,metadata={'Creator':'Matplotlib'})
        for path in paths:
            if path.suffix=='.svg':path.write_text('\n'.join(line.rstrip() for line in path.read_text().splitlines())+'\n')
        with (a.out/(name+'.csv')).open('x',newline='') as f:csv.writer(f,lineterminator='\n').writerows(rows)
        plt.close(fig)

    # A: exclusive profiled Host partition,with DMA as a non-additive overlay.
    parts=('copy_API_ns','sync_API_ns','bookkeeping_Host_ns','other_Host_API_wrapper_ns')
    partlabels=('Copy API (may block)','Stream sync API','Bookkeeping','Other Host / wrapper')
    partcolors=('#0072B2','#D55E00','#777777','#DDDDDD');hatches=('','///','xx','..')
    fig,axes=plt.subplots(1,3,figsize=(7.,3.1));rows=[['batch','operator','part','profiled_us_per_point','profiled_DMA_us_per_point']];handles=[]
    for b,ax in zip(batches,axes):
        bottom=np.zeros(3)
        for part,label,color,hatch in zip(parts,partlabels,partcolors,hatches):
            values=[]
            for op in ops:
                r=cells[f'{op}_{b}'];den=r['profile_ACKs']*r['points_per_ACK']*1000.;values.append(r['profile_host_parts_ns'][part]/den)
                rows.append([b,op,part,values[-1],r['profile_device_totals']['DMA_union_ns']/den])
            bars=ax.bar(np.arange(3),values,bottom=bottom,color=color,hatch=hatch,edgecolor='black',linewidth=.35,width=.68,label=label);bottom+=values
            if b==1:handles.append(bars[0])
        dma=[cells[f'{op}_{b}']['profile_device_totals']['DMA_union_ns']/(cells[f'{op}_{b}']['profile_ACKs']*cells[f'{op}_{b}']['points_per_ACK']*1000.) for op in ops]
        overlay=ax.scatter(range(3),dma,marker='D',s=19,facecolors='white',edgecolors='black',linewidths=.8,zorder=4)
        if b==1:handles.append(overlay)
        ax.set_xticks(range(3),['I','D','R']);ax.set_title(f'Batch B = {b}',fontsize=8);ax.set_ylabel('Profiled ACK (µs / point)',fontsize=8);ax.set_ylim(0,max(bottom)*1.1);ax.tick_params(labelsize=7)
    fig.legend(handles,[*partlabels,'DMA overlay (not added)'],ncol=3,loc='upper center',bbox_to_anchor=(.5,1.),frameon=False,fontsize=7)
    fig.subplots_adjust(left=.08,right=.99,bottom=.17,top=.75,wspace=.5);export(fig,'A_ACK_attribution',rows)

    # B: no-profiler public denominator;measured process spread,not invented CI.
    fig,ax=plt.subplots(figsize=(3.5,2.9));values=[];bands=[];rows=[['operator','batch','median_us_per_point','p10','p90','process_values']]
    for op in ops:
        stats=[cells[f'{op}_{b}']['native_metrics']['amortized_us_per_point'] for b in batches]
        values.append([s['median'] for s in stats]);bands.append(([s['p10'] for s in stats],[s['p90'] for s in stats]))
        for b,s in zip(batches,stats):rows.append([op,b,s['median'],s['p10'],s['p90'],json.dumps(s['process_values'])])
    for value,band,label,color,marker,line in zip(values,bands,labels,colors,markers,(':','-','--')):
        ax.fill_between(batches,*band,color=color,alpha=.16,linewidth=0)
        ax.plot(batches,value,label=label,color=color,marker=marker,linestyle=line,linewidth=1.5,markersize=4)
    ax.set_xlabel('Points / native operator batch (B)');ax.set_ylabel('Whole ACK (µs / point update)')
    ax.grid(axis='y',color='#DDDDDD',linewidth=.5);ax.legend(loc='upper right',fontsize=7)
    for op,color in zip(ops,colors):
        for b in batches:
            raw=cells[f'{op}_{b}']['native_metrics']['amortized_us_per_point']['process_values']
            ax.scatter(b*2.**((np.arange(6)-2.5)*.035),raw,s=7,color=color,alpha=.35,zorder=2)
    ax.set_xscale('log',base=2);ax.set_xticks(batches,[str(b) for b in batches]);ax.set_ylim(0,9.4);ax.set_title('6 processes: median and p10–p90; no profiler',fontsize=7)
    fig.tight_layout(pad=.5);export(fig,'B_batch_amortization',rows)

    # C: matched-profile ACK/device pairs;zero kernels is not zero device work.
    fig,axes=plt.subplots(1,2,figsize=(7.,2.9));rows=[['operator','batch','profiled_ACK_us','kernel_us_per_ACK','DMA_us_per_ACK']]
    for op,color,marker,label in zip(ops,colors,markers,labels):
        x=[];kernel=[];dma=[]
        for b in batches:
            r=cells[f'{op}_{b}'];x.append(r['profile_mean_ACK_ms']*1000);kernel.append(r['profile_device_totals']['kernel_union_ns']/r['profile_ACKs']/1000);dma.append(r['profile_device_totals']['DMA_union_ns']/r['profile_ACKs']/1000);rows.append([op,b,x[-1],kernel[-1],dma[-1]])
        for ax,y in zip(axes,(kernel,dma)):ax.scatter(x,y,color=color,marker=marker,s=28,label=label,edgecolors='black',linewidths=.35)
    for ax in axes:ax.set_xscale('log');ax.set_xlabel('Profiled whole ACK (µs / batch)',fontsize=8);ax.tick_params(labelsize=7)
    axes[0].set_ylabel('Update-kernel time (µs / batch)',fontsize=8);axes[0].set_ylim(-.015,.22);axes[0].set_yticks([0]);axes[0].text(.06,.76,'0 recorded application update kernels',transform=axes[0].transAxes,fontsize=7)
    axes[1].set_yscale('log');axes[1].set_ylabel('DMA time (µs / batch; overlay)',fontsize=8);axes[1].set_ylim(.2,1500)
    xx=np.array([8.,4000.]);axes[1].plot(xx,xx,color='#999999',linestyle=':',linewidth=.6,zorder=0);axes[1].text(.62,.80,'DMA = ACK',transform=axes[1].transAxes,fontsize=7,color='#555555')
    fig.legend(*axes[0].get_legend_handles_labels(),loc='upper center',bbox_to_anchor=(.5,1.),ncol=3,frameon=False,fontsize=7)
    fig.subplots_adjust(left=.075,right=.99,bottom=.21,top=.80,wspace=.4);export(fig,'C_ACK_vs_device_activity',rows)

    # D: equal payload,very different request granularity;native latency stays native.
    fig,axes=plt.subplots(2,3,figsize=(7.,4.2));rows=[['batch','operator','requested_payload_MB_per_batch','copy_API_calls_per_batch','sync_API_calls_per_batch','kernel_launches_per_batch','kernel_us_per_batch','profile_DMA_us_per_batch','native_mean_ACK_us']]
    matrix={}
    for op in ('I','D'):
        matrix[op]=[]
        for b in batches:
            r=cells[f'{op}_{b}'];t=r['profile_device_totals'];n=r['profile_ACKs'];v=[(t['H2D_activity_bytes']+t['D2D_activity_bytes'])/n/1e6,t['copy_API_calls']/n,t['sync_API_calls']/n,t['kernels']/n,t['DMA_union_ns']/n/1000,r['native_metrics']['mean_ACK_ms']['median']*1000]
            matrix[op].append(v);rows.append([b,op,*v[:4],t['kernel_union_ns']/n/1000,v[4],v[5]])
    titles=('Payload (MB / batch)','Copy API calls / batch','Explicit syncs / batch','Application kernels / batch','Profiled DMA (µs / batch)','Native whole ACK (µs / batch)')
    for index,ax in enumerate(axes.flat):
        for oi,op in enumerate(('I','D')):
            vals=[v[index] for v in matrix[op]];positions=np.arange(3)+(oi-.5)*.34
            ax.bar(positions,vals,width=.32,color=colors[oi],edgecolor='black',hatch=('..','//')[oi],linewidth=.35,label=('Insert','Delete')[oi])
            if index==5:
                s=[cells[f'{op}_{b}']['native_metrics']['mean_ACK_ms'] for b in batches]
                ax.errorbar(positions,vals,yerr=[[v-r['p10']*1000 for v,r in zip(vals,s)],[r['p90']*1000-v for v,r in zip(vals,s)]],fmt='none',ecolor='black',capsize=2,linewidth=.6)
        ax.set_xticks(range(3),['1','32','512']);ax.set_xlabel('Batch B',fontsize=7);ax.set_title(titles[index],fontsize=7);ax.tick_params(labelsize=7);ax.set_ylim(bottom=0)
        if index==3:ax.set_ylim(0,1);ax.set_yticks([0]);ax.text(.5,.45,'0 launches; 0 µs',ha='center',transform=ax.transAxes,fontsize=7)
    fig.legend(*axes[0,0].get_legend_handles_labels(),loc='upper center',bbox_to_anchor=(.5,1.),ncol=2,frameon=False,fontsize=8)
    fig.subplots_adjust(left=.075,right=.99,bottom=.12,top=.86,wspace=.4,hspace=.65);export(fig,'D_delete_vs_insert',rows)
    print('FOUR_FIGURES:PDF/SVG/400DPI PNG andnumericCSV;native andprofile scopes separate')


if __name__=='__main__':main()
