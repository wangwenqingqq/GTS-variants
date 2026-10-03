#!/usr/bin/env python3
"""Regenerate the exact small ragged/tie qualification fixtures; never overwrite."""
import json
from pathlib import Path
import struct

import numpy as np

ROOT = Path(__file__).resolve().parent


def write_checked(path, data):
    if path.exists():
        assert path.read_bytes() == data, f'Existing fixture differs: {path.name}'
    else:
        with path.open('xb') as f: f.write(data)


def main():
    for d in (96, 960):
        x = np.random.default_rng(2026100300+d).integers(0, 256, size=(4097, d)).astype('<f4')
        x[:9] = x[0]
        write_checked(ROOT/f'synthetic_{d}.f32bin', struct.pack('<iii', d, len(x), 2)+x.tobytes())
    (ROOT/'fixtures').mkdir(exist_ok=True)
    ids = [0, 1, 8, 9, *range(123, 152)]
    write_checked(ROOT/'fixtures/synthetic_ragged33.qid', ('33\n'+''.join(f'{i}\n' for i in ids)).encode())
    configs = [{'K': k, 'B': b, 'nlist': 32, 'nprobe': 32} for k in (8, 32) for b in (1, 32)]
    write_checked(ROOT/'synthetic_configs.json', json.dumps(configs).encode())


if __name__ == '__main__':
    main()
