#!/usr/bin/env python3
"""Publish a small explicit evidence whitelist; never copy private raw directories."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p): return json.loads(Path(p).read_text())
def write(p, x):
    assert not p.exists(), 'never overwrite curated evidence'
    p.write_text(json.dumps(x, indent=2)+'\n')


def curate(private, out):
    out.mkdir(parents=True, exist_ok=True)
    raw = private/'raw_cpu'; checked = private/'raw_cpu_quality'
    registration = read(raw/'CPU_REGISTERED.json')
    binding = read(checked/'CPU_QUALITY_BINDING.json')
    assert binding['registration_sha256'] == sha(raw/'CPU_REGISTERED.json')
    assert binding['executed_source_sha256'] == sha(private/'cpu.executed.py') == sha(HERE/'cpu.py')
    assert binding['analyst_sha256'] == sha(HERE/'qualify_cpu.py')
    assert binding['contract_sha256'] == sha(HERE/'CONTRACT.json')
    assert len(binding['jobs']) == len(registration['jobs']) == 6
    reports = []
    for job, bound in zip(registration['jobs'], binding['jobs']):
        label = job['label']; assert label == bound['label']
        receipt = read(raw/'cpu_guards'/label/'receipt.json')
        assert sha(raw/'cpu_guards'/label/'receipt.json') == bound['receipt_sha256']
        assert receipt['runtime_valid'] and not receipt['timed_out'] and receipt['exit_code'] == 0
        for name, digest in bound['output_hashes'].items(): assert sha(raw/'cpu_outputs'/name) == digest
        quality_path = checked/'cpu_outputs'/(label+'.quality.json')
        assert sha(quality_path) == bound['quality_sha256']
        proof = read(quality_path); assert proof['passed'] == bound['passed']
        native = read(raw/'cpu_outputs'/(label+'.native.json'))
        # Retain versions/hash and actual thread counts, but never site package paths.
        versions = {k:v for k,v in native['versions'].items() if k != 'pools'}
        versions['pools'] = [{k:v for k,v in pool.items() if k not in ('filepath', 'prefix')}
                              for pool in native['versions'].get('pools', [])]
        with (raw/'cpu_outputs'/(label+'.queries.csv')).open() as f: queries = list(csv.DictReader(f))
        keys = ('dtype','leaf_size','requested_native_threads','representation_bytes','index_bytes',
                'memory_before','memory_after_build','memory_final','preparation_ms','build_ms',
                'warmup_ms','timing','final_release_ms','trace_cpu_user_s','trace_cpu_system_s',
                'raw_field_kind','radius','scope','numpy','source_sha256','snapshot_sha256')
        reports.append(dict(label=label, snapshot=label.removesuffix('_'+job['method']), method=job['method'],
            native={**{k:native[k] for k in keys}, 'versions':versions},
            quality=proof, queries=queries, binding=bound,
            guard=dict(exit_code=receipt['exit_code'],runtime_valid=receipt['runtime_valid'],
                       wall_s=receipt['wall_s'],timed_out=receipt['timed_out'])))
    write(out/'CPU_RESULTS.json',dict(status='SIX_QUALIFIED_SINGLE_STATIC_DIAGNOSTICS_NOT_FORMAL_OR_DYNAMIC',
        registered_order=[j['label'] for j in registration['jobs']], reports=reports,
        registration_sha256=sha(raw/'CPU_REGISTERED.json'), quality_binding_sha256=sha(checked/'CPU_QUALITY_BINDING.json'),
        original_launcher_sha256=sha(private/'cpu_jobs.executed.py'),
        delivered_launcher_sha256=sha(HERE/'cpu_jobs.py'),
        launcher_difference='later portable registration helper; actual six native executions unchanged',
        faiss_extension_postrun_sha256='55dd5a3f8ab134e66ac41b7509597845d41dde9763c51917fb9a56f01d2f6e01',
        extension_binding_scope='live post-run inventory; original receipt captured Python binding hash, not this extension hash',
        no_new_GPU_kernel=True, all_quality_passed=binding['passed']))
    profiles = private/'raw_profiles'
    registration = read(profiles/'PROFILE_REGISTERED.json')
    assert registration['instrumentation_sha256'] == sha(HERE/'profile.py')
    assert registration['contract_sha256'] == sha(HERE/'CONTRACT.json')
    assert registration['prefix_sha256'] == sha(HERE/'REBUILD_PREFIX.txt')
    quality = read(private/'PROFILE_QUALITY_BOUND.json')
    assert all(q['analyst_sha256']==sha(HERE/'verify_profile.py') and q['parent_output_hashes_checked'] for q in quality)
    hashes = {Path(line.split()[1]).parts[1]:line.split()[0] for line in (private/'profile_raw_hashes.txt').read_text().splitlines()[:2]}
    guards = []
    for method in ('A','B'):
        folder = profiles/'profiles'/method; receipt = read(folder/'guard/receipt.json')
        assert receipt['runtime_valid'] and receipt['exit_code'] == 0 and receipt['stop_reason'] is None
        checks = read(folder/'guard/checks.json'); assert checks and not any(x['foreign'] for x in checks)
        assert not read(folder/'guard/before.json')['apps'] and not read(folder/'guard/after.json')['apps']
        for name, digest in next(q for q in quality if q['method']==method)['fresh_output_sha256'].items():
            assert sha(folder/name) == digest
        guards.append(dict(method=method,exit_code=0,runtime_valid=True,foreign_checks=len(checks),
            empty_GPU_before_after=True,wall_s=receipt['wall_s'],guard_receipt_sha256=sha(folder/'guard/receipt.json'),
            nsys_report_sha256=hashes[method],sqlite_sha256=sha(private/(method+'_trace.sqlite')),
            guard_command_executable_sha256=receipt['binary_sha256'],
            guard_command_hash_scope='nsys executable; instrumented target is separately bound',
            output_quality=next(q for q in quality if q['method']==method)))
    prepared = read(profiles/'profile_build_clean/PREPARED.json')
    assert sha(private/'profile_target.normalized.sass') == '7d0ff1767e79a2dbc1f8ea18e52d29015d3d5a99ce4491dab8836d75b5f40948'
    assert registration['binary_sha256'] == read(profiles/'profile_build_clean/BUILD.json')['binary_sha256']
    write(out/'PROFILE_BINDING.json',dict(source_pin=registration.get('source_pin',read(HERE/'CONTRACT.json')['source_pin']),
        contract_sha256=registration['contract_sha256'],instrumentation_sha256=registration['instrumentation_sha256'],
        prefix_sha256=registration['prefix_sha256'],registration_sha256=sha(profiles/'PROFILE_REGISTERED.json'),
        target_binary_sha256=registration['binary_sha256'],
        prepared_sha256=sha(profiles/'profile_build_clean/PREPARED.json'),profile_source_hashes=prepared['sources'],
        normalized_GPU_SASS_sha256=sha(private/'profile_target.normalized.sass'),
        functions=112,instructions=74144,instruction_count_scope='semicolon-terminated normalized instructions; excludes three container header lines',
        GPU_code_matches_parent=True,guards=guards,
        scope='diagnostic-only, one event48 per A/B; complete prefix/warmup byte identity to admitted exhaustive parent'))
    tree = read(private/'upstream_tree.json'); assert not tree['truncated']
    inspected = read(private/'upstream_audit/MANIFEST.json')
    write(out/'UPSTREAM_SOURCE_AUDIT.json',dict(upstream_pin=inspected['pin'],inspected_files=inspected['files'],
        recursive_tree_sha256=sha(private/'upstream_tree.json'),tree_truncated=False,
        license_named_files=[r['path'] for r in tree['tree'] if any(s in Path(r['path']).name.lower() for s in ('license','copying','copyright'))],
        scope='source/capability audit only; no new GPU_TREE binary/run or published third-party source'))


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--private',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();assert __debug__;curate(a.private,a.output)
