#!/usr/bin/env python3
"""Curate only scalar receipts and hashes from one completed private CPU replay."""
import argparse
import json
from pathlib import Path

from run import require, save, sha


def quantile_hist(hist, p):
    total = sum(hist.values())
    h = (total - 1) * p / 100
    low, high = int(h), int(h) + (h != int(h))
    def at(rank):
        end = 0
        for value, count in sorted(hist.items()):
            end += count
            if rank < end:
                return value
        raise RuntimeError('empty histogram')
    a, b = at(low), at(high)
    return float(a + (h - low) * (b - a))


def analyze(private, root, repo):
    contract = json.loads((root / 'CONTRACT.json').read_text())
    closure = json.loads((private / 'CLOSURE.json').read_text())
    require(closure['status'] == 'PASS' and closure['pairs'] == 32000000 and closure['queries'] == 32, 'incomplete population')
    rows = json.loads((private / 'RESULTS.json').read_text())
    require([r['query_id'] for r in rows] == contract['workload']['query_ids'], 'query order differs')
    registration = json.loads((private / 'REGISTRATION.json').read_text())
    for name, expected in registration['source_sha256'].items():
        require(sha(root / name) == expected, 'measurement source differs: ' + name)
    require(registration['contract_sha256'] == sha(root / 'CONTRACT.json'), 'contract differs')
    for name, expected in contract['parent_files'].items():
        require(sha(repo / name) == expected, 'parent evidence differs: ' + name)
    recovery = json.loads((private / 'RECOVERY.json').read_text())
    require(recovery['bit_mismatches'] == 0 and recovery['checked_coordinates'] == 960000000, 'recovery incomplete')
    require(recovery['raw_mapping_closed_before_search'] and recovery['nonfinite_database_coordinates'] == 0, 'single-source admission failed')
    qual = json.loads((private / 'QUALIFICATION.json').read_text())
    require(len(qual) == 32 and all(r['pairs'] == 4096 for r in qual), 'qualification incomplete')
    for r in qual + rows:
        require(r['false_negatives'] == r['false_positives'] == r['final_distance_bit_mismatches'] == 0, 'quality failure')
    public_registration = {k: v for k, v in registration.items() if k != 'pid'}
    save(root / 'evidence' / 'REGISTRATION.json', public_registration)
    bridges = {'REGISTRATION.json': {'removed_fields': ['pid'],
                                     'raw_sha256': sha(private / 'REGISTRATION.json'),
                                     'raw_bytes': (private / 'REGISTRATION.json').stat().st_size,
                                     'public_sha256': sha(root / 'evidence/REGISTRATION.json'),
                                     'public_bytes': (root / 'evidence/REGISTRATION.json').stat().st_size}}
    if (private / 'ENVIRONMENT_PRIVATE.json').exists():
        original = json.loads((private / 'ENVIRONMENT_PRIVATE.json').read_text())
        allowed = {'scope', 'CPU_workers', 'nice', 'endianness', 'compiler', 'Python', 'NumPy', 'OpenMP',
                   'CUDA_visible_devices', 'GPU_kernel_starts', 'NCU_starts', 'new_dependency_installs',
                   'new_hooks_or_frameworks', 'plotting'}
        save(root / 'evidence/ENVIRONMENT.json', {k: v for k, v in original.items() if k in allowed})
        bridges['ENVIRONMENT.json'] = {'raw_file': 'ENVIRONMENT_PRIVATE.json',
                                      'removed_fields': sorted(set(original) - allowed),
                                      'raw_sha256': sha(private / 'ENVIRONMENT_PRIVATE.json'),
                                      'raw_bytes': (private / 'ENVIRONMENT_PRIVATE.json').stat().st_size,
                                      'public_sha256': sha(root / 'evidence/ENVIRONMENT.json'),
                                      'public_bytes': (root / 'evidence/ENVIRONMENT.json').stat().st_size}
    save(root / 'evidence/CURATION.json', {'policy': 'curation only; original receipts and measurement sources unchanged',
                                         'bridges': bridges})
    for name in ('INPUT_CHECK.json', 'BUILD.json', 'FIXTURE_TEST.json', 'CLOSURE.json'):
        # These receipts have no placement/configuration values or restricted vectors.
        save(root / 'evidence' / name, json.loads((private / name).read_text()))
    save(root / 'correctness' / 'RECOVERY.json', recovery)
    save(root / 'correctness' / 'QUALIFICATION.json', qual)
    save(root / 'evidence' / 'QUERY_RESULTS.json', rows)
    raw = {name: {'bytes': (private / name).stat().st_size, 'sha256': sha(private / name)}
           for name in ('REGISTRATION.json', 'INPUT_CHECK.json', 'BUILD.json', 'FIXTURE_TEST.json',
                        'RECOVERY.json', 'QUALIFICATION.json', 'RESULTS.json', 'CLOSURE.json')}
    for r in rows:
        raw.update(r['private_evidence'])
        name = f'{r["query_id"]}.json'
        raw[name] = {'bytes': (private / name).stat().st_size, 'sha256': sha(private / name)}
    raw['representation.bin'] = {'bytes': recovery['representation_bytes'], 'sha256': recovery['representation_sha256']}
    if (private / 'ENVIRONMENT_PRIVATE.json').exists():
        path = private / 'ENVIRONMENT_PRIVATE.json'
        raw[path.name] = {'bytes': path.stat().st_size, 'sha256': sha(path)}
    save(root / 'evidence' / 'RAW_MANIFEST.json', {'placement': 'task-owned private evidence directory (not published)',
                                                'files': raw, 'restricted_vectors_and_full_arrays_published': False})
    quality = {'pairs': sum(r['pairs'] for r in rows), 'query_count': len(rows),
               'false_negatives': sum(r['false_negatives'] for r in rows),
               'false_positives': sum(r['false_positives'] for r in rows),
               'final_distance_bit_mismatches': sum(r['final_distance_bit_mismatches'] for r in rows),
               'final_distance_checks': sum(r['final_distance_checks'] for r in rows),
               'lower_bound_checks': sum(r['lower_bound_checks'] for r in rows),
               'complete_ID_and_multiplicity_parity': True,
               'total_result_occurrences': sum(r['hits'] for r in rows),
               'reference': 'unchanged Gate2 ordered raw-FP32/FP64 full-distance files; all 32 hashes checked before and after',
               'query_scope': 'frozen 32 GIST1M range queries only; not kNN or updates'}
    save(root / 'correctness' / 'RANGE_QUALITY.json', quality)
    stage_rows = []
    for i, width in enumerate((4, 8, 16, 32)):
        stages = [r['stages'][i] for r in rows]
        entry = {'cumulative_bits': width, 'incremental_bits': (4, 4, 8, 16)[i],
                 'incremental_bytes_per_object': stages[0]['incremental_bytes_per_object']}
        entry.update({k: sum(s[k] for s in stages) for k in ('input_objects', 'rejected_objects', 'survivors', 'payload_bytes')})
        entry['mean_input_objects_per_query'] = entry['input_objects'] / 32
        entry['mean_survivors_per_query'] = entry['survivors'] / 32
        entry['mean_payload_bytes_per_query'] = entry['payload_bytes'] / 32
        stage_rows.append(entry)
    save(root / 'model' / 'STAGE_COUNTS.json', {'denominator': '32 x 1M query-object pairs; equal query weight',
                                            'final_survivors': 'exact range results; prior survivors require next layer', 'rows': stage_rows})
    hist = {w: sum(r['histogram'][str(w)] for r in rows) for w in (4, 8, 16, 32)}
    mean_bits = sum(w * count for w, count in hist.items()) / 32000000
    save(root / 'model' / 'REQUIRED_BITS.json', {'denominator': 'pooled 32M query-object pairs; uniform stage width across each object coordinate',
                                             'histogram': hist, 'mean_bits_per_coordinate': mean_bits,
                                             'quantile_estimator': 'linear interpolation at rank (n-1)*p',
                                             'median': quantile_hist(hist, 50), 'p90': quantile_hist(hist, 90),
                                             'p95': quantile_hist(hist, 95), 'p99': quantile_hist(hist, 99),
                                             'per_query': [{'query_id': r['query_id'], 'mean': r['mean_bits_per_coordinate'],
                                                            **r['bit_quantiles']} for r in rows]})
    payload = sum(r['source_payload_bytes'] for r in rows) / len(rows)
    require(payload == sum(r['mean_payload_bytes_per_query'] for r in stage_rows), 'stage/source accounting differs')
    require(sum(r['source_payload_bytes'] for r in rows) == sum(w * count for w, count in hist.items()) * 960 // 8,
            'required-bit accounting differs')
    primary = {'logical_source_bytes_per_query': payload, 'decimal_GB_per_query': payload / 1e9,
               'full_scan_ratio': payload / 3840000000,
               'dimension_progressive_ratio': payload / contract['gates']['baseline_source_bytes_per_query'],
               'per_query_payload_bytes': [{'query_id': r['query_id'], 'bytes': r['source_payload_bytes']} for r in rows],
               'measurement': 'exact replay counts converted to DISTINCT incremental source-layer payload; not actual CPU or GPU traffic',
               'actual_DRAM_bytes': None, 'GPU_latency': None,
               'additional_accounting': {
                   'persistent_header_bytes': 64, 'setup_only_header': True,
                   'interval_table_bytes': 0, 'decoder_constants': 'finite key min/max + three widths; included in executable, no per-object table',
                   'query_bytes_per_query': 3840,
                   'CPU_retained_prefix_live_bytes': 3840 * 4, 'CPU_retained_prefix_location': 'four workers, local per-object u32[960]',
                   'implicit_object_IDs': 'loop row occurrence; no fetched ID list',
                   'flag_array_bytes_per_query': 1000000, 'flag_purpose': 'CPU terminal-width proof recording, not source payload',
                   'lower_bound_validator_bytes_per_query': 24000000, 'final_score_validator_bytes_per_query': 8000000,
                   'raw_input_recovery_read_bytes': 3840000000, 'query_copy_read_bytes': 122880,
                   'frozen_oracle_validation_read_bytes_per_query': 8000000,
                   'GPU_global_prefix_state_bytes': None, 'GPU_compaction_bytes': None,
                   'GPU_prefix_state_and_compaction': 'not implemented or priced; not assumed free',
                   'output_cost': 'complete row-occurrence result IDs and distances checked; GPU output traffic not measured',
                   'CPU_wall_seconds': 'operational provenance only; no performance claim'}}
    save(root / 'model' / 'LOGICAL_BYTES.json', primary)
    old = json.loads((repo / 'artifacts/exact_representation_gate1_20261012/bytes/STAGE_ACCOUNTING.json').read_text())
    save(root / 'comparison' / 'DIM_PROGRESSIVE_BASELINE.json', {
        'method': 'frozen 128/256/512/960 exact dimension-progressive checkpoint model',
        'logical_source_bytes_per_query': old['coordinate_bytes_per_query'],
        'source_file': 'artifacts/exact_representation_gate1_20261012/bytes/STAGE_ACCOUNTING.json',
        'source_sha256': contract['parent_files']['artifacts/exact_representation_gate1_20261012/bytes/STAGE_ACCOUNTING.json'],
        'remeasured_GPU_baseline': False, 'scope': 'same original N/D/query/radius, prior CPU ideal checkpoint source payload',
        'optional_state_RW_bytes_per_query': old['optional_global_FP64_state_read_write_bytes_per_query'],
        'optional_ID_RW_bytes_per_query': old['optional_int32_continuation_read_write_bytes_per_query'],
        'not_priced': old['not_priced'], 'persistent_raw_source_bytes': 3840000000})
    save(root / 'comparison' / 'FULL_SCAN_BASELINE.json', {'method': 'complete original FP32 coordinate scan',
                                                         'logical_source_bytes_per_query': 3840000000,
                                                         'formula': '1000000 * 960 * 4', 'actual_DRAM': None,
                                                         'persistent_raw_source_bytes': 3840000000})
    valid = quality['false_negatives'] == quality['false_positives'] == quality['final_distance_bit_mismatches'] == 0
    valid = valid and recovery['bit_mismatches'] == 0 and recovery['raw_mapping_closed_before_search']
    valid = valid and recovery['representation_bytes'] <= contract['gates']['max_persistent_bytes']
    if not valid:
        decision = 'NO_GO_LOSSLESS_PROGRESSIVE'
    elif payload <= contract['gates']['GO_source_bytes_per_query']:
        decision = 'GO_LOSSLESS_BYTE_MODEL'
    elif payload <= contract['gates']['CONDITIONAL_max_source_bytes_per_query']:
        decision = 'CONDITIONAL'
    else:
        decision = 'NO_GO_LOSSLESS_PROGRESSIVE'
    save(root / 'evidence' / 'DECISION.json', {'Gate0': decision, 'quality_ownership_size_pass': valid,
                                             'source_bytes_per_query': payload,
                                             'GO_max_bytes_per_query': contract['gates']['GO_source_bytes_per_query'],
                                             'CONDITIONAL_max_bytes_per_query': 850000000,
                                             'Gate1': 'NOT_RUN' if decision != 'GO_LOSSLESS_BYTE_MODEL' else 'ADMITTED_NOT_RUN',
                                             'CPU_population_processes': 1, 'GPU_starts': 0, 'NCU_starts': 0,
                                             'scope': 'fixed ordered-FP32 representation and 4/8/16/32 schedule; not all lossless codecs'})
    print(json.dumps({'Gate0': decision, 'bytes_per_query': payload, 'mean_bits': mean_bits,
                      'stage_counts': stage_rows, 'quality': quality}, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--private', required=True, type=Path)
    p.add_argument('--root', required=True, type=Path)
    p.add_argument('--repo', required=True, type=Path)
    args = p.parse_args()
    analyze(args.private, args.root, args.repo)
