#!/usr/bin/env python3
"""Bounded correctness/sanitizer admission only; never emits performance claims."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import shutil
import sys

if not __debug__:
    raise RuntimeError("Assertions must remain enabled; Python -O is unsupported")
import validate
import hashlib

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(8<<20),b''):h.update(chunk)
    return h.hexdigest()


def run(a, name, data, events, radius, k, mode, tool=None):
    range_mode, knn = {'A': ('NATIVE','FULL'), 'B': ('PAR_STRONG','FULL'), 'C': ('PAR_STRONG','BOUND')}[mode]
    label = f'{name}_{mode}' + (f'_{tool}' if tool else '')
    prefix = a.work/'outputs'/label
    command = [str(a.binary), str(data), str(events), '2', str(radius), str(prefix), str(k)]
    if tool:
        command = [str(Path(shutil.which('compute-sanitizer')).resolve()), '--tool', tool, '--error-exitcode', '86', *command]
    guarded = [sys.executable, str(a.guard), '--gpu', a.gpu, '--numa-node', str(a.numa_node),
               '--output', str(a.work/'runs'/label), '--', *command]
    env = {**os.environ,'REGION_MODE':range_mode,'KNN_MODE':knn,'U10_TREE_AUDIT':'1'}
    result = subprocess.run(guarded,env=env,text=True,capture_output=True)
    (a.work/f'{label}.outer.log').write_text(result.stdout+result.stderr)
    assert result.returncode==0, (label,result.stdout,result.stderr)
    receipt = json.loads((a.work/'runs'/label/'receipt.json').read_text())
    assert receipt['runtime_valid']
    # Sanitizer receipt pins the tool; its complete command additionally records target binary.
    if not tool:
        assert receipt['binary_sha256']==sha(a.binary)
    check = validate.check(data,events,prefix,radius,k)
    check['coverage']=validate.coverage(data,events,a.work/'runs'/label/'stdout.log')
    check.update(label=label,binary_sha256=sha(a.binary),tool=tool,
                 data_sha256=sha(data),events_sha256=sha(events))
    (a.work/'runs'/label/'QUALITY.json').write_text(json.dumps(check,indent=2)+'\n')
    print('PASS',label,flush=True)
    return check


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('stage',choices=('small','transition','sanitize','extreme'))
    p.add_argument('--work',type=Path,required=True)
    p.add_argument('--cases',type=Path,required=True)
    p.add_argument('--binary',type=Path,required=True)
    p.add_argument('--guard',type=Path,required=True)
    p.add_argument('--gpu',required=True)
    p.add_argument('--numa-node',type=int,required=True)
    p.add_argument('--legacy',type=Path)
    a=p.parse_args()
    a.binary=a.binary.resolve();a.guard=a.guard.resolve()
    for d in ('outputs','runs'):(a.work/d).mkdir(parents=True,exist_ok=True)
    radius=0.705625057220459
    rows=[]
    if a.stage=='small':
        specs=[(f'gist{n}',a.cases/f'gist{n}',radius,8) for n in (255,256,257,1023,1024,1025,4096)]
        specs += [(f'edge{n}',a.cases/f'edge{n}',radius,8) for n in (255,256,257,1023,1024,1025)]
        if a.legacy:
            specs += [(f'legacy_{n}',a.legacy/n,0,8) for n in ('boundary0','ties8','sparse8')]
        for name,path,radius,k in specs:
            data=path/('data.txt' if name.startswith('legacy') else 'data.f32bin')
            for mode in 'ABC':rows.append(run(a,name,data,path/'events.txt',radius,k,mode))
            for suffix in ('.ids.i32','.dist.f32','.queries.csv'):
                assert (a.work/'outputs'/f'{name}_A{suffix}').read_bytes()==(a.work/'outputs'/f'{name}_B{suffix}').read_bytes()==(a.work/'outputs'/f'{name}_C{suffix}').read_bytes(),(name,'ordered cross-mode output')
    elif a.stage=='transition':
        path=a.cases/'gist65536'
        for mode in 'ABC':rows.append(run(a,'gist65536',path/'data.f32bin',path/'events.txt',radius,8,mode))
        for suffix in ('.ids.i32','.dist.f32','.queries.csv'):
            assert (a.work/'outputs'/f'gist65536_A{suffix}').read_bytes()==(a.work/'outputs'/f'gist65536_B{suffix}').read_bytes()==(a.work/'outputs'/f'gist65536_C{suffix}').read_bytes()
    elif a.stage=='extreme':
        path=a.cases/'extreme255'
        for mode in 'ABC':rows.append(run(a,'extreme255',path/'data.f32bin',path/'events.txt',float(validate.np.finfo(validate.np.float32).max),8,mode))
    else:
        path=a.cases/'edge257'
        for tool in ('memcheck','racecheck','synccheck'):
            rows.append(run(a,'edge257',path/'data.f32bin',path/'events.txt',radius,8,'C',tool))
    (a.work/f'{a.stage}.json').write_text(json.dumps(rows,indent=2)+'\n')
