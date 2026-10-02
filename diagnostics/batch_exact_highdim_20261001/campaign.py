#!/usr/bin/env python3
"""Audit and time the frozen GIST normal-radius P1 matrix."""
import argparse
import csv
import filecmp
import hashlib
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path('/home/data/wangxuran/tmp/gts_batch_exact_highdim_20261001')
OLD = Path('/home/data/wangxuran/tmp/gts_arithmetic_path_boundary_20260928')
GPU = 'GPU-e5a0e7f5-9917-c2a1-ee8e-7282cbba2603'
DATA = OLD / 'data/GIST/1000000/fixtures/data.f32bin'
IDLIST = OLD / 'reference_v2/GIST_idlist.i32'
ORACLE = OLD / 'data/GIST/1000000/runs/batch_final1024_FR_normal_20261001/result.bin'
ORACLE_CSV = OLD / 'data/GIST/1000000/runs/batch_final1024_FR_normal_20261001/result.csv'
MODES = ('SEQ_L', 'GRID_L', 'TILE_L', 'SEQ_E', 'GRID_E', 'TILE_E')
BATCHES = (1, 8, 32, 128)


def rows(path):
    with path.open() as f:
        return list(csv.DictReader(f))


def reference():
    expected = [(int(r['qid']), int(r['count']), int(r['ordered_hash']))
                for r in rows(ORACLE_CSV)]
    assert len(expected) == 1024
    return expected


def run(label, mode, batch, reverse=False, dump=False):
    out = ROOT / 'runs' / label
    cmd = [sys.executable, str(ROOT/'run_batch.py'),
           str(ROOT/'bin/batch_bench_v2'), str(DATA), str(IDLIST),
           str(ROOT/'fixtures/GIST_final1024.qid'),
           str(ROOT/'fixtures/GIST_dev256.qid'), mode, '0x3fb4a3d8',
           str(batch), '2', str(out), '--gpu', GPU]
    if reverse:
        cmd.append('--reverse')
    if dump:
        cmd.append('--dump')
    subprocess.run(cmd, check=True)
    receipt = json.loads((out/'receipt.json').read_text())
    assert receipt['runtime_valid'] and receipt['mode'] == mode
    assert receipt['batch'] == batch and receipt['tile'] == 2
    return out


def verify(out, batch, expected):
    found = rows(out/'result_queries.csv')
    assert len(found) == len(expected)
    found.sort(key=lambda r: int(r['query_index']))
    assert [(int(r['qid']), int(r['count']), int(r['ordered_hash']))
            for r in found] == expected, out
    batches = rows(out/'result.csv')
    assert len(batches) == len(expected)//batch
    by_batch = {int(r['batch_id']): r for r in batches}
    assert set(by_batch) == set(range(len(batches)))
    for i, r in by_batch.items():
        count = sum(e[1] for e in expected[i*batch:(i+1)*batch])
        assert int(r['result_count_total']) == count
        assert int(r['d2h_bytes']) == 8*(batch+1)+8*count
        assert float(r['host_ms']) > 0 and float(r['gpu_ms']) > 0
    return sum(float(r['host_ms']) for r in batches)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('phase', choices=('audit', 'formal'))
    a = p.parse_args()
    expected = reference()
    if a.phase == 'audit':
        assert ORACLE.exists()
        oracle_sha = hashlib.sha256(ORACLE.read_bytes()).hexdigest()
        for batch in BATCHES:
            modes = ('SEQ_L', 'SEQ_E') if batch == 1 else MODES
            for mode in modes:
                label = f'audit_gist_normal_b{batch}_{mode}'
                out = run(label, mode, batch, dump=True)
                verify(out, batch, expected)
                result = out/'result.bin'
                assert filecmp.cmp(ORACLE, result, shallow=False), label
                assert hashlib.sha256(result.read_bytes()).hexdigest() == oracle_sha
                (out/'output.sha256').write_text(oracle_sha+'\n')
                result.unlink()
                print('AUDIT PASS', batch, mode, flush=True)
        return
    for round_no in range(1, 7):
        sizes = BATCHES[(round_no-1)%4:]+BATCHES[:(round_no-1)%4]
        for batch in sizes:
            base = ('SEQ_L', 'SEQ_E') if batch == 1 else MODES
            modes = base[(round_no-1)%len(base):]+base[:(round_no-1)%len(base)]
            for mode in modes:
                label = f'formal_gist_normal_r{round_no}_b{batch}_{mode}'
                out = run(label, mode, batch, reverse=round_no%2==0)
                total = verify(out, batch, expected)
                print('FORMAL PASS', round_no, batch, mode, round(total, 3), flush=True)


if __name__ == '__main__':
    main()
