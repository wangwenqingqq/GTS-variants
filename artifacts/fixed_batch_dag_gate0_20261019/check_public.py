"""Portable public scalar/source consistency gate; no private data or GPU."""
if not __debug__:
    raise SystemExit('Mandatory checks require ordinary Python.')
import argparse
import csv
from pathlib import Path
from prepare import load, sha


def check(root):
    m = load(root/'evidence/PUBLISH_MANIFEST.json')
    actual = {str(f.relative_to(root)) for f in root.rglob('*') if f.is_file()}
    assert actual == set(m['files'])|{'evidence/PUBLISH_MANIFEST.json'}
    for name,x in m['files'].items():
        f = root/name
        assert not f.is_symlink() and f.stat().st_size == x['bytes'] and sha(f) == x['sha256']
    anchors = load(root/'evidence/ANCHORS.json')
    archive = load(root/'evidence/ARCHIVE_MANIFEST.json')['files']
    assert {n[4:]:v for n,v in archive.items() if n.startswith('raw/')} == anchors['raw_files']
    assert len(archive) == 532 and len(anchors['raw_files']) == 518
    proof = load(root/'evidence/CLOSURE.json')
    for n,h in proof['checker_reference_sources'].items():
        assert sha(root/n) == h
    frozen = load(root/'evidence/EXECUTED_SOURCE_FREEZE.json')
    assert frozen['source_sha256'] == anchors['source_sha256']
    assert frozen['binary_sha256'] == anchors['binary_sha256']
    for n,h in frozen['source_sha256'].items():
        assert sha(root/n) == h
    execution = load(root/'evidence/CPU_EXECUTION.json')
    assert execution['passed'] and execution['CPU_processes'] == 28 and execution['GPU_starts'] == 0
    records = {r['label']:r for r in execution['records']}
    result = load(root/'results/RESULTS.json')
    prep = load(root/'evidence/INPUTS.json')
    assert result['passed'] and result['contract_sha256'] == sha(root/'CONTRACT.json')
    assert result['prepare_sha256'] == sha(root/'evidence/INPUTS.json') == frozen['prepare_sha256']
    assert result['execution_sha256'] == sha(root/'evidence/CPU_EXECUTION.json')
    assert prep['parent_results_sha256'] == anchors['parent_results_sha256']
    assert prep['parent_results_sha256'] == load(root/'evidence/PARENT_RESULTS_BINDING.json')['parent_results_sha256']
    batches = result['batch_results']
    assert len(batches) == 28 and {b['label'] for b in batches} == set(records)
    for b in batches:
        r = records[b['label']]
        assert r['returncode'] == 0 and r['GPU_starts'] == 0 and r['binary_sha256'] == anchors['binary_sha256']
        assert r['output_sha256'] == b['raw_output_sha256'] == anchors['raw_files']['campaign/runs/'+b['label']+'.csv']['sha256']
        assert b['source_bytes']['lower'] <= b['source_bytes']['upper'] <= b['source_bytes']['simple_envelope']
        assert b['source_bytes']['simple_envelope'] == min(b['source_bytes'][k] for k in ('trie','fanout','lookahead'))
        assert b['live_partial_bytes'] == 64*b['B'] and b['live_mask_bytes'] == b['B']
        assert b['tile_buffer_bytes'] == 1024
    for group in result['groups']:
        cells = [b for b in batches if b['B'] == group['B']]
        sums = {k:sum(b['source_bytes'][k] for b in cells) for k in cells[0]['source_bytes']}
        assert sums == group['source_bytes']
        assert group['source_bytes_per_query'] == {k:v/32 for k,v in sums.items()}
        e,lo,hi = sums['simple_envelope'],sums['lower'],sums['upper']
        assert group['envelope_headroom_proven'] == (e-hi)/e
        assert group['envelope_headroom_maximum'] == (e-lo)/e
        assert group['exact_sectors'] == sum(b['exact_sectors'] for b in cells)
    assert len(list(csv.DictReader((root/'results/summary.csv').open()))) == sum(len(g['source_bytes']) for g in result['groups'])
    print('PUBLIC_CONSISTENCY_PASS;28 CPU targets;0 GPU;not independent distance reproduction')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--artifact',type=Path,default=Path(__file__).resolve().parent)
    a = p.parse_args()
    check(a.artifact)
