#!/usr/bin/env python3
"""Validate and summarize the bounded original/reset update experiment receipts."""
import argparse
import csv
import json
from pathlib import Path
from prepare import sha, validate


def analyze(root, out):
    manifest = json.loads((root/'manifest.json').read_text())
    pins = json.loads((Path(__file__).resolve().parent.parent/'original_tree_redundancy/SOURCE_PINS.json').read_text())
    assert manifest['source_commit'] == pins['commit']
    assert manifest['source_sha256'] == {f.removeprefix('GTS/'): h for f, h in pins['sha256'].items() if f.startswith('GTS/')}
    cases = list(manifest['cases'])
    groups = {'original_clean': cases,
              'original_memcheck': ['buffer_delete', 'rebuild_after_buffer_query'],
              'rnum_reset_clean': cases, 'rnum_reset_memcheck': cases,
              'rnum_reset_synccheck': cases, 'original_verified_clean': cases}
    expected_labels = {group+'_'+case for group, items in groups.items() for case in items}
    receipts = {p.parent.name: json.loads(p.read_text()) for p in (root/'runs').glob('*/receipt.json')}
    assert set(receipts) == expected_labels
    build = {v: json.loads((root/'logs'/(v+'.build.json')).read_text())
             for v in ['gts_original_verified', 'gts_rnum_reset']}
    for value in build.values():
        assert value['exit_code'] == 0
    for label, record in receipts.items():
        assert record['exit_code'] == 0 and record['stop_reason'] is None, label
        assert not record['runtime_errors'] and record['post_gpu_clear'] and record['sanitizer_ok'], label
        assert record['manifest_sha256'] == sha(root/'manifest.json')
        assert record['input_sha256']['data.txt'] == manifest['data_sha256']
        assert record['input_sha256'][record['case']+'.updates'] == manifest['cases'][record['case']]['updates_sha256']
        expected = manifest['cases'][record['case']]['expected_counts']
        assert record['validation'] == validate((root/'runs'/label/'cost.txt').read_text(), expected)
        for moment in ['before', 'after']:
            assert not json.loads((root/'runs'/label/('gpu_'+moment+'.json')).read_text())['apps'].strip()
        assert all(not x['foreign'] for x in json.loads((root/'runs'/label/'admission_checks.json').read_text()))
        if record['mode'] != 'clean':
            logs = ''.join((root/'runs'/label/(f+'.log')).read_text() for f in ['stdout', 'stderr'])
            assert 'ERROR SUMMARY: 0 errors' in logs, label
        if record['binary_name'] in build:
            assert record['binary_sha256'] == build[record['binary_name']]['binary_sha256']
        if label.startswith('rnum_reset_'):
            assert record['validation']['pass'], label
    failures = {'buffer_delete': [2, 2], 'rebuild_after_buffer_query': [2, 12, 12]}
    rows = []
    for case in cases:
        original = receipts['original_clean_'+case]['validation']
        assert original == receipts['original_verified_clean_'+case]['validation'], case
        assert original['actual'] == failures.get(case, original['expected'])
        assert original['pass'] == (case not in failures)
        rows.append({'case': case, 'expected': original['expected'], 'original': original['actual'],
                     'original_pass': original['pass'],
                     'rnum_reset': receipts['rnum_reset_clean_'+case]['validation']['actual'],
                     'memcheck': 'PASS', 'synccheck': 'PASS'})
    for case in failures:
        assert receipts['original_memcheck_'+case]['validation'] == receipts['original_clean_'+case]['validation']
    variant = json.loads((root/'variants/rnum_reset/VARIANT.json').read_text())
    assert variant['original_source_sha256'] == manifest['source_sha256']
    changed = [f for f, h in manifest['source_sha256'].items() if variant['source_sha256'][f] != h]
    assert changed == ['include/update.cuh']
    assert build['gts_rnum_reset']['source_sha256'] == variant['source_sha256']
    assert build['gts_original_verified']['source_sha256'] == manifest['source_sha256']
    for f, h in manifest['source_sha256'].items():
        assert sha(root/'source'/f) == h, f
        assert sha(root/'variants/rnum_reset'/f) == variant['source_sha256'][f], f
    before = (root/'source/include/update.cuh').read_bytes()
    after = (root/'variants/rnum_reset/include/update.cuh').read_bytes()
    assert after.replace(b'\t\t\trnum[0] = 0;\n', b'', 1) == before
    evidence = {'source_commit': manifest['source_commit'], 'contract': manifest,
                'total_processes': len(receipts),
                'original_clean_pass': 7, 'original_clean_fail': 2,
                'original_independent_build_cases_reproduced': len(cases),
                'original_failing_cases_memcheck_zero_errors': 2,
                'rnum_reset_clean_pass': len(cases), 'rnum_reset_memcheck_pass': len(cases),
                'rnum_reset_synccheck_pass': len(cases),
                'binary_sha256': {name: sorted({r['binary_sha256'] for r in receipts.values() if r['binary_name'] == name})
                                  for name in sorted({r['binary_name'] for r in receipts.values()})},
                'runner_sha256': sorted({r['runner_sha256'] for r in receipts.values()}),
                'variant': variant, 'cases': rows,
                'raw_sha256': {str(p.relative_to(root)): sha(p) for p in sorted(root.rglob('*')) if p.is_file()},
                'scope': 'Nine synthetic integer-L2 count probes, N1000 D128; not full IDs/distances, general update correctness or performance.'}
    out.mkdir(parents=True, exist_ok=False)
    (out/'EVIDENCE.json').write_text(json.dumps(evidence, indent=2)+'\n')
    with (out/'cases.csv').open('w') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    print(json.dumps({k: v for k, v in evidence.items() if k.endswith(('pass','fail','reproduced','errors')) or k == 'total_processes'}, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('root', type=Path); p.add_argument('out', type=Path)
    a = p.parse_args(); analyze(a.root.resolve(), a.out.resolve())
