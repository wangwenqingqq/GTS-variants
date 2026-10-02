#!/usr/bin/env python3
"""P6 fresh-query exact full-range controls using frozen P5 executables."""
import csv
import filecmp
import json
import math
import os
from pathlib import Path
import statistics
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
P5 = Path('/home/data/wangxuran/tmp/gts_p5_external_mask_20261002')
P4 = Path('/home/data/wangxuran/tmp/gts_p4_tree_batch_20261002')
P0 = Path('/home/data/wangxuran/tmp/gts_batch_exact_highdim_20261001')
BASE = Path('/home/data/wangxuran/tmp/gts_arithmetic_path_boundary_20260928')
GPU = 'GPU-e5a0e7f5-9917-c2a1-ee8e-7282cbba2603'
LIBDIR = P5 / 'venv/lib/python3.12/site-packages'
os.environ['LD_LIBRARY_PATH'] = ':'.join((str(LIBDIR / 'libcuvs/lib64'),
    str(LIBDIR / 'librmm/lib64'), str(LIBDIR / 'rapids_logger/lib64'),
    str(LIBDIR / 'nvidia/cu13/lib'), os.environ.get('LD_LIBRARY_PATH', '')))
WORK = (('GIST', 'half', '0x3f34a3d8', 4),
        ('GIST', 'normal', '0x3fb4a3d8', 4),
        ('Deep', 'normal', '0x3f8a3818', 1),
        ('GIST', 'all', '0x41cb7260', 4))


def rows(path):
    with path.open() as f:
        return list(csv.DictReader(f))


def run(label, command):
    folder = ROOT / 'runs' / label
    if not folder.exists():
        subprocess.run([sys.executable, str(P5 / 'run_p4.py'), '--gpu', GPU,
                        '--output', str(folder), '--', *map(str, command)],
                       check=True, stdout=subprocess.DEVNULL)
    receipt = json.loads((folder / 'receipt.json').read_text())
    assert receipt['runtime_valid'], label
    return folder, receipt


def oracle_folder(dataset, radius):
    return ROOT / 'runs' / f'oracle_p6_{dataset.lower()}_{radius}'


def expected(dataset, radius):
    out = rows(oracle_folder(dataset, radius) / 'result.csv')
    assert len(out) == 1024
    result = [(int(x['qid']), int(x['count']), int(x['ordered_hash'])) for x in out]
    if radius == 'all':
        assert all(x[1] == 1_000_000 for x in result)
    return result


def command(dataset, radius, bits, depth, b, mode, reverse, output, dump):
    data = BASE / f'data/{dataset}/1000000/fixtures/data.f32bin'
    order = BASE / f'reference_v2/{dataset}_idlist.i32'
    index = BASE / f'replay/{dataset}_index.bin'
    qids = ROOT / 'fixtures' / f'{dataset}_p6_final1024.qid'
    warm = P0 / 'fixtures' / f'{dataset}_dev256.qid'
    if mode.startswith('LIB'):
        config = json.loads((P5 / 'frozen_external.json').read_text())
        chunk = config[f'{dataset}:{b}:{mode}']
        return [P5 / 'p5_external', data, order, qids, warm, mode, bits, b,
                2, int(reverse), output, int(dump), chunk]
    return [P4 / 'bin/p4_bench_v3', data, order, qids, warm, mode, bits, b,
            2, int(reverse), output, int(dump), index, depth]


def make_oracles():
    for dataset, radius, bits, _ in WORK:
        folder = oracle_folder(dataset, radius)
        data = BASE / f'data/{dataset}/1000000/fixtures/data.f32bin'
        qids = ROOT / 'fixtures' / f'{dataset}_p6_final1024.qid'
        value = struct.unpack('<f', struct.pack('<I', int(bits, 16)))[0]
        binary = BASE / f'data/{dataset}/1000000/bin/graph_bench_strict'
        run(folder.name, [binary, data, qids, 'FR', repr(value), '1', '8',
                          folder / 'result', 0 if radius == 'all' else 1])
        print('ORACLE', dataset, radius, sum(x[1] for x in expected(dataset, radius)), flush=True)


