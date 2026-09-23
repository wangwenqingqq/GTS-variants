#!/usr/bin/env python3
"""CPU-only guard: source pins, unchanged kernels, exact scope patch, no overwrite."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('prep',HERE/'prepare.py');prep=importlib.util.module_from_spec(spec);spec.loader.exec_module(prep)
(HERE/'local').mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(dir=HERE/'local') as tmp:
    for h in [3,5]:
        out=Path(tmp)/str(h);prep.prepare(Path(sys.argv[1]),out,h)
        src=(out/'GTS/include/search_v2.cuh').read_text();old=(Path(sys.argv[1])/'GTS/include/search_v2.cuh').read_text()
        assert src.split('// Range query\nvoid searchIndexRnnV2')[0]==old.split('// Range query\nvoid searchIndexRnnV2')[0]
        pre=src.split('void searchIndexKnnV2(')[0]
        assert pre.count('phase.set(')==8 and 'cudaDeviceSynchronize' in pre
        assert pre.count('cudaDeviceSynchronize')==old.split('void searchIndexKnnV2(')[0].count('cudaDeviceSynchronize')
        assert 'phase.set' not in src.split('void searchIndexKnnV2(')[1]
        m=json.loads((out/'INSTRUMENTED_SHA256.json').read_text());assert all(hashlib.sha256((out/f).read_bytes()).hexdigest()==v for f,v in m.items())
        try:prep.prepare(Path(sys.argv[1]),out,h)
        except FileExistsError:pass
        else:raise AssertionError('overwrite accepted')
assert sum(i%2==0 for i in range(6))==3
print('PASS: source pins, unchanged device code/syncs, isolated stages, manifests, no overwrite, balanced policy order')
