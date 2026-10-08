#!/usr/bin/env python3
"""Record the actual structural executable and sanitizer receipts for admission."""
import argparse
from pathlib import Path
import subprocess
import sys

import run_region as r


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dest', type=Path, required=True)
    p.add_argument('--raw', type=Path, required=True)
    p.add_argument('--gpu', required=True)
    a = p.parse_args()
    manifest = a.dest / 'STRUCTURAL.json'
    assert not manifest.exists(), 'retain prior structural qualification'
    binary = a.dest / 'native_timed/test_region'
    assert r.sha(binary) == r.read(a.dest / 'SOURCE.json')['structural_binary_sha256']
    rows = []
    for tool in (None, 'memcheck', 'racecheck', 'synccheck'):
        target = a.dest / 'runs' / ('structural_' + str(tool))
        cmd = [str(binary)]
        if tool:
            cmd = ['/usr/local/cuda/bin/compute-sanitizer', '--tool', tool, '--error-exitcode', '77', *cmd]
        subprocess.run([sys.executable, str(a.raw / 'run_locked.py'), '--gpu', a.gpu,
                        '--output', str(target), '--timeout-seconds', '1200', '--', *cmd],
                       check=True, stdout=subprocess.DEVNULL)
        assert r.read(target / 'receipt.json')['runtime_valid']
        text = (target / 'stdout.log').read_text() + (target / 'stderr.log').read_text()
        assert 'STRUCTURAL_PASS: 9 topologies x6 states x2 modes' in text
        if tool:
            assert ('RACECHECK SUMMARY: 0 hazards displayed (0 errors, 0 warnings)'
                    if tool == 'racecheck' else 'ERROR SUMMARY: 0 errors') in text
        rows.append(dict(tool=tool, passed=True, stdout_sha256=r.sha(target / 'stdout.log'),
                         stderr_sha256=r.sha(target / 'stderr.log'), receipt_sha256=r.sha(target / 'receipt.json')))
        r.save(manifest, dict(passed=len(rows) == 4, tests=rows, topologies=9, states=6, modes=2))
        print(tool, 'STRUCTURAL PASS', flush=True)


if __name__ == '__main__':
    main()
