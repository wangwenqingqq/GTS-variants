"""Download only small, pinned upstream sources; never execute them or install dependencies."""
if not __debug__:
    raise SystemExit('Mandatory checks require ordinary Python.')
import argparse
import hashlib
import json
from pathlib import Path
import urllib.parse
import urllib.request


def main(out):
    out.mkdir()
    records = json.loads((Path(__file__).parent/'SOURCES.json').read_text())['upstream_inspected']
    for r in records:
        assert urllib.parse.urlsplit(r['url']).netloc == 'raw.githubusercontent.com'
        assert not Path(r['file']).is_absolute() and '..' not in Path(r['file']).parts
        req = urllib.request.Request(r['url'], headers={'User-Agent': 'GTSPP-source-reproduction/1.0'})
        with urllib.request.urlopen(req, timeout=30) as response:
            body = response.read(2_000_001)
        assert len(body) == r['bytes'] <= 2_000_000
        assert hashlib.sha256(body).hexdigest() == r['sha256']
        f = out/r['source']/r['file']
        f.parent.mkdir(parents=True, exist_ok=True)
        with f.open('xb') as stream:
            stream.write(body)
    print('PINNED_SOURCE_FETCH_PASS', len(records), 'files;0 GPU targets')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    main(a.out)
