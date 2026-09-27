#!/usr/bin/env python3
"""Correctness preflight for the four new block sizes."""
import json
import subprocess
from pathlib import Path

ROOT = Path('/home/ls/tmp/gts_parent_mask_scale_20260925')
RADIUS = {'GIST': 1.411250114440918, 'Deep': 1.0798368453979492}


def main():
    for dataset in ('Deep', 'GIST'):
        data_root = ROOT / 'data' / dataset / '1000000'
        for group in (64, 128, 256, 512):
            label = f'{dataset.lower()}_B{group}_gate'
            cmd = ['python3', str(ROOT / 'run.py'), str(data_root),
                   '--gpu', '0', '--label', label, '--mode', f'B{group}',
                   '--radius', str(RADIUS[dataset]), '--warmup', '2',
                   '--repeats', '1']
            print('START', dataset, group, flush=True)
            with (ROOT / 'logs' / 'gate_runner.log').open('a') as log:
                subprocess.run(cmd, cwd=ROOT, check=True, stdout=log)
            receipt = json.loads((data_root / 'runs' / label / 'receipt.json').read_text())
            assert receipt['validation']['pass'] and receipt['stop_reason'] is None
            print('DONE', dataset, group, flush=True)


if __name__ == '__main__':
    main()
