"""Plot synthetic admission, never server latency or actual GPU traffic."""
if not __debug__:
    raise SystemExit('Optimized Python disables mandatory checks; run without -O/PYTHONOPTIMIZE.')
import argparse
import csv
import json
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--style-root', type=Path, required=True,
                        help='Installed paper-figures skill scripts directory; not vendored')
    parser.add_argument('--out', type=Path, required=True, help='Fresh scratch figure directory')
    args = parser.parse_args()
    sys.path.insert(0, str(args.style_root))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from paper_style import setup_style, trend_plot, save_fig
    artifact = Path(__file__).resolve().parent
    rows = json.loads((artifact / 'evidence/RESULTS.json').read_text())['rows']
    out = args.out
    out.mkdir(parents=True, exist_ok=False)
    setup_style('acm_double', width_inches=3.5, height_ratio=.77,
                font_family='serif', use_latex=False, use_scienceplots=False)
    x = [r['rate_qps'] for r in rows]
    cases = [
        ('batch_size_vs_arrival',
         [[r['mean_B_batch_weighted'] for r in rows], [4] * 4],
         ['Synthetic trace', 'Mean-B gate'], 'Mean batch size (queries/batch)', (0, 4.5)),
        ('queue_delay_vs_arrival',
         [[r['query_wait_ps']['mean'] / 1e9 for r in rows],
          [r['query_wait_ps']['p90'] / 1e9 for r in rows]],
         ['Mean collection wait', 'p90 = 0.50ms budget'], 'Collection wait (ms/query)', (0, .58)),
        ('ideal_bytes_vs_arrival',
         [[r['query_weighted_source_bytes'] / 1e9 for r in rows],
          [r['batch_weighted_E_source_bytes_over_B'] / 1e9 for r in rows],
          [1.014828776] * 4, [.75] * 4],
         ['Query-weighted', 'Batch-weighted', 'Range keeper reference', 'GO gate'],
         'Ideal DB source (GB/query)', (0, 5.0)),
    ]
    for name, series, labels, ylabel, ylim in cases:
        fig, ax, _ = trend_plot(x, series, labels, xlabel='Arrival rate (queries/s)',
                               ylabel=ylabel, colors=['#0072B2', '#777777', '#000000', '#444444'],
                               markers=['o', 's', '', ''], linestyles=['-', '--', ':', '-.'],
                               legend_kwargs={'loc': 'upper right' if 'ideal_bytes' in name else 'lower left',
                                              'ncol': 2 if 'ideal_bytes' in name else 1,
                                              'fontsize': 6.5, 'columnspacing': .8})
        ax.set_xscale('log')
        ax.set_xticks(x, labels=[str(v) for v in x])
        ax.set_ylim(*ylim)
        ax.set_title('Synthetic Poisson admission model', fontsize=8)
        save_fig(fig, name, output_dir=out, formats=('pdf', 'svg', 'png'), dpi=400)
        plt.close(fig)
        svg = out / (name + '.svg')
        svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines()) + '\n')
        with (out / (name + '.csv')).open('w', newline='') as f:
            writer = csv.writer(f, lineterminator='\n')
            writer.writerow(['arrival_qps'] + labels)
            writer.writerows([x[i]] + [s[i] for s in series] for i in range(4))


if __name__ == '__main__':
    main()
