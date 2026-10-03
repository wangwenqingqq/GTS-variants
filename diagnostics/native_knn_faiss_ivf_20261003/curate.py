#!/usr/bin/env python3
"""Whitelist/redact a private collection copy; never edit the source of truth."""
import argparse
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent


def digest(data): return hashlib.sha256(data).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--raw', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args(); a.out.mkdir(exist_ok=False)
    selected = json.loads((a.raw/'CONTRACT.json').read_text())['gpu']['uuid']
    rules = [
        (r'/home/data/[^/\s"]+/tmp/gts_arithmetic_path_boundary_20260928/data', '$DATA_ROOT'),
        (r'/home/data/[^/\s"]+/tmp/gts_p6_cagra_ivf_20261002/faiss_source_venv', '$FAISS_ENV_ROOT'),
        (r'/home/data/[^/\s"]+/tmp/gts_native_knn_faiss_ivf_20261003', '$REMOTE_ROOT'),
        (r'/home/data/[^/\s"]+/[^\s"\n]*', '$PRIVATE_REMOTE_PATH'),
        (r'/Users/[^/\s"]+/[^\s"\n]*', '$PRIVATE_LOCAL_PATH'),
        (re.escape(selected), '$SELECTED_GPU_UUID'),
        (r'GPU-[0-9a-f-]{36}', '$OTHER_GPU_UUID'),
        (r'pro6000-[0-9]+(?:-[A-Za-z0-9_]+)?', 'eight-GPU Blackwell host')]
    manifest = {'policy': 'Whitelisted text evidence; private raw collection preserved unchanged',
                'files': {}, 'sources': {}}
    run_names = {'before.json','after.json','receipt.json','command.json','checks.json','stdout.log','stderr.log','gpu.csv'}
    for path in sorted(a.raw.rglob('*')):
        if not path.is_file(): continue
        rel = path.relative_to(a.raw)
        if path.suffix in ('.py','.cu') and len(rel.parts) == 1:
            delivery = HERE/path.name
            manifest['sources'][str(rel)] = {'collection_sha256': digest(path.read_bytes()),
                'delivery_sha256': digest(delivery.read_bytes()) if delivery.exists() else None}
            continue
        keep = ((len(rel.parts) == 1 and path.suffix in ('.json','.csv','.log','.txt')) or
                (rel.parts[0] == 'runs' and path.name in run_names) or
                (rel.parts[0] == 'fixtures' and path.suffix == '.qid') or
                str(rel) in ('gts/adaptation.patch','gts/SOURCE_PINS.json'))
        if not keep: continue
        raw = path.read_bytes(); text = raw.decode('utf-8')
        if path.name == 'PREFLIGHT.json':
            data = json.loads(text)
            data['apps'] = 'Pre-existing foreign service on GPU0; selected GPU7 clear at admission; no service changes.'
            text = json.dumps(data,indent=2)+'\n'
        if path.name == 'CONTRACT.json':
            data = json.loads(text)
            data['gpu']['do_not_touch'] = 'All foreign jobs and GPU0 service; no clock/power changes'
            text = json.dumps(data,indent=2)+'\n'
        for pattern, replacement in rules: text = re.sub(pattern,lambda _:replacement,text)
        assert not re.search(r'/home/(?:data|[^/ ]+)/|/Users/[^/ ]+/|GPU-[0-9a-f-]{36}',text),rel
        if path.suffix == '.json': json.loads(text)
        target = a.out/rel; target.parent.mkdir(parents=True,exist_ok=True)
        curated = text.encode(); target.write_bytes(curated)
        manifest['files'][str(rel)] = {'collection_sha256': digest(raw), 'curated_sha256': digest(curated),
                                      'collection_bytes': len(raw), 'curated_bytes': len(curated)}
    (a.out/'COLLECTION_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
    # Only replace this task's public staging contract, not the private frozen file.
    (HERE/'CONTRACT.json').write_bytes((a.out/'CONTRACT.json').read_bytes())
    print(f'PASS curated {len(manifest["files"])} text artifacts; source identities retained')


if __name__ == '__main__': main()
