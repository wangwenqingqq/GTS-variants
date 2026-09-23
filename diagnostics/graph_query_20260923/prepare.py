#!/usr/bin/env python3
"""Prepare a fresh private experiment root from verified external sources/data."""
import argparse
import hashlib
import json
from pathlib import Path
import random
import shutil
HERE=Path(__file__).resolve().parent


def prepare(source,fixtures,out):
    pins=json.loads((HERE.parent/'original_tree_redundancy/SOURCE_PINS.json').read_text())['sha256']
    pins={n:h for n,h in pins.items() if n.startswith('GTS/')}
    for n,h in pins.items():assert hashlib.sha256((source/n).read_bytes()).hexdigest()==h,n
    manifest=json.loads((fixtures/'manifest.json').read_text())
    for n,h in manifest['file_sha256'].items():assert hashlib.sha256((fixtures/n).read_bytes()).hexdigest()==h,n
    out.mkdir()
    for name in ['bin','logs','runs']:(out/name).mkdir()
    for n in pins:
        dest=out/'source'/n.removeprefix('GTS/');dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source/n,dest)
    shutil.copytree(fixtures,out/'fixtures')
    for name in ['graph_bench.cu','run.py']:shutil.copy2(HERE/name,out/name)
    ids=list(map(int,(fixtures/'words_2000.qid').read_text().split()))[1:]
    assert len(ids)==32
    ids+=random.Random(20260923).sample(range(2000),32);random.Random(935).shuffle(ids)
    (out/'fixtures/queries.qid').write_text('64\n'+'\n'.join(map(str,ids))+'\n')
    (out/'source_pins.json').write_text(json.dumps(pins,indent=2)+'\n')
    print('Prepared verified originals, deterministic queries and experiment files; no GPU calls')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for arg in ['source','fixtures','out']:p.add_argument(arg,type=Path)
    a=p.parse_args();prepare(a.source,a.fixtures,a.out)
