"""Freeze query identities and reproduce development traces; no held-out scoring."""
if not __debug__:
    raise SystemExit('Mandatory checks require ordinary Python.')
import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
PARENT = HERE.parent/'fixed_batch_dag_gate0_20261019'


def load(path):
    return json.loads(path.read_text())


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True)+'\n').encode()


def save(path, value):
    with path.open('xb') as f:
        f.write(encoded(value))


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(8*1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def identity(path):
    assert path.is_file() and not path.is_symlink()
    return dict(bytes=path.stat().st_size, sha256=sha(path))


def selection(c):
    """Use identities only, never coordinates, orders, depths, or outcomes."""
    n = c['dataset']['N']
    excluded = set(c['development_qids'])
    seed = c['sampling']['query_seed']
    limit = (1 << 256)//n*n
    qids, counter = [], 0
    while len(qids) < c['sampling']['queries']:
        h = hashlib.sha256(f'BQSI-G1A-query:{seed}:{counter}'.encode()).digest()
        counter += 1
        value = int.from_bytes(h, 'big')
        q = value % n
        if value < limit and q not in excluded and q not in qids:
            qids.append(q)
    bseed = c['sampling']['batch_seed']
    permutation = sorted(range(len(qids)), key=lambda i: (
        hashlib.sha256(f'BQSI-G1A-batch:{bseed}:{qids[i]}'.encode()).digest(), i))
    batches = []
    for b in (2, 4, 8):
        for start in range(0, len(qids), b):
            group = permutation[start:start+b]
            batches.append(dict(label=f'b{b}_g{start//b:02}', B=b,
                                query_indices=group, qids=[qids[i] for i in group]))
    return dict(query_counter_end=counter, qids=qids, permutation=permutation,
                radius_bits=[c['radii']['parent_radius_bits']]*len(qids),
                threshold_hex=[c['radii']['parent_threshold_hex']]*len(qids),
                batches=batches, geometry_or_outcomes_used=False)


def check_sources():
    frozen = load(HERE/'SOURCE_FREEZE.json')
    required = {str((HERE/n).relative_to(ROOT)) for n in
                ('gate1a.py','test_gate1a.py','GATE1_CONTRACT.json','QUERY_SELECTION.json')}
    assert required <= set(frozen['files'])
    for name, item in frozen['files'].items():
        assert not Path(name).is_absolute() and '..' not in Path(name).parts
        assert identity(ROOT/name) == item, name
    c = load(HERE/'GATE1_CONTRACT.json')
    assert sha(PARENT/'CONTRACT.json') == c['parent']['contract_sha256']
    assert sha(PARENT/'evidence/PUBLISH_MANIFEST.json') == c['parent']['publish_manifest_sha256']
    manifest = load(PARENT/'evidence/PUBLISH_MANIFEST.json')['files']
    for name, item in manifest.items():
        assert identity(PARENT/name) == item, name
    s = load(HERE/'QUERY_SELECTION.json')
    assert s == selection(c)
    assert sha(HERE/'QUERY_SELECTION.json') == c['query_selection_sha256']
    assert c['development_qids'] == load(PARENT/'CONTRACT.json')['qids']
    assert c['radii']['parent_threshold_hex'] == load(PARENT/'CONTRACT.json')['threshold_hex']
    assert c['dataset']['sha256'] == load(PARENT/'CONTRACT.json')['data_sha256']
    assert len(set(s['qids'])) == 128 and not set(s['qids']) & set(c['development_qids'])
    for b in (2, 4, 8):
        cells = [x for x in s['batches'] if x['B'] == b]
        assert len(cells) == 128//b
        assert sorted(i for x in cells for i in x['query_indices']) == list(range(128))
    return c, s


def extract(data, out):
    c, s = check_sources()
    spec = c['dataset']
    assert data.is_file() and data.stat().st_size == spec['file_bytes']
    assert sha(data) == spec['sha256']
    out.mkdir()
    records, payload, old_hashes = [], bytearray(), set()
    with data.open('rb') as f:
        assert f.read(12) == struct.pack('<iii', spec['D'], spec['N'], 2)
        def row(q):
            f.seek(12+q*spec['D']*4)
            value = f.read(spec['D']*4)
            assert len(value) == spec['D']*4
            assert all(abs(x) < float('inf') for x in struct.unpack('<960f', value))
            return value
        for q in c['development_qids']:
            old_hashes.add(hashlib.sha256(row(q)).hexdigest())
        for i, q in enumerate(s['qids']):
            value = row(q)
            h = hashlib.sha256(value).hexdigest()
            assert h not in old_hashes and h not in {x['vector_sha256'] for x in records}, 'Duplicate vector: stop without redraw.'
            records.append(dict(index=i, qid=q, vector_bytes=len(value), vector_sha256=h,
                                radius_bits=s['radius_bits'][i], threshold_hex=s['threshold_hex'][i]))
            payload.extend(value)
    assert sha(data) == spec['sha256']
    with (out/'HELDOUT_QUERIES.f32').open('xb') as f:
        f.write(payload)
    receipt = dict(contract_sha256=sha(HERE/'GATE1_CONTRACT.json'),
                   selection_sha256=sha(HERE/'QUERY_SELECTION.json'),
                   source_freeze_sha256=sha(HERE/'SOURCE_FREEZE.json'),
                   dataset_sha256_before=spec['sha256'], dataset_sha256_after=spec['sha256'],
                   vectors=identity(out/'HELDOUT_QUERIES.f32'), records=records,
                   exact_vector_duplicates=0, distance_evaluations=0,
                   heldout_orders_generated=0, heldout_depths_generated=0,
                   heldout_oracle_starts=0, heldout_evaluation_starts=0, GPU_starts=0)
    save(out/'INPUT_MANIFEST.json', receipt)
    return receipt


def replay(data, parent_raw, out):
    c, _ = check_sources()
    assert os.getpriority(os.PRIO_PROCESS, 0) == c['resource']['nice'] == 10
    out.mkdir()
    save(out/'REGISTERED.json', dict(before_vector_extraction_and_development_targets=True,
         contract_sha256=sha(HERE/'GATE1_CONTRACT.json'), source_freeze_sha256=sha(HERE/'SOURCE_FREEZE.json'),
         data_path=str(data), parent_raw_path=str(parent_raw), output_path=str(out),
         Python_version=subprocess.check_output(['python3', '--version'], text=True).strip(),
         nice=os.getpriority(os.PRIO_PROCESS, 0), CPU_population_process_budget=28,
         heldout_evaluation_budget=0, GPU_start_budget=0))
    try:
        inputs = extract(data, out/'heldout')
        env = {**os.environ, 'PYTHONDONTWRITEBYTECODE':'1', 'OPENBLAS_NUM_THREADS':'1', 'OMP_NUM_THREADS':'1'}
        steps = [
            ('prepare', ['python3', str(PARENT/'prepare.py'), '--parent-raw', str(parent_raw), '--out', str(out/'dev_inputs')]),
            ('run', ['python3', str(PARENT/'run_cpu.py'), '--inputs', str(out/'dev_inputs'), '--work', str(out/'dev_campaign')]),
            ('analyze', ['python3', str(PARENT/'analyze.py'), '--inputs', str(out/'dev_inputs'), '--runs', str(out/'dev_campaign'), '--out', str(out/'dev_analysis')])]
        for name, command in steps:
            check_sources()
            save(out/(name+'.command.json'), dict(command=command, before_start=True))
            start = time.monotonic()
            p = subprocess.run(command, capture_output=True, text=True, env=env)
            (out/(name+'.stdout')).write_text(p.stdout)
            (out/(name+'.stderr')).write_text(p.stderr)
            save(out/(name+'.exit.json'), dict(returncode=p.returncode, elapsed_seconds=time.monotonic()-start))
            assert p.returncode == 0, (name, p.stdout[-2000:], p.stderr[-2000:])
        proof = verify_run(out)
        assert inputs == load(out/'heldout/INPUT_MANIFEST.json')
        save(out/'PROOF.json', proof)
        print('GATE1A_PASS:128 held-out identities;28 exact development replays;0 held-out evaluations;0 GPU')
    except BaseException as e:
        save(out/'FAILURE.json', dict(error=repr(e), heldout_evaluation_starts=0, GPU_starts=0))
        raise


def verify_run(out):
    c, s = check_sources()
    receipt = load(out/'heldout/INPUT_MANIFEST.json')
    assert receipt['contract_sha256'] == sha(HERE/'GATE1_CONTRACT.json')
    assert receipt['selection_sha256'] == sha(HERE/'QUERY_SELECTION.json')
    assert receipt['source_freeze_sha256'] == sha(HERE/'SOURCE_FREEZE.json')
    assert receipt['dataset_sha256_before'] == receipt['dataset_sha256_after'] == c['dataset']['sha256']
    assert receipt['vectors'] == identity(out/'heldout/HELDOUT_QUERIES.f32')
    assert receipt['vectors']['bytes'] == 128*960*4
    assert len(receipt['records']) == 128
    payload = (out/'heldout/HELDOUT_QUERIES.f32').read_bytes()
    for i, row in enumerate(receipt['records']):
        assert row == dict(index=i, qid=s['qids'][i], vector_bytes=3840,
                           vector_sha256=hashlib.sha256(payload[i*3840:(i+1)*3840]).hexdigest(),
                           radius_bits=s['radius_bits'][i], threshold_hex=s['threshold_hex'][i])
    for k in ('distance_evaluations','heldout_orders_generated','heldout_depths_generated',
              'heldout_oracle_starts','heldout_evaluation_starts','GPU_starts','exact_vector_duplicates'):
        assert receipt[k] == 0
    assert {p.name for p in (out/'heldout').iterdir()} == {'HELDOUT_QUERIES.f32', 'INPUT_MANIFEST.json'}
    old = load(PARENT/'results/RESULTS.json')
    result = load(out/'dev_analysis/RESULTS.json')
    prep = load(out/'dev_inputs/PREPARE.json')
    assert prep == load(PARENT/'evidence/INPUTS.json')
    assert result['passed'] and result['new_distance_evaluations'] == result['GPU_starts'] == 0
    assert result['groups'] == old['groups'] and result['batch_results'] == old['batch_results']
    execution = load(out/'dev_campaign/RUNS.json')
    assert execution['passed'] and execution['CPU_processes'] == 28 and execution['GPU_starts'] == 0
    assert result['execution_sha256'] == sha(out/'dev_campaign/RUNS.json')
    starts = [json.loads(x) for x in (out/'dev_campaign/STARTS.jsonl').read_text().splitlines()]
    assert len(starts) == 28 and {x['label'] for x in starts} == {b['label'] for b in prep['batches']}
    anchor = load(PARENT/'evidence/ANCHORS.json')['raw_files']
    for b in prep['batches']:
        f = out/'dev_campaign/runs'/(b['label']+'.csv')
        assert identity(f) == anchor['campaign/runs/'+f.name]
        assert identity(out/'dev_inputs'/(b['label']+'.bin')) == dict(bytes=b['input_bytes'], sha256=b['input_sha256'])
    for name in ('prepare','run','analyze'):
        assert load(out/(name+'.exit.json'))['returncode'] == 0
    registered = load(out/'REGISTERED.json')
    assert registered['before_vector_extraction_and_development_targets']
    assert registered['contract_sha256'] == receipt['contract_sha256']
    assert registered['source_freeze_sha256'] == receipt['source_freeze_sha256']
    assert registered['nice'] == 10
    for name in ('REGISTERED.json','START.json'):
        record = load(out/'dev_campaign'/name)
        assert record['nice'] == 10
        assert all(sha(PARENT/n) == h for n,h in record['source_sha256'].items())
    assert sha(out/'dev_campaign/build/solver') == load(out/'dev_campaign/BUILD.json')['binary_sha256']
    assert not (out/'FAILURE.json').exists()
    check_sources()
    return dict(passed=True, phase='GATE1A_ONLY',
                contract_sha256=sha(HERE/'GATE1_CONTRACT.json'),
                selection_sha256=sha(HERE/'QUERY_SELECTION.json'),
                input_manifest_sha256=sha(out/'heldout/INPUT_MANIFEST.json'),
                source_freeze_sha256=sha(HERE/'SOURCE_FREEZE.json'),
                development_results_sha256=sha(out/'dev_analysis/RESULTS.json'),
                development_batches=28, development_CSV_byte_identical=28,
                all_317807_development_contexts_reproduced=True,
                development_groups=result['groups'], heldout_queries=128,
                heldout_evaluation_starts=0, heldout_distances_computed=0, GPU_starts=0,
                Gate1B='NOT_STARTED', Gate1C='NOT_STARTED', novelty='NOT_ADMITTED')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='mode', required=True)
    sub.add_parser('check-protocol')
    r = sub.add_parser('replay')
    r.add_argument('--data', type=Path, required=True)
    r.add_argument('--parent-raw', type=Path, required=True)
    r.add_argument('--out', type=Path, required=True)
    v = sub.add_parser('verify-run')
    v.add_argument('--work', type=Path, required=True)
    a = p.parse_args()
    if a.mode == 'check-protocol':
        check_sources()
        print('PROTOCOL_PASS;not a held-out outcome or GPU admission')
    elif a.mode == 'replay':
        replay(a.data.resolve(), a.parent_raw.resolve(), a.out.resolve())
    else:
        assert verify_run(a.work.resolve()) == load(a.work/'PROOF.json')
        print('RUN_BINDING_PASS;Gate1A only')
