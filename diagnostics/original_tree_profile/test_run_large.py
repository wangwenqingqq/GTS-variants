#!/usr/bin/env python3
"""CPU-only check of fresh scale-run directories and source hash coverage."""
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch
import run_large


with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp)
    for directory in ['source','bin','fixtures']:
        (root/directory).mkdir()
    (root/'source/check.cuh').write_text('fixture source\n')
    (root/'fixtures/manifest.json').write_text(json.dumps({
        'file_sha256':{},'cases':{'words_65536':{}}}))
    original_open=Path.open
    def local_open(path,*args,**kwargs):
        if str(path)=='/tmp/gtspp_gpu0.lock':path=root/'gpu.lock'
        return original_open(path,*args,**kwargs)
    def invoke(root,uuid,label,*args):
        (root/'runs'/label).mkdir()
        return True
    with patch.object(sys,'argv',['run_large.py',str(root),'--gpu','test-only']), \
         patch.object(run_large.base,'snapshot',return_value={'apps':'','gpu':'0, test-only'}), \
         patch.object(run_large.base,'invoke',side_effect=invoke) as launched, \
         patch.object(Path,'open',local_open):
        run_large.main()
        assert launched.call_count==48
    pins=json.loads((root/'SOURCE_BINARY_INPUT_SHA256.json').read_text())
    assert pins['source/check.cuh']==run_large.base.sha(root/'source/check.cuh')
    assert len(list((root/'runs').iterdir()))==48
print('PASS: fresh scale directories, 48 mocked runs, source hashes; no GPU calls')
