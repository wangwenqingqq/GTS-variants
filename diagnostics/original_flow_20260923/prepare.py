#!/usr/bin/env python3
"""Copy pinned, unmodified author sources and already-validated Words fixtures."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

HERE=Path(__file__).resolve().parent


def prepare(source,fixtures,out):
    pins=json.loads((HERE.parent/'original_tree_redundancy/SOURCE_PINS.json').read_text())['sha256']
    pins={k:v for k,v in pins.items() if k.startswith('GTS/')}
    for name,digest in pins.items():
        assert hashlib.sha256((source/name).read_bytes()).hexdigest()==digest,name
    meta=json.loads((fixtures/'manifest.json').read_text())
    for name,digest in meta['file_sha256'].items():
        assert hashlib.sha256((fixtures/name).read_bytes()).hexdigest()==digest,name
    ids=(fixtures/'words_2000.qid').read_text().splitlines()
    assert ids[0]=='32' and len(ids)==33
    out.mkdir()
    for sub in ['bin','logs','runs']:(out/sub).mkdir()
    for name in pins:
        dest=out/'source'/name.removeprefix('GTS/');dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source/name,dest)
    shutil.copytree(fixtures,out/'fixtures')
    (out/'fixtures/words_2000_long.qid').write_text('4096\n'+'\n'.join(ids[1:]*128)+'\n')
    (out/'fixtures/words_2000_long.updates').write_text('4096\n'+''.join('2 '+q+'\n' for q in ids[1:]*128))
    (out/'source_pins.json').write_text(json.dumps(pins,indent=2)+'\n')
    print('Prepared byte-identical source and 4096-query fixtures; no GPU calls')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for arg in ['source','fixtures','out']:p.add_argument(arg,type=Path)
    a=p.parse_args();prepare(a.source,a.fixtures,a.out)
