"""Four evidence-bearing figures; uncertainty and service denominators stay explicit."""
if not __debug__:
    raise SystemExit('Optimized Python disables mandatory checks; run without -O/PYTHONOPTIMIZE.')
import argparse
import csv
import json
import sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    p = argparse.ArgumentParser(); p.add_argument('--data', type=Path, required=True); p.add_argument('--out', type=Path, required=True)
    p.add_argument('--style-root', type=Path, required=True); a = p.parse_args(); a.out.mkdir(parents=True, exist_ok=False)
    sys.path.insert(0, str(a.style_root)); from paper_style import setup_style, trend_plot, scatter_plot, save_fig
    setup_style('acm_double', width_inches=3.5, use_latex=False, use_scienceplots=False, font_family='serif')
    plt.rcParams.update({'svg.hashsalt': 'dynamic-pdx-20261015', 'svg.fonttype': 'none'})
    read = lambda n: json.loads((a.data/n).read_text())
    timing = read('results/TIMING.json')['workloads']; traffic = read('results/TRAFFIC.json')['cells']; inputs = read('evidence/INPUTS.json')
    methods = ['S0', 'S1', 'S2_STALE', 'S2_INC']; names = ['Full safe', 'Progressive', 'PDX stale', 'PDX delta']
    colors = ['#999999', '#333333', '#0072B2', '#0072B2']; markers = ['D', 's', 'o', '^']; styles = [':', '--', '-', '--']
    x = [r['mutation_fraction']*100 for r in next(r for r in inputs['records'] if r['N'] == 1000000 and r['workload'] == 2)['windows']]

    def export(fig, name, rows):
        paths = save_fig(fig, name, output_dir=a.out, formats=('pdf', 'svg', 'png'), dpi=400,
                         target_width_inches=fig.get_size_inches()[0], min_font_size=7)
        for path in paths:
            if path.suffix == '.svg': path.write_text('\n'.join(line.rstrip() for line in path.read_text().splitlines())+'\n')
        with (a.out/(name+'.csv')).open('x', newline='') as f: csv.writer(f, lineterminator='\n').writerows(rows)
        plt.close(fig)

    values = [[cell['query_mean_ms']['median'] for cell in timing['W2']['systems'][m]['windows']] for m in methods]
    errors = [[[values[i][p]-timing['W2']['systems'][m]['windows'][p]['query_mean_ms']['p10'] for p in range(5)] for i, m in enumerate(methods)],
              [[timing['W2']['systems'][m]['windows'][p]['query_mean_ms']['p90']-values[i][p] for p in range(5)] for i, m in enumerate(methods)]]
    fig, ax = plt.subplots(figsize=(3.5, 2.8)); trend_plot(x, values, names, errors=errors, ax=ax,
        xlabel='Original objects replaced (%)', ylabel='Host-ready latency (ms / query)', colors=colors, markers=markers, linestyles=styles,
        legend_kwargs=dict(loc='upper center', ncol=2, frameon=False, fontsize=7))
    ax.set_ylim(0, max(max(v) for v in values)*1.4); ax.set_title('W2 synthetic shift; 6 processes; p10–p90', fontsize=7)
    fig.tight_layout(pad=.4)
    rows = [['mode', 'mutation_percent', 'median_ms', 'p10_ms', 'p90_ms']]
    for i, m in enumerate(methods):
        for j in range(5):
            s = timing['W2']['systems'][m]['windows'][j]['query_mean_ms']; rows.append([m, x[j], s['median'], s['p10'], s['p90']])
    export(fig, 'query_vs_mutation', rows)

    values = [[r['means']['DRAM_bytes']/1e9 for r in traffic[m+'_W2']['windows']] for m in methods]
    fig, ax = plt.subplots(figsize=(3.5, 2.8)); trend_plot(x, values, names, ax=ax, xlabel='Original objects replaced (%)',
        ylabel='All-kernel DRAM (GB / query)', colors=colors, markers=markers, linestyles=styles,
        legend_kwargs=dict(loc='upper center', ncol=2, frameon=False, fontsize=7))
    ax.set_ylim(0, max(max(v) for v in values)*1.4); ax.set_title('32 queries/window; 1 NCU process/cell; no CI', fontsize=7)
    fig.tight_layout(pad=.4)
    export(fig, 'dram_vs_mutation', [['mode', 'mutation_percent', 'DRAM_GB_per_query'],
        *[[m, x[j], values[i][j]] for i, m in enumerate(methods) for j in range(5)]])

    px = []; py = []; xlo = []; xhi = []; ylo = []; yhi = []; rows = [['workload', 'tax_ms_per_query', 'tax_CI_low', 'tax_CI_high', 'paired_query_gain_percent', 'gain_CI_low', 'gain_CI_high']]
    for w in ('W0', 'W1', 'W2'):
        tax = timing[w]['incremental_update_tax']; q = timing[w]['comparisons']['S2_INC_over_S1']['query']
        xx = tax['median_difference_ms']/160; lo, hi = [v/160 for v in tax['paired_difference_95_CI_ms']]
        yy = (1-q['paired_geometric_ratio'])*100; low, high = (1-q['paired_95_CI'][1])*100, (1-q['paired_95_CI'][0])*100
        assert lo <= xx <= hi and low <= yy <= high
        px.append(xx); py.append(yy); xlo.append(xx-lo); xhi.append(hi-xx); ylo.append(yy-low); yhi.append(high-yy)
        rows.append([w, xx, lo, hi, yy, low, high])
    fig, ax = plt.subplots(figsize=(3.5, 2.8)); _, _, artists, _ = scatter_plot(px, py, ['W0', 'W1', 'W2'], ax=ax,
        xlabel='INC − stale update tax (ms / query)', ylabel='INC query gain vs progressive (%)', xerr=[xlo, xhi], yerr=[ylo, yhi],
        colors=['#555555', '#999999', '#0072B2'], markers=['o', 's', '^'], annotate=False)
    ax.legend(artists, ['W0', 'W1', 'W2'], frameon=False, fontsize=7, loc='best')
    assert all(v-e > 0 for v, e in zip(px, xlo))
    ax.set_xscale('log'); ax.axhline(0, color='#999999', linewidth=.6, zorder=0)
    ax.set_title('Paired 95% intervals; log x; points, not Pareto', fontsize=7)
    fig.tight_layout(pad=.4); export(fig, 'gain_vs_update_tax', rows)

    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.8)); rows = [['workload', 'mode', 'query_s', 'updates_including_stats_s', 'other_and_release_s', 'service_s', 'service_process_SD_s']]
    handles = None
    for workload, ax in zip(('W0', 'W1', 'W2'), axes):
        bottoms = np.zeros(4); components = []
        for metric in ('query_ms', 'update_ms_including_statistics', 'other_ms'):
            components.append([timing[workload]['systems'][m]['totals'][metric]['arithmetic_mean']/1000 for m in methods])
        components[-1] = [v+timing[workload]['systems'][m]['totals']['release_ms']['arithmetic_mean']/1000 for v, m in zip(components[-1], methods)]
        local = []
        for values, color, hatch in zip(components, ('#0072B2', '#777777', '#CCCCCC'), ('', '//', '..')):
            bars = ax.bar(np.arange(4), values, bottom=bottoms, color=color, hatch=hatch, width=.72, edgecolor='black', linewidth=.4)
            bottoms += values; local.append(bars)
        if handles is None: handles = [v[0] for v in local]
        sd = [float(np.std(timing[workload]['systems'][m]['totals']['service_ms']['process_values'], ddof=1))/1000 for m in methods]
        ax.errorbar(np.arange(4), bottoms, yerr=sd, fmt='none', ecolor='black', capsize=2, linewidth=.7)
        ax.set_xticks(range(4), ['S0', 'S1', 'Stale', 'Delta']); ax.set_title(workload, fontsize=8); ax.set_ylabel('Service time (s)', fontsize=8)
        ax.set_ylim(0, max(b+e for b, e in zip(bottoms, sd))*1.13); ax.tick_params(labelsize=7)
        for i, m in enumerate(methods): rows.append([workload, m, *[c[i] for c in components], bottoms[i], sd[i]])
    fig.legend(handles, ['Query ACKs', 'Updates incl. statistics', 'Other + release'], ncol=3, loc='upper center', bbox_to_anchor=(.5, .93), frameon=False, fontsize=8)
    fig.suptitle('Six-process arithmetic means; total error bars: SD; no standalone refresh', fontsize=8, y=.99)
    fig.subplots_adjust(left=.075, right=.99, bottom=.19, top=.73, wspace=.42)
    export(fig, 'service_composition', rows)
    print('Four scoped vector/PDF/SVG and400DPI PNG figures plus numeric CSVs')


if __name__ == '__main__': main()
