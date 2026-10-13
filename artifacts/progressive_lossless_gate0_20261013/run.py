#!/usr/bin/env python3
"""One frozen CPU replay; original vectors and old scores are validation-only."""
import argparse
import ctypes as C
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import struct
import subprocess
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parent
HEADER = struct.Struct('<8sQII4QQ')
WIDTHS = (4, 8, 16, 32)


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(8 << 20), b''):
            h.update(b)
    return h.hexdigest()


def save(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as f:
        json.dump(obj, f, indent=2, sort_keys=True, allow_nan=False)
        f.write('\n')


def build(out):
    contract = json.loads((ROOT / 'CONTRACT.json').read_text())
    command = ['g++', *contract['execution']['compiler_flags'], str(ROOT / 'lossless.cpp'), '-o', str(out)]
    result = subprocess.run(command, text=True, capture_output=True)
    receipt = {'compiler': subprocess.check_output(['g++', '--version'], text=True).splitlines()[0],
               'flags': contract['execution']['compiler_flags'], 'returncode': result.returncode,
               'stdout': result.stdout, 'stderr': result.stderr,
               'source_sha256': sha(ROOT / 'lossless.cpp')}
    require(result.returncode == 0, 'CPU library build failed: ' + result.stderr)
    receipt['binary_sha256'] = sha(out)
    return receipt


def load(path):
    lib = C.CDLL(str(path))
    ptr = C.c_void_p
    lib.recover.argtypes = [ptr, ptr, ptr, ptr, C.c_size_t, C.c_int, ptr]
    lib.recover.restype = C.c_int
    lib.search.argtypes = [ptr, ptr, ptr, ptr, ptr, C.c_size_t, C.c_int, C.c_double, ptr, ptr, ptr]
    lib.search.restype = C.c_int
    lib.interval_key.argtypes = [C.c_uint32, C.c_int, ptr]
    lib.interval_key.restype = C.c_int
    return lib


def pack_rows(bits):
    """Bijective bit permutation; this helper also encodes nonfinite recovery fixtures."""
    n, d = bits.shape
    keys = np.where(bits & np.uint32(0x80000000), ~bits,
                    bits ^ np.uint32(0x80000000)).astype('<u4')
    layers = []
    for shift in (28, 24):
        v = ((keys >> shift) & 15).astype('u1')
        packed = np.zeros((n, (d + 1) // 2), dtype='u1')
        packed[:, :] = v[:, ::2] << 4
        packed[:, :d // 2] |= v[:, 1::2]
        layers.append(packed)
    layers.extend([((keys >> 16) & 255).astype('u1'), (keys & 65535).astype('<u2').view('u1')])
    return layers


def search(lib, layers, query, cutoff, n=None):
    n = len(layers[0]) if n is None else n
    bits = np.zeros(n, dtype='u1')
    lower = np.full((3, n), np.nan, dtype='<f8')
    full = np.full(n, np.nan, dtype='<f8')
    rc = lib.search(*(v.ctypes.data for v in layers), query.ctypes.data,
                    n, len(query), cutoff, bits.ctypes.data, lower.ctypes.data, full.ctypes.data)
    require(rc == 0, f'candidate search returned {rc}')
    return bits, lower, full


def validate(bits, lower, full, reference, cutoff):
    n = len(bits)
    require(reference.shape == (n,) and np.all(np.isfinite(reference)), 'invalid oracle')
    require(np.all(np.isin(bits, WIDTHS)), 'missing/invalid terminal bits')
    bound_checks = 0
    for s, width in enumerate(WIDTHS[:3]):
        visited = bits >= width
        require(np.all(np.isfinite(lower[s, visited])), 'nonfinite visited lower bound')
        require(np.all(np.isnan(lower[s, ~visited])), 'unvisited stage was touched')
        require(np.all(lower[s, visited] >= 0), 'negative lower bound')
        require(np.all(lower[s, visited] <= reference[visited]), 'unsafe lower bound')
        if s:
            require(np.all(lower[s, visited] >= lower[s - 1, visited]), 'nonmonotone lower bound')
        rejected = bits == width
        require(np.all(lower[s, rejected] > cutoff), 'reject without strict lower bound')
        continuing = bits > width
        require(np.all(lower[s, continuing] <= cutoff), 'continued a strictly rejected object')
        bound_checks += int(visited.sum())
    final = bits == 32
    require(np.all(np.isfinite(full[final])) and np.all(np.isnan(full[~final])), 'invalid final writes')
    mismatch = int(np.count_nonzero(full[final].view('<u8') != reference[final].view('<u8')))
    candidate = final & (full <= cutoff)
    truth = reference <= cutoff
    fn = int(np.count_nonzero(truth & ~candidate))
    fp = int(np.count_nonzero(candidate & ~truth))
    require(mismatch == fn == fp == 0, 'exact range or final-distance mismatch')
    ids = np.flatnonzero(candidate).astype('<u8')
    # One flag per original row occurrence preserves duplicate vectors and multiplicity.
    require(np.array_equal(ids, np.flatnonzero(truth)), 'complete member IDs differ')
    return {'pairs': n, 'false_negatives': fn, 'false_positives': fp,
            'final_distance_bit_mismatches': mismatch, 'final_distance_checks': int(final.sum()),
            'lower_bound_checks': bound_checks, 'hits': len(ids), 'member_ids_sha256': hashlib.sha256(ids.tobytes()).hexdigest(),
            'histogram': {str(w): int((bits == w).sum()) for w in WIDTHS}}


def encode_and_recover(data, output, lib, n, d, query_ids):
    require(data.stat().st_size == 12 + n * d * 4, 'dataset file size differs')
    with data.open('rb') as f:
        require(struct.unpack('<iii', f.read(12)) == (d, n, 2), 'dataset header differs')
    raw = np.memmap(data, mode='r', dtype='<f4', offset=12, shape=(n, d))
    query = np.array(raw[query_ids], dtype='<f4', order='C', copy=True)
    sizes = [n * ((d + 1) // 2), n * ((d + 1) // 2), n * d, n * d * 2]
    offsets = [HEADER.size]
    for size in sizes[:-1]:
        offsets.append(offsets[-1] + size)
    with output.open('xb') as f:
        f.write(HEADER.pack(b'GTSPPLB1', n, d, 1, *offsets, sum(sizes)))
        f.truncate(HEADER.size + sum(sizes))
    shapes = [(n, (d + 1) // 2), (n, (d + 1) // 2), (n, d), (n, d * 2)]
    layers = [np.memmap(output, mode='r+', dtype='u1', offset=o, shape=s)
              for o, s in zip(offsets, shapes)]
    checked = nonfinite = mismatch = 0
    for start in range(0, n, 8192):
        end = min(start + 8192, n)
        chunk = raw[start:end]
        nonfinite += int(np.count_nonzero(~np.isfinite(chunk)))
        require(nonfinite == 0, 'nonfinite database coordinates: not admitted for dense L2 service')
        encoded = pack_rows(chunk.view('<u4'))
        for dest, src in zip(layers, encoded):
            dest[start:end] = src
    for layer in layers:
        layer.flush()
    # Decode the stored file, not the encoder's temporary keys, across the entire database.
    for start in range(0, n, 8192):
        end = min(start + 8192, n)
        restored = np.empty((end - start, d), dtype='<u4')
        views = [v[start:end] for v in layers]
        rc = lib.recover(*(v.ctypes.data for v in views), end - start, d, restored.ctypes.data)
        require(rc == 0, 'full reconstruction returned an error')
        mismatch += int(np.count_nonzero(restored != raw[start:end].view('<u4')))
        require(mismatch == 0, 'full representation bit recovery mismatch')
        checked += restored.size
    raw._mmap.close()
    for layer in layers:
        layer._mmap.close()
    layers = [np.memmap(output, mode='r', dtype='u1', offset=o, shape=s)
              for o, s in zip(offsets, shapes)]
    return query, layers, {'checked_coordinates': checked, 'bit_mismatches': mismatch,
                         'nonfinite_database_coordinates': nonfinite, 'raw_mapping_closed_before_search': raw._mmap.closed,
                         'raw_bytes': n * d * 4, 'representation_bytes': output.stat().st_size,
                         'layer_bytes': sizes, 'layer_offsets': offsets, 'header_bytes': HEADER.size,
                         'representation_sha256': sha(output), 'query_bytes': query.nbytes,
                         'queries_sha256': hashlib.sha256(query.tobytes()).hexdigest()}


def population(args):
    contract = json.loads((ROOT / 'CONTRACT.json').read_text())
    require(os.environ.get('CUDA_VISIBLE_DEVICES') == '', 'must disable CUDA visibility')
    require(os.environ.get('OMP_NUM_THREADS') == '4' and os.environ.get('OMP_DYNAMIC') == 'FALSE', 'freeze four CPU workers')
    require(os.nice(0) >= contract['execution']['nice'], 'CPU task must run nice >=10')
    work = args.work.resolve()
    work.mkdir()  # Exclusive: never overwrite or automatically resume an old population.
    args.created_work = True
    source_names = ['CONTRACT.json', 'lossless.cpp', 'run.py', 'test_format.py']
    frozen = {name: sha(ROOT / name) for name in source_names}
    identity = json.loads(args.parent_identity.read_text())
    require(sha(args.parent_identity) == contract['parent_files']['artifacts/progressive_gpu_gate2_20261013/evidence/INPUT_IDENTITY.json'],
            'parent identity content differs from frozen Gate2 evidence')
    require(identity['query_ids'] == contract['workload']['query_ids'], 'parent query IDs differ')
    registration = {'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'pid': os.getpid(),
                    'scope': contract['scope'], 'contract_sha256': frozen['CONTRACT.json'], 'source_sha256': frozen,
                    'CPU_workers': 4, 'nice': os.nice(0), 'GPU_starts': 0, 'NCU_starts': 0,
                    'data_identity': contract['workload']['data_sha256'], 'N': contract['workload']['N'],
                    'D': contract['workload']['D'], 'query_count': 32, 'query_ids': identity['query_ids'],
                    'parent_identity_sha256': sha(args.parent_identity), 'reference_hashes': identity['reference_hashes']}
    save(work / 'REGISTRATION.json', registration)
    start = time.monotonic()
    require(sha(args.data) == contract['workload']['data_sha256'], 'dataset hash differs')
    n, d = contract['workload']['N'], contract['workload']['D']
    for qid in identity['query_ids']:
        path = args.cache / f'{qid}.f64'
        require(path.stat().st_size == 8 * n, 'reference size differs')
        require(sha(path) == identity['reference_hashes'][path.name], 'frozen reference hash differs')
    save(work / 'INPUT_CHECK.json', {'data_sha256': sha(args.data), 'reference_hashes': identity['reference_hashes'],
                                    'all_hashes_match': True, 'validation_only_reference_bytes': n * 8 * 32})
    binary = work / 'lossless.so'
    save(work / 'BUILD.json', build(binary))
    # The executable fixture test is mandatory before any database encoding or query replay.
    result = subprocess.run([sys.executable, str(ROOT / 'test_format.py'), '--library', str(binary)], text=True, capture_output=True)
    save(work / 'FIXTURE_TEST.json', {'returncode': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr})
    require(result.returncode == 0, 'fixture qualification failed')
    lib = load(binary)
    query, layers, recovery = encode_and_recover(args.data, work / 'representation.bin', lib, n, d, identity['query_ids'])
    require(recovery['representation_bytes'] == contract['format']['representation_bytes'], 'persistent size differs')
    save(work / 'RECOVERY.json', recovery)
    cutoff = float.fromhex(contract['workload']['cutoff_hex'])
    qualification = []
    for qid, q in zip(identity['query_ids'], query):
        ref = np.memmap(args.cache / f'{qid}.f64', mode='r', dtype='<f8', shape=(n,))
        result = search(lib, [v[:4096] for v in layers], q, cutoff)
        qualification.append({'query_id': qid, **validate(*result, ref[:4096], cutoff)})
        ref._mmap.close()
    save(work / 'QUALIFICATION.json', qualification)
    print('Qualification passed; starting frozen 32 x 1M replay', flush=True)
    rows = []
    for qid, q in zip(identity['query_ids'], query):
        tick = time.monotonic()
        bits, lower, full = search(lib, layers, q, cutoff)
        # Validation reference is opened only after candidate search returns.
        ref = np.memmap(args.cache / f'{qid}.f64', mode='r', dtype='<f8', shape=(n,))
        row = {'query_id': qid, **validate(bits, lower, full, ref, cutoff)}
        ref._mmap.close()
        inputs = [n, int((bits > 4).sum()), int((bits > 8).sum()), int((bits > 16).sum())]
        row['stages'] = [{'cumulative_bits': width, 'input_objects': count,
                          'rejected_objects': int((bits == width).sum()) if width < 32 else count - row['hits'],
                          'survivors': int((bits > width).sum()) if width < 32 else row['hits'],
                          'incremental_bytes_per_object': byte,
                          'payload_bytes': count * byte}
                         for width, count, byte in zip(WIDTHS, inputs, (d // 2, d // 2, d, d * 2))]
        row['source_payload_bytes'] = sum(s['payload_bytes'] for s in row['stages'])
        row['mean_bits_per_coordinate'] = float(bits.astype('u8').sum()) / n
        row['bit_quantiles'] = {f'p{p}': float(np.percentile(bits, p, method='linear')) for p in (50, 90, 95, 99)}
        require(row['source_payload_bytes'] == int(bits.astype('u8').sum()) * d // 8, 'layer/terminal accounting differs')
        raw_hashes = {}
        for label, a in [('bits.u8', bits), ('lower.f64', lower), ('full.f64', full)]:
            out = work / f'{qid}.{label}'
            with out.open('xb') as f:
                a.tofile(f)
            raw_hashes[out.name] = {'bytes': out.stat().st_size, 'sha256': sha(out)}
        row['private_evidence'] = raw_hashes
        row['operational_seconds'] = time.monotonic() - tick
        save(work / f'{qid}.json', row)
        rows.append(row)
        print(f'qid={qid} bytes={row["source_payload_bytes"]} hits={row["hits"]} terminal={row["histogram"]}', flush=True)
    require(frozen == {name: sha(ROOT / name) for name in source_names}, 'source changed during run')
    require(sha(work / 'representation.bin') == recovery['representation_sha256'], 'representation changed during replay')
    require(all(sha(args.cache / f'{qid}.f64') == identity['reference_hashes'][f'{qid}.f64']
                for qid in identity['query_ids']), 'oracle changed during replay')
    require(sha(args.data) == contract['workload']['data_sha256'], 'database changed during replay')
    save(work / 'RESULTS.json', rows)
    save(work / 'CLOSURE.json', {'status': 'PASS', 'completed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                               'population_processes': 1, 'queries': len(rows), 'pairs': n * len(rows),
                               'GPU_starts': 0, 'NCU_starts': 0, 'source_unchanged': True, 'data_unchanged': True,
                               'references_unchanged': True, 'representation_unchanged': True,
                               'operational_seconds': time.monotonic() - start,
                               'Python': platform.python_version(), 'NumPy': np.__version__})


if __name__ == '__main__':
    require(not sys.flags.optimize, 'run without Python -O')
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data', type=Path, required=True)
    p.add_argument('--cache', type=Path, required=True)
    p.add_argument('--parent-identity', type=Path, required=True)
    p.add_argument('--work', type=Path, required=True)
    args = p.parse_args()
    try:
        population(args)
    except Exception as exc:
        if getattr(args, 'created_work', False) and not (args.work / 'FAILURE.json').exists():
            save(args.work / 'FAILURE.json', {'type': type(exc).__name__, 'message': str(exc), 'GPU_starts': 0, 'NCU_starts': 0})
        raise
