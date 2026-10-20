"""Portable hash/scalar gate; no private vectors, experiments, or GPU."""
if not __debug__:
    raise SystemExit('Mandatory checks require ordinary Python.')
import gate1a as g


def main():
    root = g.HERE
    manifest = g.load(root/'evidence/PUBLISH_MANIFEST.json')['files']
    actual = {str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()}
    assert actual == set(manifest)|{'evidence/PUBLISH_MANIFEST.json'}
    for n,item in manifest.items():
        assert g.identity(root/n) == item
    c,s = g.check_sources()
    anchors = g.load(root/'evidence/RAW_ANCHORS.json')
    assert g.sha(root/'evidence/RAW_ANCHORS.json') == '2c04d4512b35d6278a9ae56119f319ce5c9a6255bd65152ca43759923ba69af5'
    raw = anchors['raw_files']
    assert len(raw) == 450
    archived = g.load(root/'evidence/ARCHIVE_MANIFEST.json')['files']
    assert {n[4:]:v for n,v in archived.items() if n.startswith('raw/')} == raw
    custody = g.load(root/'evidence/CUSTODY.json')
    assert custody['archive_files'] == len(archived) == 713
    assert custody['raw_anchors_sha256'] == g.sha(root/'evidence/RAW_ANCHORS.json')
    assert custody['archive_manifest_sha256'] == g.sha(root/'evidence/ARCHIVE_MANIFEST.json')
    assert custody['remote_all_members_verified']
    local = g.load(root/'evidence/LOCAL_VALIDATION.json')
    assert local['passed'] and local['all_members_independently_checked'] == 713
    assert local['raw_census_rechecked'] == 450 and local['archive'] == custody['archive']
    assert g.identity(root/'evidence/RAW_ANCHORS.json') == archived['seal/RAW_ANCHORS_R1.json']
    inputs = g.load(root/'evidence/HELDOUT_INPUT_MANIFEST.json')
    assert g.identity(root/'evidence/HELDOUT_INPUT_MANIFEST.json') == raw['run/heldout/INPUT_MANIFEST.json']
    assert inputs['vectors'] == raw['run/heldout/HELDOUT_QUERIES.f32']
    assert inputs['vectors']['bytes'] == 128*960*4 and inputs['exact_vector_duplicates'] == 0
    assert [r['qid'] for r in inputs['records']] == s['qids']
    assert inputs['contract_sha256'] == g.sha(root/'GATE1_CONTRACT.json')
    assert inputs['selection_sha256'] == g.sha(root/'QUERY_SELECTION.json')
    assert inputs['source_freeze_sha256'] == g.sha(root/'SOURCE_FREEZE.json')
    for k in ('distance_evaluations','heldout_orders_generated','heldout_depths_generated',
              'heldout_oracle_starts','heldout_evaluation_starts','GPU_starts'):
        assert inputs[k] == 0
    dev = g.load(root/'results/DEVELOPMENT_REPRODUCTION.json')
    assert g.identity(root/'results/DEVELOPMENT_REPRODUCTION.json') == raw['run/PROOF.json']
    assert dev['development_groups'] == g.load(g.PARENT/'results/RESULTS.json')['groups']
    assert dev['development_CSV_byte_identical'] == dev['development_batches'] == 28
    assert dev['heldout_evaluation_starts'] == dev['GPU_starts'] == 0
    assert dev['Gate1B'] == dev['Gate1C'] == 'NOT_STARTED'
    assert dev['development_results_sha256'] == raw['run/dev_analysis/RESULTS.json']['sha256']
    closure = g.load(root/'evidence/CLOSURE.json')
    assert closure['passed']
    assert g.identity(root/'evidence/CLOSURE.json') == archived['postrun/closure_v1/CHECK_PROOF.json']
    assert closure['raw_anchors_sha256'] == g.sha(root/'evidence/RAW_ANCHORS.json')
    assert closure['checker_sha256'] == g.sha(root/'check_evidence.py')
    assert closure['dataset_sha256'] == c['dataset']['sha256']
    assert closure['raw_files'] == 450 and closure['original_rows_byte_equal'] == 128
    assert closure['exact_development_commands'] == 28
    assert closure['all_raw_commands_logs_exits_qualification_bound']
    assert closure['identical_binary_rebuild'] and closure['all_contexts_reanalyzed']
    tests = g.load(root/'evidence/TAMPER_TESTS.json')
    assert g.identity(root/'evidence/TAMPER_TESTS.json') == archived['postrun/tamper_v1/TESTS.json']
    assert tests['passed'] and len(tests['counterfactual_mutations_rejected']) == 8
    assert tests['raw_anchors_sha256'] == closure['raw_anchors_sha256']
    assert tests['sealed_originals_unchanged']
    for n,item in g.load(root/'evidence/CHECKER_SOURCE.json')['files'].items():
        assert g.identity(root/n) == item
        assert archived['checker_source/artifacts/fixed_batch_dag_gate1a_20261020/'+n] == item
    print('PUBLIC_PASS:128 frozen identities;28 development replays;0 heldout outcomes;Gate1B/C pending')


if __name__ == '__main__':
    main()
