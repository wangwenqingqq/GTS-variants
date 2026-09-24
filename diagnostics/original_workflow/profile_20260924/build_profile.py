#!/usr/bin/env python3
"""Compile a verified source variant and retain the compiler exit code and hashes."""
import argparse
import json
import os
import subprocess
import time
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from prepare import sha


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('root', type=Path)
    p.add_argument('--variant', choices=['rnum_reset', 'profile'], required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--nvcc', default='/usr/local/cuda-13.1/bin/nvcc')
    a = p.parse_args()
    root = a.root.resolve()
    assert Path(a.output).name == a.output
    source = root/'variants'/a.variant
    record = json.loads((source/'VARIANT.json').read_text())
    for name, h in record['source_sha256'].items():
        assert sha(source/name) == h, name
    binary = root/'bin'/a.output
    assert not binary.exists()
    log = root/'logs'/(a.output+'.build.log')
    cmd = [a.nvcc, '-std=c++17', '-O3', '-arch=sm_120', '-rdc=true', '-lineinfo',
           '-Xptxas=-v', '-Xnvlink=--ignore-host-info', '-I'+str(source/'include'),
           str(source/'src/main.cu'), '-o', str(binary)]
    if a.variant == 'profile':
        cmd += ['-DGTS_DIAG_NVTX', '-I/opt/nvidia/nsight-systems/2025.5.2/target-linux-x64/nvtx/include', '-ldl']
    tmp = root/'compiler_tmp'
    tmp.mkdir(exist_ok=True)
    start = time.time()
    with log.open('x') as f:
        result = subprocess.run(['nice', '-n', '10', *cmd], stdout=f, stderr=subprocess.STDOUT,
                                env={**os.environ, 'TMPDIR': str(tmp)}, timeout=240)
    receipt = {'variant': a.variant, 'command': cmd, 'exit_code': result.returncode,
               'source_sha256': record['source_sha256'], 'start': start,
               'elapsed_s': time.time()-start, 'log_sha256': sha(log),
               'binary_sha256': sha(binary) if binary.exists() else None,
               'compiler': subprocess.check_output([a.nvcc, '--version'], text=True),
               'scope': 'Compilation only; no GPU execution'}
    (root/'logs'/(a.output+'.build.json')).write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps(receipt), flush=True)
    raise SystemExit(result.returncode)


if __name__ == '__main__':
    main()
