#!/usr/bin/env python3
"""Four fixed-pool diagnostics, matching the preceding count/model style."""
import argparse
import json
from pathlib import Path
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parent


def read(name):return json.loads((ROOT/name).read_text())


def figures(helper):
    sys.path.insert(0,str(helper))
    from paper_style import setup_style,grouped_bars,save_fig,audit_figure
    setup_style('custom',width_inches=3.4,font_family='serif',use_latex=False,use_scienceplots=False)
    plt.rcParams.update({'font.family':'DejaVu Serif','font.size':9,'axes.labelsize':9,'xtick.labelsize':8,'ytick.labelsize':8,'legend.fontsize':7,'pdf.fonttype':42,'svg.fonttype':'none','axes.spines.top':False,'axes.spines.right':False})
    qa=[];target=ROOT/'figures';target.mkdir(exist_ok=True)
    def save(fig,name,scope):
        fig.tight_layout(pad=.8);fig.canvas.draw();renderer=fig.canvas.get_renderer();box=fig.bbox
        for t in fig.findobj(matplotlib.text.Text):
            if not t.get_visible() or not t.get_text():continue
            b=t.get_window_extent(renderer)
            assert b.x0>=box.x0-1 and b.y0>=box.y0-1 and b.x1<=box.x1+1 and b.y1<=box.y1+1,('clipped text',name,t.get_text())
        issues=audit_figure(fig,target_width_inches=3.4,min_font_size=7);assert not issues,issues
        save_fig(fig,name,output_dir=target,formats=('svg','pdf','png'),dpi=300,target_width_inches=3.4,min_font_size=7)
        svg=target/(name+'.svg')
        svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines())+'\n')
        qa.append({'name':name,'scope':scope,'canvas_inches':list(fig.get_size_inches()),'PNG_dpi':300,'SVG_and_PDF_vector':True,'minimum_font_pt':min(t.get_fontsize() for t in fig.findobj(matplotlib.text.Text) if t.get_visible() and t.get_text()),'geometry_and_style_audit':'PASS','error_bars':'none: deterministic complete fixed pool, not timing repeats'})
        plt.close(fig)
    paths=['baseline/B0_ORIGINAL_FIRST16.json','baseline/C1_SCATTERED_REFERENCE.json','baseline/O2_ORACLE_REFERENCE.json','baseline/S1_ORIGINAL_LAYOUT.json','candidate/P1_PACKED_SECTOR_MOMENT.json']
    vals=[read(p)['mean_survivors']/1000 for p in paths]
    fig,ax=plt.subplots(figsize=(3.4,2.6))
    bars=ax.bar(range(5),vals,color=['#777777','#bcbcbc','#009E73','#999999','#0072B2'],hatch=['//','','xx','\\\\','..'],edgecolor='black',linewidth=.5)
    ax.set_xticks(range(5),['B0','C1*','O2*','S1','P1']);ax.set(ylabel='Mean survivors / query (thousands)',ylim=(0,740))
    for b,v in zip(bars,vals):ax.text(b.get_x()+b.get_width()/2,v+12,f'{v:.1f}',ha='center',fontsize=7)
    ax.set_title('32 x 1M; *historical scattered / oracle',fontsize=7,pad=8)
    save(fig,'survivors_packed_vs_original','fixed32; nominal512B; C1 scattered/ineligible; O2 pair-specific/unpriced; parent baselines not rerun')
    recovery=read('analysis/C1_RECOVERY.json');fig,ax=plt.subplots(figsize=(3.4,2.55));x=list(range(1,33))
    ax.scatter(x,[r['fraction'] for r in recovery['queries']],color='#0072B2',s=16,marker='o')
    ax.set(xlabel='Frozen query index',ylabel='C1 top128 recovered / 128',ylim=(0,1),xlim=(.5,32.5));ax.set_xticks([1,8,16,24,32])
    ax.set_title(f"Independent evaluation mean: {recovery['mean']:.3f}",fontsize=7,pad=8)
    save(fig,'c1_recovery','set overlap, not recall or search correctness; all32 evaluation queries shown')
    purity=read('analysis/SECTOR_PURITY.json');fig,ax=plt.subplots(figsize=(3.4,2.55))
    grouped_bars([[purity['S1_mean']],[purity['P1_mean']]],['32-query mean'],['S1 original','P1 packed'],ylabel='High-value dims / selected sector',ax=ax,colors=['#999999','#0072B2'],hatches=['//','..'],ylim=(0,8),annotate_values=True,value_fmt='{:.3f}',legend_kwargs={'loc':'upper left','frameon':False})
    ax.set_title('C1 top128 membership; eight dims / sector',fontsize=7,pad=8)
    save(fig,'sector_purity','equal query weight and16 selected sectors per query; high-value is C1 demand, not measured pair outcome')
    cost=read('cost/FULL_FALLBACK_BYTES.json');s1=512000000+3328*read('baseline/S1_ORIGINAL_LAYOUT.json')['mean_survivors']
    vals=[cost['strong_baseline_mean_bytes']/1e9,s1/1e9,cost['mean_bytes']/1e9];fig,ax=plt.subplots(figsize=(3.4,2.55))
    bars=ax.bar(range(3),vals,color=['#777777','#999999','#0072B2'],hatch=['//','\\\\','..'],edgecolor='black',linewidth=.5)
    ax.set_xticks(range(3),['Strong/ref','S1/model','P1/model']);ax.set(ylabel='Conditional source GB / query',ylim=(0,1.2))
    for b,v in zip(bars,vals):ax.text(b.get_x()+b.get_width()/2,v+.025,f'{v:.6f}',ha='center',fontsize=7)
    ax.set_title('GO ceiling 0.811863 GB; not DRAM',fontsize=7,pad=8)
    save(fig,'conservative_bytes','source bytes only; retain/reorder/spill costs unknown; source-payload model not actual DRAM or complete-search cost')
    (ROOT/'evidence/FIGURE_QA.json').write_text(json.dumps({'plots':qa,'visual_inspection':'PENDING','font_family':'DejaVu Serif; inherited from preceding diagnostics','grayscale_safe':'hatches or markers redundant with colors'},indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--style-helper',type=Path,required=True);figures(p.parse_args().style_helper)
