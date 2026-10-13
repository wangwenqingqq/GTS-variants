#!/usr/bin/env python3
"""Fixed-pool certificate counts, not timing or physical-memory figures."""
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent


def read(name):
    return json.loads((ROOT/name).read_text())


def figures():
    # Keep the preceding diagnostic's font, size and candidate blue.
    plt.rcParams.update({'font.family': 'DejaVu Serif', 'font.size': 9, 'axes.labelsize': 9,
                         'xtick.labelsize': 8, 'ytick.labelsize': 8, 'legend.fontsize': 7,
                         'axes.spines.top': False, 'axes.spines.right': False,
                         'pdf.fonttype': 42, 'svg.fonttype': 'none', 'savefig.dpi': 300})
    b0=read('baseline/B0_FIRST128.json'); b1=read('baseline/B1_BIT4.json')
    o1=read('oracle/O1_PAIR_TOP128.json'); c1=read('routing/C1_MOMENT_SCORE.json')
    rows=read('analysis/QUERY_DISTRIBUTION.json')['queries']
    names=['B1 prior /480B','B0 first128','O1 oracle','C1 moments']
    colors=['#bcbcbc','#777777','#009E73','#0072B2']; hatches=['','//','xx','..']
    target=ROOT/'figures'; target.mkdir(exist_ok=True); qa=[]
    def save(fig,name,scope):
        fig.tight_layout(pad=.4); fig.canvas.draw()
        renderer=fig.canvas.get_renderer(); box=fig.bbox
        for text in fig.findobj(matplotlib.text.Text):
            if not text.get_visible() or not text.get_text(): continue
            bound=text.get_window_extent(renderer)
            assert bound.x0>=box.x0-1 and bound.y0>=box.y0-1 and bound.x1<=box.x1+1 and bound.y1<=box.y1+1, ('text clipping',name,text.get_text())
        for ext in ('svg','png'):
            p=target/f'{name}.{ext}'; fig.savefig(p,bbox_inches='tight')
            if ext=='svg': p.write_text('\n'.join(line.rstrip() for line in p.read_text().splitlines())+'\n')
        qa.append({'name':name,'scope':scope,'canvas_inches':list(fig.get_size_inches()),
                   'PNG_dpi':300,'SVG_vector':True,'text_clipping_check':'PASS',
                   'smallest_visible_font_pt':min(t.get_fontsize() for t in fig.findobj(matplotlib.text.Text) if t.get_visible() and t.get_text()),
                   'uncertainty':'none: complete fixed pool, not repeated timing'})
        plt.close(fig)
    values=[b1['prior_mean_survivors'],b0['mean_survivors'],o1['mean_survivors'],c1['mean_survivors']]
    fig,ax=plt.subplots(figsize=(3.4,2.45))
    bars=ax.barh(range(4),values,color=colors,edgecolor='black',linewidth=.5,hatch=hatches)
    ax.set_yticks(range(4),names); ax.invert_yaxis()
    ax.set(xlabel='Mean survivors / query',xlim=(0,1050000)); ax.ticklabel_format(axis='x',style='sci',scilimits=(6,6))
    ax.set_xticks([0,250000,500000,750000,1000000])
    for i,(rect,v) in enumerate(zip(bars,values)):
        inside=v>500000
        ax.text(v-18000 if inside else v+18000,rect.get_y()+rect.get_height()/2,
                f'{v:,.5f}'.rstrip('0').rstrip('.'),ha='right' if inside else 'left',va='center',
                fontsize=7,color='white' if i==1 else 'black')
    ax.set_title('32 queries x 1M; nominal payload',fontsize=7,pad=7)
    save(fig,'survivors_512B','B0/C1 selected128 FP32 values; O1 unpriced; B1 historical480B')
    fig,ax=plt.subplots(figsize=(3.4,2.45))
    x=list(range(1,33))
    ax.scatter(x,[r['O1_over_B0'] for r in rows],marker='^',s=17,facecolors='none',edgecolors=colors[2],label='O1 oracle')
    ax.scatter(x,[r['C1_over_B0'] for r in rows],marker='o',s=13,color=colors[3],label='C1 moments')
    ax.axhline(.8,color='#777777',linestyle='--',linewidth=.7)
    ax.set(xlabel='Frozen query index',ylabel='Survivor ratio to B0 (log scale)',yscale='log',ylim=(8e-7,2),xlim=(.3,32.7))
    ax.set_yticks([1e-6,1e-4,1e-2,1])
    ax.set_xticks([1,8,16,24,32])
    ax.legend(loc='lower left',bbox_to_anchor=(0,1.02),ncol=2,frameon=False,
              handletextpad=.4,borderaxespad=0,columnspacing=1)
    save(fig,'per_query_ratio','all32 matched ratios; horizontal line is the0.80 p90 gate, not a per-query requirement')
    values=[(1000000-b1['prior_mean_survivors'])/(1000000*480/1e6),b0['proof_yield_per_decimal_MB'],o1['proof_yield_per_decimal_MB'],c1['proof_yield_per_decimal_MB']]
    fig,ax=plt.subplots(figsize=(3.4,2.45))
    bars=ax.barh(range(4),values,color=colors,edgecolor='black',linewidth=.5,hatch=hatches)
    ax.set_yticks(range(4),names); ax.invert_yaxis()
    ax.set(xlabel='Certificates / nominal source MB',xlim=(0,2800))
    ax.set_xticks([0,500,1000,1500,2000,2500])
    for rect,v in zip(bars,values):
        ax.text(v+32,rect.get_y()+rect.get_height()/2,f'{v:,.3f}',va='center',fontsize=8)
    ax.set_title('Not DRAM; O1 selector unpriced',fontsize=7,pad=7)
    save(fig,'proof_yield','strict rejections per decimal nominal selected payload MB; no physical traffic claim')
    (ROOT/'evidence/FIGURE_QA.json').write_text(json.dumps({'plots':qa,'visual_inspection':'PENDING','grayscale_safe':'redundant hatch or marker encodings','data_source':'frozen scalar files'},indent=2)+'\n')


if __name__=='__main__': figures()
