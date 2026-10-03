#!/usr/bin/env python3
"""Separate native-output validation replay; retained bins do not replace timing."""
import hashlib
import json
from pathlib import Path
import struct
import sys

import verify_outputs

OUT = Path(sys.argv[sys.argv.index('--out')+1])
records = []


def check_and_retain(ids, distances, reference, data, k, allow_missing=False):
    q = verify_outputs.quality(ids, distances, reference, data, k, allow_missing)
    raw = struct.pack('<iiii',len(data),data.shape[1],len(ids),k)+ids.astype('<i4').tobytes()+distances.astype('<f4').tobytes()
    path = OUT.with_suffix(f'.row{len(records)}.bin')
    with path.open('xb') as f: f.write(raw)
    records.append({'result':path.name,'sha256':hashlib.sha256(raw).hexdigest(),
                    'Q':len(ids),'K':k,'quality':q})
    return q


if __name__ == '__main__':
    verify_outputs.native_ivf.quality = check_and_retain
    verify_outputs.native_ivf.main()
    assert all(r['quality']['distance_tolerance_pass'] for r in records)
    OUT.with_suffix('.validation.json').write_text(json.dumps({
        'scope':'Separate replay with fixed frozen configurations; not the six original formal outputs/times',
        'outputs':records},indent=2)+'\n')
