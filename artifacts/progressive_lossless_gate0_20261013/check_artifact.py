#!/usr/bin/env python3
"""Check published scalar conservation, frozen parents, and optional private raw arrays."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(8 << 20), b''):
            h.update(block)
    return h.hexdigest()


def read(name):
    return json.loads((ROOT / name).read_text())


def scalars(repo):
    contract = read('CONTRACT.json')
    reg = read('evidence/REGISTRATION.json')
    require(sha(ROOT / 'CONTRACT.json') == reg['contract_sha256'], 'frozen contract differs')
    for name, digest in reg['source_sha256'].items():
        require(sha(ROOT / name) == digest, 'measurement source differs: ' + name)
    for name, digest in contract['parent_files'].items():
        require(sha(repo / name) == digest, 'frozen parent differs: ' + name)
    rows = read('evidence/QUERY_RESULTS.json')
    require([r['query_id'] for r in rows] == contract['workload']['query_ids'], 'query identity/order differs')
    quality = read('correctness/RANGE_QUALITY.json')
    recovery = read('correctness/RECOVERY.json')
    require(quality['pairs'] == 32000000 and quality['query_count'] == 32, 'population incomplete')
    require(quality['false_negatives'] == quality['false_positives'] == quality['final_distance_bit_mismatches'] == 0, 'quality failed')
    require(quality['complete_ID_and_multiplicity_parity'] and quality['total_result_occurrences'] == 6590, 'IDs/multiplicity differ')
    require(recovery['checked_coordinates'] == 960000000 and recovery['bit_mismatches'] == 0, 'whole database recovery failed')
    require(recovery['representation_bytes'] == 3840000064 and recovery['raw_mapping_closed_before_search'], 'size/single-source failed')
    stage = read('model/STAGE_COUNTS.json')['rows']
    histogram = {str(w): sum(r['histogram'][str(w)] for r in rows) for w in (4, 8, 16, 32)}
    require(sum(histogram.values()) == 32000000, 'terminal population differs')
    for i, s in enumerate(stage):
        require(s['input_objects'] == s['rejected_objects'] + s['survivors'], 'stage conservation failed')
        require(s['input_objects'] == (32000000 if i == 0 else stage[i - 1]['survivors']), 'continuation differs')
        require(s['payload_bytes'] == s['input_objects'] * s['incremental_bytes_per_object'], 'payload differs')
        for name in ('input_objects', 'rejected_objects', 'survivors', 'payload_bytes'):
            require(s[name] == sum(r['stages'][i][name] for r in rows), 'pooled stage differs')
    bits = read('model/REQUIRED_BITS.json')
    require(histogram == bits['histogram'], 'histogram differs')
    require(bits['mean_bits_per_coordinate'] == sum(int(w) * n for w, n in histogram.items()) / 32000000, 'mean bits differs')
    require((bits['median'], bits['p90'], bits['p95'], bits['p99']) == (8, 8, 16, 16), 'pooled quantiles differ')
    primary = read('model/LOGICAL_BYTES.json')
    payload = sum(s['payload_bytes'] for s in stage) / 32
    require(payload == sum(r['source_payload_bytes'] for r in rows) / 32 == primary['logical_source_bytes_per_query'], 'primary denominator differs')
    require(payload == 1025475825 and primary['actual_DRAM_bytes'] is None and primary['GPU_latency'] is None, 'metric scope differs')
    decision = read('evidence/DECISION.json')
    require(payload > contract['gates']['CONDITIONAL_max_source_bytes_per_query'], 'declared rejection threshold not reached')
    require(decision['Gate0'] == 'NO_GO_LOSSLESS_PROGRESSIVE' and decision['Gate1'] == 'NOT_RUN', 'wrong gate decision')
    closure = read('evidence/CLOSURE.json')
    require(closure['GPU_starts'] == closure['NCU_starts'] == 0 and closure['population_processes'] == 1, 'process budget differs')
    if (ROOT / 'PUBLICATION_SET.json').exists():
        manifest = read('PUBLICATION_SET.json')
        for name, entry in manifest['files'].items():
            path = ROOT / name
            require(path.stat().st_size == entry['bytes'] and sha(path) == entry['sha256'], 'publication blob differs: ' + name)
        actual = {str(p.relative_to(ROOT)) for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
        require(actual == set(manifest['files']) | {'PUBLICATION_SET.json'}, 'publication set differs')
    print('PASS: frozen sources/parents, 32M pairs, 960M coordinate recovery, stage/bit/byte conservation, NO-GO, zero GPU/NCU')
    return rows


def raw_arrays(work, cache, rows):
    import numpy as np
    manifest = read('evidence/RAW_MANIFEST.json')['files']
    references = read('evidence/REGISTRATION.json')['reference_hashes']
    checked = bound_checks = final_checks = 0
    for r in rows:
        qid = r['query_id']; n = 1000000
        for suffix in ('bits.u8', 'lower.f64', 'full.f64'):
            name = f'{qid}.{suffix}'; path = work / name
            require(path.stat().st_size == manifest[name]['bytes'] and sha(path) == manifest[name]['sha256'], 'private raw hash differs')
        ref_path = cache / f'{qid}.f64'
        require(sha(ref_path) == references[ref_path.name], 'oracle hash differs')
        bits = np.memmap(work / f'{qid}.bits.u8', mode='r', dtype='u1', shape=(n,))
        lower = np.memmap(work / f'{qid}.lower.f64', mode='r', dtype='<f8', shape=(3, n))
        full = np.memmap(work / f'{qid}.full.f64', mode='r', dtype='<f8', shape=(n,))
        ref = np.memmap(ref_path, mode='r', dtype='<f8', shape=(n,))
        require({str(w): int((bits == w).sum()) for w in (4, 8, 16, 32)} == r['histogram'], 'raw terminal histogram differs')
        cutoff = float.fromhex(read('CONTRACT.json')['workload']['cutoff_hex'])
        for i, w in enumerate((4, 8, 16)):
            visited = bits >= w
            require(np.all(np.isfinite(lower[i, visited])) and np.all(lower[i, visited] >= 0), 'invalid raw bounds')
            require(np.all(lower[i, visited] <= ref[visited]) and np.all(np.isnan(lower[i, ~visited])), 'raw safety/write mask differs')
            if i:
                require(np.all(lower[i, visited] >= lower[i - 1, visited]), 'raw bounds not monotone')
            require(np.all(lower[i, bits == w] > cutoff) and np.all(lower[i, bits > w] <= cutoff), 'raw rejection/equality differs')
            bound_checks += int(visited.sum())
        final = bits == 32
        require(np.all(np.isfinite(full[final])) and np.all(np.isnan(full[~final])), 'raw final write mask differs')
        require(np.array_equal(full[final].view('<u8'), ref[final].view('<u8')), 'raw final score bits differ')
        candidate = np.flatnonzero(final & (full <= cutoff)).astype('<u8')
        require(np.array_equal(candidate, np.flatnonzero(ref <= cutoff)), 'raw exact IDs/multiplicity differ')
        require(hashlib.sha256(candidate.tobytes()).hexdigest() == r['member_ids_sha256'], 'raw member digest differs')
        final_checks += int(final.sum()); checked += n
        for a in (bits, lower, full, ref):
            a._mmap.close()
    require(checked == 32000000 and bound_checks == 66167243 and final_checks == 6917, 'raw audit coverage differs')
    print(f'PASS: offline raw-only audit; {checked} memberships, {bound_checks} visited bounds, {final_checks} exact final scores; no candidate rerun')


if __name__ == '__main__':
    require(not sys.flags.optimize, 'run without Python -O')
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo', type=Path, default=ROOT.parents[1])
    p.add_argument('--raw', type=Path)
    p.add_argument('--cache', type=Path)
    args = p.parse_args()
    require(bool(args.raw) == bool(args.cache), '--raw and --cache must be supplied together')
    rows = scalars(args.repo)
    if args.raw:
        raw_arrays(args.raw, args.cache, rows)
