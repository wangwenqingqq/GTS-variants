"""Two finite-population/source-model charts; never invent GPU performance bars."""
if not __debug__:
    raise SystemExit('Optimized Python disables mandatory checks; run without -O/PYTHONOPTIMIZE.')
import argparse
import csv
import json
import os
import sys
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    p=argparse.ArgumentParser();p.add_argument('--data',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--style-root',type=Path,default=Path(os.environ.get('AGENTS_SKILLS_HOME',Path.home()/'.agents/skills'))/'paper-figures/scripts')
    a=p.parse_args();sys.path.insert(0,str(a.style_root))
    from paper_style import setup_style,grouped_bars,save_fig
    a.out.mkdir(parents=True,exist_ok=False)
    setup_style('acm_double',width_inches=3.5,height_ratio=.75,use_latex=False,use_scienceplots=False,font_family='serif')
    plt.rcParams.update({'svg.hashsalt':'pdx-bond-gate4','svg.fonttype':'none'})
    load=lambda n:json.loads((a.data/n).read_text())
    dims=[load('logical/ORIGINAL.json')['mean_required_dims'],load('logical/ORACLE.json')['mean_required_dims'],load('logical/PDX_BOND.json')['safe']['mean']]
    source=load('source/SOURCE_BYTES.json')['mean_coordinate_source_bytes']['decimal']/1e9
    data=[('required_dims',['Original','Oracle','PDX zone32'],dims,'Mean required coordinates / pair',200,'Finite population:32M pairs; not GPU time'),
          ('source_bytes',['P1 keeper','PDX zone32'],[1.014828776,source],'Stage coordinate model (GB / query)',1.2,'Source model only; physical DRAM not measured')]
    for name,labels,values,ylabel,limit,note in data:
        fig,ax=plt.subplots(figsize=(3.5,2.6))
        grouped_bars([values],labels,['Complete fixed population'],ax=ax,ylabel=ylabel,
                     colors=['#0072B2'],annotate_values=False,legend=False)
        bars=ax.patches
        for i,(bar,value) in enumerate(zip(bars,values)):
            bar.set_facecolor('#0072B2' if i==len(values)-1 else '#777777')
            bar.set_hatch('//' if i==len(values)-1 else '')
            ax.text(bar.get_x()+bar.get_width()/2,value+limit*.025,f'{value:.2f}' if name=='required_dims' else f'{value:.3f}',ha='center',fontsize=8)
        ax.set_ylim(0,limit);ax.set_title(note,fontsize=7,pad=8)
        fig.tight_layout(pad=.35)
        paths=save_fig(fig,name,output_dir=a.out,formats=('pdf','svg','png'),dpi=400,target_width_inches=3.5,min_font_size=7)
        for path in paths:
            if path.suffix=='.svg':path.write_text('\n'.join(line.rstrip() for line in path.read_text().splitlines())+'\n')
        with (a.out/(name+'.csv')).open('x',newline='') as f:
            csv.writer(f,lineterminator='\n').writerows([['method',ylabel],*zip(labels,values)])
        plt.close(fig)
    print('Two CPU/model figures;no DRAM or latency invented')


if __name__=='__main__':main()
