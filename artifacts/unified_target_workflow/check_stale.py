#!/usr/bin/env python3
"""Verify fail-closed pointer/PAR/mirror publication guards using real metadata corruption."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

if not __debug__:
    raise RuntimeError("Assertions must remain enabled; Python -O is unsupported")

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--work',type=Path,required=True)
p.add_argument('--case',type=Path,required=True)
p.add_argument('--binary',type=Path,required=True)
p.add_argument('--guard',type=Path,required=True)
p.add_argument('--gpu',required=True)
p.add_argument('--numa-node',type=int,required=True)
a=p.parse_args();results=[]
for flag,mode in [('TARGET_STALE','NATIVE'),('PAR_STALE','PAR_STRONG'),('KNN_STALE','PAR_STRONG')]:
    out=a.work/'outputs'/flag;receipt=a.work/'runs'/flag
    args=[sys.executable,str(a.guard.resolve()),'--gpu',a.gpu,'--numa-node',str(a.numa_node),
          '--output',str(receipt),'--',str(a.binary.resolve()),str(a.case/'data.f32bin'),
          str(a.case/'events.txt'),'2','0.705625057220459',str(out),'8']
    r=subprocess.run(args,env={**os.environ,flag:'1','REGION_MODE':mode,'KNN_MODE':'BOUND'},capture_output=True,text=True)
    (a.work/f'{flag}.outer.log').write_text(r.stdout+r.stderr)
    recorded=json.loads((receipt/'receipt.json').read_text())
    assert r.returncode==1 and recorded['exit_code']==1 and recorded['stop_reason'] is None
    assert not any(x['foreign'] for x in json.loads((receipt/'checks.json').read_text()))
    assert not json.loads((receipt/'after.json').read_text())['apps']
    assert 'stale' in (receipt/'stderr.log').read_text()
    assert not list(out.parent.glob(out.name+'.*')),'rejected state emitted completed trace outputs'
    results.append(dict(injection=flag,range_mode=mode,expected_rejection=True,target_binary_sha256=recorded['binary_sha256']))
(a.work/'stale.json').write_text(json.dumps(results,indent=2)+'\n')
print('PASS real stale pointer, PAR epoch and kNN mirror epoch rejections')
