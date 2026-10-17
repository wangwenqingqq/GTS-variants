"""Scoped,print-safe figures;consume fixed estimates instead of recomputing wins."""
if not __debug__:raise SystemExit('Mandatory checks require ordinary Python.')
import argparse,csv,json,sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
FAMILIES=('W2_ORIGINAL','UNIFORM_LIVE','MIX_RECENT8','RECENT4')
LABELS=('W2','Uniform live','Mix recent8','Recent4')
def main():
    p=argparse.ArgumentParser();p.add_argument('--summary',type=Path,required=True);p.add_argument('--processes',type=Path,required=True);p.add_argument('--cpu',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--style-root',type=Path);a=p.parse_args();a.out.mkdir()
    if a.style_root:
        sys.path.insert(0,str(a.style_root));from paper_style import setup_style
        setup_style('acm_double',width_inches=3.5,use_latex=False,use_scienceplots=False,font_family='serif')
    plt.rcParams.update({'font.family':'serif','font.size':8,'axes.labelsize':8,'axes.titlesize':8,'xtick.labelsize':7,'ytick.labelsize':7,'legend.fontsize':7,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42,'ps.fonttype':42,'svg.fonttype':'none','svg.hashsalt':'dependency-update-20261017'})
    summary=json.loads(a.summary.read_text());processes=json.loads(a.processes.read_text());cpu=json.loads(a.cpu.read_text())['records']
    def export(fig,name,rows):
        fig.canvas.draw();renderer=fig.canvas.get_renderer();bounds=fig.bbox
        for text in fig.findobj(matplotlib.text.Text):
            if not text.get_text() or not text.get_visible():continue
            assert text.get_fontsize()>=7
            box=text.get_window_extent(renderer);assert box.x0>=-1 and box.y0>=-1 and box.x1<=bounds.x1+1 and box.y1<=bounds.y1+1,('clipped text',text.get_text())
        for ext in ('pdf','svg','png'):fig.savefig(a.out/(name+'.'+ext),dpi=400,bbox_inches=None,metadata={'Creator':'Matplotlib'})
        with (a.out/(name+'.csv')).open('x',newline='') as f:csv.writer(f,lineterminator='\n').writerows(rows)
        plt.close(fig)
    fig,ax=plt.subplots(figsize=(3.5,2.7));rows=[['family','seed','N','native_moves','final_assignments','elimination_percent']]
    for x,family in enumerate(FAMILIES):
        cell=[r for r in cpu if r['N']==1000000 and r['family']==family];assert len(cell)==2
        values=[100*r['elimination_ratio'] for r in cell];ax.bar(x,np.mean(values),color='#DDDDDD',edgecolor='black',linewidth=.5,width=.55)
        ax.scatter([x-.065,x+.065],values,color='#0072B2',marker='o',s=14,zorder=3)
        ax.text(x,max(values)+1.3,f'{np.mean(values):.3f}%' if x<2 else f'{np.mean(values):.2f}%',ha='center',fontsize=7)
        rows.extend([family,r['seed'],r['N'],r['native_moves'],r['final_assignments'],100*r['elimination_ratio']] for r in cell)
    ax.set_xticks(range(4),LABELS,rotation=12);ax.set_ylim(0,50);ax.set_ylabel('Eliminated row assignments (%)');ax.set_title('1M vectors; B512; two fixed CPU trace seeds\nW2 seeds are identical,not independent repetitions',fontsize=7);fig.subplots_adjust(left=.17,right=.98,bottom=.21,top=.82);export(fig,'structure',rows)
    comparisons=(('GENERIC_WAVES','GENERIC_DSE','Composition','#333333','o'),('GENERIC_DSE','TAIL_GENERIC','Tail planner','#0072B2','s'),('TAIL_GENERIC','TAIL_CUSTOM','Custom executor','#D55E00','^'))
    fig,axes=plt.subplots(1,2,figsize=(7.2,3.0));rows=[['metric','family','comparison','gain_percent','CI_low','CI_high']]
    for ax,metric,title in zip(axes,('delete_mean_ms','service_ms'),('Complete Delete ACK','Mixed service: events + release')):
        for offset,(base,candidate,label,color,marker) in zip((-.17,0,.17),comparisons):
            vals=[];lo=[];hi=[]
            for family in FAMILIES:
                r=next(c for c in summary['contrasts'] if c['family']==family and not c['micro'] and c['comparator']==base and c['candidate']==candidate)['ratios'][metric]
                y=100*(1-r['candidate_over_comparator']);lower=100*(1-r['bootstrap95'][1]);upper=100*(1-r['bootstrap95'][0]);assert lower<=y<=upper
                vals.append(y);lo.append(y-lower);hi.append(upper-y);rows.append([metric,family,label,y,lower,upper])
            ax.errorbar(np.arange(4)+offset,vals,yerr=[lo,hi],color=color,marker=marker,linestyle='none',capsize=2,linewidth=.7,markersize=4,label=label)
        ax.axhline(0,color='#888888',linewidth=.6);ax.set_xticks(range(4),LABELS,rotation=15);ax.set_ylabel('Time reduction vs matched comparator (%)');ax.set_title(title);ax.tick_params(labelsize=7)
    fig.legend(*axes[0].get_legend_handles_labels(),ncol=3,loc='upper center',bbox_to_anchor=(.5,.99),frameon=False);fig.subplots_adjust(left=.09,right=.985,bottom=.23,top=.79,wspace=.40);export(fig,'causal_attribution',rows)
    fig,axes=plt.subplots(2,2,figsize=(7.2,4.7));rows=[['family','variant','capture_us','construction_us','remainder_us','total_us_SD']]
    for ax,family,label in zip(axes.flat,FAMILIES,LABELS):
        methods=('GENERIC_DSE','TAIL_GENERIC','TAIL_CUSTOM');values=[];errors=[]
        for v in methods:
            rr=[r for r in processes if r['family']==family and not r['micro'] and r['variant']==v];assert len(rr)==6
            capture=np.mean([r['capture_mean_ms'] for r in rr])*1000;compile=np.mean([r['plan_construction_mean_ms'] for r in rr])*1000;total=np.mean([r['delete_mean_ms'] for r in rr])*1000;rest=total-capture-compile;assert rest>=0
            sd=np.std([r['delete_mean_ms'] for r in rr],ddof=1)*1000;values.append((capture,compile,rest));errors.append(sd);rows.append([family,v,capture,compile,rest,sd])
        bottom=np.zeros(3)
        for i,(color,hatch,name) in enumerate((('#CCCCCC','..','Owner/capture'),('#0072B2','//','Compile + certificate'),('#777777','','Remaining ACK'))):
            part=[x[i] for x in values];ax.bar(range(3),part,bottom=bottom,color=color,hatch=hatch,edgecolor='black',linewidth=.4,width=.65,label=name);bottom+=part
        ax.errorbar(range(3),bottom,yerr=errors,fmt='none',color='black',capsize=2,linewidth=.6);ax.set_xticks(range(3),['Generic DSE','Tail + generic','Tail + custom'],rotation=8);ax.set_ylabel('Complete Delete ACK (µs / batch)');ax.set_title(label);ax.set_ylim(bottom=0)
    fig.legend(*axes[0,0].get_legend_handles_labels(),ncol=3,loc='upper center',bbox_to_anchor=(.5,.995),frameon=False);fig.subplots_adjust(left=.10,right=.985,bottom=.11,top=.87,wspace=.32,hspace=.55);export(fig,'planning_cost',rows)
    print('FIGURES_PASS:3 PDF/SVG/400DPI PNG figures and exact numeric CSVs')
if __name__=='__main__':main()
