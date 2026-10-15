"""Frozen experiment routes;imports never initialize CUDA."""
if not __debug__:raise SystemExit('Mandatory checks require ordinary Python without optimization.')
import importlib.util
import hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
REPO=HERE.parent.parent
PARENT=HERE.parent/'dynamic_query_aware_exact_gpu_20261015'
BASE=HERE.parent/'dynamic_update_critical_path_20261015_recovery_01'
UPDATES=('NATIVE','WAVES','FINAL')
STAGES=('qualification','screen','primary','shapes','calibration','profile')
def module(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def load(p):return json.loads(Path(p).read_text())
def save(p,x):
    with Path(p).open('x') as f:json.dump(x,f,indent=2);f.write('\n')
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(4<<20),b''):h.update(b)
    return h.hexdigest()
old=module('immutable_query_protocol',PARENT/'common.py')
MODES,requests,batches,ends=old.MODES,old.requests,old.batches,old.ends

def jobs(stage):
    if stage=='qualification':
        out=[dict(label=f'{u}_{t}',kind='selftest',update=u,variant='PLAIN',**({} if t=='selftest' else dict(tool=t))) for u in UPDATES for t in ('selftest','memcheck','racecheck','synccheck')]
        out+=[dict(label=f'{u}_full_{op}_{b}',kind='micro',update=u,variant='PLAIN',N=1000000,K=8192,op=op,batch=b,diagnostic=2) for u in UPDATES for op in ('I','D','R') for b in (1,32,512)]
        out+=[dict(label=f'{u}_bounded_W2',kind='service',update=u,variant='PLAIN',mode='S2_STALE',N=4096,diagnostic=2) for u in UPDATES];assert len(out)==42;return out
    if stage in ('screen','primary','calibration'):
        out=[];rounds=2 if stage=='screen' else 6
        for r in range(1,rounds+1):
            order='forward' if r%2 else 'reverse';variants=UPDATES if r%2 else UPDATES[::-1]
            cells=[('D',512)] if stage=='screen' else [(op,b) for op in ('I','D','R') for b in (1,32,512)] if stage=='primary' else [('R',1),('R',512)]
            for op,b in (cells if r%2 else cells[::-1]):
                for u in variants:
                    vv=('PLAIN','MARKED') if stage=='calibration' else ('PLAIN',)
                    # PLAIN calibration observations reuse primary;only MARKED adds a target.
                    vv=('MARKED',) if stage=='calibration' else vv
                    for v in vv:out.append(dict(label=f'r{r}_{u}_{v}_{op}_{b}',kind='micro',update=u,variant=v,N=1000000,K=8192,op=op,batch=b,diagnostic=0,round=r,order=order))
            if stage=='primary':
                systems=('S1','CURRENT','NATIVE','WAVES','FINAL') if r%2 else ('FINAL','WAVES','NATIVE','CURRENT','S1')
                for u in systems:out.append(dict(label=f'r{r}_W2_{u}',kind='service',update=u,variant='PLAIN',mode='S1' if u=='S1' else 'S2_STALE',N=1000000,diagnostic=0,round=r,order=order))
        assert len(out)==dict(screen=6,primary=192,calibration=36)[stage];return out
    if stage=='shapes':
        out=[]
        for r in range(1,7):
            for shape in (('random','localized','chain') if r%2 else ('chain','localized','random')):
                for u in (UPDATES if r%2 else UPDATES[::-1]):out.append(dict(label=f'r{r}_{shape}_{u}',kind='shape',update=u,variant='PLAIN',shape=shape,round=r,order='forward' if r%2 else 'reverse'))
        assert len(out)==54;return out
    assert stage=='profile'
    out=[dict(label=f'nsys_D512_{u}',kind='micro',update=u,variant='MARKED',N=1000000,K=8192,op='D',batch=512,diagnostic=1,tool='nsys') for u in UPDATES]
    out+=[dict(label=f'nsys_W2_{u}',kind='service',update=u,variant='MARKED',mode='S2_STALE',N=1000000,diagnostic=3,tool='nsys') for u in UPDATES]
    out+=[dict(label=f'ncu_query_{u}',kind='service',update=u,variant='PLAIN',mode='S2_STALE',N=1000000,diagnostic=1,tool='ncu') for u in UPDATES]
    out+=[dict(label='ncu_update_FINAL',kind='micro',update='FINAL',variant='PLAIN',N=1000000,K=8192,op='D',batch=512,diagnostic=1,tool='ncu')]
    assert len(out)==10;return out
