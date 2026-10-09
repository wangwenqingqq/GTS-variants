#!/usr/bin/env python3
"""Small portable parser regression; no CUDA initialization or private dataset required."""
import argparse
import json
from pathlib import Path
import struct
import subprocess

if not __debug__:
    raise RuntimeError('Assertions must remain enabled')
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--binary',type=Path,required=True)
p.add_argument('--work',type=Path,required=True)
a=p.parse_args();a.work.mkdir(parents=True,exist_ok=False);binary=a.binary.resolve();passed=[]
for n,d in ((255,960),(1025,960),(1000,128)):
    path=a.work/f'{n}_{d}.f32bin';path.write_bytes(struct.pack('<iii',d,n,2)+bytes(n*d*4))
    events=a.work/f'{n}.events';events.write_text('3\n2 0\n0 0\n3 0\n')
    r=subprocess.run([str(binary),str(path),str(events),'0.705625057220459'],capture_output=True,text=True)
    assert r.returncode==0,r.stderr;passed.append(f'valid_{n}_{d}')
raw=(a.work/'255_960.f32bin').read_bytes();events='3\n2 0\n0 0\n3 0\n'
for label,body,event in [
    ('nan',raw[:12]+struct.pack('<f',float('nan'))+raw[16:],events),
    ('trailing',raw+b'x',events),('short',raw[:-1],events),
    ('bad_rank',raw,'2\n1 255\n3 0\n'),('bad_physical',raw,'1\n3 255\n'),
    ('empty_events',raw,'0\n'),('huge_truncated',struct.pack('<iii',960,1000000,2),events)]:
    path=a.work/f'{label}.f32bin';path.write_bytes(body);ops=a.work/f'{label}.events';ops.write_text(event)
    r=subprocess.run([str(binary),str(path),str(ops),'0.7'],capture_output=True,text=True)
    assert r.returncode==1 and 'FAIL:' in r.stderr,(label,r.stderr);passed.append(label)
result={'passed':passed,'cuda_used':False,'scope':'host rank replay, shape arithmetic and parser only'}
(a.work/'results.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS',len(passed),'parser cases')
