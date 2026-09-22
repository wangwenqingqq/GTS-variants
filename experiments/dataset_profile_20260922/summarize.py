#!/usr/bin/env python3
"""Render the measured JSON results; requires NumPy and Matplotlib."""
import argparse
import json
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

NAMES = ['SIFT-1M', 'Deep-1M', 'GIST-1M', 'Word', 'T-loc-1M']


def fmt(x, digits=3):
    return 'N/A' if x is None else f'{x:.{digits}f}'


def seed_values(r, metric, estimator='mean'):
    return np.asarray([v[metric][estimator] for v in r['geometry_runs']])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('run', type=Path)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    results = [json.loads((a.run/n/'results.json').read_text()) for n in NAMES]
    lines = ['# Dataset characterization results', '',
        'Completed under `CONTRACT.md`, native-metric version 1. Inputs are read-only.',
        '**Scope:** full scans for elementary statistics; exact search over 50,000 sampled references, '
        '512 held-out queries, and three fixed seeds for geometry. These are not full-corpus nearest neighbors.',
        'No normalization or whitening was applied. No GPU was used. Seed ranges are not confidence intervals.', '',
        '## Main comparison', '',
        '| Dataset | N | Dimension / length | Exact zero (%) | Hoyer mean | PCA95 | LID50 median* | RC10 mean* | Expansion10 median* | Adjacent/random median |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in results:
        f = r['full']
        dim = str(f['dimension']) if r['kind'] != 'word' else f"{f['length']['min']:.0f}–{f['length']['max']:.0f} chars"
        zero = fmt(100*f['zero_fraction']) if r['kind'] == 'vector' else 'N/A'
        l = fmt(float(np.median(seed_values(r, 'lid50', 'p50')))) if r['kind'] != 'word' else 'N/A'
        lines.append(f"| {r['dataset']} | {f['n']:,} | {dim} | {zero} | {fmt(f.get('hoyer',{}).get('mean'))} | "
                     f"{r.get('covariance_sample',{}).get('pca95','N/A')} | {l} | "
                     f"{np.median(seed_values(r,'rc10')):.3f} | {np.median(seed_values(r,'expansion10','p50')):.3f} | "
                     f"{r['row_order']['adjacent_to_random_median_ratio']:.4f} |")
    lines += ['', '*Main geometry entries are the median of the three seed-level estimates. '
              'PCA uses 10,000 rows; file-order distance summaries use every adjacent pair and '
              '20,000 random distinct-index pairs. Spatial zero-coordinate counts are not interpreted as sparsity.', '',
              '## Sampling sensitivity', '',
              '| Dataset | RC10 mean: seed min–max | LID50 median: seed min–max | Expansion10 median: seed min–max |',
              '|---|---:|---:|---:|']
    for r in results:
        vals = []
        for metric, est in [('rc10', 'mean'), ('lid50', 'p50'), ('expansion10', 'p50')]:
            if metric == 'lid50' and r['kind'] == 'word':
                vals.append('N/A')
            else:
                v = seed_values(r, metric, est)
                vals.append(f'{v.min():.3f}–{v.max():.3f}')
        lines.append('| '+r['dataset']+' | '+' | '.join(vals)+' |')
    lines += ['', '## Native-query workload versus uniform base queries', '',
              '| Dataset | Uniform RC10 mean* | Native-query RC10 mean | Native mean nearest distance | Discrepancy check |',
              '|---|---:|---:|---:|---|']
    for r in results:
        q = r['native_query_profile']
        if 'native_query_mmd' in r:
            m = r['native_query_mmd']
            disc = f"RBF MMD²={m['biased_mmd_squared']:.5g}; permutation p={m['permutation_p']:.2f}"
        else:
            disc = f"Length KS distance={r['native_query_length_shift']['ks_distance']:.4f}"
        lines.append(f"| {r['dataset']} | {np.median(seed_values(r,'rc10')):.3f} | {q['rc10']['mean']:.3f} | "
                     f"{q['nearest_distance']['mean']:.5g} | {disc} |")
    lines += ['', 'MMD is a bandwidth-dependent exploratory within-dataset test with 99 label permutations; '
              'raw MMD magnitudes are not a cross-dataset ranking. The Word and T-loc native query-ID files '
              'select IDs 0–999; these prefix workloads must not be treated as uniformly sampled queries.', '',
              '## Dataset-specific structure', '']
    for r in results:
        f = r['full']
        lines.append(f"### {r['dataset']}")
        if r['kind'] == 'vector':
            lines += [f"- Norm mean/SD: {f['norm']['mean']:.6g} / {f['norm']['std']:.6g}.",
                f"- Relative near-zero fractions (0.001 / 0.01 / 0.05 × row RMS): "
                + ' / '.join(f'{100*v:.4f}%' for v in f['relative_nearzero_fraction'].values())+'.',
                f"- Duplicate fraction in the 50,000-object sample: {r['vector_duplicate_sample']['duplicate_fraction']:.6g}."]
        elif r['kind'] == 'word':
            lines += [f"- Mean length: {f['length']['mean']:.4f}; character vocabulary: {f['character_vocabulary']}.",
                f"- Character / bigram / trigram entropy (bits): {f['character_entropy_bits']:.4f} / "
                f"{f['2gram_entropy_bits']:.4f} / {f['3gram_entropy_bits']:.4f}.",
                f"- Exact full duplicate fraction: {f['duplicate_fraction_full']:.6g}.",
                f"- Lexicographically nondecreasing adjacent pairs: {100*f['lexicographic_nondecreasing_fraction']:.4f}%."]
        else:
            lines += [f"- Exact full duplicate fraction: {f['duplicate_fraction_full']:.6g}.",
                f"- Coordinate ranges: {list(zip(f['coordinate_min'],f['coordinate_max']))}.",
                '- Raw-coordinate Euclidean distance is retained for benchmark consistency; these are not kilometers.']
            for bins, g in f['spatial_grid'].items():
                lines.append(f"- {bins}×{bins} bounding-box grid: occupancy {100*g['occupied_fraction']:.2f}%; "
                             f"normalized count entropy {g['normalized_entropy']:.4f}; largest-cell share {100*g['max_cell_share']:.3f}%.")
        if 'covariance_sample' in r:
            p = r['covariance_sample']
            lines.append(f"- Covariance effective rank: {p['covariance_effective_rank']:.3f}; first-PC share: {100*p['pc1_share']:.3f}%.")
        h = r['hubness_sample']
        lines.append(f"- Sample hubness (2,048 objects, k=10, fractional tie handling): incoming-count skewness "
                     f"{fmt(h['skewness'])}; top-1%-object share {100*h['top1pct_share']:.3f}%.")
        s = r['row_order']
        lines.append(f"- Adjacent distance P50/P95/P99: {s['adjacent_distance']['p50']:.6g} / "
                     f"{s['adjacent_distance']['p95']:.6g} / {s['adjacent_distance']['p99']:.6g}.")
        lines.append(f"- Excess-step fraction above the predeclared robust threshold: {fmt(s['excess_step_fraction'],6)}.")
        for key, sig in s['signals'].items():
            original = [w['original']['acf1'] for w in sig['spectral_windows']]
            shuffled = [w['shuffled']['acf1'] for w in sig['spectral_windows']]
            original = [v for v in original if v is not None]
            shuffled = [v for v in shuffled if v is not None]
            lines.append(f"- File-order {key}: median detrended ACF1 {np.median(original):.4f}, "
                         f"shuffled control {np.median(shuffled):.4f}; maximum 5,000-row mean shift "
                         f"{fmt(sig['max_level_shift_in_global_sd'])} global SD.")
        lines.append('')
    lines += ['## Interpretation limits', '',
        '- File-order autocorrelation, jumps, and spectral peaks do not establish temporal periodicity. '
        'No timestamp or verified time axis is present; temporal periodicity and arrival burstiness remain N/A.',
        '- LID is a continuous local-distance estimator. It is omitted for Word; quantization, ties and '
        'duplicates in numeric datasets are retained and invalid estimates are explicitly counted.',
        '- Relative contrast, neighbor expansion, LID and hubness are geometric descriptors, '
        'not measured latency, pruning efficiency, or causal explanations of system performance.',
        '- Duplicate fractions for vectors are sample-only. Full duplicate fractions are available only '
        'for Word and T-loc.',
        '- Deep vectors have almost exactly unit norm (SD about 3.28e-8); norm-series ACF and spectral '
        'diagnostics mainly concern numerical normalization residuals, not semantic vector dynamics.',
        '- T-loc PCA95=1 and local LID near 2 are compatible: the former describes global variance '
        'concentration, while the latter describes sampled local distance growth.',
        '- Inspect the complete per-dataset JSON for distribution quantiles, invalid counts, all three '
        'LID neighborhood sizes, source hashes, and spectral window results.', '',
        '## Provenance', '',
        '| Dataset | Input SHA-256 |', '|---|---|']
    for r in results:
        lines.append(f"| {r['dataset']} | `{r['source']['sha256']}` |")
    (a.out/'RESULTS.md').write_text('\n'.join(lines)+'\n')

    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 8,
                        'axes.spines.top': False, 'axes.spines.right': False,
                        'pdf.fonttype': 42, 'svg.fonttype': 'none'})
    fig, axes = plt.subplots(2, 2, figsize=(7.2, 5.3), layout='constrained')
    configs = [('rc10', 'mean', 'Relative contrast RC10', 'Mean distance / r10'),
               ('lid50', 'p50', 'Local intrinsic dimension', 'Median LID (k = 50)'),
               ('expansion10', 'p50', 'Neighborhood expansion', 'Median r20 / r10')]
    colors = ['#0072B2', '#E69F00', '#009E73', '#CC79A7', '#333333']
    for ax, (key, est, title, ylabel) in zip(axes.ravel(), configs):
        for i, r in enumerate(results):
            if key == 'lid50' and r['kind'] == 'word':
                ax.text(i, 0, 'N/A', ha='center', va='bottom', fontsize=7)
                continue
            v = seed_values(r, key, est)
            ax.plot(np.full(len(v), i)+np.array([-.10, 0, .10]), v, 'o', color=colors[i], markersize=3)
            ax.vlines(i, v.min(), v.max(), color=colors[i], lw=1)
        ax.set_title(title, fontsize=9)
        ax.set_ylabel(ylabel)
        if key == 'rc10':
            ax.set_yscale('log')
            ax.set_ylabel(ylabel+' (log scale)')
        ax.set_xticks(range(5), ['SIFT', 'Deep', 'GIST', 'Word', 'T-loc'])
        ax.set_xlim(-.5, 4.5)
    ax = axes.ravel()[3]
    v = [r['row_order']['adjacent_to_random_median_ratio'] for r in results]
    ax.bar(range(5), v, color='white', edgecolor=colors, hatch='//', linewidth=1)
    ax.axhline(1, color='.6', linewidth=.7)
    for i, z in enumerate(v):
        ax.text(i, z+.035*max(v), f'{z:.3f}', ha='center', fontsize=7)
    ax.set_ylim(0, max(v)*1.22)
    ax.set_title('File-order locality (not time)', fontsize=9)
    ax.set_ylabel('Median adjacent / random distance')
    ax.set_xticks(range(5), ['SIFT', 'Deep', 'GIST', 'Word', 'T-loc'])
    fig.suptitle('Dataset structure differs beyond nominal dimension', fontsize=11)
    for ext in ['png', 'pdf', 'svg']:
        fig.savefig(a.out/f'profile_summary.{ext}', dpi=220, bbox_inches='tight')
    svg = a.out/'profile_summary.svg'
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines())+'\n')
    (a.out/'FIGURE_CAPTION.md').write_text(
        'Sampled neighborhood geometry and file-order locality differ across the five datasets. '
        'Dots show three independently sampled 50,000-reference / 512-query runs; vertical segments '
        'show the observed seed range, not a confidence interval. Word LID is omitted because the '
        'distance is discrete. The last panel uses all adjacent rows versus 20,000 random pairs; '
        'the row order is not a verified time axis. No preprocessing changes the native metric.\n')


if __name__ == '__main__':
    main()
