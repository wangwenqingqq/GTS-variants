#!/usr/bin/env python3
"""Bounded correctness/sanitizer admission only; never emits performance claims."""
import argparse
import csv
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
    check = validate.check(data,events,prefix,radius,k,expected_mode=(int(range_mode=='PAR_STRONG'),knn))
    check['coverage']=validate.coverage(data,events,a.work/'runs'/label/'stdout.log')
    check.update(label=label,binary_sha256=sha(a.binary),tool=tool,expected_mode_checked=True,
                 data_sha256=sha(data),events_sha256=sha(events))
    (a.work/'runs'/label/'QUALITY.json').write_text(json.dumps(check,indent=2)+'\n')
    print('PASS',label,flush=True)
    return check


def equal_outputs(a, labels):
    for suffix in ('.ids.i32','.dist.f32','.queries.csv'):
        first=(a.work/'outputs'/f'{labels[0]}{suffix}').read_bytes()
        assert all((a.work/'outputs'/f'{label}{suffix}').read_bytes()==first for label in labels[1:]), (labels,'ordered cross-mode output',suffix)
    # ACK/rebuild times are observations, not deterministic output semantics.
    states=[]
    for label in labels:
        with (a.work/'outputs'/f'{label}.ops.csv').open() as f:
            states.append([tuple(int(row[key]) for key in ('step','flag','base_before','buffer_before','base_after','buffer_after')) for row in csv.DictReader(f)])
    assert all(state==states[0] for state in states[1:]), (labels,'cross-mode operation states')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('stage',choices=('small','transition','sanitize','extreme','legacy32','growth','million'))
    p.add_argument('--work',type=Path,required=True)
    p.add_argument('--cases',type=Path,required=True)
    p.add_argument('--binary',type=Path,required=True)
    p.add_argument('--guard',type=Path,required=True)
    p.add_argument('--gpu',required=True)
    p.add_argument('--numa-node',type=int,required=True)
    p.add_argument('--legacy',type=Path)
    p.add_argument('--data',type=Path,help='registered original FP32 GIST binary (million stage)')
    a=p.parse_args()
    if a.stage in ('small','legacy32','growth') and a.legacy is None:p.error('--legacy is required for this stage')
    if a.stage=='million' and a.data is None:p.error('--data is required for million')
    a.binary=a.binary.resolve();a.guard=a.guard.resolve()
    for d in ('outputs','runs'):(a.work/d).mkdir(parents=True,exist_ok=True)
    radius=0.705625057220459
    rows=[]
    if a.stage=='small':
        specs=[(f'gist{n}',a.cases/f'gist{n}',radius,8) for n in (255,256,257,1023,1024,1025,4096)]
        specs += [(f'edge{n}',a.cases/f'edge{n}',radius,8) for n in (255,256,257,1023,1024,1025)]
        specs += [(f'legacy_{n}',a.legacy/n,0,8) for n in ('boundary0','ties8','sparse8')]
        for name,path,radius,k in specs:
            data=path/('data.txt' if name.startswith('legacy') else 'data.f32bin')
            for mode in 'ABC':rows.append(run(a,name,data,path/'events.txt',radius,k,mode))
            equal_outputs(a,[f'{name}_{mode}' for mode in 'ABC'])
    elif a.stage=='transition':
        path=a.cases/'gist65536'
        for mode in 'ABC':rows.append(run(a,'gist65536',path/'data.f32bin',path/'events.txt',radius,8,mode))
        equal_outputs(a,[f'gist65536_{mode}' for mode in 'ABC'])
    elif a.stage=='extreme':
        path=a.cases/'extreme255'
        for mode in 'ABC':rows.append(run(a,'extreme255',path/'data.f32bin',path/'events.txt',float(validate.np.finfo(validate.np.float32).max),8,mode))
        equal_outputs(a,[f'extreme255_{mode}' for mode in 'ABC'])
    elif a.stage=='legacy32':
        for name in ('boundary10000','ties32','sparse32'):
            path=a.legacy/name
            case_radius=10000 if name=='boundary10000' else 0
            for mode in 'ABC':rows.append(run(a,f'legacy_{name}',path/'data.txt',path/'events.txt',case_radius,32,mode))
            equal_outputs(a,[f'legacy_{name}_{mode}' for mode in 'ABC'])
    elif a.stage=='growth':
        for mode in 'ABC':rows.append(run(a,'growth1000to2010',a.legacy/'ties8'/'data.txt',a.cases/'growth'/'events.txt',0,8,mode))
        equal_outputs(a,[f'growth1000to2010_{mode}' for mode in 'ABC'])
    elif a.stage=='million':
        validate.verify_target_data(a.data)
        for mode in 'ABC':rows.append(run(a,'million',a.data,a.cases/'million'/'events.txt',radius,8,mode))
        rows.append(run(a,'million',a.data,a.cases/'million'/'events.txt',radius,8,'C','memcheck'))
        equal_outputs(a,['million_A','million_B','million_C','million_C_memcheck'])
    else:
        path=a.cases/'edge257'
        for tool in ('memcheck','racecheck','synccheck'):
            rows.append(run(a,'edge257',path/'data.f32bin',path/'events.txt',radius,8,'C',tool))
    (a.work/f'{a.stage}.json').write_text(json.dumps(rows,indent=2)+'\n')
