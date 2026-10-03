#!/usr/bin/env python3
"""Create final queries only after the development parameter freeze exists."""
import hashlib
import json
from pathlib import Path
import random

ROOT=Path(__file__).resolve().parent
DIAG=ROOT.parent

def qids(path):
    values=list(map(int,path.read_text().split()))
    assert values[0]==len(values)-1
    return values[1:]

def main():
    frozen=ROOT/'FROZEN_CONFIG.json';assert frozen.is_file()
    metadata=json.loads((ROOT/'QUERY_SETS.json').read_text())
    for dataset,seed in (('GIST',2026100303),('Deep',2026100304)):
        previous=metadata[dataset]['previous_files']
        forbidden=set()
        for name,digest in previous.items():
            path=DIAG.parent/name
            assert hashlib.sha256(path.read_bytes()).hexdigest()==digest,name
            forbidden.update(qids(path))
        forbidden.update(qids(ROOT/metadata[dataset]['development_file']))
        rng=random.Random(seed);chosen=[]
        while len(chosen)<256:
            q=rng.randrange(1_000_000)
            if q not in forbidden:
                chosen.append(q);forbidden.add(q)
        target=ROOT/'fixtures'/f'{dataset}_final256.qid'
        assert not target.exists()
        target.write_text('256\n'+''.join(f'{q}\n' for q in chosen))
        metadata[dataset].update({'final_status':'frozen_after_development','final_seed':seed,
            'final_file':str(target.relative_to(ROOT)),'final_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
            'frozen_config_sha256':hashlib.sha256(frozen.read_bytes()).hexdigest(),
            'intersection_with_previous_and_development':0})
    (ROOT/'QUERY_SETS.json').write_text(json.dumps(metadata,indent=2)+'\n')

if __name__=='__main__':main()
