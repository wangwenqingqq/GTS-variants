"""Measured latency and all-kernel DRAM; no profiler-duration speedup claims."""
if not __debug__:
    raise SystemExit('Optimized Python disables mandatory checks; run without -O/PYTHONOPTIMIZE.')
import argparse
import csv
import json
import sys
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    p = argparse.ArgumentParser(); p.add_argument('--data', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True); p.add_argument('--style-root', type=Path, required=True)
    a = p.parse_args(); sys.path.insert(0, str(a.style_root))
    from paper_style import setup_style, grouped_bars, save_fig
    a.out.mkdir(parents=True, exist_ok=False)
    setup_style('acm_double', width_inches=3.5, height_ratio=.75, use_latex=False,
                use_scienceplots=False, font_family='serif')
    plt.rcParams.update({'svg.hashsalt': 'pdx-bond-gate4-recovery', 'svg.fonttype': 'none'})
    read = lambda n: json.loads((a.data/'evidence'/f'{n}.json').read_text())
    timing, dram = read('TIMING'), read('DRAM')
    modes = ('keeper', 'candidate'); labels = ['P1 keeper', 'PDX zone32']
    for name in ('latency', 'dram'):
        if name == 'latency':
            v = [timing['modes'][m]['median'] for m in modes]
            errors = [[[v[i]-timing['modes'][m]['p10'] for i, m in enumerate(modes)]],
                      [[timing['modes'][m]['p90']-v[i] for i, m in enumerate(modes)]]]
            ylabel, note, limit = 'Host-ready latency (ms / query)', '6 processes / mode; p10–p90 of process means', 1.35
        else:
            v = [dram['modes'][m]['means']['DRAM_bytes']/1e9 for m in modes]
            errors = None
            ylabel, note, limit = 'All-kernel DRAM (GB / query)', '32 queries; 1 NCU process / mode; no process CI', 1.35
        fig, ax = plt.subplots(figsize=(3.5, 2.6))
        grouped_bars([v], labels, ['Observed'], ax=ax, ylabel=ylabel,
                     colors=['#0072B2'], errors=errors, annotate_values=False, legend=False)
        for i, (bar, value) in enumerate(zip(ax.patches, v)):
            bar.set_facecolor('#777777' if i == 0 else '#0072B2')
            bar.set_hatch('' if i == 0 else '//')
            ax.text(bar.get_x()+bar.get_width()/2, value+.055, f'{value:.5f}' if name == 'latency' else f'{value:.3f}',
                    ha='center', fontsize=8)
            if name == 'latency':
                xs = [bar.get_x()+bar.get_width()/2+(r-2.5)*.025 for r in range(6)]
                ax.scatter(xs, timing['modes'][modes[i]]['process_means'], s=9,
                           facecolors='white', edgecolors='black', linewidths=.5, zorder=5)
        ax.set_ylim(0, limit); ax.set_title(note, fontsize=7, pad=8)
        fig.tight_layout(pad=.35)
        paths = save_fig(fig, name, output_dir=a.out, formats=('pdf', 'svg', 'png'),
                         dpi=400, target_width_inches=3.5, min_font_size=7)
        for path in paths:
            if path.suffix == '.svg': path.write_text('\n'.join(line.rstrip() for line in path.read_text().splitlines())+'\n')
        with (a.out/(name+'.csv')).open('x', newline='') as f:
            w = csv.writer(f, lineterminator='\n')
            if name == 'latency':
                w.writerow(['round', 'mode', 'mean_ACK_ms'])
                w.writerows((x['round'], x['mode'], x['mean_query_ms']) for x in timing['processes'])
            else:
                w.writerow(['mode', 'all_kernel_DRAM_GB']); w.writerows(zip(modes, v))
        plt.close(fig)
    print('Two measured GPU figures; source-model and logical charts remain in the immutable CPU checkpoint')


if __name__ == '__main__': main()
