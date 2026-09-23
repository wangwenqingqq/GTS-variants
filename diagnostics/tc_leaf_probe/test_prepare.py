#!/usr/bin/env python3
"""CPU-only source/fixture regression; pass the original source root."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
spec=importlib.util.spec_from_file_location('probe_prepare',Path(__file__).with_name('prepare.py'))
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
local=Path(__file__).resolve().parent/'local';local.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(dir=local) as tmp:
    root=Path(tmp)
    for h in [3,5]:
        out=root/f'h{h}';p.prepare(Path(sys.argv[1]),out,h)
        source=(out/'GTS/include/search_v2.cuh').read_text()
        assert source.count('GTS_TC_EXPORT')==1
        assert 'GTS_TC_EXPORT' not in source.split('void searchIndexKnnV2(')[1]
        assert f'__managed__ int MAX_H = {h};' in (out/'GTS/include/tree.cuh').read_text()
        manifest=json.loads((out/'INSTRUMENTED_SHA256.json').read_text())
        assert all(hashlib.sha256((out/name).read_bytes()).hexdigest()==sha for name,sha in manifest.items())
        try:p.prepare(Path(sys.argv[1]),out,h)
        except FileExistsError:pass
        else:raise AssertionError('must refuse overwrite')
    f=root/'tiny.txt';f.write_text('128 2000 2\n'+(' '.join(str(i%256) for i in range(128))+'\n')*2000)
    p.fixture(f,root/'fixture',2000)
    assert (root/'fixture/q32.txt').read_text().splitlines()==['32']+[str(i*2000//32) for i in range(32)]
    f.write_text('128 2000 2\n'+' '.join(['0.5']*128)+'\n')
    try:p.fixture(f,root/'bad-fixture',2000)
    except AssertionError:pass
    else:raise AssertionError('must reject noninteger values')
print('PASS: pins, isolated range export, heights, manifests, no overwrite, fixture contract')
