#!/usr/bin/env python3
import hashlib
import json
from pathlib import Path
import random
import numpy as np

ROOT=Path(__file__).resolve().parent

def main():
    frozen=ROOT/'FROZEN_CONFIG.json';assert frozen.exists()
    metadata=json.loads((ROOT/'EXCLUSIONS.json').read_text())
    for dataset,seed in (('GIST',2026100317),('Deep',2026100318)):
        path=ROOT/f'fixtures/{dataset}_excluded.i32'
        assert hashlib.sha256(path.read_bytes()).hexdigest()==metadata[dataset]['excluded_sha256']
        excluded=set(map(int,np.fromfile(path,dtype='<i4')));chosen=[];rng=random.Random(seed)
        while len(chosen)<256:
            q=rng.randrange(1000000)
            if q not in excluded and q not in chosen:chosen.append(q)
        assert not (set(chosen)&excluded)
        target=ROOT/f'fixtures/{dataset}_final256.qid';assert not target.exists()
        target.write_text('256\n'+''.join(f'{q}\n' for q in chosen))
        metadata[dataset].update(final_file=target.name,final_seed=seed,
            final_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),collision_count=0,
            frozen_config_sha256=hashlib.sha256(frozen.read_bytes()).hexdigest())
    (ROOT/'QUERY_SETS.json').write_text(json.dumps(metadata,indent=2)+'\n')
    print('NEW FINAL QUERIES FROZEN',flush=True)

if __name__=='__main__':main()
