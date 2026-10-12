#!/usr/bin/env python3
"""Bind every selected payload to the frozen raw/small manifests, then rehash."""
import hashlib
import json
from pathlib import Path


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(8 << 20), b''):
            h.update(block)
    return h.hexdigest()


def verify_inputs(inputs, task):
    contract = json.loads((task/'CONTRACT.json').read_text())
    selected = json.loads((task/'evidence/INPUT_MANIFEST.json').read_text())
    small_pin = 'e12f27f62d2bbbfa1f6dc62a3b8d49ce1d377e0ccc95d1db6b5d17da75855a37'
    pins = {'CLOSURE.json': contract['baseline_closure_sha256'],
            'RAW_MANIFEST.json': contract['baseline_raw_manifest_sha256'],
            'summary_final/RESULT.json': contract['baseline_result_sha256'],
            'SMALL_RAW_MANIFEST.json': small_pin}
    for name, expected in pins.items():
        assert sha(inputs/name) == expected, name
    raw = json.loads((inputs/'RAW_MANIFEST.json').read_text())
    small = json.loads((inputs/'SMALL_RAW_MANIFEST.json').read_text())
    closure = json.loads((inputs/'CLOSURE.json').read_text())
    assert closure['passed'] and sha(inputs/'CONTRACT.json') == closure['contract_sha256']
    for name, entry in selected.items():
        relative = Path(name)
        assert not relative.is_absolute() and '..' not in relative.parts
        if name not in pins:
            origin = raw if entry['source'] == 'baseline raw manifest' else small
            assert name in origin
            assert {k: entry[k] for k in ('bytes', 'sha256')} == origin[name], name
        assert (inputs/name).stat().st_size == entry['bytes'], name
        assert sha(inputs/name) == entry['sha256'], name
    required = set(pins) | {'CONTRACT.json'}
    for r in (1, 2):
        for state in ('PRE', 'POST'):
            required.update(f'prior_snapshots/{state}_R{r}/{n}' for n in
                            ('base.i32', 'live.i32', 'order.i32', 'nodes.bin', 'empty.i32'))
        for mode in ('PRE', 'C3'):
            required.update(f'runs/R{r}_{mode}/{n}' for n in
                            ('order.i32', 'nodes.bin', 'empty.i32', 'DECISIONS.csv', 'REPLAY.json', 'PROCESS.json'))
            required.update(f'runs/R{r}_{mode}/audit/build0/level3.{n}' for n in
                            ('input.order', 'distance.keys', 'distance.pids', 'sorted.order', 'sorted.keys'))
    assert set(selected) == required
    return {'passed': True, 'files': len(selected),
            'bytes': sum(v['bytes'] for v in selected.values()),
            'input_manifest_sha256': sha(task/'evidence/INPUT_MANIFEST.json'),
            'raw_manifest_sha256': pins['RAW_MANIFEST.json'],
            'small_manifest_sha256': small_pin,
            'scope': 'All selected structural, actual L3 pivot, input-order and encoded-key bytes. Coordinates are inherited from prior host closure, not re-read here.'}
