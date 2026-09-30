#!/usr/bin/env python3
"""Run the frozen GIST correctness gate and six paired timing rounds."""
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path('/home/data/wangxuran/tmp/gts_gist_rootcause_20260929/data/GIST/1000000')
OLD = Path('/home/data/wangxuran/tmp/gts_arithmetic_path_boundary_20260928')
GPU = 'GPU-e5a0e7f5-9917-c2a1-ee8e-7282cbba2603'
RADII = {'normal': ('0x3fb4a3d8', 1.411250114440918),
         'half': ('0x3f34a3d8', 0.705625057220459),
         'all': ('0x41cb7260', 25.43084716796875)}
MODES = ('B', 'L', 'E64', 'L_E64')


def completed(label):
    path = ROOT / 'runs' / label
    if not path.exists():
        return False
    receipt = json.loads((path / 'receipt.json').read_text())
    assert receipt['exit_code'] == 0 and not receipt['stop_reason']
    assert receipt['post_gpu_clear'] and not receipt['runtime_errors']
    assert len(list(csv.DictReader((path / 'result.csv').open()))) == 64
    return True


def run(label, mode, radius, dump):
    if completed(label):
        return
    args = [sys.executable, str(ROOT.parent.parent.parent / 'run.py'), str(ROOT),
            '--gpu', GPU, '--label', label, '--mode', mode, '--radius', str(radius),
            '--repeats', '1', '--warmup', '8', '--tool', 'clean',
            '--qfile', 'final_v3.qid', '--binary', 'graph_bench_rootcause']
    if dump:
        args.append('--dump')
    subprocess.run(args, check=True)
    assert completed(label)


def rows(label):
    with (ROOT / 'runs' / label / 'result.csv').open() as f:
        return list(csv.DictReader(f))


def audit(kind, mode, bits):
    label = f'audit_{kind}_{mode}'
    result = ROOT / 'runs' / label
    report = result / 'audit.json'
    if not report.exists():
        subprocess.run([sys.executable, str(OLD / 'audit_strict_run.py'),
                        str(OLD / 'reference_v3/GIST_final.sq64'),
                        str(OLD / 'reference_v2/GIST_idlist.i32'),
                        str(result / 'result.bin'), bits, str(report)], check=True)
    x = json.loads(report.read_text())
    assert x['pass'] and len(x['queries']) == 64 and x['radius_bits'] == bits
    expected = rows(label)
    assert all(int(r['count']) == a['count'] and
               int(r['qid']) == a['query_id'] for r, a in zip(expected, x['queries']))
    return hashlib.sha256((result / 'result.bin').read_bytes()).hexdigest()


def main():
    audits = {}
    for kind, (bits, radius) in RADII.items():
        for mode in MODES:
            label = f'audit_{kind}_{mode}'
            run(label, mode, radius, True)
            audits[kind, mode] = audit(kind, mode, bits)
            assert audits[kind, mode] == audits[kind, 'B'], (kind, mode)
            print('AUDITED', kind, mode, audits[kind, mode], flush=True)

    for kind, (_, radius) in RADII.items():
        for round_no in range(1, 7):
            order = MODES if round_no % 2 else MODES[::-1]
            for mode in order:
                label = f'time_{kind}_r{round_no}_{mode}'
                run(label, mode, radius, False)
                reference = rows(f'audit_{kind}_{mode}')
                timed = rows(label)
                assert [(r['qid'], r['count'], r['ordered_hash']) for r in timed] == [
                    (r['qid'], r['count'], r['ordered_hash']) for r in reference]
                print('TIMED', kind, round_no, mode, flush=True)
    print('CAMPAIGN PASS', flush=True)


if __name__ == '__main__':
    main()
