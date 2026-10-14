"""Four final-size, source-model figures; a fresh output directory is mandatory."""
if not __debug__:
    raise SystemExit('Optimized Python disables mandatory checks; run without -O/PYTHONOPTIMIZE.')
import argparse
import csv
import json
import os
import sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--style-root', type=Path, default=Path(os.environ.get('AGENTS_SKILLS_HOME', Path.home() / '.agents/skills')) / 'paper-figures/scripts')
    a = p.parse_args()
    sys.path.insert(0, str(a.style_root))
    from paper_style import setup_style, trend_plot, heatmap, scatter_plot, save_fig
    a.out.mkdir(parents=True, exist_ok=False)
    setup_style('acm_double', width_inches=3.5, height_ratio=.75, use_latex=False, use_scienceplots=False, font_family='serif')
    plt.rcParams.update({'svg.hashsalt': 'exact-gpu-limits-gate1', 'svg.fonttype': 'none'})
    load = lambda name: json.loads((a.data / name).read_text())

    def export(fig, name, rows):
        fig.tight_layout(pad=.35)
        paths = save_fig(fig, name, output_dir=a.out, formats=('pdf', 'svg', 'png'), dpi=400, target_width_inches=3.5, min_font_size=7)
        for path in paths:
            if path.suffix == '.svg':
                # XML whitespace only; no geometry, text, or path command is changed.
                path.write_text('\n'.join(line.rstrip() for line in path.read_text().splitlines()) + '\n')
        with (a.out / (name + '.csv')).open('x', newline='') as f:
            csv.writer(f, lineterminator='\n').writerows(rows)
        plt.close(fig)

    original = load('b1_information_floor/ORIGINAL_ORDER.json')
    global_oracle = load('b1_information_floor/QUERY_GLOBAL_ORACLE.json')['nominal']
    pair = load('b1_information_floor/PAIR_ORACLE.json')['nominal']
    values = [original, global_oracle, pair]
    names = ['Original', 'Query-global', 'Pair-specific']
    x = np.arange(1, 961)
    cdfs = [100 * np.cumsum(v['histogram'])[1:] / v['count'] for v in values]
    fig, ax = plt.subplots(figsize=(3.5, 3.2))
    fig, ax, _ = trend_plot(x, cdfs, [f'{n} (mean {v["mean"]:.2f})' for n, v in zip(names, values)], ax=ax,
                           xlabel='Required coordinates / object', ylabel='Pairs resolved (%)',
                           colors=['#0072B2', '#D55E00', '#333333'], markers=['', '', ''], linestyles=['-', '--', ':'],
                           legend_kwargs={'loc': 'lower left', 'bbox_to_anchor': (0, 1.02), 'frameon': False, 'fontsize': 7, 'borderaxespad': 0})
    ax.set_xscale('log')
    ax.set_xticks([1, 4, 16, 64, 256, 960], labels=['1', '4', '16', '64', '256', '960'])
    ax.set_xlim(1, 960)
    ax.set_ylim(0, 101)
    export(fig, 'required_dims_oracles', [['required_dims', *names]] + [[int(k), *[float(v[k-1]) for v in cdfs]] for k in x])

    b2 = load('b2_metadata_floor/BREAK_EVEN.json')
    budgets = [r['bytes_per_vector'] for r in b2['rows']]
    rejection = [100 * r['break_even_rejection_fraction']['decimal'] for r in b2['rows']]
    fig, ax, _ = trend_plot(budgets, [rejection], ['Break-even (conditional)'],
                           xlabel='Extra metadata (B / vector)', ylabel='Required safe rejection (%)',
                           colors=['#0072B2'], markers=['o'], linestyles=['-'], legend=False)
    ax.set_xscale('log', base=2)
    ax.set_xticks([1, 4, 16, 64, 256], labels=['1', '4', '16', '64', '256'])
    ax.set_xlim(.9, 290)
    ax.set_ylim(65, 100)
    ax.axhline(90, color='#333333', linestyle='--', linewidth=1)
    ax.text(1.1, 91.5, 'Proposed 90% barrier', fontsize=7)
    ax.text(1.1, 67, 'No achievable representation inferred', fontsize=7)
    export(fig, 'metadata_rejection_pareto', [['metadata_B_per_vector', 'break_even_rejection_percent']] + list(zip(budgets, rejection)))

    b3 = load('b3_online_reuse/BREAK_EVEN_SURFACE.json')
    z = np.asarray(b3['source_bytes_per_query_matrix']) / 1e9
    fig, ax, image, colorbar = heatmap(z, cmap='cividis', cbar_label='Source (GB / query)')
    ax.invert_yaxis()
    ax.set_xlabel('Arrival rate (kquery / s)')
    ax.set_ylabel('Collection window (ms)')
    ax.set_xticks([0, 24, 49, 74, 99], labels=['0.1', '2.5', '5', '7.5', '10'])
    ax.set_yticks([0, 9, 19, 29, 39], labels=['0.05', '0.5', '1', '1.5', '2'])
    contour = ax.contour(z, levels=[b3['keeper_source_bytes'] / 1e9], colors=['black'], linewidths=1.1)
    ax.clabel(contour, inline=True, fontsize=7, fmt={b3['keeper_source_bytes'] / 1e9: 'Keeper'})
    ax.plot(49, 9, marker='x', color='black', markersize=5)
    ax.annotate('Frozen corner', (49, 9), xytext=(-8, -16), textcoords='offset points', ha='right', fontsize=7)
    export(fig, 'lambda_window_heatmap', [['lambda_qps', 'window_us', 'source_bytes_per_query']] +
           [[rate, us, b3['source_bytes_per_query_matrix'][i][j]] for i, us in enumerate(b3['window_us']) for j, rate in enumerate(b3['lambda_qps'])])

    # Only coordinate/metadata payload is on these axes. Unpriced systems get no fake point.
    keeper = b3['keeper_source_bytes'] / 1e9
    fig, ax, _, _ = scatter_plot([0, 0, 0, .968], [3.84, keeper, 3.84 / 3.5, .968],
        xlabel='Extra indexed payload (GB)', ylabel='Query source model (GB)', annotate=False,
        colors=['#333333', '#0072B2', '#D55E00', '#777777'], markers=['s', 'o', '^', 'D'])
    ax.set_xlim(-.055, 1.07)
    ax.set_ylim(0, 5.05)
    ax.axhline(keeper, color='#0072B2', linestyle=':', linewidth=.8)
    ax.annotate('Full scan', (0, 3.84), xytext=(8, 0), textcoords='offset points', fontsize=7)
    ax.annotate('Progressive', (0, keeper), xytext=(8, -8), textcoords='offset points', fontsize=7)
    ax.annotate('Batching oracle', (0, 3.84/3.5), xytext=(8, 10), textcoords='offset points', fontsize=7)
    ax.vlines(.968, .968, 4.808, colors='#777777', linestyles='--', linewidth=1)
    ax.annotate('INT8, F = 0', (.968, .968), xytext=(-5, -18), textcoords='offset points', ha='right', fontsize=7)
    ax.text(.94, 4.7, 'INT8 fallback', ha='right', fontsize=7)
    metadata_x = np.asarray(budgets) * .001
    metadata_y = metadata_x + .384
    ax.plot(metadata_x, metadata_y, color='#555555', linestyle='--', marker='+', markersize=3, linewidth=1)
    ax.annotate('Metadata, f = 90%\n(conditional only)', (.256, .640), xytext=(12, -12), textcoords='offset points', fontsize=7)
    ax.text(.15, 4.55, 'Tree/index: unpriced', fontsize=7)
    export(fig, 'design_space_map', [['method', 'extra_indexed_GB', 'query_source_GB', 'status']] +
           [['Full scan', 0, 3.84, 'coordinate model'], ['Progressive', 0, keeper, 'checkpoint coordinate model'],
            ['Batching oracle', 0, 3.84/3.5, 'ideal uncapped Poisson'], ['INT8 F=0', .968, .968, 'unrealized optimistic model']] +
           [[f'Metadata{b}B_f90', float(xx), float(yy), 'conditional unrealized'] for b, xx, yy in zip(budgets, metadata_x, metadata_y)])
    print('PASS: four figures; no timing or physical-bound inference')


if __name__ == '__main__':
    main()
