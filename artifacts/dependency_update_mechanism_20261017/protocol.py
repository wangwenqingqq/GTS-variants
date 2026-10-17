"""Fixed attribution matrix;imports do not initialize CUDA."""
if not __debug__:raise SystemExit('Mandatory checks require ordinary Python.')
import hashlib,json,importlib.util
from pathlib import Path
HERE=Path(__file__).resolve().parent;REPO=HERE.parent.parent
VARIANTS=('NATIVE','WAVES','GENERIC_WAVES','GENERIC_DSE','TAIL_GENERIC','TAIL_CUSTOM')
FAMILIES=('W2_ORIGINAL','UNIFORM_LIVE','MIX_RECENT8','RECENT4')
SEED=2026101701
STAGES=('qualification','primary','profile')
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for block in iter(lambda:f.read(4<<20),b''):h.update(block)
    return h.hexdigest()
def load(p):return json.loads(Path(p).read_text())
def save(p,x):
    with Path(p).open('x') as f:json.dump(x,f,indent=2);f.write('\n')
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def ends(n,micro=False):return [0,2048,4096,6144,8192] if micro else [0,n//20,n//5,n*35//100,n//2]
def batches(n,b,micro=False):
    result=[];at=0
    for phase,stop in enumerate(ends(n,micro)):
        while at<stop:
            count=min(b,stop-at);result.append(dict(phase=phase,begin=at,count=count));at+=count
    return result
def job(label,v,**kw):return dict(label=label,variant=v,**kw)
def jobs(stage):
    out=[]
    if stage=='qualification':
        for v in VARIANTS:
            for tool in ('plain','memcheck','initcheck','racecheck','synccheck'):
                out.append(job(f'{v}_{tool}',v,kind='selftest',tool=tool,trace=0))
        for n in (4096,1000000):
            for f in FAMILIES:
                for v in VARIANTS:out.append(job(f'{v}_N{n}_{f}',v,kind='service',N=n,family=f,batch=512,micro=False,diagnostic=2,trace=0))
        for b in (1,32,512):
            for v in VARIANTS:out.append(job(f'{v}_micro_B{b}',v,kind='service',N=1000000,family='W2_ORIGINAL',batch=b,micro=True,diagnostic=2,trace=0))
        assert len(out)==96
    elif stage=='primary':
        for r in range(1,7):
            vs=VARIANTS if r%2 else VARIANTS[::-1]
            cells=[(f,512,False) for f in FAMILIES]+[('W2_ORIGINAL',b,True) for b in (1,32,512)]
            for f,b,micro in cells if r%2 else cells[::-1]:
                for v in vs:out.append(job(f'r{r}_{v}_{f}_B{b}_'+('micro' if micro else 'mixed'),v,kind='service',N=1000000,family=f,batch=b,micro=micro,diagnostic=0,trace=0,round=r,order='forward' if r%2 else 'reverse'))
        assert len(out)==252
    else:
        assert stage=='profile'
        for f in ('W2_ORIGINAL','RECENT4'):
            for v in VARIANTS:out.append(job(f'nsys_{v}_{f}',v,kind='service',N=1000000,family=f,batch=512,micro=False,diagnostic=3,trace=1,tool='nsys'))
            for v in VARIANTS[2:]:out.append(job(f'ncu_{v}_{f}',v,kind='service',N=1000000,family=f,batch=512,micro=False,diagnostic=3,trace=1,tool='ncu'))
        assert len(out)==20
    return out
