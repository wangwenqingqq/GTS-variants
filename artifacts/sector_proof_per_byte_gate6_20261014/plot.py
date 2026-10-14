#!/usr/bin/env python3
"""Four fixed-pool count/model diagnostics; no invented timing uncertainty."""
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parent


def read(name):return json.loads((ROOT/name).read_text())


def figures():
    # Match the preceding diagnostic's font/size and use blue only for this probe.
    plt.rcParams.update({'font.family':'DejaVu Serif','font.size':9,'axes.labelsize':9,
                         'xtick.labelsize':8,'ytick.labelsize':8,'legend.fontsize':7,
                         'axes.spines.top':False,'axes.spines.right':False,
                         'pdf.fonttype':42,'svg.fonttype':'none','savefig.dpi':300})
    b0=read('baseline/B0_FIRST16_SECTORS.json');c1=read('baseline/C1_SCATTERED_REFERENCE.json')
    o2=read('oracle/O2_PAIR_TOP16_SECTORS.json');s1=read('routing/S1_SECTOR_MOMENT.json')
    require_run=s1.get('status')=='MEASURED_CPU_CERTIFICATE_DIAGNOSTIC'
    if not require_run:raise RuntimeError('S1 not run: do not fabricate the gated figures')
    cost=read('cost/FULL_FALLBACK_BYTES.json');rows=read('analysis/QUERY_DISTRIBUTION.json')['queries']
    colors=['#777777','#bcbcbc','#009E73','#0072B2'];hatches=['//','','xx','..']
    target=ROOT/'figures';target.mkdir(exist_ok=True);qa=[]
    def save(fig,name,scope):
        fig.tight_layout(pad=.6);fig.canvas.draw();renderer=fig.canvas.get_renderer();box=fig.bbox
        for t in fig.findobj(matplotlib.text.Text):
            if not t.get_visible() or not t.get_text():continue
            b=t.get_window_extent(renderer)
            assert b.x0>=box.x0-1 and b.y0>=box.y0-1 and b.x1<=box.x1+1 and b.y1<=box.y1+1, ('text clipping',name,t.get_text())
        for ext in ('svg','png'):
            p=target/f'{name}.{ext}';fig.savefig(p,bbox_inches='tight')
            if ext=='svg':p.write_text('\n'.join(line.rstrip() for line in p.read_text().splitlines())+'\n')
        qa.append({'name':name,'scope':scope,'canvas_inches':list(fig.get_size_inches()),'PNG_dpi':300,'SVG_vector':True,
                   'text_clipping_check':'PASS','smallest_visible_font_pt':min(t.get_fontsize() for t in fig.findobj(matplotlib.text.Text) if t.get_visible() and t.get_text()),
                   'uncertainty':'none: complete fixed pool, not timing repeats'})
        plt.close(fig)
    vals=[b0['mean_survivors'],c1['mean_survivors'],o2['mean_survivors'],s1['mean_survivors']]
    fig,ax=plt.subplots(figsize=(3.4,2.45));bars=ax.barh(range(4),vals,color=colors,edgecolor='black',linewidth=.5,hatch=hatches)
    ax.set_yticks(range(4),['B0 first16','C1 scattered/ref','O2 pair oracle','S1 sectors']);ax.invert_yaxis()
    ax.set(xlabel='Mean survivors / query',xlim=(0,760000));ax.set_xticks([0,200000,400000,600000]);ax.ticklabel_format(axis='x',style='sci',scilimits=(5,5))
    for i,(bar,v) in enumerate(zip(bars,vals)):
        inside=v>400000;ax.text(v-14000 if inside else v+14000,bar.get_y()+bar.get_height()/2,
            f'{v:,.5f}'.rstrip('0').rstrip('.'),va='center',ha='right' if inside else 'left',fontsize=7,color='white' if i==0 else 'black')
    ax.set_title('32 x 1M; O2 unpriced, C1 historical',fontsize=7,pad=7)
    save(fig,'survivors_sector512','nominal16 x 32B; C1 scattered historical/ineligible; O2 full reads unpriced')
    vals=[cost['strong_baseline_mean_bytes']/1e9,cost['mean_bytes']/1e9]
    fig,ax=plt.subplots(figsize=(3.4,2.45));bars=ax.barh(range(2),vals,color=[colors[0],colors[3]],edgecolor='black',linewidth=.5,hatch=['//','..'])
    ax.set_yticks(range(2),['Progressive/ref','S1 conditional']);ax.invert_yaxis()
    ax.set(xlabel='Modeled coordinate source GB / query',xlim=(0,1.2));ax.set_xticks([0,.3,.6,.9,1.2])
    for bar,v in zip(bars,vals):ax.text(v-.025,bar.get_y()+bar.get_height()/2,f'{v:.9f}',va='center',ha='right',fontsize=7,color='white')
    ax.set_title('GO ceiling 0.811863 GB; not DRAM',fontsize=7,pad=7)
    save(fig,'conservative_bytes','conditional selected-value reuse source model; retention/spills unknown; exact GO target in JSON')
    fig,ax=plt.subplots(figsize=(3.4,2.45));x=list(range(1,33))
    ax.scatter(x,[r['O2_over_B0'] for r in rows],marker='^',s=17,facecolors='none',edgecolors=colors[2],label='O2 oracle')
    ax.scatter(x,[r['S1_over_B0'] for r in rows],marker='o',s=13,color=colors[3],label='S1 sectors')
    ax.axhline(.5,color='#777777',linestyle='--',linewidth=.7)
    ax.set(xlabel='Frozen query index',ylabel='Survivor ratio to B0 (log scale)',yscale='log',ylim=(8e-7,2),xlim=(.3,32.7))
    ax.set_yticks([1e-6,1e-4,1e-2,1]);ax.set_xticks([1,8,16,24,32])
    ax.legend(loc='lower left',bbox_to_anchor=(0,1.02),ncol=2,frameon=False,handletextpad=.4,borderaxespad=0,columnspacing=1)
    save(fig,'per_query_ratio','all32 matched ratios; dashed0.50 line is p90 threshold, not parity/per-query gate')
    overlap=read('analysis/SECTOR_OVERLAP.json')
    fig,ax=plt.subplots(figsize=(3.4,3.05));im=ax.imshow(overlap['matrix_fraction'],vmin=0,vmax=1,cmap='cividis',interpolation='nearest')
    ticks=[0,7,15,23,31];labels=[1,8,16,24,32];ax.set_xticks(ticks,labels);ax.set_yticks(ticks,labels)
    ax.set(xlabel='Frozen query index',ylabel='Frozen query index');cb=fig.colorbar(im,ax=ax,fraction=.045,pad=.04);cb.set_label('Intersection / 16',fontsize=8);cb.set_ticks([0,.5,1])
    ax.set_title('Sector-set overlap; diagonal = self',fontsize=7,pad=7)
    save(fig,'sector_overlap','actual32 x 32 intersection fractions; all496 off-diagonal pairs kept, diagonal self=1')
    (ROOT/'evidence/FIGURE_QA.json').write_text(json.dumps({'plots':qa,'visual_inspection':'PENDING','grayscale_safe':'redundant bar/marker encodings; sequential overlap intensity','data_source':'frozen scalar files'},indent=2)+'\n')


if __name__=='__main__':figures()
