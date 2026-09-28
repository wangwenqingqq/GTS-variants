#!/usr/bin/env python3
"""Same-binary paired complete-query timings of Q, B16, and B32."""
import json
import subprocess
from pathlib import Path

ROOT = Path('/home/ls/tmp/gts_parent_mask_20260925')
RADIUS = {'GIST': 1.411250114440918, 'Deep': 1.0798368453979492}
ORDERS = (('Q', 'B16', 'B32'), ('B32', 'Q', 'B16'),
          ('B16', 'B32', 'Q'), ('Q', 'B32', 'B16'))


def main():
    for dataset in ('GIST', 'Deep'):
        for mode in ('Q', 'B16', 'B32'):
            path = ROOT / 'data' / dataset / '1000000' / 'runs' / f'{dataset.lower()}_{mode}_gate' / 'receipt.json'
            receipt = json.loads(path.read_text())
            assert receipt['validation']['pass'] and receipt['exit_code'] == 0
    records = []
    for round_id, modes in enumerate(ORDERS):
        datasets = ('GIST', 'Deep') if round_id % 2 == 0 else ('Deep', 'GIST')
        for dataset in datasets:
            data_root = ROOT / 'data' / dataset / '1000000'
            for mode in modes:
                label = f'timing_{round_id}_{mode}'
                cmd = ['python3', str(ROOT / 'run.py'), str(data_root),
                       '--gpu', '0', '--label', label, '--mode', mode,
                       '--radius', str(RADIUS[dataset]), '--warmup', '8',
                       '--repeats', '1']
                print('START', round_id, dataset, mode, flush=True)
                with (ROOT / 'logs' / 'timing_runner.log').open('a') as log:
                    subprocess.run(cmd, cwd=ROOT, check=True, stdout=log)
                receipt_path = data_root / 'runs' / label / 'receipt.json'
                receipt = json.loads(receipt_path.read_text())
                assert receipt['validation']['pass'] and receipt['stop_reason'] is None
                records.append({'round': round_id, 'dataset': dataset,
                                'mode': mode, 'receipt': str(receipt_path)})
                (ROOT / 'logs' / 'timing_progress.json').write_text(json.dumps(records, indent=2) + '\n')
                print('DONE', round_id, dataset, mode, flush=True)
    (ROOT / 'logs' / 'timing_COMPLETE.json').write_text(
        json.dumps({'orders': ORDERS, 'runs': records}, indent=2) + '\n')


if __name__ == '__main__':
    main()
