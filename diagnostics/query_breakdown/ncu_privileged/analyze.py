#!/usr/bin/env python3
"""Curate counter values and derived instruction ledgers, never raw SASS/addresses."""
import argparse
from collections import defaultdict
import csv
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
COUNTS = {'warp_instructions': 'Instructions Executed', 'thread_instructions': 'Thread Instructions Executed',
          'predicated_thread_instructions': 'Predicated-On Thread Instructions Executed', 'stall_samples': 'Warp Stall Sampling (All Samples)'}
PROFILE_COUNTS = {'leaf_q128_r500_0': 1, 'leaf_q128_r500_1': 1, 'leaf_q32_r300': 1, 'aggregate_q128_r500': 1, 'node_q128_r500': 4}
PREFIXES = ('dram__', 'gpu__', 'l1tex__', 'lts__', 'launch__', 'sm__', 'smsp__', 'profiler__')

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def raw_metrics(path):
    with path.open() as f:
        reader = csv.DictReader(f); units = next(reader); rows = list(reader)
    assert units['Kernel Name'] == '' and rows
    return units, rows

def source_groups(path):
    groups = []; header = None
    with path.open() as f:
        for row in csv.reader(f):
            if row and row[0] == 'Kernel Name': groups.append({'function': row[1], 'rows': []})
            elif row and row[0] == 'Address': header = row
            elif row and row[0].startswith('0x'):
                assert groups and header
                d = dict(zip(header, row)); assert all(d[k].isdigit() for k in COUNTS.values())
                groups[-1]['rows'].append(d)
    assert groups and all(g['rows'] for g in groups)
    return groups

def summarize_group(group):
    rows = group['rows']; base = min(int(r['Address'], 16) for r in rows)
    totals = {k: sum(int(r[col]) for r in rows) for k, col in COUNTS.items()}
    opcodes = defaultdict(lambda: dict.fromkeys(COUNTS, 0)); sites = []
    for r in rows:
        words = r['Source'].strip().split(); op = words[1] if words[0].startswith('@') else words[0]
        counts = {k: int(r[col]) for k, col in COUNTS.items()}
        for k, v in counts.items(): opcodes[op][k] += v
        sites.append({'relative_pc': int(r['Address'], 16) - base, 'opcode': op, **counts})
    return {'function': group['function'], 'instruction_sites': len(rows), 'totals': totals,
            'entry': sites[0], 'executed_calls': [s for s in sites if s['opcode'].startswith('CALL') and s['warp_instructions']],
            'top_stall_sites': sorted(sites, key=lambda s: s['stall_samples'], reverse=True)[:10], 'opcodes': dict(opcodes)}

def analyze(root, out):
    out.mkdir(exist_ok=False)
    p = json.loads((root / 'provenance.json').read_text()); parent = json.loads((HERE.parent / 'EVIDENCE.json').read_text())
    assert p['bench5_sha256'] == parent['binary_sha256']['bench5'] and not p['apps_after'].strip()
    assert p['contract_sha256'] == sha(HERE / 'CONTRACT.md')
    for name, data in parent['static_functions'].items():
        assert p['static_functions'][name]['normalized_instruction_sha256'] == data['normalized_instruction_sha256']
    e = {'scope': 'Privileged NCU kernel-replay diagnostics only, not clean query timing or a speedup claim',
         'parent_commit': '11f93aae8357063407f84c337fd3ce0109a1bb16',
         'provenance': {k: v for k, v in p.items() if k not in ['gpu_after', 'apps_after']},
         'hardware': {'gpu': 'RTX PRO 6000 Blackwell Server Edition', 'physical_gpu': 0, 'sm_count': 188, 'driver': '590.48.01', 'toolkit': '13.1.115', 'clock_control': 'none', 'cache_control': 'none'},
         'workload': {'n': 65536, 'dimensions': 128, 'metric': 'L2', 'input_storage': 'float32 integer coordinates', 'primary_q_radius': [128, 500], 'boundary_q_radius': [32, 300]},
         'runs': {}, 'source': {}, 'private_raw_files': {},
         'delivery_source_sha256': {name: sha(HERE / name) for name in ['CONTRACT.md', 'README.md', 'run.py', 'analyze.py', 'test_analysis.py']}}
    with (out / 'metrics.csv').open('w', newline='') as f, (out / 'instruction_ledger.csv').open('w', newline='') as lf:
        w = csv.writer(f, lineterminator='\n'); w.writerow(['run', 'launch_ordinal', 'kernel', 'metric', 'unit', 'value'])
        lw = csv.writer(lf, lineterminator='\n'); lw.writerow(['run', 'source_group', 'function', 'opcode'] + list(COUNTS))
        for run in sorted(root.iterdir()):
            if not run.is_dir(): continue
            r = json.loads((run / 'receipt.json').read_text())
            assert r['exit_code'] == 0 and r['correct'] and r['post_clear'] and r['profiling_restriction_unchanged']
            assert r['binary_sha256'] == p['bench5_sha256'] and r['contract_sha256'] == p['contract_sha256']
            e['runs'][run.name] = {k: r[k] for k in ['exit_code', 'correct', 'post_clear', 'wall_s', 'binary_sha256', 'profiling_restriction_unchanged']}
            if run.name in PROFILE_COUNTS:
                units, launches = raw_metrics(run / 'raw.csv'); assert len(launches) == PROFILE_COUNTS[run.name]
                e['runs'][run.name]['launches'] = []
                for i, d in enumerate(launches):
                    kernel = d['Kernel Name']; assert kernel.startswith({'leaf': 'dataProcessRnn', 'aggregate': 'mergeResRnn', 'node': 'nodeProcessRnn'}[run.name.split('_')[0]])
                    e['runs'][run.name]['launches'].append({'ordinal': i, 'kernel': kernel, 'block': d['Block Size'], 'grid': d['Grid Size']})
                    for key, value in d.items():
                        if key.startswith(PREFIXES) and key != 'launch__function_pcs' and not key.endswith('_id'):
                            assert not re.search(r'0x[0-9a-f]+|/|\\', value, re.I), (key, value)
                            w.writerow([run.name, i, kernel, key, units[key], value])
                e['source'][run.name] = []
                for i, group in enumerate(source_groups(run / 'source.csv')):
                    s = summarize_group(group)
                    for op, counts in s.pop('opcodes').items():
                        if any(counts.values()): lw.writerow([run.name, i, s['function'], op] + [counts[k] for k in COUNTS])
                    e['source'][run.name].append(s)
                assert sum(s['totals']['warp_instructions'] for s in e['source'][run.name]) == sum(int(d['smsp__inst_executed.sum']) for d in launches)
            for file in sorted(run.iterdir()):
                if file.is_file(): e['private_raw_files'][str(file.relative_to(root))] = {'bytes': file.stat().st_size, 'sha256': sha(file)}
    assert len(e['runs']) == 7 and len(e['source']) == 5
    e['portable_tables_sha256'] = {name: sha(out / name) for name in ['metrics.csv', 'instruction_ledger.csv']}
    (out / 'EVIDENCE.json').write_text(json.dumps(e, indent=2, sort_keys=True) + '\n')
    print('PASS: seven runs, eight profiled launches, source totals match hardware warp instruction counts')

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('root', type=Path); p.add_argument('out', type=Path)
    a = p.parse_args(); analyze(a.root, a.out)
