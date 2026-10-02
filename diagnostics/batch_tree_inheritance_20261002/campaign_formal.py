#!/usr/bin/env python3
"""Run the frozen GIST P4 matrix with a full-output audit and paired rounds."""
import argparse
import csv
import filecmp
import hashlib
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parent
GPU = 'GPU-e5a0e7f5-9917-c2a1-ee8e-7282cbba2603'
OLD = Path('/home/data/wangxuran/tmp/gts_arithmetic_path_boundary_20260928')
P0 = Path('/home/data/wangxuran/tmp/gts_batch_exact_highdim_20261001')
DATA = OLD/'data/GIST/1000000/fixtures/data.f32bin'
IDLIST = OLD/'reference_v2/GIST_idlist.i32'
INDEX = OLD/'replay/GIST_index.bin'
QID = ROOT/'fixtures/GIST_final1024.qid'
WARMUP = P0/'fixtures/GIST_dev256.qid'
MODES = ('SCAN_L', 'C_ID_L', 'C_MASK_L', 'C_TASK_L',
         'SCAN_E', 'C_ID_E', 'C_MASK_E', 'C_TASK_E')
RADII = {'half': '0x3f34a3d8', 'normal': '0x3fb4a3d8', 'all': '0x41cb7260'}


def rows(path):
    with path.open() as stream:
        return list(csv.DictReader(stream))


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(4*1024*1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('audit', 'formal'))
    parser.add_argument('radius', choices=RADII)
    args = parser.parse_args()
    oracle = ROOT/'runs'/f'oracle_gist_{args.radius}_final1024'
    expected = [(int(r['qid']), int(r['count']), int(r['ordered_hash']))
                for r in rows(oracle/'result.csv')]
    assert len(expected) == 1024
    oracle_bin = oracle/'result.bin'
    if args.phase == 'audit':
        oracle_hash = (sha256(oracle_bin) if oracle_bin.exists()
                       else (oracle/'output.sha256').read_text().strip())
    sizes = (8, 32) if args.radius == 'half' else (32,)
    rounds = (0,) if args.phase == 'audit' else range(1, 7)
    for round_no in rounds:
        batches = sizes[round_no % len(sizes):]+sizes[:round_no % len(sizes)]
        for batch in batches:
            modes = MODES[round_no % len(MODES):]+MODES[:round_no % len(MODES)]
            for mode in modes:
                label = f'final_{args.phase}_gist_{args.radius}_r{round_no}_b{batch}_{mode}'
                out = ROOT/'runs'/label
                if not out.exists():
                    command = [sys.executable, str(ROOT/'run_p4.py'), '--gpu', GPU,
                               '--output', str(out), '--', str(ROOT/'bin/p4_bench_v3'),
                               str(DATA), str(IDLIST), str(QID), str(WARMUP), mode,
                               RADII[args.radius], str(batch), '2',
                               str(int(round_no % 2 == 0 and round_no > 0)),
                               str(out/'result'), str(int(args.phase == 'audit')),
                               str(INDEX), '4']
                    subprocess.run(command, check=True, stdout=subprocess.DEVNULL)
                receipt = json.loads((out/'receipt.json').read_text())
                assert receipt['runtime_valid'], label
                got = rows(out/'result_queries.csv')
                got.sort(key=lambda r: int(r['query_index']))
                assert [(int(r['qid']), int(r['count']), int(r['ordered_hash']))
                        for r in got] == expected, label
                batches_csv = rows(out/'result.csv')
                assert len(batches_csv) == 1024//batch
                by_batch = {int(r['batch_id']): r for r in batches_csv}
                assert set(by_batch) == set(range(1024//batch))
                for i, row in by_batch.items():
                    count = sum(e[1] for e in expected[i*batch:(i+1)*batch])
                    assert int(row['result_count_total']) == count, label
                    assert int(row['d2h_bytes']) == (batch+1)*8+count*8, label
                    assert float(row['host_ms']) > 0 and float(row['gpu_ms']) > 0
                if args.phase == 'audit':
                    if oracle_bin.exists():
                        assert filecmp.cmp(out/'result.bin', oracle_bin, shallow=False), label
                    else:
                        assert sha256(out/'result.bin') == oracle_hash, label
                    (out/'output.sha256').write_text(oracle_hash+'\n')
                    (out/'result.bin').unlink()
                host = sum(float(row['host_ms']) for row in batches_csv)
                print('PASS', args.phase, args.radius, round_no, batch, mode,
                      round(host, 3), flush=True)


if __name__ == '__main__':
    main()
