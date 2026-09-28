#!/usr/bin/env python3
"""Run one clean full-output gate on an admitted idle physical GPU."""
import argparse
import json
from pathlib import Path
import subprocess
import time


ROOT = Path('/home/data/wangxuran/tmp/gts_20260922_cpu_io/leaf_early_l2_20260924')
GPUS = ('2', '3', '4', '6', '7')  # root-owned advisory lock files


def idle(gpu):
    output = subprocess.check_output(
        ['nvidia-smi', '-i', gpu, '--query-compute-apps=pid', '--format=csv,noheader'],
        text=True)
    return not output.strip()


def main(max_wait):
    deadline = time.monotonic() + max_wait
    while True:
        for gpu in GPUS:
            if not idle(gpu):
                continue
            print('ADMIT', gpu, flush=True)
            for dataset in ('GIST', 'Deep'):
                base = ROOT/'data'/dataset/'1000000'
                radius = json.loads((base/'fixtures/oracle.json').read_text())['radii']['normal']
                for mode in ('Q', 'H', 'J'):
                    label = f'full_normal_{mode}'
                    print('START', gpu, dataset, mode, flush=True)
                    cmd = ['python3', str(ROOT/'run.py'), str(base), '--gpu', gpu,
                           '--label', label, '--mode', mode, '--radius', str(radius),
                           '--repeats', '1', '--warmup', '0', '--dump']
                    if subprocess.run(cmd).returncode:
                        print('STOP: admission, foreign activity or validation failed', flush=True)
                        return 1
                    print('DONE', gpu, dataset, mode, flush=True)
            (ROOT/'logs/full_gate_complete.json').write_text(
                json.dumps({'gpu':gpu,'datasets':['GIST','Deep'],'modes':['Q','H','J']})+'\n')
            return 0
        if time.monotonic() >= deadline:
            print('STOP: no idle GPU before deadline', flush=True)
            return 2
        time.sleep(20)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--max-wait', type=int, default=600)
    a = p.parse_args()
    raise SystemExit(main(a.max_wait))
