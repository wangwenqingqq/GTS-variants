#!/usr/bin/env python3
"""Three interleaved same-binary rounds of six parent group sizes."""
import json
import subprocess
from pathlib import Path

ROOT = Path('/home/ls/tmp/gts_parent_mask_scale_20260925')
RADIUS = {'GIST': 1.411250114440918, 'Deep': 1.0798368453979492}
MODES = ('B16', 'B32', 'B64', 'B128', 'B256', 'B512')
ORDERS = (MODES, tuple(reversed(MODES)),
          ('B64', 'B16', 'B256', 'B32', 'B512', 'B128'))


def main():
    for dataset in ('GIST', 'Deep'):
        for mode in MODES[2:]:
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
