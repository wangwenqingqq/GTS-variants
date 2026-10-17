"""Post-run independent source-to-result closure. Never launch a measured target."""
if not __debug__:
    raise SystemExit('Mandatory checks require ordinary Python.')
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import cost
import metadata
import replay

HERE = Path(__file__).resolve().parent
PROOF = 'CLOSED_IDENTITY.json'
EXCLUDED = {'postrun', 'independent_recheck_v1', 'archives', 'published'}


def load(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest(path, expected, size=None):
    assert path.is_file() and sha(path) == expected, ('Identity mismatch', path.name)
    assert size is None or path.stat().st_size == size


def input_identity(identity, frozen):
    assert identity == frozen, 'Self-reported inputs differ from the frozen CPU contract'


def command_identity(record, expected, binary, input_hash, contract_hash):
    assert record == dict(command=expected, binary_sha256=binary,
                          input_sha256=input_hash, contract_sha256=contract_hash)


def completed(record, label, input_hash, binary, output):
    assert record['label'] == label and record['returncode'] == 0
    assert record['input_sha256'] == input_hash and record['binary_sha256'] == binary
    assert record['GPU_starts'] == 0 and record['wall_seconds'] >= 0
    digest(output, record['output_sha256'])


def raw_inventory(work):
    bundled = load(work/'BUNDLE.json')['files']
    names = set(bundled) | {'BUNDLE.json', 'BUILD.json', 'RUNS.json',
                           'CPU_STARTS.jsonl', 'CPU_COST_SUMMARY.json',
                           'build/cpu_cost', 'build/compile.stdout', 'build/compile.stderr'}
    for book in cost.BOOKS:
        for r in range(6):
            label = f'{book}_r{r}'
            names.add('runs/'+label+'.csv')
            names.update('receipts/'+label+suffix for suffix in
                         ('.command.json', '.result.json', '.stdout', '.stderr'))
    actual = {str(f.relative_to(work)) for f in work.rglob('*')
              if f.is_file() and f.relative_to(work).parts[0] not in EXCLUDED
              and str(f.relative_to(work)) != PROOF}
    assert actual == names, ('Extra/missing raw files', actual ^ names)
    assert all(not (work/name).is_symlink() for name in names)
    return names


def reference_sources():
    return {name: sha(HERE/name) for name in
            ('bind.py', 'replay.py', 'cost.py', 'metadata.py', 'capture.py',
             'SOURCES.json', 'CONTRACT.json', 'CPU_COST_CONTRACT.json', 'EVIDENCE_ANCHORS.json')}


def source_checks(work):
    anchors = load(HERE/'EVIDENCE_ANCHORS.json')
    for name, h in anchors['files'].items():
        digest(work/name, h)
    source = work/'source/artifacts'
    measured = source/HERE.name
    digest(HERE/'CONTRACT.json', anchors['contract_sha256'])
    digest(HERE/'CPU_COST_CONTRACT.json', anchors['CPU_cost_contract_sha256'])
    digest(measured/'CONTRACT.json', anchors['contract_sha256'])
    digest(measured/'CPU_COST_CONTRACT.json', anchors['CPU_cost_contract_sha256'])
    assert load(work/'REGISTERED_R1.json')['contract_sha256'] == anchors['contract_sha256']
    for name, h in load(work/'SOURCE_FREEZE_R1.json').items():
        digest(measured/name, h)
        digest(HERE/name, h)
    reg = load(HERE/'CPU_COST_CONTRACT.json')
    for name, h in reg['source_sha256'].items():
        digest(measured/name, h)
        digest(HERE/name, h)
    sources = load(HERE/'SOURCES.json')
    for name, identity in sources['frozen_parent_files'].items():
        assert reg['source_parent_sha256'][name] == identity
        digest(source/name, identity['sha256'], identity['bytes'])
        digest(HERE.parent/name, identity['sha256'], identity['bytes'])
    for record in sources['upstream_inspected']:
        digest(work/'upstream_inspection'/record['source']/record['file'],
               record['sha256'], record['bytes'])
    for name, identity in load(work/'BUNDLE.json')['files'].items():
        digest(work/name, identity['sha256'], identity['bytes'])
    input_identity(load(work/'inputs/INPUTS.json'), reg['inputs'])
    build = load(work/'BUILD.json')
    assert build['passed'] and build['GPU_starts'] == 0
    assert type(build['CPU_core']) is int and build['CPU_core'] >= 0
    assert build['binary_sha256'] == anchors['binary_sha256']
    digest(work/'build/cpu_cost', anchors['binary_sha256'])
    assert build['contract_sha256'] == anchors['CPU_cost_contract_sha256']
    assert build['bundle_sha256'] == anchors['files']['BUNDLE.json']
    return reg, build


def executions(work, reg, build):
    starts = [json.loads(line) for line in (work/'CPU_STARTS.jsonl').read_text().splitlines()]
    expected = [(book, r) for r in range(6) for book in sorted(cost.BOOKS)]
    assert len(starts) == len(expected) == 12
    rows = []
    for start, (book, r) in zip(starts, expected):
        label = f'{book}_r{r}'
        assert start['label'] == label and start['round'] == r and start['GPU'] is False
        identity = reg['inputs']['files'][book+'.bin']
        f, output = work/'inputs'/(book+'.bin'), work/'runs'/(label+'.csv')
        digest(f, identity['sha256'], identity['bytes'])
        expected_command = ['taskset', '-c', str(build['CPU_core']), str(work/'build/cpu_cost'),
                            str(f), str(r), str(output)]
        command_identity(load(work/'receipts'/(label+'.command.json')), expected_command,
                         build['binary_sha256'], identity['sha256'], sha(HERE/'CPU_COST_CONTRACT.json'))
        row = load(work/'receipts'/(label+'.result.json'))
        completed(row, label, identity['sha256'], build['binary_sha256'], output)
        assert (work/'receipts'/(label+'.stdout')).read_text().strip() == f"CPU_COST_PASS {identity['cases']} batches;GPU starts 0"
        assert not (work/'receipts'/(label+'.stderr')).read_bytes()
        rows.append(row)
    result = load(work/'RUNS.json')
    assert result == dict(passed=True, CPU_processes=12, GPU_starts=0, records=rows)


def same_tree(left, right):
    a = {str(f.relative_to(left)) for f in left.rglob('*') if f.is_file()}
    b = {str(f.relative_to(right)) for f in right.rglob('*') if f.is_file()}
    assert a == b
    for name in a:
        assert (left/name).read_bytes() == (right/name).read_bytes(), ('Recheck differs', name)


def run(work):
    assert not (work/PROOF).exists()
    names = raw_inventory(work)
    before = {name: dict(sha256=sha(work/name), bytes=(work/name).stat().st_size) for name in sorted(names)}
    reg, build = source_checks(work)
    executions(work, reg, build)
    check = work/'independent_recheck_v1'
    check.mkdir()
    (check/'replay').mkdir()
    for book in (*cost.BOOKS, 'wikipedia-1M_expiration_time_replace_only_runbook'):
        original = work/'upstream_inspection/bigann/neurips23/runbooks'/(book+'.yaml')
        replay.replay(original, check/'replay'/book)
        same_tree(check/'replay'/book, work/'replay'/book)
    cost.prepare(check/'replay', check/'inputs')
    same_tree(check/'inputs', work/'inputs')
    cost.analyze(check/'inputs', work/'runs', check/'CPU_COST_SUMMARY.json')
    assert (check/'CPU_COST_SUMMARY.json').read_bytes() == (work/'CPU_COST_SUMMARY.json').read_bytes()
    replay.save(check/'METADATA.json', metadata.analyze(work/'raw_capture'))
    assert (check/'METADATA.json').read_bytes() == (work/'METADATA_R1.json').read_bytes()
    source = work/'source/artifacts'
    expected_compile = ['c++', '-std=c++17', '-O2', '-I', str(source/'dependency_update_mechanism_20261017'),
                        '-I', str(source/'ownership_safe_gpu_update_20261015'),
                        str(source/HERE.name/'cpu_cost.cpp'), '-o', str(work/'build/cpu_cost')]
    assert build['compile_command'] == expected_compile
    command = expected_compile[:-1]+[str(check/'cpu_cost')]
    result = subprocess.run(command, capture_output=True, text=True)
    (check/'compile.stdout').write_text(result.stdout)
    (check/'compile.stderr').write_text(result.stderr)
    assert result.returncode == 0 and not result.stderr, result.stderr
    digest(check/'cpu_cost', build['binary_sha256'])
    assert raw_inventory(work) == names
    for name, record in before.items():
        digest(work/name, record['sha256'], record['bytes'])
    proof = dict(schema=1, passed=True, references=reference_sources(), raw_files=before,
                 replay_and_input_regeneration_byte_identical=True, metadata_recomputed=True,
                 all_CPU_commands_exits_and_outputs_bound=True, CPU_processes=12, GPU_starts=0,
                 diagnostic_binary_recompiled_identically=True, no_measured_target_rerun=True,
                 scope='CPU structural and planning evidence only;not vector-service ACK or GPU admission')
    replay.save(work/PROOF, proof)
    require_closed(work)
    print('SOURCE_TO_RESULT_CLOSURE_PASS', len(names), 'raw files;12 CPU processes;0 GPU targets')


def checker_identity(proof, current, receipt, proof_hash):
    if proof['references'] != current:
        assert proof_hash == receipt['proof_sha256']
        previous = receipt['checker_reference_sources']
        assert proof['references'] == previous and set(previous) == set(current)
        assert all(current[n] == previous[n] for n in current if n != 'bind.py')


def require_closed(work):
    proof = load(work/PROOF)
    assert proof['schema'] == 1 and proof['passed'] and proof['CPU_processes'] == 12 and proof['GPU_starts'] == 0
    for key in ('replay_and_input_regeneration_byte_identical', 'metadata_recomputed',
                'all_CPU_commands_exits_and_outputs_bound', 'diagnostic_binary_recompiled_identically'):
        assert proof[key] is True
    checker_identity(proof, reference_sources(), load(HERE/'evidence/CLOSED_BINDING.json'),
                     sha(work/PROOF))
    assert set(proof['raw_files']) == raw_inventory(work)
    for name, record in proof['raw_files'].items():
        digest(work/name, record['sha256'], record['bytes'])
    source_checks(work)
    return proof


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--work', type=Path, required=True)
    p.add_argument('--check-seal', action='store_true')
    a = p.parse_args()
    if a.check_seal:
        require_closed(a.work)
        print('CLOSED_SEAL_PASS')
    else:
        run(a.work)
