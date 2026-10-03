#!/usr/bin/env python3
"""Run the declared exhaustive control after, not inside, the frozen campaign."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
RUNNER = ROOT/'delivery/run_locked.py' if (ROOT/'delivery/run_locked.py').is_file() else ROOT/'run_locked.py'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--python', required=True)
    p.add_argument('--data-root', required=True, type=Path)
    p.add_argument('--gpu', required=True)
    a = p.parse_args()
    assert 'FORMAL COMPLETE' in (ROOT/'formal_console.log').read_text()
    declaration = json.loads((ROOT/'EXHAUSTIVE_CONTROL.json').read_text())
    assert declaration['nlist'] == declaration['nprobe'] == 1024
    configs = [{'K': k, 'B': b, 'nlist': 1024, 'nprobe': 1024}
               for k in (8, 32) for b in (1, 32)]
    for r in range(1, 7):
        for dataset in (('GIST', 'Deep') if r % 2 else ('Deep', 'GIST')):
            path = ROOT/f'control_r{r}_{dataset}_configs.json'
            path.write_text(json.dumps(configs if r % 2 else configs[::-1])+'\n')
            label = f'control_r{r}_ivf_{dataset}'
            subprocess.run([sys.executable, RUNNER, '--gpu', a.gpu,
                            '--output', ROOT/'runs'/label, '--', a.python, ROOT/'verify_outputs.py',
                            'faiss', '--data', a.data_root/dataset/'1000000/fixtures/data.f32bin',
                            '--qids', ROOT/'fixtures'/f'{dataset}_final256.qid',
                            '--reference', ROOT/f'oracle_{dataset}_final256.json',
                            '--configs', path, '--out', ROOT/f'{label}.json'], check=True)
    print('EXHAUSTIVE CONTROL COMPLETE', flush=True)


if __name__ == '__main__':
    main()
