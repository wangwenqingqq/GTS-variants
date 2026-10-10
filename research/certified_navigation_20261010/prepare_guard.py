#!/usr/bin/env python3
"""Reuse the existing two-sided-starttime GPU guard with bounded observer calls."""
import argparse
from pathlib import Path
from audit import sha,save
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent.parent

def prepare(out):
    out.mkdir(parents=True,exist_ok=False)
    guard=ROOT/'artifacts/external_closure/static_guard.py'
    boundary=ROOT/'artifacts/unified_target_workflow/run.py'
    source=boundary.read_text();a=source.index('def outside_repo(');b=source.index('\n\ndef prepare(',a)
    text=guard.read_text().replace('from common import outside_repo',
        'REPO = Path(__file__).resolve().parent\n\n'+source[a:b])
    old="['nvidia-smi', '-i', gpu, field, '--format=csv,noheader'], text=True)"
    if text.count(old)!=1:raise ValueError('guard source drift')
    text=text.replace(old,old[:-1]+', timeout=10)')
    (out/'guard.py').write_text(text)
    save(out/'GUARD_IDENTITY.json',dict(parent_guard_sha256=sha(guard),boundary_sha256=sha(boundary),
         generated_guard_sha256=sha(out/'guard.py'),changes=['inline existing private-work boundary','observer timeout=10 seconds']))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('out',type=Path);prepare(p.parse_args().out)
