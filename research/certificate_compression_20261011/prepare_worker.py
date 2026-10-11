#!/usr/bin/env python3
"""Reuse the previously admitted scalar exporter; change only bounded query count to 64."""
import argparse,json,sys,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'region_truth_diagnosis_20261011'))
from prepare_scores import prepare

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('out',type=Path);a=p.parse_args()
    prepare(a.out)
    source=a.out/'compute_scores.cpp';text=source.read_text()
    assert text.count('require(q==8 &&')==1
    source.write_text(text.replace('require(q==8 &&','require(q==64 &&'))
    pin=json.loads((a.out/'SOURCE.json').read_text())
    pin['prior_8_exporter_sha256']=pin['generated_sha256']
    pin['generated_sha256']=hashlib.sha256(source.read_bytes()).hexdigest()
    pin['changes']=['unchanged old scalar score/top-K loop and full score export','bounded 64-query count instead of 8']
    pin['generator_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    (a.out/'SOURCE.json').write_text(json.dumps(pin,indent=2)+'\n')
