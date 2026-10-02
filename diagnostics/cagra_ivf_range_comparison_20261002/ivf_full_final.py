#!/usr/bin/env python3
"""Faiss-IVF list order plus custom complete P4 GPU scan and Host order restore."""
import csv
import json
from pathlib import Path
import statistics
import struct
import subprocess
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parent
P5 = Path('/home/data/wangxuran/tmp/gts_p5_external_mask_20261002')
P4 = Path('/home/data/wangxuran/tmp/gts_p4_tree_batch_20261002')
P0 = Path('/home/data/wangxuran/tmp/gts_batch_exact_highdim_20261001')
BASE = Path('/home/data/wangxuran/tmp/gts_arithmetic_path_boundary_20260928')
GPU = 'GPU-e5a0e7f5-9917-c2a1-ee8e-7282cbba2603'
WORK = (('GIST', 'half', '0x3f34a3d8', 4),
        ('GIST', 'normal', '0x3fb4a3d8', 4),
        ('Deep', 'normal', '0x3f8a3818', 1))


def scan_index(dataset, order):
    """SCAN_E ignores tree nodes, but its loader validates the embedded ID order."""
    target = ROOT / 'fixtures' / f'{dataset}_ivf_n1024_scan_index.bin'
    if not target.exists():
        source = BASE / f'replay/{dataset}_index.bin'
        canonical = (BASE / f'reference_v2/{dataset}_idlist.i32').read_bytes()
        replacement = order.read_bytes()
        assert len(canonical) == len(replacement) == 4_000_000
        image = bytearray(source.read_bytes())
        assert image[-len(canonical):] == canonical
        image[-len(canonical):] = replacement
        target.write_bytes(image)
    return target


def read_rows(path):
    with path.open() as f:
        return list(csv.DictReader(f))


def oracle_offsets(path):
    offsets = {}
    with path.open('rb') as f:
        while header := f.read(8):
            qid, count = struct.unpack('<ii', header)
            offsets[qid] = f.tell()
            f.seek(count * 8, 1)
    assert len(offsets) == 1024
    return offsets


def audit_and_time(result, reference, rank):
    offsets = oracle_offsets(reference)
    reorder_ms = 0.0
    queries = hits = 0
    with result.open('rb') as f, reference.open('rb') as ref:
        while header := f.read(8):
            qid, count = struct.unpack('<ii', header)
            ids = np.frombuffer(f.read(count*4), dtype='<i4').copy()
            fields = np.frombuffer(f.read(count*4), dtype='<u4').copy()
            assert len(ids) == len(fields) == count and qid in offsets
            start = time.perf_counter()
            # Every ID has a unique canonical rank, so stability cannot change the output.
            permutation = np.argsort(rank[ids], kind='quicksort')
            ids = ids[permutation]
            fields = fields[permutation]
            reorder_ms += (time.perf_counter() - start)*1000
            ref.seek(offsets[qid] - 8)
            expected_qid, expected_count = struct.unpack('<ii', ref.read(8))
            assert (qid, count) == (expected_qid, expected_count)
            expected_ids = np.frombuffer(ref.read(count*4), dtype='<i4')
            expected_fields = np.frombuffer(ref.read(count*4), dtype='<u4')
            assert np.array_equal(ids, expected_ids), ('ID mismatch', qid)
            assert np.array_equal(fields, expected_fields), ('field mismatch', qid)
            queries += 1
            hits += count
    assert queries == 1024
    return {'queries': queries, 'hits': hits, 'reorder_ms': reorder_ms,
            'sort_kind': 'quicksort_unique_rank',
            'qualification': 'BITWISE_MATCH_ON_TESTED_AFTER_ORDER_RESTORE'}


def main():
    output = []
    for round_no in range(1, 7):
        workloads = [(d, r, bits, depth, b) for d, r, bits, depth in WORK
                     for b in (8, 32)]
        workloads = workloads[(round_no-1) % len(workloads):] + workloads[:(round_no-1) % len(workloads)]
        for dataset, radius, bits, depth, b in workloads:
            label = f'ivf_full_p6_r{round_no}_{dataset.lower()}_{radius}_b{b}'
            folder = ROOT / 'runs' / label
            order = ROOT / 'fixtures' / f'{dataset}_ivf_n1024_order.i32'
            assert order.exists()
            if not folder.exists():
                data = BASE / f'data/{dataset}/1000000/fixtures/data.f32bin'
                qids = ROOT / 'fixtures' / f'{dataset}_p6_final1024.qid'
                warm = P0 / 'fixtures' / f'{dataset}_dev256.qid'
                index = scan_index(dataset, order)
                command = [P4 / 'bin/p4_bench_v3', data, order, qids, warm,
                           'SCAN_E', bits, b, 2, int(round_no % 2 == 0),
                           folder / 'result', 1, index, depth]
                subprocess.run([sys.executable, str(P5 / 'run_p4.py'), '--gpu', GPU,
                                '--output', str(folder), '--', *map(str, command)],
                               check=True, stdout=subprocess.DEVNULL)
            receipt = json.loads((folder / 'receipt.json').read_text())
            assert receipt['runtime_valid']
            audit_file = folder / 'order_audit.json'
            if audit_file.exists():
                audit = json.loads(audit_file.read_text())
            else:
                canonical = np.fromfile(BASE / f'reference_v2/{dataset}_idlist.i32',
                                        dtype='<i4')
                rank = np.empty(1_000_000, dtype=np.int32)
                rank[canonical] = np.arange(1_000_000, dtype=np.int32)
                audit = audit_and_time(folder / 'result.bin',
                                       ROOT / 'runs' / f'oracle_p6_{dataset.lower()}_{radius}' / 'result.bin',
                                       rank)
                audit_file.write_text(json.dumps(audit, indent=2) + '\n')
                (folder / 'result.bin').unlink()
            batches = read_rows(folder / 'result.csv')
            assert len(batches) == 1024//b
            times = [float(x['host_ms']) for x in batches]
            scan_ms = sum(times)
            setup = json.loads((folder / 'result.json').read_text())
            output.append({'round': round_no, 'dataset': dataset, 'radius': radius,
                           'B': b, 'method': 'FAISS_IVF_STRUCTURE_CUSTOM_GPU_RANGE',
                           'nlist': 1024, 'nprobe': 1024, 'coverage': 'all lists, all records',
                           'scan_host_ms': scan_ms, 'reorder_ms': audit['reorder_ms'],
                           'host_ready_ms': scan_ms + audit['reorder_ms'],
                           'batch_scan_p50_ms': statistics.median(times),
                           'hits': audit['hits'], 'qualification': audit['qualification'],
                           'data_setup_s': setup['data_setup_s'],
                           'layout_s': setup['layout_s']})
            print('IVF_FULL', round_no, dataset, radius, b,
                  round(scan_ms, 2), round(audit['reorder_ms'], 2), flush=True)
    with (ROOT / 'ivf_full_latency.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=output[0])
        writer.writeheader()
        writer.writerows(output)


if __name__ == '__main__':
    main()
