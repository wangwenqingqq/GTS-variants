#!/usr/bin/env python3
"""Postmeasurement integrity revision: valid build passes, mixed/tampered fails."""
import tempfile
from aabb_math import *

def main():
    with tempfile.TemporaryDirectory() as directory:
        out=Path(directory);raw=out/'aabb_raw.npz';raw.write_bytes(b'synthetic raw payload')
        receipt=out/'BUILD_VALIDATION.json'
        def setup(state='PASS',freeze=None):
            receipt.write_text(json.dumps(dict(status=state,source_freeze_sha256=freeze or sha(HERE/'evidence/SOURCE_FREEZE.json'))))
            (out/'OUTPUT_MANIFEST.json').write_text(json.dumps({p.name:dict(bytes=p.stat().st_size,sha256=sha(p)) for p in (raw,receipt)}))
        def rejected():
            try:build_check(out)
            except AssertionError:return
            raise AssertionError('mixed/tampered build accepted')
        setup();assert build_check(out)['status']=='PASS'
        raw.write_bytes(b'changed raw payload');rejected()
        setup(freeze='0'*64);rejected()
        setup(state='FAILED');rejected()
    print('Build hash/receipt binding positive and negative tests PASS')

if __name__=='__main__':main()
