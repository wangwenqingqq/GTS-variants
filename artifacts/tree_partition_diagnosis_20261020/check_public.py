"""Portable source/scalar/custody checks; optional private archive hash check."""
if not __debug__:
    raise SystemExit('Assertions are mandatory.')
import argparse
import hashlib
from pathlib import Path
import sys
import tarfile
sys.dont_write_bytecode = True
from analyze import HERE, load, summarize, distribution

ROOT = HERE.parent.parent
PREFIX = 'artifacts/tree_partition_diagnosis_20261020/'
POPULATION_ANCHOR_SHA256 = '3f0e76e04bf5d233a445881f28611a189c054586b41bd75138f1412f38dc742f'


def identity(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(1048576), b''):
            h.update(b)
    return dict(bytes=Path(path).stat().st_size, sha256=h.hexdigest())


def check(root, archive=None):
    published = load(root/'evidence/PUBLISH_MANIFEST.json')['files']
    actual = {str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()}
    assert actual == set(published)|{'evidence/PUBLISH_MANIFEST.json'}
    assert all(not p.is_symlink() for p in root.rglob('*'))
    assert all(identity(root/n) == item for n,item in published.items())
    c = load(root/'CONTRACT.json')
    freeze = load(root/'SOURCE_FREEZE.json')
    assert freeze['before_population_and_verification'] and len(freeze['files']) == 12
    assert identity(root/'CONTRACT.json')['sha256'] == freeze['contract_sha256']
    for n,h in freeze['files'].items():
        f = root/n[len(PREFIX):] if n.startswith(PREFIX) else ROOT/n
        assert identity(f)['sha256'] == h
    assert identity(ROOT/'artifacts/fixed_batch_dag_gate0_20261019/CONTRACT.json')['sha256'] == c['input_identity']['old_query_contract_sha256']
    assert identity(ROOT/'artifacts/pdx_bond_gpu_realizability_gate4_20261015_recovery_01/evidence/INPUT_IDENTITY.json')['sha256'] == c['input_identity']['parent_identity_sha256']
    anchor_path = root/'evidence/POPULATION_ANCHORS.json'
    assert identity(anchor_path)['sha256'] == POPULATION_ANCHOR_SHA256
    anchors = load(anchor_path)
    assert anchors['before_verification'] and anchors['sources'] == freeze['files']
    assert len(anchors['files']) == 59
    archived = load(root/'evidence/ARCHIVE_MANIFEST.json')['files']
    assert {n[4:]:v['sha256'] for n,v in archived.items() if n.startswith('run/')} == anchors['files']
    assert identity(anchor_path) == archived['run.ANCHORS.json']
    bindings = {
        'evidence/VERIFICATION.json': 'verification/PROOF.json',
        'evidence/QUALIFICATION_O3.json': 'run/qualification/TESTS.json',
        'evidence/QUALIFICATION_O0.json': 'verification/qualification/TESTS.json',
        'evidence/EXECUTION_SOURCE_MANIFEST.json': 'EXECUTION_SOURCE_R1.json',
        'evidence/POPULATION_COMPLETE.json': 'run/COMPLETE.json',
        'evidence/RAW_CENSUS.json': 'RAW_CENSUS_R1.json',
    }
    for public,raw in bindings.items():
        assert identity(root/public) == archived[raw]
    proof = load(root/'evidence/VERIFICATION.json')
    assert proof['passed'] and proof['sources'] == freeze['files']
    assert proof['population_anchor_sha256'] == POPULATION_ANCHOR_SHA256
    assert proof['exact_population_commands'] == proof['original_population_starts'] == proof['verification_starts'] == 3
    assert proof['raw_campaign_files'] == 59
    assert proof['GPU_starts'] == proof['heldout_query_evaluations'] == 0
    assert [p['kind'] for p in proof['records']] == c['builders']
    results = {}
    for p in proof['records']:
        k = p['kind']
        assert p['passed'] and p['all_nodes_geometry_reconstructed'] == 8191
        assert p['all_internal_splits_reconstructed'] == 4095
        assert p['query_center_scores_bit_equal'] == 32*8191
        assert p['owner_oracle_all_pairs'] == 32000000
        assert p['every_query_and_level_checked'] and p['reverse_orientation_O0_cover']
        assert p['false_prune_nodes'] == p['GPU_starts'] == p['heldout_query_evaluations'] == 0
        assert p['population_anchor_sha256'] == POPULATION_ANCHOR_SHA256
        f = root/'results'/(k+'.json')
        assert identity(f) == archived['run/'+k+'/RESULTS.json']
        assert identity(f)['sha256'] == p['result_sha256'] == anchors['files'][k+'/RESULTS.json']
        results[k] = load(f)
    assert summarize(results,c) == load(root/'results/SUMMARY.json')
    assert distribution([None,None])['non_null'] == 0
    assert distribution([0,10])['p10'] == 1 and distribution([0,10])['p90'] == 9
    for suffix in ('O3','O0'):
        q = load(root/('evidence/QUALIFICATION_'+suffix+'.json'))
        assert q['passed'] and q['structural_fixture_cases'] == 9
        assert q['altered_scalar_records_rejected'] == 3 and q['raw_checkout_output_rejected']
        assert q['GPU_starts'] == 0
    src = load(root/'evidence/EXECUTION_SOURCE_MANIFEST.json')
    assert archived['EXECUTION_SOURCE_R1.tar']['sha256'] == src['archive_sha256']
    for n,item in src['files'].items():
        assert archived['source/'+n] == item
    custody = load(root/'evidence/CUSTODY.json')
    local = load(root/'evidence/LOCAL_VALIDATION.json')
    assert custody['archive_files'] == len(archived)
    assert custody['population_anchor_sha256'] == POPULATION_ANCHOR_SHA256
    assert custody['archive_manifest_sha256'] == identity(root/'evidence/ARCHIVE_MANIFEST.json')['sha256']
    assert custody['raw_census_sha256'] == identity(root/'evidence/RAW_CENSUS.json')['sha256']
    raw_census = load(root/'evidence/RAW_CENSUS.json')
    assert raw_census['before_archive']
    assert raw_census['files'] == {n:v for n,v in archived.items() if n != 'RAW_CENSUS_R1.json'}
    assert custody['remote_all_members_verified'] and custody['GPU_starts'] == custody['heldout_query_evaluations'] == 0
    assert local['passed'] and local['archive'] == custody['archive']
    assert local['all_members_independently_checked'] == len(archived)
    assert local['raw_census_rechecked'] == 59
    env = load(root/'evidence/ENVIRONMENT.json')
    assert env['nice'] == 10 and env['GPU_starts'] == 0
    assert env['population_registration'] == archived['run/REGISTERED.json']
    assert env['CPU_capture'] == archived['ENVIRONMENT_AFTER_POPULATION_R1.json']
    if archive is not None:
        assert identity(archive) == custody['archive']
        seen = set()
        with tarfile.open(archive, 'r:gz') as t:
            for m in t:
                assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
                assert m.name in archived and m.name not in seen
                h = hashlib.sha256()
                with t.extractfile(m) as f:
                    for b in iter(lambda: f.read(1048576), b''):
                        h.update(b)
                assert dict(bytes=m.size,sha256=h.hexdigest()) == archived[m.name]
                seen.add(m.name)
        assert seen == set(archived)
    return dict(passed=True, methods=3, old_queries=32, population_files=59,
                GPU_starts=0, heldout_query_evaluations=0,
                archive_checked=archive is not None,
                scope='Source/scalar/custody identities;full geometry replay remains a separate gate')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, default=HERE)
    p.add_argument('--archive', type=Path)
    a = p.parse_args()
    print(check(a.root.resolve(), a.archive))
