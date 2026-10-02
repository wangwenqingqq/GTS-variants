#!/usr/bin/env python3
"""P5 G1/G2 development runs; output includes complete GPU admission receipts."""
import csv
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
P4 = Path('/home/data/wangxuran/tmp/gts_p4_tree_batch_20261002')
P0 = Path('/home/data/wangxuran/tmp/gts_batch_exact_highdim_20261001')
BASE = Path('/home/data/wangxuran/tmp/gts_arithmetic_path_boundary_20260928')
GPU = 'GPU-e5a0e7f5-9917-c2a1-ee8e-7282cbba2603'
DATA = BASE/'data/GIST/1000000/fixtures/data.f32bin'
ORDER = BASE/'reference_v2/GIST_idlist.i32'
QIDS = P0/'fixtures/GIST_dev256.qid'
INDEX = BASE/'replay/GIST_index.bin'
REF = P4/'runs/scan_e_dev256_b8/result.bin'
REF_NORMAL = ROOT/'runs/g2_normal_reference/result.bin'
MODES = {
    'G1': ('SCAN_L', 'SCAN_E', 'C_MASK_E', 'LIB64_U', 'LIB32_U'),
    'G2': ('SCAN_E', 'MASK_ALL_E', 'TREE_ALL_E', 'TREE_REAL_E'),
}
RADII = {'half': '0x3f34a3d8', 'normal': '0x3fb4a3d8'}


def run(phase):
    entries = []
    for round_no in range(1, 4):
        for radius in (('half',) if phase == 'G1' else ('half', 'normal')):
            modes = MODES[phase]
            modes = modes[(round_no - 1) % len(modes):] + modes[:(round_no - 1) % len(modes)]
            if radius == 'normal':
                modes = modes[::-1]
            for mode in modes:
                label = f'{phase.lower()}_r{round_no}_{radius}_b32_{mode}_v2'
                folder = ROOT/'runs'/label
                binary = (ROOT/'p5_external' if mode.startswith('LIB') else
                          ROOT/'p5_causal' if phase == 'G2' else P4/'bin/p4_bench_v3')
                cmd = [sys.executable, str(ROOT/'run_p4.py'), '--gpu', GPU,
                       '--output', str(folder), '--', str(binary), str(DATA),
                       str(ORDER), str(QIDS), str(QIDS), mode, RADII[radius],
                       '32', '2', str(round_no % 2), str(folder/'result'),
                       str(int(mode.startswith('LIB') or phase == 'G2')),]
                if not mode.startswith('LIB'):
                    cmd += [str(INDEX), '4']
                subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, env=os.environ)
                receipt = json.loads((folder/'receipt.json').read_text())
                assert receipt['runtime_valid']
                rows = list(csv.DictReader((folder/'result.csv').open()))
                assert len(rows) == 8
                counts = [int(r['result_count_total']) for r in rows]
                total_ms = sum(float(r['host_ms']) for r in rows)
                gpu_ms = sum(float(r['gpu_ms']) for r in rows)
                qual = 'BITWISE_MATCH_ON_TESTED'
                if mode.startswith('LIB') or phase == 'G2':
                    result = subprocess.check_output([sys.executable, str(ROOT/'compare_outputs.py'),
                                                      str(REF if radius == 'half' else REF_NORMAL),
                                                      str(folder/'result.bin')], text=True)
                    (folder/'qualification.json').write_text(result)
                    qual = json.loads(result)['qualification']
                    (folder/'result.bin').unlink()
                entries.append((phase, round_no, radius, 32, mode, total_ms, gpu_ms,
                                sum(counts), qual, receipt['binary_sha256']))
                print('PASS', label, round(total_ms, 3), qual, flush=True)
    with (ROOT/f'{phase.lower()}_dev.csv').open('w') as f:
        writer = csv.writer(f)
        writer.writerow(('phase','round','radius','B','mode','host_total_ms','gpu_total_ms',
                         'hits','qualification','binary_sha256'))
        writer.writerows(entries)


if __name__ == '__main__':
    if len(sys.argv) != 2 or sys.argv[1] not in MODES:
        raise SystemExit('usage: campaign_dev.py G1|G2')
    run(sys.argv[1])
