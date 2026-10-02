#!/usr/bin/env python3
"""Six independent-process P6 final rounds with frozen configurations."""
import csv
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
P5 = Path('/home/data/wangxuran/tmp/gts_p5_external_mask_20261002')
GPU = 'GPU-e5a0e7f5-9917-c2a1-ee8e-7282cbba2603'


def run(label, command):
    folder = ROOT / 'runs' / label
    if not folder.exists():
        subprocess.run([sys.executable, str(P5 / 'run_p4.py'), '--gpu', GPU,
                        '--output', str(folder), '--', *map(str, command)],
                       check=True, stdout=subprocess.DEVNULL)
    receipt = json.loads((folder / 'receipt.json').read_text())
    assert receipt['runtime_valid'], label
    return json.loads((folder / 'stdout.log').read_text())


def write_csv(path, rows):
    if not rows:
        return
    with path.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(dict.fromkeys(k for row in rows for k in row)))
        writer.writeheader()
        writer.writerows(rows)


def main():
    frozen = json.loads((ROOT / 'FROZEN_CONFIG.json').read_text())['configs']
    results = []
    for round_no in range(1, 7):
        config_order = frozen[(round_no-1) % len(frozen):] + frozen[:(round_no-1) % len(frozen)]
        datasets = ('GIST', 'Deep') if round_no % 2 else ('Deep', 'GIST')
        for dataset in datasets:
            for config in config_order:
                method = 'cagra' if config['method'].startswith('CAGRA') else 'faiss'
                suffix = f"{method}_{dataset.lower()}_k{config['k']}"
                if method == 'faiss':
                    suffix += f"_n{config['nlist']}_p{config['nprobe']}"
                label = f'final_p6_r{round_no}_{suffix}'
                python = (P5 / 'venv/bin/python' if method == 'cagra' else
                          ROOT / 'faiss_source_venv/bin/python')
                command = [python, ROOT / 'ann_final.py', '--method', method,
                           '--dataset', dataset, '--k', config['k'], '--round', round_no]
                if method == 'faiss':
                    command += ['--nlist', config['nlist'], '--nprobe', config['nprobe']]
                payload = run(label, command)
                results.append({'label': label, 'config': config['name'], **payload})
                print('PASS', label, [(x['radius'], x['B'], round(x['host_ready_ms'], 2))
                                      for x in payload['timing'] if x['mode']=='common_refined'],
                      flush=True)
                (ROOT / 'final_raw.json').write_text(json.dumps(results, indent=2) + '\n')
    native, refined, quality, builds = [], [], [], []
    for record in results:
        common = {'phase': 'final', 'label': record['label'], 'config': record['config']}
        builds.append({**common, **record['build']})
        for row in record['timing']:
            (refined if row['mode']=='common_refined' else native).append({**common, **row})
        for row in record['quality']:
            quality.append({**common, **row})
    for name, rows in (('final_native_latency.csv', native),
                       ('final_refined_latency.csv', refined),
                       ('final_range_quality.csv', quality),
                       ('final_BUILD_COST.csv', builds)):
        write_csv(ROOT / name, rows)


if __name__ == '__main__':
    main()