def audit():
    output = []
    for dataset, radius, bits, depth in WORK:
        truth = expected(dataset, radius)
        reference = oracle_folder(dataset, radius) / 'result.bin'
        modes = ('SCAN_L', 'SCAN_E', 'C_MASK_E',
                 'LIB64_X' if dataset == 'Deep' else 'LIB64_U')
        for mode in modes:
            label = f'audit_p6_{dataset.lower()}_{radius}_b32_{mode}'
            folder = ROOT / 'runs' / label
            run(label, command(dataset, radius, bits, depth, 32, mode, False,
                               folder / 'result', radius != 'all'))
            got = rows(folder / 'result_queries.csv')
            current = [(int(x['qid']), int(x['count']), int(x['ordered_hash'])) for x in got]
            assert len(current) == 1024 and all(x[0] == y[0] for x, y in zip(current, truth))
            count_diff = sum(x[1] != y[1] for x, y in zip(current, truth))
            hash_diff = sum(x[2] != y[2] for x, y in zip(current, truth))
            if mode in ('SCAN_L', 'SCAN_E', 'C_MASK_E'):
                assert count_diff == hash_diff == 0, label
            if radius != 'all' and (folder / 'qualification.json').exists():
                result = json.loads((folder / 'qualification.json').read_text())
            elif radius != 'all':
                if mode in ('SCAN_L', 'SCAN_E', 'C_MASK_E'):
                    assert filecmp.cmp(reference, folder / 'result.bin', shallow=False), label
                result = json.loads(subprocess.check_output(
                    [sys.executable, str(P5 / 'compare_outputs.py'),
                     str(reference), str(folder / 'result.bin')], text=True))
                (folder / 'qualification.json').write_text(json.dumps(result, indent=2) + '\n')
                (folder / 'result.bin').unlink()
            else:
                result = {'qualification': 'COUNT_HASH_ONLY_ALL_RADIUS'}
            output.append({'dataset': dataset, 'radius': radius, 'mode': mode,
                           'count_mismatch_queries': count_diff,
                           'hash_mismatch_queries': hash_diff, **result})
            print('AUDIT', dataset, radius, mode, result['qualification'],
                  count_diff, hash_diff, flush=True)
    with (ROOT / 'numerical_qualification.csv').open('w', newline='') as f:
        keys = list(dict.fromkeys(k for x in output for k in x))
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(output)


def formal():
    qualification = {(x['dataset'], x['radius'], x['mode']): x
                     for x in rows(ROOT / 'numerical_qualification.csv')}
    output = []
    for round_no in range(1, 7):
        workloads = [(d, r, bits, depth, b) for d, r, bits, depth in WORK
                     if r != 'all' for b in (8, 32)]
        workloads = workloads[(round_no-1) % len(workloads):] + workloads[:(round_no-1) % len(workloads)]
        for dataset, radius, bits, depth, b in workloads:
            truth = expected(dataset, radius)
            modes = ['SCAN_L', 'SCAN_E', 'C_MASK_E']
            external = 'LIB64_X' if dataset == 'Deep' else 'LIB64_U'
            q = qualification[dataset, radius, external]
            if q['qualification'] == 'BITWISE_MATCH_ON_TESTED' and int(q['count_mismatch_queries']) == 0:
                modes.append(external)
            modes = modes[(round_no-1) % len(modes):] + modes[:(round_no-1) % len(modes)]
            for mode in modes:
                label = f'formal_p6_r{round_no}_{dataset.lower()}_{radius}_b{b}_{mode}'
                folder = ROOT / 'runs' / label
                _, receipt = run(label, command(dataset, radius, bits, depth, b, mode,
                                                 round_no % 2 == 0, folder / 'result', False))
                got = rows(folder / 'result_queries.csv')
                got.sort(key=lambda x: int(x['query_index']))
                current = [(int(x['qid']), int(x['count']), int(x['ordered_hash'])) for x in got]
                assert len(current) == 1024 and all(x == y for x, y in zip(current, truth)), label
                batches = rows(folder / 'result.csv')
                assert len(batches) == 1024 // b
                times = [float(x['host_ms']) for x in batches]
                host = sum(times)
                output.append({'round': round_no, 'dataset': dataset, 'radius': radius,
                               'B': b, 'method': mode, 'host_ready_ms': host,
                               'batch_p50_ms': statistics.median(times),
                               'batch_p95_ms': sorted(times)[math.ceil(.95*len(times))-1],
                               'qps': 1024000 / host,
                               'hits': sum(int(x['result_count_total']) for x in batches),
                               'd2h_bytes': sum(int(x['d2h_bytes']) for x in batches),
                               'binary_sha256': receipt['binary_sha256']})
                print('FORMAL', round_no, dataset, radius, b, mode, round(host, 2), flush=True)
    with (ROOT / 'exact_latency.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=output[0])
        writer.writeheader()
        writer.writerows(output)


if __name__ == '__main__':
    {'oracle': make_oracles, 'audit': audit, 'formal': formal}[sys.argv[1]]()
