#!/usr/bin/env python3
"""Render available accepted runs without hiding requested missing datasets."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

NAMES = ['SIFT-1M', 'Deep-1M', 'GIST-1M', 'Word', 'T-loc-1M', 'T-loc-10M',
         'Vector-200K', 'Protein', 'ChEMBL']


def fmt(x, digits=3):
    return 'N/A' if x is None else f'{x:.{digits}f}'


def seed(r, metric, estimator='mean'):
    return np.array([g[metric][estimator] for g in r['geometry_runs']])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--runs', type=Path, nargs='+', required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    results = {}
    for run in a.runs:
        validation = json.loads((run/'VALIDATION.json').read_text())
        for record in validation['datasets']:
            name = record['dataset']
            assert name not in results, 'ambiguous repeated dataset'
            assert record['status'] == 'PASS'
            raw = (run/name/'results.json').read_bytes()
            assert hashlib.sha256(raw).hexdigest() == record['result_sha256']
            results[name] = json.loads(raw)
    assert all(r['contract'] == 'native_metric_v2' for r in results.values())
    a.out.mkdir(parents=True, exist_ok=True)
    lines = ['# Extended dataset comparison', '',
        f'**Coverage: {len(results)}/9 requested datasets measured and validated.**',
        'All neighborhood comparisons use 20,000 sampled references, 512 disjoint uniform base queries, '
        'and three fixed seeds. Distances are exact within the sample, not the full corpus. '
        'The original 50,000-reference experiment remains separate and unchanged.', '',
        '## Matched comparison', '',
        '| Dataset | N | Representation | Distance | Exact zeros (%) | Hoyer mean | LID50* | RC10* |',
        '|---|---:|---|---|---:|---:|---:|---:|']
    for name in NAMES:
        if name not in results:
            lines.append(f'| {name} | — | Source confirmation pending | — | — | — | — | — |')
            continue
        r = results[name]; f = r['full']
        dim = f"{f['length']['min']:.0f}–{f['length']['max']:.0f} chars" if r['kind'] == 'word' else str(f['dimension'])
        sparse = r['kind'] in ['vector', 'binary']
        lid = float(np.median(seed(r, 'lid50', 'p50'))) if 'lid50' in r['geometry_runs'][0] else None
        lines.append(f"| {name} | {f['n']:,} | {dim} | {r['metric']} | "
            f"{fmt(100*f['zero_fraction'],4) if sparse else 'N/A'} | {fmt(f.get('hoyer',{}).get('mean'))} | "
            f"{fmt(lid)} | {np.median(seed(r,'rc10')):.3f} |")
    lines += ['', '*RC10 is the median across seeds of the per-query mean RC10; LID50 is the median '
              'across seeds of the per-query median LID50. Spatial coordinate zeros and string alphabets '
              'are not coordinate sparsity. LID is omitted for discrete strings and binary fingerprints.', '',
              '## Sequence and fingerprint descriptors', '',
              '| Dataset | Mean sequence length | Symbols | Symbol entropy (bits) | Bigram entropy (bits) | Trigram entropy (bits) | Full duplicate fraction (%) |',
              '|---|---:|---:|---:|---:|---:|---:|']
    for name in ['Word', 'Protein']:
        if name not in results: continue
        f = results[name]['full']
        lines.append(f"| {name} | {f['length']['mean']:.3f} | {f['character_vocabulary']} | "
                     f"{f['character_entropy_bits']:.3f} | {f['2gram_entropy_bits']:.3f} | "
                     f"{f['3gram_entropy_bits']:.3f} | {100*f['duplicate_fraction_full']:.5f} |")
    lines += ['', 'Duplicate fraction is 1 − unique-object count / row count: excess copies, '
              'not all rows belonging to a repeated group.']
    if 'ChEMBL' in results:
        f = results['ChEMBL']['full']; bits = f['active_bits']
        lines += ['', f"ChEMBL: mean active bits {bits['mean']:.3f} / {f['dimension']}; "
                  f"P10/P50/P90 = {bits['p10']:.0f}/{bits['p50']:.0f}/{bits['p90']:.0f}. "
                  f"Mean per-bit marginal entropy {f['bit_marginal_entropy_bits']['mean']:.4f} bits; "
                  f"constant bits {f['constant_dimensions']}; empty fingerprints {f['allzero_rows']}; "
                  f"full duplicate-fingerprint fraction {100*f['duplicate_fraction_full']:.5f}%.",
                  'Identical fingerprints do not prove identical molecules. Sequence symbol/gram entropy '
                  'and per-bit marginal entropy describe different representations; neither is temporal entropy.']
    lines += ['',
              '## Order sensitivity, abruptness, and representation dimension', '',
              '| Dataset | Adjacent/random median | Excess steps (%) | PCA95 | Effective rank | Expansion10* | Hub top-1% share (%) |',
              '|---|---:|---:|---:|---:|---:|---:|']
    for name in NAMES:
        if name not in results: continue
        r = results[name]
        o, c, h = r['row_order'], r.get('covariance_sample',{}), r['hubness_sample']
        excess = o['excess_step_fraction']
        bound = (r['full']['length']['max'] if r['metric'] == 'Levenshtein' else
                 1 if r['metric'] == 'Tanimoto' else 180 if r['metric'] == 'Angular-degrees' else None)
        saturated = bound is not None and o['mad_step_threshold'] is not None and o['mad_step_threshold'] >= bound
        lines.append(f"| {name} | {fmt(o['adjacent_to_random_median_ratio'],5)} | "
            f"{fmt(None if excess is None else excess*100,5)}{'†' if saturated else ''} | {c.get('pca95','N/A')} | "
            f"{fmt(c.get('covariance_effective_rank'))} | {np.median(seed(r,'expansion10','p50')):.3f} | {100*h['top1pct_share']:.3f} |")
    lines += ['', 'Adjacent distances cover every neighboring row; the random comparison uses 20,000 '
        'distinct-index pairs. Excess steps exceed median + 6 × 1.4826 × MAD (N/A for zero MAD): '
        'a descriptive heuristic, not an anomaly test. Expansion is median r20/r10. PCA uses 10,000 '
        'stored-coordinate rows, not standardized features. Binary/Angular PCA is a representation '
        'diagnostic, not native-metric intrinsic dimension. Hubness uses 2,048 objects and fractional ties.', '',
        '† The registered robust threshold reaches or exceeds the metric upper bound, so a zero '
        'exceedance rate is uninformative about abruptness, not evidence of smoothness. Thresholds '
        'and quantiles are retained below; no post-hoc threshold replacement is made.', '',
        '| Dataset | Adjacent P50 | Adjacent P95 | Adjacent P99 | Robust threshold |',
        '|---|---:|---:|---:|---:|']
    for name in NAMES:
        if name not in results: continue
        o = results[name]['row_order']; q = o['adjacent_distance']
        lines.append(f"| {name} | {fmt(q['p50'])} | {fmt(q['p95'])} | {fmt(q['p99'])} | {fmt(o['mad_step_threshold'])} |")
    lines += ['', 'Adjacent quantiles use each dataset\'s native distance units, not a common physical '
        'scale. For Protein, distance cannot exceed the longest stored sequence (100); for binary '
        'Tanimoto it cannot exceed 1. These bounds explain their flagged zero exceedance rates.', '',
        '## Sampling sensitivity and native-query workload', '',
        '| Dataset | RC10 seed range | LID50 seed range | Invalid LID50 / 512 by seed | Native queries | Native RC10 mean |',
        '|---|---:|---:|---|---:|---:|']
    for name in NAMES:
        if name not in results: continue
        r = results[name]; v = seed(r, 'rc10')
        lidrange, invalid = 'N/A', 'N/A'
        if 'lid50' in r['geometry_runs'][0]:
            l = seed(r, 'lid50', 'p50'); lidrange = f'{l.min():.3f}–{l.max():.3f}'
            invalid = '/'.join(str(g['lid50']['invalid']) for g in r['geometry_runs'])
        q = r['native_query_profile']
        lines.append(f"| {name} | {v.min():.3f}–{v.max():.3f} | {lidrange} | {invalid} | "
                     f"{q['sampled_queries']} | {q['rc10']['mean']:.3f} |")
    lines += ['', 'Seed ranges are observed sampling sensitivity, not confidence intervals. Native '
              'query comparisons exclude matching base IDs. Vector provides only 100 query IDs and '
              'is not silently expanded to 512. Native workloads need not represent uniform base queries.', '',
              '| Dataset | Zero-nearest queries (%) by seed | Invalid RC10 / 512 by seed |',
              '|---|---|---|']
    for name in NAMES:
        if name not in results: continue
        runs = results[name]['geometry_runs']
        zero = ' / '.join(f"{100*g['zero_nearest_fraction']:.3f}" for g in runs)
        invalid = ' / '.join(str(g['rc10']['invalid']) for g in runs)
        lines.append(f'| {name} | {zero} | {invalid} |')
    lines += ['', 'Zero-distance and invalid-radius cases are retained, not stabilized by an epsilon. '
              'RC summaries use valid queries only.', '',
              '## File-order correlations, not temporal periodicity', '',
              '| Dataset / scalar | Median ACF1 | Shuffled ACF1 | Median dominant-bin power share |',
              '|---|---:|---:|---:|']
    for name in NAMES:
        if name not in results: continue
        r = results[name]
        for key, sig in r['row_order']['signals'].items():
            def med(which, field):
                v = [w[which][field] for w in sig['spectral_windows'] if w[which][field] is not None]
                return float(np.median(v)) if v else None
            lines.append(f"| {name} / {key} | {fmt(med('original','acf1'),4)} | "
                         f"{fmt(med('shuffled','acf1'),4)} | {fmt(med('original','dominant_bin_power_share'),4)} |")
    lines += ['', 'Eight detrended 8,192-row windows per scalar, with fixed shuffled controls. '
              '**Temporal periodicity and arrival burstiness are N/A for every dataset: no timestamp '
              'or verified time axis is supplied.** Deep norm variation is almost entirely numerical '
              'normalization residue and must not be interpreted as semantic dynamics.', '',
              '## Limits and provenance', '',
              '- These describe stored representations and sampled neighborhoods, not index speed or causal pruning efficiency.',
              '- T-loc uses raw-coordinate Euclidean distance, not kilometers. Its grid occupancy depends on the observed bounding box.',
              '- Equal reference count controls sample density budget; it does not emulate the full 1M or 10M search index.',
              '- Vector uses the benchmark angular metric, not 1−cos. Coordinate PCA and Hoyer still describe stored amplitudes.',
              '- Full scans, PCA, hubness, and order summaries for the first five datasets are reused only after input SHA verification; all their 20k-reference geometry and native-query diagnostics are freshly measured.',
              '- Full duplicate rates are available for new text datasets. Original vector duplicate estimates remain the original 50k sample, not full-corpus rates.',
              '- Protein/ChEMBL use the explicitly admitted supplementary-root files when present. '
              'The upstream release and fingerprint generator remain unverified; no similarly named version is substituted.', '',
              '| Dataset | Source role | Input SHA-256 |', '|---|---|---|']
    for name in NAMES:
        if name in results:
            r = results[name]
            lines.append(f"| {name} | {r['source_root_role']} | `{r['source']['sha256']}` |")
    (a.out/'RESULTS.md').write_text('\n'.join(lines)+'\n')

    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':8,'axes.spines.top':False,
                        'axes.spines.right':False,'pdf.fonttype':42,'svg.fonttype':'none'})
    fig, axes = plt.subplots(2, 2, figsize=(8, 6.6), layout='constrained')
    labels = [n.replace('T-loc-', 'T-loc ') for n in NAMES]
    for ax in axes.ravel():
        ax.set_yticks(range(9), labels); ax.set_ylim(8.6, -.6)
        ax.tick_params(axis='y', length=0)
    for i, name in enumerate(NAMES):
        if name not in results:
            for ax in axes.ravel():
                ax.text(.02, i, 'Pending source', transform=ax.get_yaxis_transform(), va='center', color='.5', fontsize=7)
            continue
        r = results[name]
        for ax, key, est in [(axes[0,0], 'rc10','mean'), (axes[0,1],'lid50','p50')]:
            if key not in r['geometry_runs'][0]:
                ax.text(.02, i, 'N/A: discrete', transform=ax.get_yaxis_transform(), va='center', fontsize=7)
                continue
            v = seed(r, key, est)
            ax.hlines(i, v.min(), v.max(), color='#0072B2')
            ax.plot(v, i+np.array([-.12, 0, .12]), 'o', color='#0072B2', ms=3)
        if r['kind'] in ['vector','binary']:
            axes[1,0].barh(i, 100*r['full']['zero_fraction'], facecolor='white', edgecolor='#0072B2', hatch='//', height=.55)
        else:
            axes[1,0].text(.02, i, 'N/A', transform=axes[1,0].get_yaxis_transform(), va='center', fontsize=7)
        ratio = r['row_order']['adjacent_to_random_median_ratio']
        axes[1,1].plot(ratio, i, 'o', ms=4, color='#0072B2')
    axes[0,0].set(xscale='log', xlabel='Mean distance / r10 (log)', title='Matched-sample relative contrast')
    axes[0,1].set(xlabel='Median LID50', title='Continuous local dimension')
    axes[0,1].set_xlim(left=0)
    axes[1,0].set(xlabel='Exactly zero coordinates (%)', title='Representation sparsity')
    sparsities = [(i, 100*results[n]['full']['zero_fraction']) for i, n in enumerate(NAMES)
                  if n in results and results[n]['kind'] in ['vector','binary']]
    limit = max(1, min(100, max(v for _, v in sparsities)*1.3))
    axes[1,0].set_xlim(0, limit)
    for i, value in sparsities:
        inside = value > .83*limit
        axes[1,0].text(value+(-.02 if inside else .02)*limit, i, f'{value:.4f}%',
                       va='center', ha='right' if inside else 'left', fontsize=7,
                       bbox=dict(facecolor='white', edgecolor='none', pad=.5))
    axes[1,1].set(xscale='log', xlabel='Median adjacent / random distance (log)', title='File-order locality, not time')
    axes[1,1].axvline(1, color='.65', lw=.7)
    fig.suptitle(f'Extended native-metric comparison ({len(results)} of 9 datasets)', fontsize=11)
    for ext in ['png','pdf','svg']:
        fig.savefig(a.out/f'extended_summary.{ext}', dpi=300, bbox_inches='tight')
    svg = a.out/'extended_summary.svg'
    svg.write_text('\n'.join(x.rstrip() for x in svg.read_text().splitlines())+'\n')
    (a.out/'FIGURE_CAPTION.md').write_text('Stored sparsity, matched sampled geometry, and file-order locality '
        'differ across the measured datasets. Geometry dots show three independent 20,000-reference / '
        '512-query runs; segments show the observed seed range, not a confidence interval. RC10 averages '
        'exclude undefined zero-r10 cases; see the per-seed invalid counts in the results table. Discrete LID '
        'and nonnumeric coordinate sparsity are N/A. Any pending row has no measurements. The last panel '
        'uses all adjacent rows versus 20,000 random pairs and does not establish time-series periodicity.\n')


if __name__ == '__main__':
    main()
